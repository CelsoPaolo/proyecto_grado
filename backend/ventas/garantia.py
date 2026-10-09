"""Garantia de una venta (RN-VEN-12 a RN-VEN-16, plan.md 7.10).

`sumar_meses` es una funcion pura con la biblioteca estandar: no se
anade python-dateutil para una operacion de cinco lineas con sus
pruebas propias (plan.md 7.10).
"""

import calendar
from datetime import date

from django.utils import timezone


def sumar_meses(fecha, meses):
    """RN-VEN-13 — suma meses de calendario a una fecha.

    Si el dia no existe en el mes resultante se toma el ultimo de ese
    mes: 31 de enero + 1 mes = 28 de febrero (29 en bisiesto).
    """
    if meses < 0:
        raise ValueError("Los meses no pueden ser negativos.")
    indice = fecha.month - 1 + meses
    anio, mes = fecha.year + indice // 12, indice % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def fecha_local(momento):
    """La fecha de un instante en hora de Bolivia (TIME_ZONE).

    Una venta de las 22:00 en La Paz ya es del dia siguiente en UTC; para
    el cliente es del dia en que compro.
    """
    return timezone.localtime(momento).date()


def vencimiento(momento_de_la_venta, meses):
    """RN-VEN-13 — fecha de la venta en hora de Bolivia mas sus meses."""
    return sumar_meses(fecha_local(momento_de_la_venta), meses)
