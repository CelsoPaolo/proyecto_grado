"""T-10.3 — Calculo del vencimiento de la garantia (RN-VEN-13).

Funcion pura: no necesita base de datos.
"""

from datetime import date, datetime, timezone as tz
from zoneinfo import ZoneInfo

import pytest

from ventas.garantia import sumar_meses, vencimiento


@pytest.mark.parametrize(
    ("fecha", "meses", "esperado"),
    [
        # Los casos del «hecho cuando» de T-10.3
        (date(2026, 1, 31), 1, date(2026, 2, 28)),  # dia inexistente → ultimo del mes
        (date(2028, 1, 31), 1, date(2028, 2, 29)),  # bisiesto
        (date(2026, 11, 30), 3, date(2027, 2, 28)),  # cruza el año y cae en febrero
        (date(2026, 3, 15), 12, date(2027, 3, 15)),  # un año exacto
        (date(2026, 3, 15), 0, date(2026, 3, 15)),  # cero meses: la misma fecha
        # Bordes adicionales
        (date(2026, 12, 15), 1, date(2027, 1, 15)),  # diciembre → enero
        (date(2026, 8, 31), 1, date(2026, 9, 30)),  # mes de 30 dias
        (date(2028, 2, 29), 12, date(2029, 2, 28)),  # 29 de febrero sin bisiesto al año siguiente
        (date(2026, 1, 31), 25, date(2028, 2, 29)),  # dos años y un mes, a bisiesto
        (date(2026, 5, 31), 120, date(2036, 5, 31)),  # diez años
    ],
)
def test_sumar_meses(fecha, meses, esperado):
    assert sumar_meses(fecha, meses) == esperado


def test_meses_negativos_es_un_error():
    with pytest.raises(ValueError):
        sumar_meses(date(2026, 1, 1), -1)


def test_el_vencimiento_cuenta_desde_el_dia_de_la_venta_en_bolivia():
    """Una venta del 31 de enero a las 22:00 en La Paz es del 1 de febrero
    en UTC. El cliente compro el 31: con un mes, vence el 28 de febrero, no
    el 1 de marzo."""
    venta = datetime(2026, 1, 31, 22, 0, tzinfo=ZoneInfo("America/La_Paz"))
    assert venta.astimezone(tz.utc).date() == date(2026, 2, 1)

    assert vencimiento(venta, 1) == date(2026, 2, 28)
