"""Indicadores del panel (spec.md seccion 6.6, RN-IND-01 a RN-IND-05).

Cada indicador es una funcion con una sola responsabilidad, y las
cinco reglas quedan visibles en el codigo:

  RN-IND-01  ventas del dia: solo CONFIRMADAS de hoy
  RN-IND-02  servicios pendientes: REGISTRADA o EN_ATENCION, sin
             limite de fecha, con el desglose de sin cotizar
  RN-IND-03  existencias bajas segun el umbral GLOBAL vigente
  RN-IND-04  ingresos por servicios: FINALIZADAS hoy, por su fecha de
             CIERRE y no la de registro
  RN-IND-05  el total siempre viaja desglosado por origen

El panel no tiene modelos propios: solo agrega lo que ya existe.
"""

from django.db.models import Count, Q
from django.utils import timezone

from catalogo.models import Producto
from catalogo.services import umbral_stock_bajo
from panel import reportes
from servicios.models import ESTADOS_PENDIENTES, EstadoSolicitud, SolicitudServicio


def _hoy():
    """Fecha local (America/La_Paz), no UTC.

    Usar la fecha UTC desplazaria el corte del dia cuatro horas: las
    ventas de la tarde apareceria como del dia siguiente.
    """
    return timezone.localdate()


def ventas_del_dia(fecha=None):
    """RN-IND-01 — solo las CONFIRMADAS; las anuladas quedan fuera.

    Desde la v1.4 es el reporte de UN dia (RN-REP-08): el criterio vive
    en panel.reportes y aqui solo se elige el rango. Asi el panel y el
    reporte de hoy no pueden dar numeros distintos.
    """
    fecha = fecha or _hoy()
    return reportes.calcular(fecha, fecha)["ventas"]


def servicios_del_dia(fecha=None):
    """RN-IND-04 — FINALIZADAS hoy, por su fecha de CIERRE.

    Un servicio que entro hace una semana y se cobra hoy es ingreso de
    HOY. Las canceladas quedan fuera (RN-SER-14). El criterio vive en
    panel.reportes (RN-REP-08).
    """
    fecha = fecha or _hoy()
    return reportes.calcular(fecha, fecha)["servicios"]


def ingreso_total(ventas, servicios):
    """RN-IND-05 — siempre desglosado por origen (panel.reportes)."""
    return reportes.ingreso_desglosado(ventas, servicios)


def servicios_pendientes():
    """RN-IND-02 — sin limite de fecha, con el desglose de RF-49.

    `sin_cotizar` es el trabajo que espera al Administrador: son las
    que no podran cerrarse hasta que el fije el monto (RN-SER-13).
    """
    agregado = SolicitudServicio.objects.filter(
        estado__in=ESTADOS_PENDIENTES
    ).aggregate(
        total=Count("id"),
        registradas=Count("id", filter=Q(estado=EstadoSolicitud.REGISTRADA)),
        en_atencion=Count("id", filter=Q(estado=EstadoSolicitud.EN_ATENCION)),
        sin_cotizar=Count("id", filter=Q(monto_cobrado__isnull=True)),
    )

    return {clave: valor or 0 for clave, valor in agregado.items()}


def productos_con_stock_bajo(limite=10):
    """RN-IND-03 — contra el umbral GLOBAL vigente (RN-CAT-07).

    Se devuelve el umbral junto a la lista para que la interfaz pueda
    explicar el criterio sin conocerlo ella misma, igual que hace el
    catalogo con `stock_bajo`.

    Los productos retirados quedan fuera: no se reponen.
    """
    umbral = umbral_stock_bajo()

    consulta = Producto.objects.filter(activo=True, stock__lte=umbral).order_by(
        "stock", "nombre"
    )

    return {
        "umbral": umbral,
        "cantidad": consulta.count(),
        "productos": [
            {"id": p.id, "nombre": p.nombre, "stock": p.stock}
            for p in consulta[:limite]
        ],
    }


def resumen_del_panel(fecha=None):
    """CU-PAN-01 — todos los indicadores en una sola respuesta.

    Una sola llamada en vez de cinco: el panel se carga de golpe y no
    muestra cifras que aparecen a destiempo.
    """
    fecha = fecha or _hoy()
    # RN-REP-08: las cifras del dia SON el reporte del rango [hoy, hoy].
    # Una sola llamada a la misma funcion que usa /reportes.
    reporte = reportes.calcular(fecha, fecha)

    return {
        "fecha": fecha,
        "ventas_dia": reporte["ventas"],
        "servicios_dia": reporte["servicios"],
        "ingreso_total": reporte["ingreso_total"],
        "servicios_pendientes": servicios_pendientes(),
        "stock_bajo": productos_con_stock_bajo(),
    }
