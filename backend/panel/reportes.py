"""Reportes por rango de fechas (spec.md 6.9, plan.md 4.4).

UNA sola funcion, `calcular(desde, hasta)`, produce el reporte. La vista
JSON, el PDF y el Excel la llaman y solo difieren en como PRESENTAN el
resultado (RN-REP-07): no hay consultas propias en los exportadores, asi
que las tres salidas coinciden por construccion y no por cuidado. El
panel diario es el reporte del rango [hoy, hoy] (RN-REP-08).

Fechas en hora de Bolivia: `__date` convierte cada instante a la zona
horaria del proyecto (TIME_ZONE) antes de compararlo. Una venta de las
23:59 del ultimo dia del rango cuenta; una de las 00:00 del dia
siguiente, no (RN-REP-01).

Reportes de operacion, no de personas: nada de aqui lee el carnet ni
otro dato personal de un cliente (RN-REP-09).
"""

from decimal import Decimal

from django.db.models import Count, Sum

from servicios.models import EstadoSolicitud, SolicitudServicio
from ventas.models import EstadoVenta, Venta

CERO = Decimal("0.00")


def ventas_confirmadas(desde, hasta):
    """RN-REP-02: las CONFIRMADAS registradas en el rango. Las anuladas
    quedan fuera aunque se registraran dentro (RN-IND-01)."""
    return Venta.objects.filter(
        estado=EstadoVenta.CONFIRMADA, fecha_hora__date__range=(desde, hasta)
    )


def servicios_finalizados(desde, hasta):
    """RN-REP-02: los FINALIZADOS cuya fecha de CIERRE cae en el rango,
    aunque se registraran antes. Los cancelados no suman nunca
    (RN-IND-04, RN-SER-14)."""
    return SolicitudServicio.objects.filter(
        estado=EstadoSolicitud.FINALIZADA, fecha_cierre__date__range=(desde, hasta)
    )


def _cantidad_e_importe(consulta, campo):
    agregado = consulta.aggregate(cantidad=Count("id"), importe=Sum(campo))
    return {"cantidad": agregado["cantidad"] or 0, "importe": agregado["importe"] or CERO}


def ingreso_desglosado(ventas, servicios):
    """RN-REP-03 y RN-IND-05: el total viaja SIEMPRE con su desglose. La
    funcion no ofrece forma de obtener el total sin el."""
    return {
        "importe": ventas["importe"] + servicios["importe"],
        "de_ventas": ventas["importe"],
        "de_servicios": servicios["importe"],
    }


def calcular(desde, hasta):
    """RF-91 — el reporte del rango [desde, hasta], inclusivo en los dos extremos.

    Quien llama garantiza desde <= hasta; la API lo valida antes
    (RN-REP-01).
    """
    ventas = _cantidad_e_importe(ventas_confirmadas(desde, hasta), "total")
    servicios = _cantidad_e_importe(servicios_finalizados(desde, hasta), "monto_cobrado")
    return {
        "desde": desde,
        "hasta": hasta,
        "ventas": ventas,
        "servicios": servicios,
        "ingreso_total": ingreso_desglosado(ventas, servicios),
    }
