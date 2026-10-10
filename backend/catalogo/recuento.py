"""Carga posterior del recuento en productos ya importados (T-OP.5,
plan.md 11.3).

Operacion de una sola vez, como la importacion: sin pantalla ni caso de
uso. Tres pasos:
  1. escribir_planilla_importados(): la planilla de los productos del
     catalogo antiguo que ya estan en el sistema.
  2. construir_plan(): sin escribir nada, decide que se cargaria y
     calcula la huella, que incluye las existencias ACTUALES.
  3. aplicar(): solo con la huella aprobada; todo o nada.

No duplica: un producto que ya tiene un AJUSTE «Carga inicial» se salta.
"""

import csv
import hashlib
import json
from dataclasses import dataclass, field

from django.db import connection, transaction

from catalogo.importacion import (
    MOTIVO_CARGA_INICIAL,
    HuellaNoCoincide,
    _leer_csv,
    normalizar,
)
from catalogo.models import Producto
from inventario.models import MovimientoStock, TipoMovimiento
from inventario.services import ajustar_existencias

CABECERA = ["id_antiguo", "nombre", "categoria", "existencias_contadas", "meses_garantia"]


def _productos_del_catalogo_antiguo(productos_csv):
    """{id_antiguo: Producto} de las filas del CSV antiguo que ya estan en
    el sistema, buscadas por nombre (la importacion conserva el nombre)."""
    nombres = {(f.get("nombre") or "").strip(): f["id"].strip() for f in _leer_csv(productos_csv)}
    por_nombre = {normalizar(p.nombre): p for p in Producto.objects.select_related("categoria")}
    return {
        id_antiguo: por_nombre[normalizar(nombre)]
        for nombre, id_antiguo in nombres.items()
        if normalizar(nombre) in por_nombre
    }, {id_antiguo: nombre for nombre, id_antiguo in nombres.items()}


def escribir_planilla_importados(productos_csv, ruta):
    """La planilla para el recuento, con las columnas vacias por rellenar."""
    importados, _ = _productos_del_catalogo_antiguo(productos_csv)
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["fecha_del_recuento", ""])
        escritor.writerow(CABECERA)
        for id_antiguo in sorted(importados, key=lambda i: int(i) if i.isdigit() else 0):
            p = importados[id_antiguo]
            escritor.writerow([id_antiguo, p.nombre, p.categoria.nombre, "", ""])
    return len(importados)


@dataclass
class PlanRecuento:
    ajustes: list = field(default_factory=list)  # (producto, id_antiguo, actual, contado)
    meses: list = field(default_factory=list)  # (producto, id_antiguo, actual, nuevo)
    ya_cargados: list = field(default_factory=list)
    sin_diferencia: list = field(default_factory=list)
    sin_contar: list = field(default_factory=list)
    invalidas: list = field(default_factory=list)  # (id, nombre, motivo)
    fecha: str = ""
    huella: str = ""


def _entero_no_negativo(texto):
    texto = (texto or "").strip()
    if texto == "":
        return None, None
    if texto.isascii() and texto.isdigit():
        return int(texto), None
    return None, f"«{texto}» no es un entero no negativo"


