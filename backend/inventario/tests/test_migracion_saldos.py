"""T-8.4 — Migracion de saldos iniciales (RNF-29, RN-MOV-02, RN-MOV-03).

Se prueba la migracion de verdad: se lleva la base al estado anterior
(inventario 0001), se cargan productos, y se aplica y revierte con el
mismo MigrationExecutor que usa `manage.py migrate`. Con mas de 160
productos, porque el catalogo que se importara tiene 153 y la base
real podria tener mas.

`transaction=True`: una migracion cambia el estado de la base de
verdad y no puede probarse dentro de la transaccion que pytest-django
abre y revierte en las demas pruebas.
"""

import importlib
import random

import pytest
from django.apps import apps as registro_actual
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Sum

from catalogo.models import Producto
from catalogo.services import crear_producto
from catalogo.tests.factories import CategoriaFactory, ProductoFactory
from inventario.models import MovimientoStock, TipoMovimiento
from usuarios.tests.factories import AdministradorFactory, VendedorFactory
from ventas.services import registrar_venta

pytestmark = pytest.mark.django_db(transaction=True)

ANTES = [("inventario", "0001_initial")]
DESPUES = [("inventario", "0002_saldos_iniciales")]
MIGRACION = importlib.import_module("inventario.migrations.0002_saldos_iniciales")

CANTIDAD = 165


def _migrar(destino):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(destino)


@pytest.fixture
def base_antes_de_la_migracion():
    """Deja la base en inventario 0001 y, al terminar, en el ultimo estado.

    Antes de volver a migrar se vacia el libro: alguna prueba siembra a
    proposito un libro inconsistente, y con el dentro la migracion se
    negaria a aplicarse otra vez. Se hace en SQL porque el modelo, a
    proposito, no permite borrar movimientos (RN-MOV-04); como la prueba
    es transaccional, la base se vacia entera al terminar de todos modos.
    """
    _migrar(ANTES)
    yield
    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM {MovimientoStock._meta.db_table}")
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.fixture
def catalogo(base_antes_de_la_migracion):
    """165 productos con existencias variadas, incluidos varios en cero."""
    azar = random.Random(20261009)  # reproducible
    categoria = CategoriaFactory()
    stocks = [0, 0, 0, 1, 1] + [azar.randint(0, 60) for _ in range(CANTIDAD - 5)]
    return [ProductoFactory(categoria=categoria, stock=s) for s in stocks]


def _foto(productos):
    """Lo que la migracion NO debe tocar de los productos."""
    return {
        p["id"]: (p["nombre"], p["stock"], p["precio"], p["activo"])
        for p in Producto.objects.filter(id__in=[x.id for x in productos]).values(
            "id", "nombre", "stock", "precio", "activo"
        )
    }


def _saldos():
    return MovimientoStock.objects.filter(tipo=TipoMovimiento.SALDO_INICIAL)


def _libro_cuadra(producto):
    producto.refresh_from_db()
    suma = MovimientoStock.objects.filter(producto=producto).aggregate(t=Sum("cantidad"))["t"]
    return suma == producto.stock


# ─────────────────────────────────────────────────────────────────────
# Aplicar
# ─────────────────────────────────────────────────────────────────────
def test_cada_producto_recibe_un_saldo_inicial_igual_a_su_stock(catalogo):
    _migrar(DESPUES)

    assert _saldos().count() == CANTIDAD
    por_producto = {m.producto_id: m for m in _saldos()}
    for producto in catalogo:
        saldo = por_producto[producto.id]
        assert saldo.cantidad == saldo.stock_resultante == producto.stock
        assert saldo.usuario is None, "el saldo inicial lo crea el sistema, no una persona"
        assert saldo.venta is None
        assert saldo.fecha_hora is not None
        assert _libro_cuadra(producto)


def test_los_productos_sin_existencias_tambien_tienen_su_saldo(catalogo):
    """Todo producto necesita un punto de partida, aunque sea cero."""
    _migrar(DESPUES)

    sin_stock = [p for p in catalogo if p.stock == 0]
    assert len(sin_stock) >= 3
    for producto in sin_stock:
        assert _saldos().get(producto=producto).cantidad == 0


def test_la_migracion_no_cambia_ningun_dato_de_los_productos(catalogo):
    antes = _foto(catalogo)

    _migrar(DESPUES)

    assert _foto(catalogo) == antes


