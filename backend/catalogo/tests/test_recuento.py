"""T-OP.5 — Carga posterior del recuento (plan.md 11.3).

Los productos se crean primero con el servicio de alta (como quedaron
tras T-OP.4) y luego se carga la planilla con --solo-existencias.
"""

import csv
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command

from catalogo import importacion, recuento
from catalogo.models import Producto
from catalogo.services import crear_producto
from catalogo.tests.factories import CategoriaFactory
from inventario.models import MovimientoStock, TipoMovimiento
from inventario.verificacion import libros_descuadrados
from usuarios.tests.factories import AdministradorFactory, VendedorFactory
from ventas.services import registrar_venta

pytestmark = pytest.mark.django_db

NOMBRES = {"1": "Cámara Bullet Dahua 2MP", "2": "Router TP-Link AC1200", "3": "Switch PoE 8 puertos", "4": "Nunca importado"}


@pytest.fixture
def admin():
    return AdministradorFactory(username="importador")


@pytest.fixture
def catalogo(tmp_path, admin):
    """productos.csv con 4 filas; 3 importadas (la 4 no está en el sistema)."""
    ruta = tmp_path / "productos.csv"
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["id", "categoria_id", "nombre", "precio"])
        for id_, nombre in NOMBRES.items():
            escritor.writerow([id_, "1", nombre, "100.00"])
    categoria = CategoriaFactory()
    productos = {
        id_: crear_producto(usuario=admin, nombre=NOMBRES[id_], descripcion="", precio=100, stock=0, categoria=categoria)
        for id_ in ("1", "2", "3")
    }
    return {"csv": str(ruta), "tmp": tmp_path, "productos": productos}


def _planilla(catalogo, cantidades=None, meses=None, nombres=None, fecha="2026-10-15", nombre_archivo="planilla.csv"):
    ruta = catalogo["tmp"] / nombre_archivo
    recuento.escribir_planilla_importados(catalogo["csv"], ruta)
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.reader(archivo))
    filas[0][1] = fecha
    for fila in filas[2:]:
        fila[3] = (cantidades or {}).get(fila[0], "")
        fila[4] = (meses or {}).get(fila[0], "")
        fila[1] = (nombres or {}).get(fila[0], fila[1])
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        csv.writer(archivo).writerows(filas)
    return str(ruta)


def _plan(catalogo, **kw):
    return recuento.construir_plan(catalogo["csv"], _planilla(catalogo, **kw))


def _cargas(producto):
    return MovimientoStock.objects.filter(producto=producto, tipo=TipoMovimiento.AJUSTE, motivo="Carga inicial")


def test_la_planilla_lista_los_importados_con_las_columnas_vacias(catalogo):
    ruta = catalogo["tmp"] / "p.csv"

    n = recuento.escribir_planilla_importados(catalogo["csv"], ruta)

    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.reader(archivo))
    assert n == 3
    assert filas[1] == recuento.CABECERA
    assert [f[0] for f in filas[2:]] == ["1", "2", "3"]
    assert all(f[3] == "" and f[4] == "" for f in filas[2:])


def test_el_informe_no_escribe_nada(catalogo):
    antes = MovimientoStock.objects.count()

    _plan(catalogo, cantidades={"1": "12"}, meses={"1": "12"})

    assert MovimientoStock.objects.count() == antes
    assert Producto.objects.get(pk=catalogo["productos"]["1"].pk).meses_garantia == 0


def test_cada_fila_valida_deja_su_carga_inicial_y_el_libro_cuadra(catalogo, admin):
    plan = _plan(catalogo, cantidades={"1": "12", "2": "5"})

    recuento.aplicar(plan, huella=plan.huella, usuario=admin)

    for id_, cantidad in (("1", 12), ("2", 5)):
        producto = Producto.objects.get(pk=catalogo["productos"][id_].pk)
        assert producto.stock == cantidad
        [carga] = _cargas(producto)
        assert (carga.cantidad, carga.usuario) == (cantidad, admin)
    assert libros_descuadrados() == []


