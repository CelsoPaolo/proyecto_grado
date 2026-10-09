"""T-12.1 — Calculo del reporte por rango (RN-REP-01 a RN-REP-03).

Datos limite en hora de Bolivia: los instantes se fijan con
timezone.now simulado, porque fecha_hora y fecha_registro son
auto_now_add.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest import mock
from zoneinfo import ZoneInfo

import pytest

from catalogo.tests.factories import ProductoFactory
from panel.reportes import calcular
from servicios.models import EstadoSolicitud
from servicios.tests.factories import SolicitudFactory
from usuarios.tests.factories import TecnicoFactory, VendedorFactory
from ventas.services import anular_venta, registrar_venta

pytestmark = pytest.mark.django_db

LA_PAZ = ZoneInfo("America/La_Paz")
DESDE, HASTA = date(2026, 10, 1), date(2026, 10, 7)


def _en(año, mes, dia, hora=12, minuto=0):
    return mock.patch(
        "django.utils.timezone.now",
        return_value=datetime(año, mes, dia, hora, minuto, tzinfo=LA_PAZ),
    )


def vender(precio, momento, vendedor=None):
    producto = ProductoFactory(stock=5, precio=Decimal(precio))
    with momento:
        return registrar_venta(
            usuario=vendedor or VendedorFactory(),
            cliente_nombre="Cliente",
            cliente_telefono="70000000",
            items=[{"producto_id": producto.pk, "cantidad": 1}],
        )


def servicio(estado, registrado, cierre=None, monto="0.00"):
    tecnico = TecnicoFactory()
    campos = {"registrada_por": tecnico, "estado": estado}
    if estado == EstadoSolicitud.FINALIZADA:
        campos |= {
            "observaciones": "Hecho",
            "monto_cobrado": Decimal(monto),
            "fecha_cierre": cierre,
            "cerrada_por": tecnico,
        }
    if estado == EstadoSolicitud.CANCELADA:
        campos |= {
            "motivo_cancelacion": "Desistió",
            "monto_cobrado": Decimal(monto),
            "fecha_cierre": cierre,
            "cerrada_por": tecnico,
        }
    with registrado:
        return SolicitudFactory(**campos)


def test_un_rango_sin_actividad_da_ceros():
    reporte = calcular(DESDE, HASTA)

    assert reporte["ventas"] == {"cantidad": 0, "importe": Decimal("0.00")}
    assert reporte["ingreso_total"]["importe"] == Decimal("0.00")


def test_una_venta_anulada_no_suma():
    vender("100.00", _en(2026, 10, 2))
    anulada = vender("999.00", _en(2026, 10, 3))
    anular_venta(venta=anulada, usuario=anulada.usuario, motivo="Devolución")

    assert calcular(DESDE, HASTA)["ventas"] == {"cantidad": 1, "importe": Decimal("100.00")}


def test_un_servicio_cancelado_no_suma():
    servicio(EstadoSolicitud.FINALIZADA, _en(2026, 10, 2), datetime(2026, 10, 2, 15, tzinfo=LA_PAZ), "250.00")
    servicio(EstadoSolicitud.CANCELADA, _en(2026, 10, 2), datetime(2026, 10, 3, 15, tzinfo=LA_PAZ), "500.00")

    assert calcular(DESDE, HASTA)["servicios"] == {"cantidad": 1, "importe": Decimal("250.00")}


def test_un_servicio_registrado_antes_del_rango_y_cerrado_dentro_si_suma():
    servicio(EstadoSolicitud.FINALIZADA, _en(2026, 9, 20), datetime(2026, 10, 5, 10, tzinfo=LA_PAZ), "300.00")

    assert calcular(DESDE, HASTA)["servicios"]["importe"] == Decimal("300.00")


def test_un_servicio_registrado_dentro_y_cerrado_despues_no_suma():
    servicio(EstadoSolicitud.FINALIZADA, _en(2026, 10, 6), datetime(2026, 10, 8, 10, tzinfo=LA_PAZ), "300.00")

    assert calcular(DESDE, HASTA)["servicios"]["cantidad"] == 0


def test_los_extremos_del_rango_en_hora_de_bolivia():
    """23:59 del ultimo dia cuenta; 00:00 del dia siguiente, no. Y la
    venta de las 00:00 del primer dia, si."""
    vender("10.00", _en(2026, 10, 1, 0, 0))  # dentro
    vender("20.00", _en(2026, 10, 7, 23, 59))  # dentro (ya 8 de octubre en UTC)
    vender("40.00", _en(2026, 10, 8, 0, 0))  # fuera
    vender("80.00", _en(2026, 9, 30, 23, 59))  # fuera

    assert calcular(DESDE, HASTA)["ventas"] == {"cantidad": 2, "importe": Decimal("30.00")}


def test_el_ingreso_total_viaja_desglosado():
    vender("100.00", _en(2026, 10, 2))
    servicio(EstadoSolicitud.FINALIZADA, _en(2026, 10, 2), datetime(2026, 10, 2, 18, tzinfo=LA_PAZ), "50.00")

    assert calcular(DESDE, HASTA)["ingreso_total"] == {
        "importe": Decimal("150.00"),
        "de_ventas": Decimal("100.00"),
        "de_servicios": Decimal("50.00"),
    }


def test_un_rango_de_un_dia():
    vender("100.00", _en(2026, 10, 2))
    vender("200.00", _en(2026, 10, 3))

    assert calcular(date(2026, 10, 2), date(2026, 10, 2))["ventas"]["importe"] == Decimal("100.00")
