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

from django.db.models import Count, F, Sum

from servicios.models import EstadoSolicitud, SolicitudServicio
from ventas.models import DetalleVenta, EstadoVenta, Venta

CERO = Decimal("0.00")

#: RN-REP-04: cuantos productos lista «los mas vendidos».
LIMITE_MAS_VENDIDOS = 10


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


def productos_mas_vendidos(desde, hasta):
    """RF-92 y RN-REP-04 — los diez con mas unidades en las ventas
    confirmadas del rango; a igualdad de unidades, el mayor importe.

    Se agrupa por PRODUCTO, no por el nombre congelado: en el rango el
    nombre pudo cambiar, y lo que identifica la fila es el producto. Se
    muestra su nombre actual y su codigo, que no cambia nunca (plan.md
    4.4). El id desempata al final para que el orden sea estable.
    """
    filas = (
        DetalleVenta.objects.filter(venta__in=ventas_confirmadas(desde, hasta))
        .values("producto_id")
        .annotate(
            codigo=F("producto__codigo"),
            nombre=F("producto__nombre"),
            unidades=Sum("cantidad"),
            importe=Sum("subtotal"),
        )
        .order_by("-unidades", "-importe", "producto_id")[:LIMITE_MAS_VENDIDOS]
    )
    return [dict(fila) for fila in filas]


def ventas_por_usuario(desde, hasta):
    """RF-93 y RN-REP-05 — cantidad e importe de las ventas confirmadas,
    por quien las registro. Sus importes suman el total de ventas."""
    filas = (
        ventas_confirmadas(desde, hasta)
        .values("usuario_id")
        .annotate(
            nombre_completo=F("usuario__nombre_completo"),
            cantidad=Count("id"),
            importe=Sum("total"),
        )
        .order_by("-importe", "nombre_completo", "usuario_id")
    )
    return [dict(fila) for fila in filas]


def servicios_por_estado(desde, hasta):
    """RF-94 y RN-REP-06 — solicitudes REGISTRADAS en el rango, por su
    estado actual, incluidas las canceladas como fila propia (PA-08).

    Solo recuentos, nunca importes: las canceladas aparecen para ver
    cuantas se perdieron, sin riesgo de sumarlas a un ingreso. Los
    cuatro estados viajan siempre, aunque valgan cero, para que pantalla,
    PDF y Excel muestren las mismas filas.
    """
    recuentos = dict(
        SolicitudServicio.objects.filter(fecha_registro__date__range=(desde, hasta))
        .values_list("estado")
        .annotate(n=Count("id"))
        .order_by()
    )
    return {estado: recuentos.get(estado, 0) for estado in EstadoSolicitud.values}


def calcular(desde, hasta, con_detalles=True):
    """RF-91 — el reporte del rango [desde, hasta], inclusivo en los dos extremos.

    Quien llama garantiza desde <= hasta; la API lo valida antes
    (RN-REP-01). El panel diario pide `con_detalles=False`: solo usa las
    tres cifras, y asi no paga las consultas de las tablas.
    """
    ventas = _cantidad_e_importe(ventas_confirmadas(desde, hasta), "total")
    servicios = _cantidad_e_importe(servicios_finalizados(desde, hasta), "monto_cobrado")
    reporte = {
        "desde": desde,
        "hasta": hasta,
        "ventas": ventas,
        "servicios": servicios,
        "ingreso_total": ingreso_desglosado(ventas, servicios),
    }
    if con_detalles:
        reporte["productos_mas_vendidos"] = productos_mas_vendidos(desde, hasta)
        reporte["ventas_por_usuario"] = ventas_por_usuario(desde, hasta)
        reporte["servicios_por_estado"] = servicios_por_estado(desde, hasta)
    return reporte
