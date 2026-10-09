"""T-4.3 y T-4.5 — Servicios de registro y anulacion de ventas.

Concentra las reglas mas delicadas de la especificacion:

  RN-VEN-02  la confirmacion es todo o nada
  RN-VEN-04  el nombre y el precio se congelan al confirmar
  RN-VEN-07  la anulacion devuelve las existencias
  RNF-09     el registro es atomico
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction

from catalogo.models import Producto
from catalogo.tests.factories import ProductoFactory
from usuarios.tests.factories import AdministradorFactory, VendedorFactory
from ventas.exceptions import (
    ProductoNoDisponible,
    StockInsuficiente,
    VentaSinItems,
    VentaYaAnulada,
)
from ventas.models import EstadoVenta, Venta
from ventas.services import anular_venta, registrar_venta

pytestmark = pytest.mark.django_db


def _vender(usuario, items, cliente="María Gutiérrez", telefono="70012345"):
    return registrar_venta(
        usuario=usuario,
        cliente_nombre=cliente,
        cliente_telefono=telefono,
        items=items,
    )


# ═════════════════════════════════════════════════════════════════════
# CU-VEN-01 — registro correcto
# ═════════════════════════════════════════════════════════════════════
def test_registrar_una_venta_descuenta_las_existencias():
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10, precio=Decimal("350.00"))

    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 3}])

    producto.refresh_from_db()
    assert producto.stock == 7
    assert venta.estado == EstadoVenta.CONFIRMADA
    assert venta.usuario == vendedor


def test_el_total_es_la_suma_de_los_subtotales():
    """RN-VEN-05."""
    vendedor = VendedorFactory()
    teclado = ProductoFactory(stock=10, precio=Decimal("350.00"))
    monitor = ProductoFactory(stock=10, precio=Decimal("750.00"))

    venta = _vender(
        vendedor,
        [
            {"producto_id": teclado.id, "cantidad": 2},
            {"producto_id": monitor.id, "cantidad": 1},
        ],
    )

    assert venta.total == Decimal("1450.00")
    assert sum(i.subtotal for i in venta.items.all()) == Decimal("1450.00")


def test_los_centavos_no_se_pierden_en_el_total():
    """RN-VEN-05 con Decimal, no con coma flotante.

    Con float, 0.1 * 3 da 0.30000000000000004, y esos restos se
    acumularian en los totales del panel.
    """
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=100, precio=Decimal("33.33"))

    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 3}])

    assert venta.total == Decimal("99.99")


def test_la_venta_queda_asociada_a_su_autor_y_momento():
    """RN-VEN-09."""
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=5)

    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 1}])

    assert venta.usuario_id == vendedor.id
    assert venta.fecha_hora is not None


def test_repetir_un_producto_en_dos_lineas_suma_las_cantidades():
    """Si la pantalla enviara el mismo producto dos veces, el stock
    debe validarse y descontarse por el TOTAL, no linea a linea: de lo
    contrario dos lineas de 3 pasarian la validacion con 5 unidades y
    dejarian el stock en -1."""
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=5)

    with pytest.raises(StockInsuficiente):
        _vender(
            vendedor,
            [
                {"producto_id": producto.id, "cantidad": 3},
                {"producto_id": producto.id, "cantidad": 3},
            ],
        )

    producto.refresh_from_db()
    assert producto.stock == 5


# ═════════════════════════════════════════════════════════════════════
# RN-VEN-02 — todo o nada
# ═════════════════════════════════════════════════════════════════════
def test_si_falta_stock_de_un_solo_producto_no_se_descuenta_ninguno():
    """El criterio central de T-4.3.

    La confirmacion es todo o nada: no existe la venta parcial.
    """
    vendedor = VendedorFactory()
    disponible = ProductoFactory(stock=10)
    escaso = ProductoFactory(stock=1)

    with pytest.raises(StockInsuficiente):
        _vender(
            vendedor,
            [
                {"producto_id": disponible.id, "cantidad": 2},
                {"producto_id": escaso.id, "cantidad": 5},
            ],
        )

    disponible.refresh_from_db()
    escaso.refresh_from_db()
    assert disponible.stock == 10  # intacto
    assert escaso.stock == 1
    assert Venta.objects.count() == 0  # RNF-09: tampoco quedo la venta


def test_el_error_de_stock_indica_que_falta_y_cuanto_hay():
    """El frontend debe poder explicarlo, no solo decir que fallo."""
    vendedor = VendedorFactory()
    escaso = ProductoFactory(nombre="Teclado mecánico", stock=2)

    with pytest.raises(StockInsuficiente) as excepcion:
        _vender(vendedor, [{"producto_id": escaso.id, "cantidad": 5}])

    faltante = excepcion.value.errores["items"][0]
    assert faltante["nombre"] == "Teclado mecánico"
    assert faltante["solicitado"] == 5
    assert faltante["disponible"] == 2


def test_no_se_puede_vender_un_producto_agotado():
    """RN-CAT-05."""
    vendedor = VendedorFactory()
    agotado = ProductoFactory(stock=0)

    with pytest.raises(StockInsuficiente):
        _vender(vendedor, [{"producto_id": agotado.id, "cantidad": 1}])


def test_no_se_puede_vender_un_producto_retirado_del_catalogo():
    """CU-CAT-04: un producto retirado no entra en ventas nuevas."""
    vendedor = VendedorFactory()
    retirado = ProductoFactory(stock=10, activo=False)

    with pytest.raises(ProductoNoDisponible):
        _vender(vendedor, [{"producto_id": retirado.id, "cantidad": 1}])

    assert Venta.objects.count() == 0


def test_una_venta_sin_productos_se_rechaza():
    """RN-VEN-01."""
    with pytest.raises(VentaSinItems):
        _vender(VendedorFactory(), [])


# ═════════════════════════════════════════════════════════════════════
# RN-VEN-04 — congelado de nombre y precio
# ═════════════════════════════════════════════════════════════════════
def test_cambiar_el_precio_despues_no_altera_la_venta_historica():
    """El criterio mas importante del congelado.

    Si el detalle se calculara al leer, subir el precio reescribiria
    el pasado y el historial dejaria de ser fiable.
    """
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10, precio=Decimal("350.00"))
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 2}])

    producto.precio = Decimal("999.00")
    producto.save(update_fields=["precio"])

    venta.refresh_from_db()
    linea = venta.items.first()
    assert linea.precio_unitario == Decimal("350.00")
    assert linea.subtotal == Decimal("700.00")
    assert venta.total == Decimal("700.00")


def test_cambiar_el_nombre_despues_no_altera_la_venta_historica():
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10, nombre="Teclado mecánico")
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 1}])

    producto.nombre = "Teclado mecánico v2"
    producto.save(update_fields=["nombre"])

    assert venta.items.first().producto_nombre == "Teclado mecánico"


def test_la_venta_copia_los_meses_de_garantia_de_cada_producto():
    """T-10.2 (RF-75): cada linea guarda la garantia vigente al vender,
    incluida la ausencia de garantia."""
    vendedor = VendedorFactory()
    con = ProductoFactory(stock=5, meses_garantia=12)
    sin = ProductoFactory(stock=5, meses_garantia=0)

    venta = _vender(
        vendedor,
        [{"producto_id": con.id, "cantidad": 1}, {"producto_id": sin.id, "cantidad": 1}],
    )

    meses = {l.producto_id: l.meses_garantia for l in venta.items.all()}
    assert meses == {con.id: 12, sin.id: 0}


@pytest.mark.parametrize("nuevos", [0, 6, 24])
def test_cambiar_los_meses_de_garantia_despues_no_altera_la_venta(nuevos):
    """T-10.2 (RN-VEN-12): ni quitarla, ni reducirla, ni ampliarla
    cambia lo que se pacto al vender."""
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10, meses_garantia=12)
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 1}])

    producto.meses_garantia = nuevos
    producto.save(update_fields=["meses_garantia"])

    venta.refresh_from_db()
    assert venta.items.first().meses_garantia == 12


def test_retirar_el_producto_despues_no_afecta_la_venta_historica():
    """CU-CAT-04 + RN-VEN-04 juntos."""
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10, nombre="Monitor 24")
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 1}])

    producto.activo = False
    producto.save(update_fields=["activo"])

    linea = venta.items.first()
    assert linea.producto_nombre == "Monitor 24"
    assert linea.precio_unitario == producto.precio


def test_el_precio_lo_toma_el_servidor_y_no_el_cliente():
    """Aceptar el precio del navegador permitiria alterarlo desde alli.

    El servicio solo recibe producto_id y cantidad; no hay forma de
    inyectar un precio.
    """
    import inspect

    from ventas import services

    firma = inspect.signature(services.registrar_venta)

    assert "precio" not in firma.parameters
    assert set(firma.parameters) == {
        "usuario",
        "cliente_nombre",
        "cliente_telefono",
        # T-11.4 (RF-79): el cliente registrado, opcional. Tampoco
        # lleva precio.
        "cliente_id",
        "items",
    }


# ═════════════════════════════════════════════════════════════════════
# RN-VEN-07, RN-VEN-08, RN-VEN-11 — anulacion
# ═════════════════════════════════════════════════════════════════════
def test_anular_devuelve_las_existencias_al_valor_previo():
    """El criterio central de T-4.5."""
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 4}])

    producto.refresh_from_db()
    assert producto.stock == 6

    anular_venta(venta=venta, usuario=vendedor, motivo="Cliente se arrepintió")

    producto.refresh_from_db()
    assert producto.stock == 10


def test_la_anulacion_registra_quien_cuando_y_por_que():
    """RN-VEN-07. Es el control que sustituye al limite de plazo."""
    vendedor = VendedorFactory()
    admin = AdministradorFactory()
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 1}])

    anulada = anular_venta(venta=venta, usuario=admin, motivo="Error de registro")

    assert anulada.estado == EstadoVenta.ANULADA
    assert anulada.anulada_por == admin
    assert anulada.fecha_anulacion is not None
    assert anulada.motivo_anulacion == "Error de registro"


def test_una_venta_anulada_no_se_anula_dos_veces():
    """RN-VEN-08.

    Sin esta comprobacion, anular dos veces devolveria las existencias
    por duplicado e inflaria el inventario.
    """
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 3}])
    anular_venta(venta=venta, usuario=vendedor, motivo="Primera")

    with pytest.raises(VentaYaAnulada):
        anular_venta(venta=venta, usuario=vendedor, motivo="Segunda")

    producto.refresh_from_db()
    assert producto.stock == 10  # devuelto una sola vez


def test_se_puede_anular_una_venta_antigua_sin_limite_de_plazo():
    """RN-VEN-11, decision PA-02."""
    from datetime import timedelta

    from django.utils import timezone

    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 2}])

    # Se envejece la venta un ano.
    Venta.objects.filter(pk=venta.pk).update(
        fecha_hora=timezone.now() - timedelta(days=365)
    )
    venta.refresh_from_db()

    anulada = anular_venta(venta=venta, usuario=vendedor, motivo="Error antiguo")

    assert anulada.estado == EstadoVenta.ANULADA
    producto.refresh_from_db()
    assert producto.stock == 10


def test_anular_devuelve_existencias_de_un_producto_ya_retirado():
    """El flujo alternativo de CU-VEN-03, que el borrado suave vuelve
    imposible de fallar: el producto nunca desaparece de la base, asi
    que la devolucion siempre puede hacerse."""
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 3}])

    producto.activo = False
    producto.save(update_fields=["activo"])

    anular_venta(venta=venta, usuario=vendedor, motivo="Producto retirado")

    producto.refresh_from_db()
    assert producto.stock == 10


def test_la_venta_anulada_conserva_su_detalle_congelado():
    """RNF-11: el historial no se borra al anular."""
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10, nombre="Router", precio=Decimal("420.00"))
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 2}])

    anular_venta(venta=venta, usuario=vendedor, motivo="Devolución")

    venta.refresh_from_db()
    linea = venta.items.first()
    assert linea.producto_nombre == "Router"
    assert linea.precio_unitario == Decimal("420.00")
    assert venta.total == Decimal("840.00")


# ═════════════════════════════════════════════════════════════════════
# Restricciones en la base (RNF-08, RN-VEN-07)
# ═════════════════════════════════════════════════════════════════════
def test_la_base_impide_dejar_una_venta_anulada_sin_trazabilidad():
    """RN-VEN-07 declarado en la base, no solo en el servicio."""
    vendedor = VendedorFactory()
    producto = ProductoFactory(stock=10)
    venta = _vender(vendedor, [{"producto_id": producto.id, "cantidad": 1}])

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE ventas_venta SET estado = 'ANULADA' WHERE id = %s",
                    [venta.id],
                )


def test_el_descuento_no_puede_dejar_el_stock_negativo_ni_por_sql_directo():
    """RNF-08, ultima linea de defensa.

    Si un cambio futuro rompiera la validacion del servicio, la base
    rechaza la operacion en lugar de corromper el inventario.
    """
    producto = ProductoFactory(stock=3)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Producto.objects.filter(pk=producto.pk).update(stock=-1)
