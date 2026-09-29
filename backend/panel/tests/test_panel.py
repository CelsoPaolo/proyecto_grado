"""T-6.1 y T-6.2 — Panel de indicadores (RN-IND-01 a RN-IND-05).

Las pruebas se concentran en los casos LIMITE, que son los que hacen
correcto un indicador: la venta anulada que no debe sumar, el servicio
cancelado que tampoco, y el que entro ayer pero se cobro hoy.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.tests.factories import ProductoFactory
from configuracion.models import ConfiguracionSistema
from panel.services import resumen_del_panel
from servicios.models import EstadoSolicitud, SolicitudServicio
from servicios.services import (
    cancelar_solicitud,
    cotizar_solicitud,
    finalizar_solicitud,
    iniciar_atencion,
    registrar_solicitud,
)
from servicios.models import TipoServicio
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)
from ventas.models import Venta
from ventas.services import anular_venta, registrar_venta

pytestmark = pytest.mark.django_db

URL = "/api/v1/panel/resumen"


def _autenticar(usuario):
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


@pytest.fixture
def como_admin():
    return _autenticar(AdministradorFactory())


def _vender(precio="100.00", cantidad=1, usuario=None):
    producto = ProductoFactory(stock=100, precio=Decimal(precio))
    return registrar_venta(
        usuario=usuario or VendedorFactory(),
        cliente_nombre="Cliente",
        cliente_telefono="70000000",
        items=[{"producto_id": producto.id, "cantidad": cantidad}],
    )


def _servicio_finalizado(monto="250.00", usuario=None):
    usuario = usuario or TecnicoFactory()
    solicitud = registrar_solicitud(
        usuario=usuario,
        cliente_nombre="Cliente",
        cliente_telefono="70000000",
        tipo=TipoServicio.REPARACION,
        descripcion="No enciende",
    )
    iniciar_atencion(solicitud=solicitud, usuario=usuario)
    cotizar_solicitud(
        solicitud=solicitud, usuario=AdministradorFactory(), monto=monto
    )
    return finalizar_solicitud(
        solicitud=solicitud, usuario=usuario, observaciones="Reparado."
    )


# ═════════════════════════════════════════════════════════════════════
# RN-IND-01 — ventas del dia
# ═════════════════════════════════════════════════════════════════════
def test_las_ventas_del_dia_suman_las_confirmadas():
    _vender("100.00")
    _vender("250.50")

    resumen = resumen_del_panel()

    assert resumen["ventas_dia"]["cantidad"] == 2
    assert resumen["ventas_dia"]["importe"] == Decimal("350.50")


def test_una_venta_anulada_no_cuenta_en_el_dia():
    """El caso limite de RN-IND-01.

    Una venta anulada devolvio sus existencias y no represento
    ingreso: contarla inflaria la caja del dia.
    """
    vendedor = VendedorFactory()
    _vender("100.00", usuario=vendedor)
    anulada = _vender("999.00", usuario=vendedor)
    anular_venta(venta=anulada, usuario=vendedor, motivo="Error")

    resumen = resumen_del_panel()

    assert resumen["ventas_dia"]["cantidad"] == 1
    assert resumen["ventas_dia"]["importe"] == Decimal("100.00")


def test_una_venta_de_ayer_no_cuenta_hoy():
    venta = _vender("500.00")
    Venta.objects.filter(pk=venta.pk).update(
        fecha_hora=timezone.now() - timedelta(days=1)
    )

    resumen = resumen_del_panel()

    assert resumen["ventas_dia"]["cantidad"] == 0
    assert resumen["ventas_dia"]["importe"] == Decimal("0.00")


def test_sin_ventas_el_importe_es_cero_y_no_nulo():
    """Un None romperia la suma del total y la interfaz mostraria
    'null' en lugar de Bs 0,00."""
    resumen = resumen_del_panel()

    assert resumen["ventas_dia"]["importe"] == Decimal("0.00")
    assert resumen["ingreso_total"]["importe"] == Decimal("0.00")


# ═════════════════════════════════════════════════════════════════════
# RN-IND-04 — ingresos por servicios
# ═════════════════════════════════════════════════════════════════════
def test_los_servicios_del_dia_suman_los_finalizados():
    _servicio_finalizado("250.00")
    _servicio_finalizado("150.00")

    resumen = resumen_del_panel()

    assert resumen["servicios_dia"]["cantidad"] == 2
    assert resumen["servicios_dia"]["importe"] == Decimal("400.00")


def test_un_servicio_registrado_ayer_y_cerrado_hoy_cuenta_HOY():
    """El criterio central de RN-IND-04.

    El indicador cuenta por la fecha de CIERRE, no la de registro: un
    servicio que entro hace una semana y se cobra hoy es ingreso de
    hoy. Contarlo por la fecha de registro dejaria el dinero cobrado
    fuera de la caja del dia.
    """
    solicitud = _servicio_finalizado("300.00")
    SolicitudServicio.objects.filter(pk=solicitud.pk).update(
        fecha_registro=timezone.now() - timedelta(days=7)
    )

    resumen = resumen_del_panel()

    assert resumen["servicios_dia"]["cantidad"] == 1
    assert resumen["servicios_dia"]["importe"] == Decimal("300.00")


def test_un_servicio_cerrado_ayer_no_cuenta_hoy():
    solicitud = _servicio_finalizado("300.00")
    SolicitudServicio.objects.filter(pk=solicitud.pk).update(
        fecha_cierre=timezone.now() - timedelta(days=1)
    )

    resumen = resumen_del_panel()

    assert resumen["servicios_dia"]["cantidad"] == 0


def test_un_servicio_cancelado_no_cuenta_aunque_estuviera_cotizado():
    """RN-SER-14 visto desde el panel."""
    tecnico = TecnicoFactory()
    solicitud = registrar_solicitud(
        usuario=tecnico,
        cliente_nombre="Cliente",
        cliente_telefono="70000000",
        tipo=TipoServicio.REPARACION,
        descripcion="X",
    )
    cotizar_solicitud(
        solicitud=solicitud, usuario=AdministradorFactory(), monto="500.00"
    )
    cancelar_solicitud(solicitud=solicitud, usuario=tecnico, motivo="Desistió")

    resumen = resumen_del_panel()

    assert resumen["servicios_dia"]["cantidad"] == 0
    assert resumen["servicios_dia"]["importe"] == Decimal("0.00")


def test_un_servicio_cotizado_en_cero_cuenta_como_finalizado_sin_aportar():
    """Garantía: suma a la cantidad, no al importe."""
    _servicio_finalizado("0.00")

    resumen = resumen_del_panel()

    assert resumen["servicios_dia"]["cantidad"] == 1
    assert resumen["servicios_dia"]["importe"] == Decimal("0.00")


# ═════════════════════════════════════════════════════════════════════
# RN-IND-05 — el total siempre desglosado
# ═════════════════════════════════════════════════════════════════════
def test_el_ingreso_total_suma_ambos_origenes():
    _vender("800.00")
    _servicio_finalizado("200.00")

    total = resumen_del_panel()["ingreso_total"]

    assert total["importe"] == Decimal("1000.00")
    assert total["de_ventas"] == Decimal("800.00")
    assert total["de_servicios"] == Decimal("200.00")


def test_el_total_nunca_viaja_sin_su_desglose(como_admin):
    """El criterio central de RN-IND-05.

    No existe forma de pedir el agregado solo: los tres campos van
    siempre juntos en la respuesta.
    """
    _vender("500.00")

    respuesta = como_admin.get(URL)
    total = respuesta.data["ingreso_total"]

    assert set(total) == {"importe", "de_ventas", "de_servicios"}


def test_el_desglose_cuadra_con_el_total(como_admin):
    _vender("333.33")
    _servicio_finalizado("166.67")

    total = como_admin.get(URL).data["ingreso_total"]

    assert Decimal(total["de_ventas"]) + Decimal(total["de_servicios"]) == Decimal(
        total["importe"]
    )


# ═════════════════════════════════════════════════════════════════════
# RN-IND-02 — servicios pendientes
# ═════════════════════════════════════════════════════════════════════
def test_los_pendientes_no_tienen_limite_de_fecha():
    """RN-IND-02: un servicio de hace un mes sigue pendiente."""
    tecnico = TecnicoFactory()
    antigua = registrar_solicitud(
        usuario=tecnico,
        cliente_nombre="Cliente",
        cliente_telefono="70000000",
        tipo=TipoServicio.REPARACION,
        descripcion="X",
    )
    SolicitudServicio.objects.filter(pk=antigua.pk).update(
        fecha_registro=timezone.now() - timedelta(days=30)
    )

    pendientes = resumen_del_panel()["servicios_pendientes"]

    assert pendientes["total"] == 1


def test_los_pendientes_se_desglosan_por_estado_y_por_cotizacion():
    """RF-49: `sin_cotizar` es el trabajo que espera al Administrador."""
    tecnico = TecnicoFactory()
    admin = AdministradorFactory()

    # Registrada y sin cotizar.
    registrar_solicitud(
        usuario=tecnico, cliente_nombre="A", cliente_telefono="7",
        tipo=TipoServicio.REPARACION, descripcion="X",
    )
    # En atencion y ya cotizada.
    segunda = registrar_solicitud(
        usuario=tecnico, cliente_nombre="B", cliente_telefono="7",
        tipo=TipoServicio.REPARACION, descripcion="X",
    )
    iniciar_atencion(solicitud=segunda, usuario=tecnico)
    cotizar_solicitud(solicitud=segunda, usuario=admin, monto="100.00")

    pendientes = resumen_del_panel()["servicios_pendientes"]

    assert pendientes["total"] == 2
    assert pendientes["registradas"] == 1
    assert pendientes["en_atencion"] == 1
    assert pendientes["sin_cotizar"] == 1


def test_una_solicitud_cerrada_deja_de_estar_pendiente():
    _servicio_finalizado()

    assert resumen_del_panel()["servicios_pendientes"]["total"] == 0


# ═════════════════════════════════════════════════════════════════════
# RN-IND-03 — existencias bajas
# ═════════════════════════════════════════════════════════════════════
def test_el_stock_bajo_usa_el_umbral_global_vigente():
    ProductoFactory(nombre="Escaso", stock=2)
    ProductoFactory(nombre="Abundante", stock=50)

    stock = resumen_del_panel()["stock_bajo"]

    assert stock["umbral"] == 5
    assert stock["cantidad"] == 1
    assert stock["productos"][0]["nombre"] == "Escaso"


def test_cambiar_el_umbral_cambia_el_indicador():
    """RN-CAT-07 y RN-IND-03 juntos."""
    ProductoFactory(nombre="Con ocho", stock=8)

    assert resumen_del_panel()["stock_bajo"]["cantidad"] == 0

    configuracion = ConfiguracionSistema.obtener()
    configuracion.umbral_stock_bajo = 10
    configuracion.save(update_fields=["umbral_stock_bajo"])

    assert resumen_del_panel()["stock_bajo"]["cantidad"] == 1


def test_un_producto_retirado_no_figura_en_existencias_bajas():
    """No se repone: avisar de el seria ruido."""
    ProductoFactory(nombre="Retirado", stock=0, activo=False)

    assert resumen_del_panel()["stock_bajo"]["cantidad"] == 0


def test_los_productos_escasos_se_ordenan_del_mas_urgente():
    ProductoFactory(nombre="Con tres", stock=3)
    ProductoFactory(nombre="Agotado", stock=0)
    ProductoFactory(nombre="Con uno", stock=1)

    productos = resumen_del_panel()["stock_bajo"]["productos"]

    assert [p["nombre"] for p in productos] == ["Agotado", "Con uno", "Con tres"]


def test_la_lista_de_productos_escasos_esta_acotada():
    """El panel resume; el catalogo tiene la lista completa. Sin tope,
    un inventario entero por debajo del umbral haria la respuesta
    inmanejable."""
    ProductoFactory.create_batch(15, stock=1)

    stock = resumen_del_panel()["stock_bajo"]

    assert stock["cantidad"] == 15
    assert len(stock["productos"]) == 10


# ═════════════════════════════════════════════════════════════════════
# T-6.2 — API (RF-48 a RF-51, RF-65, RF-66)
# ═════════════════════════════════════════════════════════════════════
def test_el_resumen_trae_los_cinco_indicadores(como_admin):
    respuesta = como_admin.get(URL)

    assert respuesta.status_code == status.HTTP_200_OK
    assert set(respuesta.data) == {
        "fecha",
        "ventas_dia",
        "servicios_dia",
        "ingreso_total",
        "servicios_pendientes",
        "stock_bajo",
    }


def test_los_importes_viajan_como_cadena_decimal(como_admin):
    _vender("1250.50")

    respuesta = como_admin.get(URL)

    assert respuesta.data["ventas_dia"]["importe"] == "1250.50"
    assert isinstance(respuesta.data["ventas_dia"]["importe"], str)


@pytest.mark.parametrize("fabrica", [VendedorFactory, TecnicoFactory])
def test_los_otros_roles_no_acceden_al_panel(fabrica):
    """spec.md matriz 4.4: el panel es solo del Administrador."""
    cliente = _autenticar(fabrica())

    assert cliente.get(URL).status_code == status.HTTP_403_FORBIDDEN


def test_sin_autenticar_no_se_accede_al_panel():
    assert APIClient().get(URL).status_code == status.HTTP_401_UNAUTHORIZED


def test_el_panel_no_admite_escritura(como_admin):
    """Es un recurso de solo lectura: agrega, no modifica."""
    for metodo in ("post", "patch", "delete"):
        respuesta = getattr(como_admin, metodo)(URL, {}, format="json")
        assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ═════════════════════════════════════════════════════════════════════
# T-6.4 — Rendimiento (RNF-17)
# ═════════════════════════════════════════════════════════════════════
def test_el_panel_usa_un_numero_fijo_de_consultas(django_assert_num_queries):
    """RNF-17: el coste no debe crecer con el volumen de datos.

    Cinco indicadores, seis consultas: una por agregado mas la cuenta
    de productos escasos. Si alguien sustituyera un aggregate por un
    bucle en Python, este numero se dispararia y la prueba lo
    detectaria antes de que el panel se volviera lento en produccion.
    """
    for _ in range(5):
        _vender("100.00")
        _servicio_finalizado("50.00")
    ProductoFactory.create_batch(5, stock=1)

    with django_assert_num_queries(6):
        resumen_del_panel()


def test_el_coste_no_crece_con_el_volumen(django_assert_num_queries):
    """La contraprueba del anterior: con el triple de datos, el mismo
    numero de consultas."""
    for _ in range(15):
        _vender("100.00")
        _servicio_finalizado("50.00")
    ProductoFactory.create_batch(15, stock=1)

    with django_assert_num_queries(6):
        resumen_del_panel()


def test_los_indicadores_no_recorren_filas_en_python():
    """Prueba estructural.

    Sumar en Python con un bucle daria el mismo resultado y pasaria las
    demas pruebas, pero el panel se degradaria conforme creciera el
    historial. Aqui se comprueba que la suma la hace la base.
    """
    import inspect

    from panel import services

    codigo = inspect.getsource(services)

    assert "aggregate" in codigo
    assert "Sum(" in codigo
    # Ningun bucle sobre ventas o solicitudes para acumular importes.
    assert "for venta in" not in codigo
    assert "for solicitud in" not in codigo
