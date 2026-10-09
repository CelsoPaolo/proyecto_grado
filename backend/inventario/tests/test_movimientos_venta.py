"""T-8.2 — Movimientos de stock dentro de la venta y la anulacion.

RN-MOV-01: todo cambio de existencias genera exactamente un movimiento
por producto, en la MISMA operacion atomica que el cambio. Las pruebas
de este archivo comprueban las dos mitades de esa frase:

  - lo que se escribe: un movimiento por producto, con su signo, su
    resultante, su autor y su venta;
  - lo que NO queda: si la operacion falla en cualquier punto, ni el
    stock, ni la venta, ni el movimiento sobreviven.

La prueba de concurrencia que demuestra RNF-24 con hilos reales es
T-8.5; aqui se verifica la atomicidad sin concurrencia.
"""

from unittest import mock

import pytest
from django.db import transaction

from catalogo.tests.factories import ProductoFactory
from inventario.models import MovimientoStock, TipoMovimiento
from inventario.services import MovimientoFueraDeTransaccion, registrar_movimiento
from usuarios.tests.factories import AdministradorFactory, VendedorFactory
from ventas.exceptions import ProductoNoDisponible, StockInsuficiente, VentaYaAnulada
from ventas.models import DetalleVenta, Venta
from ventas.services import anular_venta, registrar_venta

pytestmark = pytest.mark.django_db


@pytest.fixture
def vendedor():
    return VendedorFactory()


def _vender(usuario, *items):
    return registrar_venta(
        usuario=usuario,
        cliente_nombre="María Gutiérrez",
        cliente_telefono="70012345",
        items=[{"producto_id": p.pk, "cantidad": c} for p, c in items],
    )


def _movimientos(**filtro):
    return list(MovimientoStock.objects.filter(**filtro).order_by("producto_id", "id"))


# ─────────────────────────────────────────────────────────────────────
# Lo que se escribe al vender
# ─────────────────────────────────────────────────────────────────────
def test_una_venta_deja_un_movimiento_por_producto(vendedor):
    teclado = ProductoFactory(stock=10)
    monitor = ProductoFactory(stock=4)

    venta = _vender(vendedor, (teclado, 3), (monitor, 1))

    movimientos = _movimientos(venta=venta)
    assert len(movimientos) == 2

    por_producto = {m.producto_id: m for m in movimientos}
    assert por_producto[teclado.pk].cantidad == -3
    assert por_producto[teclado.pk].stock_resultante == 7
    assert por_producto[monitor.pk].cantidad == -1
    assert por_producto[monitor.pk].stock_resultante == 3

    for m in movimientos:
        assert m.tipo == TipoMovimiento.VENTA
        assert m.usuario == vendedor
        assert m.venta == venta


def test_el_resultante_coincide_con_el_stock_guardado(vendedor):
    """El resultante se calcula en Python a partir del valor bloqueado.
    Esta prueba comprueba que coincide con lo que la base guardo de
    verdad con F(); si alguna vez divergieran, el libro mentiria."""
    producto = ProductoFactory(stock=10)

    _vender(vendedor, (producto, 4))

    producto.refresh_from_db()
    movimiento = MovimientoStock.objects.get(producto=producto)
    assert movimiento.stock_resultante == producto.stock == 6


def test_el_mismo_producto_en_dos_lineas_deja_un_solo_movimiento(vendedor):
    """RN-MOV-01 dice «por producto afectado», no «por linea»."""
    producto = ProductoFactory(stock=10)

    venta = _vender(vendedor, (producto, 2), (producto, 3))

    [movimiento] = _movimientos(venta=venta)
    assert movimiento.cantidad == -5
    assert movimiento.stock_resultante == 5


def test_vender_todo_el_stock_deja_resultante_cero(vendedor):
    """El limite inferior que el CHECK del libro debe aceptar."""
    producto = ProductoFactory(stock=2)

    _vender(vendedor, (producto, 2))

    assert MovimientoStock.objects.get(producto=producto).stock_resultante == 0


# ─────────────────────────────────────────────────────────────────────
# Lo que NO queda cuando la venta falla
# ─────────────────────────────────────────────────────────────────────
def test_una_venta_rechazada_por_stock_no_deja_movimientos(vendedor):
    """RN-VEN-02 y RN-MOV-01: todo o nada, tambien para el libro."""
    hay = ProductoFactory(stock=10)
    falta = ProductoFactory(stock=1)

    with pytest.raises(StockInsuficiente):
        _vender(vendedor, (hay, 2), (falta, 5))

    assert MovimientoStock.objects.count() == 0
    hay.refresh_from_db()
    assert hay.stock == 10


def test_una_venta_con_producto_retirado_no_deja_movimientos(vendedor):
    vigente = ProductoFactory(stock=10)
    retirado = ProductoFactory(stock=10, activo=False)

    with pytest.raises(ProductoNoDisponible):
        _vender(vendedor, (vigente, 1), (retirado, 1))

    assert MovimientoStock.objects.count() == 0