def construir_plan(productos_csv, planilla):
    """Decide que se cargaria, sin escribir nada."""
    plan = PlanRecuento()
    importados, nombre_antiguo = _productos_del_catalogo_antiguo(productos_csv)
    ya_tienen = set(
        MovimientoStock.objects.filter(tipo=TipoMovimiento.AJUSTE, motivo=MOTIVO_CARGA_INICIAL)
        .values_list("producto_id", flat=True)
    )

    with open(planilla, encoding="utf-8-sig", newline="") as archivo:
        lineas = list(csv.reader(archivo))
    if lineas and lineas[0] and lineas[0][0].strip() == "fecha_del_recuento":
        plan.fecha = (lineas[0][1] if len(lineas[0]) > 1 else "").strip()
        lineas = lineas[1:]
    cabecera = [c.strip() for c in lineas[0]] if lineas else []
    if cabecera[:4] != CABECERA[:4]:
        raise ValueError("La planilla no tiene la cabecera esperada: " + ",".join(CABECERA))
    con_meses = len(cabecera) >= 5 and cabecera[4] == "meses_garantia"

    for fila in lineas[1:]:
        if not any(c.strip() for c in fila):
            continue
        fila = [c.strip() for c in (fila + [""] * 5)[:5]]
        id_antiguo, nombre, _, texto_existencias, texto_meses = fila
        if id_antiguo not in nombre_antiguo:
            plan.invalidas.append((id_antiguo, nombre, "el id_antiguo no está en productos.csv"))
            continue
        if normalizar(nombre) != normalizar(nombre_antiguo[id_antiguo]):
            plan.invalidas.append(
                (id_antiguo, nombre, f"el nombre no corresponde a «{nombre_antiguo[id_antiguo]}»: ¿planilla desordenada?")
            )
            continue
        producto = importados.get(id_antiguo)
        if producto is None:
            plan.invalidas.append((id_antiguo, nombre, "el producto no está en el sistema"))
            continue

        contado, error = _entero_no_negativo(texto_existencias)
        meses, error_meses = _entero_no_negativo(texto_meses) if con_meses else (None, None)
        if error or error_meses:
            plan.invalidas.append((id_antiguo, nombre, "; ".join(e for e in (error, error_meses) if e)))
            continue

        if contado is None:
            plan.sin_contar.append((id_antiguo, producto.nombre))
        elif producto.pk in ya_tienen:
            plan.ya_cargados.append((id_antiguo, producto.nombre))
        elif contado == producto.stock:
            plan.sin_diferencia.append((id_antiguo, producto.nombre))
        else:
            plan.ajustes.append((producto, id_antiguo, producto.stock, contado))

        if meses is not None and meses != producto.meses_garantia:
            plan.meses.append((producto, id_antiguo, producto.meses_garantia, meses))

    plan.huella = calcular_huella(plan)
    return plan


def calcular_huella(plan):
    """Incluye las existencias ACTUALES: si se vende algo despues del
    informe, la diferencia aprobada ya no seria la que se registra."""
    datos = {
        "ajustes": sorted([p.pk, actual, contado] for p, _, actual, contado in plan.ajustes),
        "meses": sorted([p.pk, actual, nuevo] for p, _, actual, nuevo in plan.meses),
    }
    canonico = json.dumps(datos, sort_keys=True)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:16]


def aplicar(plan, *, huella, usuario):
    """Ajustes «Carga inicial» y meses de garantia. Todo o nada."""
    if huella != plan.huella:
        raise HuellaNoCoincide(
            f"La huella indicada ({huella}) no es la del plan actual ({plan.huella}). "
            "Algo cambió desde el informe: vuelva a generarlo y apruébelo."
        )
    with transaction.atomic():
        for producto, _, _, contado in plan.ajustes:
            ajustar_existencias(
                producto_id=producto.pk,
                cantidad_real=contado,
                motivo=MOTIVO_CARGA_INICIAL,
                usuario=usuario,
            )
        for producto, _, _, nuevo in plan.meses:
            producto.meses_garantia = nuevo
            producto.save(update_fields=["meses_garantia", "actualizado_en"])
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE catalogo_producto, inventario_movimientostock")


def informe(plan, *, fecha_de_ejecucion=None):
    lineas = ["INFORME DE CARGA DEL RECUENTO («Carga inicial»)", "=" * 47, ""]
    lineas.append(
        f"Fecha del recuento: {plan.fecha or '(SIN FECHA)'}"
        + (f" · fecha de esta ejecución: {fecha_de_ejecucion}" if fecha_de_ejecucion else "")
    )
    lineas.append("")
    lineas.append(f"Ajustes que se registrarían: {len(plan.ajustes)}")
    lineas += [f"  - [{i}] {p.nombre}: {actual} -> {contado}" for p, i, actual, contado in plan.ajustes]
    lineas.append(f"Meses de garantía que cambiarían: {len(plan.meses)}")
    lineas += [f"  - [{i}] {p.nombre}: {actual} -> {nuevo} meses" for p, i, actual, nuevo in plan.meses]
    lineas.append(f"Ya cargados antes (se saltan): {len(plan.ya_cargados)}")
    lineas += [f"  - [{i}] {n}" for i, n in plan.ya_cargados]
    lineas.append(f"Contados igual a lo registrado (sin ajuste): {len(plan.sin_diferencia)}")
    lineas.append(f"Sin contar (no cambian): {len(plan.sin_contar)}")
    lineas.append(f"Filas inválidas (no se cargan): {len(plan.invalidas)}")
    lineas += [f"  - [{i}] {n}: {m}" for i, n, m in plan.invalidas]
    lineas.append("")
    lineas.append(f"HUELLA: {plan.huella}")
    lineas.append("Para aplicar exactamente esto: --aplicar --huella " + plan.huella)
    return "\n".join(lineas)
