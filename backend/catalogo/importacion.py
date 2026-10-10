"""Importacion del catalogo anterior (plan.md 11.3, PT-05, T-OP.2).

Operacion de UNA sola vez: no es una funcionalidad del sistema. Lee los
CSV exportados del proyecto Laravel —nunca la base de origen— y crea
cada producto a traves del servicio de alta, igual que uno creado a
mano: con su codigo EAN-13, su movimiento ALTA de 0 y 0 meses de
garantia. Opcionalmente carga las existencias contadas a traves del
servicio de ajuste, con el motivo «Carga inicial».

Dos pasos y una huella:
  1. construir_plan() no escribe nada: decide que se importaria, que no
     y por que, y calcula la HUELLA de ese conjunto exacto.
  2. aplicar() recalcula el plan y solo escribe si la huella coincide
     con la aprobada. Todo o nada, en una transaccion.

Este modulo no conoce la linea de comandos: el comando de gestion
(management/commands/importar_catalogo.py) es una capa fina encima.
"""

import csv
import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.files import File
from django.db import connection, transaction
from PIL import Image

from catalogo.models import Categoria, Producto
from catalogo.serializers import FORMATOS_IMAGEN, TAMANO_MAXIMO_IMAGEN
from catalogo.services import crear_producto
from inventario.services import ajustar_existencias

MOTIVO_CARGA_INICIAL = "Carga inicial"
LARGO_NOMBRE_PRODUCTO = 150
LARGO_NOMBRE_CATEGORIA = 100
CABECERA_PLANILLA = ["id_antiguo", "nombre", "categoria", "existencias_contadas"]


class HuellaNoCoincide(Exception):
    """El plan cambio desde el informe aprobado: no se importa nada."""


# ─────────────────────────────────────────────────────────────────────
# Lectura
# ─────────────────────────────────────────────────────────────────────
def _leer_csv(ruta):
    """UTF-8 con o sin BOM: los CSV exportados lo llevan (T-OP.1)."""
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def normalizar(texto):
    """Para comparar nombres: minusculas, sin tildes y sin espacios de
    mas. «Cámaras» y «camaras» son la misma categoria."""
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())


def _parecidas(nombre, existentes):
    """Categorias existentes que comparten palabras con significado con
    `nombre`: «Redes» y «Redes y Conectividad». Solo se senalan; decidir
    si se fusionan es del usuario (--mapa-categorias)."""
    vacias = {"y", "de", "e", "o", "para", "la", "el", "los", "las"}
    palabras = set(normalizar(nombre).split()) - vacias
    return sorted(
        e.nombre
        for e in existentes
        if palabras & (set(normalizar(e.nombre).split()) - vacias)
    )


def leer_mapa_categorias(ruta):
    """CSV con columnas `origen,destino`: la categoria antigua `origen` se
    importa dentro de la existente (o nueva) `destino`."""
    if not ruta:
        return {}
    return {normalizar(f["origen"]): f["destino"].strip() for f in _leer_csv(ruta)}


def leer_fusiones(ruta, existentes):
    """plan.md 11.3 — CSV `existente,nombre_final`: la categoria
    existente se RENOMBRA a `nombre_final`, y los productos importados de
    la categoria antigua con ese nombre entran en ella.

    Se valida aqui, antes de aprobar nada: la categoria debe existir y el
    nombre final no puede chocar con OTRA existente (el UNIQUE sin
    distinguir mayusculas lo impediria al aplicar).
    """
    if not ruta:
        return []
    por_nombre = {normalizar(c.nombre): c for c in existentes}
    fusiones = []
    for fila in _leer_csv(ruta):
        actual, final = fila["existente"].strip(), fila["nombre_final"].strip()
        categoria = por_nombre.get(normalizar(actual))
        if categoria is None:
            raise ValueError(f"--fusionar-categorias: no existe la categoría «{actual}».")
        otra = por_nombre.get(normalizar(final))
        if otra is not None and otra.pk != categoria.pk:
            raise ValueError(f"--fusionar-categorias: «{final}» ya es otra categoría existente.")
        if len(final) > LARGO_NOMBRE_CATEGORIA or not final:
            raise ValueError(f"--fusionar-categorias: nombre final no válido: «{final}».")
        fusiones.append((categoria.pk, categoria.nombre, final, categoria.productos.count()))
    return fusiones