def test_un_producto_ya_cargado_se_salta_y_una_segunda_ejecucion_no_crea_nada(catalogo, admin):
    primero = _plan(catalogo, cantidades={"1": "12"})
    recuento.aplicar(primero, huella=primero.huella, usuario=admin)
    movimientos = MovimientoStock.objects.count()

    segundo = _plan(catalogo, cantidades={"1": "30"}, nombre_archivo="otra.csv")
    recuento.aplicar(segundo, huella=segundo.huella, usuario=admin)

    assert [i for i, _ in segundo.ya_cargados] == ["1"]
    assert segundo.ajustes == []
    assert MovimientoStock.objects.count() == movimientos
    assert Producto.objects.get(pk=catalogo["productos"]["1"].pk).stock == 12


def test_lo_contado_igual_a_lo_vigente_no_crea_ajuste(catalogo, admin):
    plan = _plan(catalogo, cantidades={"1": "0"})

    recuento.aplicar(plan, huella=plan.huella, usuario=admin)

    assert [i for i, _ in plan.sin_diferencia] == ["1"]
    assert not _cargas(catalogo["productos"]["1"]).exists()


def test_el_ajuste_se_calcula_contra_las_existencias_actuales(catalogo, admin):
    """Si hubo ventas despues de importar (con stock cargado por otra via),
    el producto queda en lo contado, no en lo contado mas lo vendido."""
    producto = catalogo["productos"]["1"]
    from inventario.services import ajustar_existencias

    ajustar_existencias(producto_id=producto.pk, cantidad_real=10, motivo="Entrada de mercadería", usuario=admin)
    registrar_venta(usuario=VendedorFactory(), cliente_nombre="C", cliente_telefono="1",
                    items=[{"producto_id": producto.pk, "cantidad": 3}])

    plan = _plan(catalogo, cantidades={"1": "6"})
    recuento.aplicar(plan, huella=plan.huella, usuario=admin)

    producto.refresh_from_db()
    assert producto.stock == 6
    assert _cargas(producto).get().cantidad == -1
    assert libros_descuadrados() == []


@pytest.mark.parametrize(
    ("kw", "id_", "motivo"),
    [
        ({"cantidades": {"1": "-2"}}, "1", "no es un entero no negativo"),
        ({"cantidades": {"1": "3.5"}}, "1", "no es un entero no negativo"),
        ({"cantidades": {"1": "5"}, "nombres": {"1": "Router TP-Link AC1200"}}, "1", "planilla desordenada"),
        ({"meses": {"2": "doce"}}, "2", "no es un entero no negativo"),
    ],
    ids=["negativa", "decimal", "nombre-equivocado", "meses-invalidos"],
)
def test_una_fila_invalida_no_se_carga_y_se_lista(catalogo, admin, kw, id_, motivo):
    plan = _plan(catalogo, **kw)

    assert [(i, motivo in m) for i, _, m in plan.invalidas] == [(id_, True)]
    assert plan.ajustes == [] and plan.meses == []


def test_un_producto_que_no_esta_en_el_sistema_o_un_id_desconocido_se_listan(catalogo):
    ruta = _planilla(catalogo)
    with open(ruta, "a", encoding="utf-8", newline="") as archivo:
        csv.writer(archivo).writerows([["4", "Nunca importado", "X", "3", ""], ["99", "Inventado", "X", "3", ""]])

    plan = recuento.construir_plan(catalogo["csv"], ruta)

    motivos = {i: m for i, _, m in plan.invalidas}
    assert motivos["4"] == "el producto no está en el sistema"
    assert motivos["99"] == "el id_antiguo no está en productos.csv"


