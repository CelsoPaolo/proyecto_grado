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

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from catalogo.models import Producto
from catalogo.services import umbral_stock_bajo
from servicios.models import ESTADOS_PENDIENTES, EstadoSolicitud, SolicitudServicio
from ventas.models import EstadoVenta, Venta

CERO = Decimal("0.00")


def _hoy():
    """Fecha local (America/La_Paz), no UTC.

    Usar la fecha UTC desplazaria el corte del dia cuatro horas: las
    ventas de la tarde apareceria como del dia siguiente.
    """
    return timezone.localdate()


def ventas_del_dia(fecha=None):
    """RN-IND-01 — solo las CONFIRMADAS; las anuladas quedan fuera.

    Una venta anulada devolvio sus existencias y no represento ingreso:
    contarla inflaria la caja del dia.
    """
    fecha = fecha or _hoy()

    agregado = Venta.objects.filter(
        fecha_hora__date=fecha, estado=EstadoVenta.CONFIRMADA
    ).aggregate(cantidad=Count("id"), importe=Sum("total"))

    return {
        "cantidad": agregado["cantidad"] or 0,
        "importe": agregado["importe"] or CERO,
    }


def servicios_del_dia(fecha=None):
    """RN-IND-04 — FINALIZADAS hoy, por su fecha de CIERRE.

    Que cuente por la fecha de cierre y no por la de registro es lo que
    hace correcto el indicador: un servicio que entro hace una semana y
    se cobra hoy es ingreso de HOY.

    Las canceladas quedan fuera aunque se hubieran cotizado
    (RN-SER-14).
    """
    fecha = fecha or _hoy()

    agregado = SolicitudServicio.objects.filter(
        fecha_cierre__date=fecha, estado=EstadoSolicitud.FINALIZADA
    ).aggregate(cantidad=Count("id"), importe=Sum("monto_cobrado"))

    return {
        "cantidad": agregado["cantidad"] or 0,
        "importe": agregado["importe"] or CERO,
    }


def ingreso_total(ventas, servicios):
    """RN-IND-05 — siempre desglosado por origen.

    La funcion devuelve las tres cifras juntas a proposito: no existe
    forma de obtener el total sin su desglose, que es exactamente lo
    que la regla pide garantizar.
    """
    de_ventas = ventas["importe"]
    de_servicios = servicios["importe"]

    return {
        "importe": de_ventas + de_servicios,
        "de_ventas": de_ventas,
        "de_servicios": de_servicios,
    }


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
    ventas = ventas_del_dia(fecha)
    servicios = servicios_del_dia(fecha)

    return {
        "fecha": fecha,
        "ventas_dia": ventas,
        "servicios_dia": servicios,
        "ingreso_total": ingreso_total(ventas, servicios),
        "servicios_pendientes": servicios_pendientes(),
        "stock_bajo": productos_con_stock_bajo(),
    }