def _huella_de_archivo(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def _validar_imagen(ruta):
    """La misma validacion que una subida (plan.md 5.4): imagen real
    segun Pillow, formato admitido y hasta 2 MB. Devuelve el motivo del
    rechazo o None."""
    if not ruta.is_file():
        return "el archivo no existe"
    if ruta.stat().st_size > TAMANO_MAXIMO_IMAGEN:
        return "pesa más de 2 MB"
    try:
        with Image.open(ruta) as imagen:
            imagen.verify()
            formato = (imagen.format or "").lower()
    except Exception:
        return "no es una imagen válida"
    if formato not in FORMATOS_IMAGEN:
        return f"formato no admitido ({formato or 'desconocido'})"
    return None


# ─────────────────────────────────────────────────────────────────────
# Plan
# ─────────────────────────────────────────────────────────────────────
@dataclass
class Plan:
    a_importar: list = field(default_factory=list)
    problematicos: list = field(default_factory=list)  # (id, nombre, motivo)
    sin_imagen: list = field(default_factory=list)  # (id, nombre, motivo)
    categorias_nuevas: list = field(default_factory=list)
    categorias_existentes: list = field(default_factory=list)
    categorias_parecidas: dict = field(default_factory=dict)  # nueva -> [existentes]
    diferencias: list = field(default_factory=list)
    # (id, nombre_actual, nombre_final, productos que ya tiene)
    fusiones: list = field(default_factory=list)
    recuento: dict = field(default_factory=dict)
    huella: str = ""

    @property
    def con_existencias(self):
        return [p for p in self.a_importar if p["existencias"]]


def _leer_existencias(ruta, por_id):
    """La planilla de recuento devuelta (plan.md 11.3).

    Primera fila: `fecha_del_recuento,<AAAA-MM-DD>`. Despues, la cabecera
    y una fila por producto. Devuelve ({id: cantidad}, resumen).
    """
    resumen = {"fecha": "", "cargados": [], "en_cero": [], "sin_contar": [], "invalidas": [], "ignoradas": []}
    if not ruta:
        return {}, None
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        lineas = list(csv.reader(archivo))
    if lineas and lineas[0] and lineas[0][0].strip() == "fecha_del_recuento":
        resumen["fecha"] = (lineas[0][1] if len(lineas[0]) > 1 else "").strip()
        lineas = lineas[1:]
    if not lineas or [c.strip() for c in lineas[0][:4]] != CABECERA_PLANILLA:
        raise ValueError(
            "La planilla de existencias no tiene la cabecera esperada: " + ",".join(CABECERA_PLANILLA)
        )

    contadas, vistos = {}, set()
    for fila in lineas[1:]:
        if not any(c.strip() for c in fila):
            continue
        fila = (fila + [""] * 4)[:4]
        id_antiguo, nombre, _, texto = (c.strip() for c in fila)
        if id_antiguo not in por_id:
            resumen["ignoradas"].append((id_antiguo, nombre, "no es un producto que se importe"))
            continue
        producto = por_id[id_antiguo]
        if normalizar(nombre) != normalizar(producto["nombre"]):
            resumen["invalidas"].append(
                (id_antiguo, nombre, f"el nombre no corresponde a «{producto['nombre']}»: ¿planilla desordenada?")
            )
            continue
        vistos.add(id_antiguo)
        if texto == "":
            resumen["sin_contar"].append((id_antiguo, producto["nombre"]))
            continue
        if not (texto.isascii() and texto.isdigit()):
            resumen["invalidas"].append((id_antiguo, producto["nombre"], f"«{texto}» no es un entero no negativo"))
            continue
        cantidad = int(texto)
        if cantidad == 0:
            resumen["en_cero"].append((id_antiguo, producto["nombre"]))
        else:
            contadas[id_antiguo] = cantidad
            resumen["cargados"].append((id_antiguo, producto["nombre"], cantidad))
    for id_antiguo, producto in por_id.items():
        if id_antiguo not in vistos and not any(i == id_antiguo for i, *_ in resumen["invalidas"]):
            resumen["sin_contar"].append((id_antiguo, producto["nombre"]))
    return contadas, resumen


def construir_plan(
    productos_csv,
    categorias_csv,
    imagenes=None,
    mapa_categorias=None,
    diferencias_csv=None,
    existencias_csv=None,
    fusiones_csv=None,
):
    """Decide que se importaria, sin escribir nada en la base."""
    plan = Plan()
    filas = _leer_csv(productos_csv)
    categorias_antiguas = {f["id"].strip(): f["nombre"].strip() for f in _leer_csv(categorias_csv)}
    mapa = leer_mapa_categorias(mapa_categorias)
    existentes = list(Categoria.objects.all())
    plan.fusiones = leer_fusiones(fusiones_csv, existentes)
    # El plan se calcula como si los renombrados ya estuvieran hechos:
    # asi «Redes y Conectividad» coincide con la «Redes» renombrada.
    nombres_finales = {pk: final for pk, _, final, _ in plan.fusiones}
    for categoria in existentes:
        categoria.nombre = nombres_finales.get(categoria.pk, categoria.nombre)
    existentes_por_nombre = {normalizar(c.nombre): c.nombre for c in existentes}
    productos_existentes = {normalizar(n) for n in Producto.objects.values_list("nombre", flat=True)}
    imagenes = Path(imagenes) if imagenes else None

    vistos, categorias_usadas = set(), {}
    for fila in filas:
        id_antiguo = fila["id"].strip()
        nombre = (fila.get("nombre") or "").strip()
        motivo = None

        if not nombre:
            motivo = "nombre vacío"
        elif len(nombre) > LARGO_NOMBRE_PRODUCTO:
            motivo = f"nombre de más de {LARGO_NOMBRE_PRODUCTO} caracteres"
        elif normalizar(nombre) in vistos:
            motivo = "nombre repetido dentro del CSV"
        elif normalizar(nombre) in productos_existentes:
            motivo = "ya existe un producto con ese nombre"

        try:
            precio = Decimal((fila.get("precio") or "").strip())
            if not motivo and precio <= 0:
                motivo = "precio no positivo"
        except InvalidOperation:
            precio = None
            motivo = motivo or "precio no numérico"

        categoria_antigua = categorias_antiguas.get((fila.get("categoria_id") or "").strip())
        if not motivo and categoria_antigua is None:
            motivo = "su categoría no existe en categorias.csv"
        if not motivo:
            destino = mapa.get(normalizar(categoria_antigua), categoria_antigua)
            if len(destino) > LARGO_NOMBRE_CATEGORIA:
                motivo = f"nombre de categoría de más de {LARGO_NOMBRE_CATEGORIA} caracteres"

        if motivo:
            plan.problematicos.append((id_antiguo, nombre, motivo))
            continue
        vistos.add(normalizar(nombre))

        # La categoria se nombra como la existente si ya hay una igual.
        categoria = existentes_por_nombre.get(normalizar(destino), destino)
        categorias_usadas[normalizar(categoria)] = categoria

        imagen, huella_imagen = None, None
        ruta_relativa = (fila.get("imagen") or "").strip()
        if not ruta_relativa:
            plan.sin_imagen.append((id_antiguo, nombre, "no tenía imagen"))
        elif imagenes is None:
            plan.sin_imagen.append((id_antiguo, nombre, "no se indicó la carpeta de imágenes (--imagenes)"))
        else:
            ruta = imagenes / ruta_relativa
            rechazo = _validar_imagen(ruta)
            if rechazo:
                plan.sin_imagen.append((id_antiguo, nombre, f"{ruta_relativa}: {rechazo}"))
            else:
                imagen, huella_imagen = str(ruta), _huella_de_archivo(ruta)

        plan.a_importar.append(
            {
                "id_antiguo": id_antiguo,
                "nombre": nombre,
                "descripcion": fila.get("descripcion") or "",
                "precio": str(precio),
                "categoria": categoria,
                "imagen": imagen,
                "huella_imagen": huella_imagen,
                "existencias": 0,
            }
        )

    for clave, nombre in sorted(categorias_usadas.items()):
        if clave in existentes_por_nombre:
            plan.categorias_existentes.append(nombre)
        else:
            plan.categorias_nuevas.append(nombre)
            parecidas = _parecidas(nombre, existentes)
            if parecidas:
                plan.categorias_parecidas[nombre] = parecidas

    if diferencias_csv:
        importados = {p["id_antiguo"]: p for p in plan.a_importar}
        for fila in _leer_csv(diferencias_csv):
            plan.diferencias.append(
                {
                    **{k: (v or "").strip() for k, v in fila.items()},
                    "se_importa": fila["id_antiguo"].strip() in importados,
                }
            )

    por_id = {p["id_antiguo"]: p for p in plan.a_importar}
    contadas, plan.recuento = _leer_existencias(existencias_csv, por_id)
    for id_antiguo, cantidad in contadas.items():
        por_id[id_antiguo]["existencias"] = cantidad

    plan.huella = calcular_huella(plan)
    return plan


def calcular_huella(plan):
    """Resumen criptografico del conjunto EXACTO que se escribiria:
    cada producto con sus campos, el contenido de su imagen y las
    existencias contadas. Cambiar cualquier cosa cambia la huella."""
    datos = [
        {k: v for k, v in p.items() if k != "imagen"} for p in sorted(plan.a_importar, key=lambda p: p["id_antiguo"])
    ]
    canonico = json.dumps(
        {"productos": datos, "fusiones": [list(f[:3]) for f in plan.fusiones]},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────
# Planilla de recuento
# ─────────────────────────────────────────────────────────────────────
def escribir_planilla(plan, ruta):
    """Un producto por fila, solo los que se importarian, con la columna
    de existencias vacia y la fecha del recuento por completar."""
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["fecha_del_recuento", ""])
        escritor.writerow(CABECERA_PLANILLA)
        for p in sorted(plan.a_importar, key=lambda p: int(p["id_antiguo"]) if p["id_antiguo"].isdigit() else 0):
            escritor.writerow([p["id_antiguo"], p["nombre"], p["categoria"], ""])


# ─────────────────────────────────────────────────────────────────────
# Aplicar
# ─────────────────────────────────────────────────────────────────────
def aplicar(plan, *, huella, usuario):
    """Importa el plan si su huella es la aprobada. Todo o nada.

    Cada producto pasa por crear_producto() (codigo EAN-13 y movimiento
    ALTA de 0) y, si se conto, por ajustar_existencias() con el motivo
    «Carga inicial». Si cualquier paso falla, no queda nada.

    Al terminar se ejecuta ANALYZE: tras una carga masiva, PostgreSQL
    planifica mal hasta que se actualizan sus estadisticas (T-12.7).
    """
    if huella != plan.huella:
        raise HuellaNoCoincide(
            f"La huella indicada ({huella}) no es la del plan actual ({plan.huella}). "
            "Algo cambió desde el informe: vuelva a generarlo y apruébelo."
        )

    creados = []
    with transaction.atomic():
        # Primero los renombrados (plan.md 11.3): conservan el id, asi que
        # sus productos actuales siguen en ellas.
        for pk, actual, final, _ in plan.fusiones:
            categoria = Categoria.objects.select_for_update().get(pk=pk)
            if normalizar(categoria.nombre) != normalizar(actual):
                raise HuellaNoCoincide(f"La categoría {pk} ya no se llama «{actual}».")
            categoria.nombre = final
            categoria.save(update_fields=["nombre"])
        categorias = {}
        for p in plan.a_importar:
            clave = normalizar(p["categoria"])
            if clave not in categorias:
                categorias[clave] = next(
                    (c for c in Categoria.objects.all() if normalizar(c.nombre) == clave), None
                ) or Categoria.objects.create(nombre=p["categoria"], descripcion="")
            datos = {
                "nombre": p["nombre"],
                "descripcion": p["descripcion"],
                "precio": Decimal(p["precio"]),
                "stock": 0,
                "categoria": categorias[clave],
                "meses_garantia": 0,
            }
            if p["imagen"]:
                with open(p["imagen"], "rb") as archivo:
                    datos["imagen"] = File(archivo, name=Path(p["imagen"]).name)
                    producto = crear_producto(usuario=usuario, **datos)
            else:
                producto = crear_producto(usuario=usuario, **datos)
            if p["existencias"]:
                ajustar_existencias(
                    producto_id=producto.pk,
                    cantidad_real=p["existencias"],
                    motivo=MOTIVO_CARGA_INICIAL,
                    usuario=usuario,
                )
            creados.append(producto)

    with connection.cursor() as cursor:
        cursor.execute("ANALYZE catalogo_producto, catalogo_categoria, inventario_movimientostock")
    return creados


# ─────────────────────────────────────────────────────────────────────
# Informe
# ─────────────────────────────────────────────────────────────────────
def informe(plan, *, fecha_de_ejecucion=None):
    """El informe en texto, para leerlo y aprobarlo (T-OP.3)."""
    lineas = ["INFORME DE IMPORTACIÓN DEL CATÁLOGO ANTERIOR", "=" * 44, ""]
    lineas.append(f"Se importarían {len(plan.a_importar)} productos, con existencias 0, sin marca y 0 meses de garantía.")
    lineas.append("Los precios se importan tal cual: son referenciales y conviene revisarlos.")
    lineas.append("")

    lineas.append(f"Problemáticos, NO se importan: {len(plan.problematicos)}")
    lineas += [f"  - [{i}] {n or '(sin nombre)'}: {m}" for i, n, m in plan.problematicos]
    lineas.append("")
    lineas.append(f"Se importarían SIN imagen: {len(plan.sin_imagen)}")
    lineas += [f"  - [{i}] {n}: {m}" for i, n, m in plan.sin_imagen]
    lineas.append("")

    if plan.fusiones:
        lineas.append("Categorías existentes que se RENOMBRAN (fusión; conservan su id y sus productos):")
        lineas += [
            f"  - «{actual}» -> «{final}» (tiene {n} producto{'s' if n != 1 else ''})"
            for _, actual, final, n in plan.fusiones
        ]
        lineas.append("")
    lineas.append(f"Categorías que ya existen: {', '.join(plan.categorias_existentes) or 'ninguna'}")
    lineas.append(f"Categorías que se crearían: {len(plan.categorias_nuevas)}")
    for nombre in plan.categorias_nuevas:
        parecidas = plan.categorias_parecidas.get(nombre)
        extra = f"  <- PARECIDA a: {', '.join(parecidas)} (¿fusionar con --mapa-categorias?)" if parecidas else ""
        lineas.append(f"  - {nombre}{extra}")
    lineas.append("")

    if plan.diferencias:
        lineas.append("Productos que difieren entre la base antigua y el seeder:")
        for d in plan.diferencias:
            aviso = "  <- precio por confirmar con la empresa" if d.get("campo") == "precio" else ""
            estado = "" if d["se_importa"] else " (no se importa)"
            lineas.append(
                f"  - [{d['id_antiguo']}] {d['nombre']}, {d['campo']}: base antigua {d['base_antigua']}, "
                f"seeder {d['seeder']}, se importaría {d['valor_que_se_importaria']}{estado}{aviso}"
            )
        lineas.append("")
        por_confirmar = [d for d in plan.diferencias if d.get("campo") == "precio" and d["se_importa"]]
        if por_confirmar:
            lineas.append("PRECIOS POR CONFIRMAR CON LA EMPRESA:")
            lineas += [
                f"  - [{d['id_antiguo']}] {d['nombre']}: se importa a {d['valor_que_se_importaria']} "
                f"(el seeder decía {d['seeder']})"
                for d in por_confirmar
            ]
            lineas.append("")

    if plan.recuento:
        r = plan.recuento
        lineas.append("Carga de existencias contadas («Carga inicial»):")
        lineas.append(f"  Fecha del recuento: {r['fecha'] or '(SIN FECHA)'}"
                      + (f" · fecha de esta ejecución: {fecha_de_ejecucion}" if fecha_de_ejecucion else ""))
        lineas.append(f"  Productos con existencias que se cargan: {len(r['cargados'])}"
                      f" ({sum(n for *_, n in r['cargados'])} unidades)")
        lineas.append(f"  Contados en cero: {len(r['en_cero'])}")
        lineas.append(f"  Sin contar (quedan en 0): {len(r['sin_contar'])}")
        lineas += [f"    - [{i}] {n}" for i, n in r["sin_contar"]]
        lineas.append(f"  Filas inválidas (no se cargan): {len(r['invalidas'])}")
        lineas += [f"    - [{i}] {n}: {m}" for i, n, m in r["invalidas"]]
        if r["ignoradas"]:
            lineas.append(f"  Filas ignoradas: {len(r['ignoradas'])}")
            lineas += [f"    - [{i}] {n}: {m}" for i, n, m in r["ignoradas"]]
        lineas.append("")

    lineas.append(f"HUELLA: {plan.huella}")
    lineas.append("Para aplicar exactamente esto: --aplicar --huella " + plan.huella)
    return "\n".join(lineas)