def test_los_meses_de_garantia_se_aplican_en_la_misma_ejecucion_y_vacios_no_tocan_nada(catalogo, admin):
    catalogo["productos"]["3"].meses_garantia = 6
    catalogo["productos"]["3"].save()
    plan = _plan(catalogo, cantidades={"1": "4"}, meses={"1": "12", "2": "24"})

    recuento.aplicar(plan, huella=plan.huella, usuario=admin)

    meses = dict(Producto.objects.filter(pk__in=[p.pk for p in catalogo["productos"].values()]).values_list("nombre", "meses_garantia"))
    assert meses == {NOMBRES["1"]: 12, NOMBRES["2"]: 24, NOMBRES["3"]: 6}
    # Los meses no son un movimiento de stock.
    assert not _cargas(catalogo["productos"]["2"]).exists()


def test_cambiar_una_cifra_o_vender_despues_del_informe_cambia_la_huella(catalogo, admin):
    aprobado = _plan(catalogo, cantidades={"1": "12"})
    otra_cifra = _plan(catalogo, cantidades={"1": "13"}, nombre_archivo="b.csv")
    assert aprobado.huella != otra_cifra.huella

    # Una venta entre el informe y la aplicacion cambia las existencias
    # actuales, que estan en la huella.
    from inventario.services import ajustar_existencias

    producto = catalogo["productos"]["2"]
    plan = _plan(catalogo, cantidades={"2": "8"}, nombre_archivo="c.csv")
    ajustar_existencias(producto_id=producto.pk, cantidad_real=3, motivo="Entrada", usuario=admin)
    registrar_venta(usuario=VendedorFactory(), cliente_nombre="C", cliente_telefono="1",
                    items=[{"producto_id": producto.pk, "cantidad": 1}])
    recalculado = _plan(catalogo, cantidades={"2": "8"}, nombre_archivo="c.csv")

    assert recalculado.huella != plan.huella
    with pytest.raises(importacion.HuellaNoCoincide):
        recuento.aplicar(recalculado, huella=plan.huella, usuario=admin)
    assert not _cargas(producto).exists()


def test_un_fallo_a_mitad_no_deja_ningun_ajuste_ni_cambio_de_meses(catalogo, admin):
    plan = _plan(catalogo, cantidades={"1": "4", "2": "7"}, meses={"3": "12"})
    real = recuento.ajustar_existencias
    llamadas = []

    def falla_en_el_segundo(**kw):
        llamadas.append(1)
        if len(llamadas) == 2:
            raise RuntimeError("fallo simulado")
        return real(**kw)

    with mock.patch.object(recuento, "ajustar_existencias", side_effect=falla_en_el_segundo):
        with pytest.raises(RuntimeError):
            recuento.aplicar(plan, huella=plan.huella, usuario=admin)

    assert not MovimientoStock.objects.filter(motivo="Carga inicial").exists()
    assert Producto.objects.get(pk=catalogo["productos"]["3"].pk).meses_garantia == 0


def test_el_comando_informa_y_aplica_con_huella_y_administrador(catalogo, admin):
    planilla = _planilla(catalogo, cantidades={"1": "9"})
    salida = StringIO()
    call_command("importar_catalogo", "--productos", catalogo["csv"], "--solo-existencias", planilla, stdout=salida)
    texto = salida.getvalue()
    assert "no se escribió nada" in texto
    huella = texto.split("HUELLA: ")[1].split()[0]

    salida = StringIO()
    call_command("importar_catalogo", "--productos", catalogo["csv"], "--solo-existencias", planilla,
                 "--aplicar", "--huella", huella, "--usuario", "importador", stdout=salida)

    assert "Ajustes «Carga inicial»: 1" in salida.getvalue()
    assert Producto.objects.get(pk=catalogo["productos"]["1"].pk).stock == 9


def test_el_informe_se_puede_mostrar_en_la_consola_de_windows(catalogo):
    recuento.informe(_plan(catalogo, cantidades={"1": "x", "2": "4"}, meses={"2": "12"})).encode("cp1252")