# ─────────────────────────────────────────────────────────────────────
# Revertir (RNF-29)
# ─────────────────────────────────────────────────────────────────────
def test_revertir_borra_los_saldos_y_no_toca_los_productos(catalogo):
    antes = _foto(catalogo)
    _migrar(DESPUES)

    _migrar(ANTES)

    assert _saldos().count() == 0
    assert _foto(catalogo) == antes


def test_revertir_solo_borra_los_saldos_iniciales(catalogo):
    """Si despues de migrar hubo ventas, revertir no puede llevarselas:
    solo deshace lo que la migracion creo."""
    _migrar(DESPUES)
    producto = next(p for p in catalogo if p.stock >= 2)
    registrar_venta(
        usuario=VendedorFactory(),
        cliente_nombre="María",
        cliente_telefono="70012345",
        items=[{"producto_id": producto.id, "cantidad": 1}],
    )

    _migrar(ANTES)

    assert _saldos().count() == 0
    assert MovimientoStock.objects.filter(tipo=TipoMovimiento.VENTA).count() == 1


# ─────────────────────────────────────────────────────────────────────
# Idempotencia
# ─────────────────────────────────────────────────────────────────────
def test_aplicar_revertir_y_volver_a_aplicar_no_duplica(catalogo):
    _migrar(DESPUES)
    primera = sorted(_saldos().values_list("producto_id", "cantidad"))

    _migrar(ANTES)
    _migrar(DESPUES)

    assert sorted(_saldos().values_list("producto_id", "cantidad")) == primera
    assert _saldos().count() == CANTIDAD


def test_ejecutar_la_funcion_dos_veces_no_duplica(catalogo):
    """La garantia no depende de que Django recuerde que ya aplico la
    migracion: la funcion misma es idempotente."""
    _migrar(DESPUES)

    MIGRACION.crear_saldos_iniciales(registro_actual, None)
    MIGRACION.crear_saldos_iniciales(registro_actual, None)

    assert _saldos().count() == CANTIDAD


def test_un_producto_creado_con_su_alta_no_recibe_saldo_inicial(base_antes_de_la_migracion):
    """Creado despues de T-8.3: ya tiene su ALTA. Un segundo origen
    contaria sus existencias dos veces."""
    producto = crear_producto(
        usuario=AdministradorFactory(),
        nombre="Creado con alta",
        precio=100,
        stock=8,
        categoria=CategoriaFactory(),
    )

    _migrar(DESPUES)

    assert not _saldos().filter(producto=producto).exists()
    assert _libro_cuadra(producto)


# ─────────────────────────────────────────────────────────────────────
# Productos vendidos antes de la migracion
# ─────────────────────────────────────────────────────────────────────
def test_un_producto_vendido_antes_de_migrar_cuadra_igual(base_antes_de_la_migracion):
    """Entre T-8.2 y T-8.4 una venta ya deja su movimiento, pero el
    producto aun no tiene origen. Tenia 10, se vendieron 3: quedan 7 y
    hay un movimiento de -3. El saldo inicial debe ser 10, no 7, para
    que el libro sume 7."""
    producto = ProductoFactory(stock=10)
    registrar_venta(
        usuario=VendedorFactory(),
        cliente_nombre="María",
        cliente_telefono="70012345",
        items=[{"producto_id": producto.id, "cantidad": 3}],
    )

    _migrar(DESPUES)

    saldo = _saldos().get(producto=producto)
    assert saldo.cantidad == 10
    assert _libro_cuadra(producto)


def test_un_libro_inconsistente_detiene_la_migracion_sin_dejar_nada(base_antes_de_la_migracion):
    """Movimientos que suman mas que el stock no tienen saldo posible.
    La migracion se detiene entera en vez de inventar uno negativo."""
    producto = ProductoFactory(stock=2)
    MovimientoStock.objects.create(
        producto=producto,
        tipo=TipoMovimiento.AJUSTE,
        cantidad=5,
        stock_resultante=5,
        usuario=AdministradorFactory(),
        motivo="dato corrupto a proposito",
    )
    otro = ProductoFactory(stock=4)

    with pytest.raises(MIGRACION.LibroInconsistente):
        _migrar(DESPUES)

    assert _saldos().count() == 0, "la migracion es atomica: el otro producto tampoco recibe saldo"
    assert not _saldos().filter(producto=otro).exists()
