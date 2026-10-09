"""Garantia de una venta (RN-VEN-12 a RN-VEN-16, plan.md 7.10).

`sumar_meses` es una funcion pura con la biblioteca estandar: no se
anade python-dateutil para una operacion de cinco lineas con sus
pruebas propias (plan.md 7.10).
"""

import calendar
from datetime import date

from django.utils import timezone

from ventas.exceptions import GarantiaDeVentaAnulada, VentaSinGarantia
from ventas.models import EstadoVenta


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


def lineas_con_garantia(venta):
    """RN-VEN-14 — las lineas que la garantia lista, con su vencimiento.

    Todo sale de la venta GUARDADA: los meses son los congelados en la
    linea (RN-VEN-12) y la fecha es la de la venta. Por eso emitirla
    varias veces da siempre el mismo contenido, aunque el producto haya
    cambiado despues (CU-VEN-04).

    Lanza los dos rechazos de RF-78: venta anulada, o ninguna linea con
    garantia.
    """
    if venta.estado == EstadoVenta.ANULADA:
        raise GarantiaDeVentaAnulada()

    lineas = [
        {
            "producto": linea.producto_nombre,
            # El codigo no se congela: no cambia nunca (RN-CAT-08), asi
            # que leerlo del producto da siempre el mismo (plan.md 3.5).
            "codigo": linea.producto.codigo,
            "cantidad": linea.cantidad,
            "meses": linea.meses_garantia,
            "vence": vencimiento(venta.fecha_hora, linea.meses_garantia),
        }
        for linea in venta.items.select_related("producto").order_by("id")
        if linea.meses_garantia > 0
    ]
    if not lineas:
        raise VentaSinGarantia()
    return lineas