def test_un_fallo_al_registrar_el_movimiento_revierte_toda_la_venta(vendedor):
    """La otra mitad de RN-MOV-01: si el movimiento no puede escribirse,
    las existencias NO cambian.

    Se fuerza el fallo en el SEGUNDO producto, despues de que el
    primero ya descontara su stock y registrara su movimiento. Si la
    transaccion no envolviera las dos escrituras, el primero quedaria
    descontado.
    """
    primero = ProductoFactory(stock=10)
    segundo = ProductoFactory(stock=10)
    real = registrar_movimiento
    llamadas = []

    def falla_en_la_segunda(**kwargs):
        llamadas.append(kwargs["producto"].pk)
        if len(llamadas) == 2:
            raise RuntimeError("fallo simulado al escribir el movimiento")
        return real(**kwargs)

    with mock.patch("ventas.services.registrar_movimiento", side_effect=falla_en_la_segunda):
        with pytest.raises(RuntimeError):
            _vender(vendedor, (primero, 3), (segundo, 2))

    assert len(llamadas) == 2, "el fallo debia ocurrir en el segundo producto"
    primero.refresh_from_db()
    segundo.refresh_from_db()
    assert (primero.stock, segundo.stock) == (10, 10)
    assert Venta.objects.count() == 0
    assert DetalleVenta.objects.count() == 0
    assert MovimientoStock.objects.count() == 0


# ─────────────────────────────────────────────────────────────────────
# Anulacion
# ─────────────────────────────────────────────────────────────────────
def test_anular_deja_un_movimiento_de_anulacion_por_producto(vendedor):
    teclado = ProductoFactory(stock=10)
    monitor = ProductoFactory(stock=4)
    venta = _vender(vendedor, (teclado, 3), (monitor, 1))
    admin = AdministradorFactory()

    anular_venta(venta=venta, usuario=admin, motivo="Error de registro")

    anulaciones = _movimientos(venta=venta, tipo=TipoMovimiento.ANULACION)
    por_producto = {m.producto_id: m for m in anulaciones}
    assert len(anulaciones) == 2
    assert por_producto[teclado.pk].cantidad == 3
    assert por_producto[teclado.pk].stock_resultante == 10
    assert por_producto[monitor.pk].cantidad == 1
    assert por_producto[monitor.pk].stock_resultante == 4
    # El autor de la anulacion es quien anula, no quien vendio.
    assert {m.usuario for m in anulaciones} == {admin}


def test_venta_y_anulacion_se_compensan_en_el_libro(vendedor):
    """Lo que salio vuelve: la suma de los movimientos de la venta y de
    su anulacion es cero para cada producto."""
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, (producto, 4))

    anular_venta(venta=venta, usuario=vendedor, motivo="Cliente se arrepintió")

    cantidades = [m.cantidad for m in MovimientoStock.objects.filter(producto=producto)]
    assert sorted(cantidades) == [-4, 4]
    producto.refresh_from_db()
    assert producto.stock == 10


def test_anular_una_venta_de_un_producto_retirado_tambien_deja_movimiento(vendedor):
    """Los productos se retiran, no se borran (RN-CAT-04): la devolucion
    siempre es posible, y por tanto su movimiento tambien."""
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, (producto, 2))
    producto.activo = False
    producto.save(update_fields=["activo"])

    anular_venta(venta=venta, usuario=vendedor, motivo="Devolución")

    assert MovimientoStock.objects.filter(
        producto=producto, tipo=TipoMovimiento.ANULACION
    ).exists()


def test_anular_dos_veces_no_duplica_movimientos(vendedor):
    """RN-VEN-08: la segunda anulacion se rechaza antes de devolver nada."""
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, (producto, 2))
    anular_venta(venta=venta, usuario=vendedor, motivo="Primera")

    with pytest.raises(VentaYaAnulada):
        anular_venta(venta=venta, usuario=vendedor, motivo="Segunda")

    assert MovimientoStock.objects.filter(tipo=TipoMovimiento.ANULACION).count() == 1


def test_un_fallo_al_registrar_la_anulacion_deja_la_venta_confirmada(vendedor):
    """Si el movimiento de anulacion no se escribe, ni se devuelve el
    stock ni la venta pasa a anulada."""
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, (producto, 3))

    with mock.patch(
        "ventas.services.registrar_movimiento",
        side_effect=RuntimeError("fallo simulado"),
    ):
        with pytest.raises(RuntimeError):
            anular_venta(venta=venta, usuario=vendedor, motivo="Error")

    producto.refresh_from_db()
    venta.refresh_from_db()
    assert producto.stock == 7
    assert not venta.esta_anulada
    assert not MovimientoStock.objects.filter(tipo=TipoMovimiento.ANULACION).exists()


# ─────────────────────────────────────────────────────────────────────
# El servicio se niega a escribir fuera de una transaccion
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.django_db(transaction=True)
def test_no_se_registra_un_movimiento_fuera_de_una_transaccion():
    """RNF-24 como guarda programatica.

    Con `transaction=True` la prueba no va envuelta en ninguna
    transaccion, asi que esta es la unica forma de comprobar la guarda:
    en las demas pruebas pytest-django ya abre una por su cuenta y la
    guarda siempre pasaria.
    """
    producto = ProductoFactory(stock=5)

    with pytest.raises(MovimientoFueraDeTransaccion):
        registrar_movimiento(
            producto=producto,
            tipo=TipoMovimiento.AJUSTE,
            cantidad=1,
            stock_resultante=6,
            usuario=AdministradorFactory(),
            motivo="x",
        )

    assert MovimientoStock.objects.count() == 0

    # Y dentro de una, si funciona.
    with transaction.atomic():
        registrar_movimiento(
            producto=producto,
            tipo=TipoMovimiento.AJUSTE,
            cantidad=1,
            stock_resultante=6,
            usuario=AdministradorFactory(),
            motivo="x",
        )
    assert MovimientoStock.objects.count() == 1
