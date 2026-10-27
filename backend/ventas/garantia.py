"""Garantia de una venta (RN-VEN-12 a RN-VEN-16, plan.md 7.10).

`sumar_meses` es una funcion pura con la biblioteca estandar: no se
anade python-dateutil para una operacion de cinco lineas con sus
pruebas propias (plan.md 7.10).
"""

import calendar
from datetime import date

from django.utils import timezone

from ventas.exceptions import GarantiaDeVentaAnulada, VentaSinGarantia
from ventas.models import EstadoVenta, UnidadVendida

# ─────────────────────────────────────────────────────────────────────
# PUNTO DE EXTENSION: condiciones de la garantia
# ─────────────────────────────────────────────────────────────────────
#: Texto fijo de las condiciones que PC-Solution aplica a sus garantias
#: (que cubre, que no, donde presentarla). Lo definen el responsable del
#: proyecto y el dueno de la empresa; la spec no lo fija.
#:
#: Es el UNICO lugar donde pegarlo. Mientras este vacio, el PDF no
#: muestra la seccion «Condiciones de la garantia». Los saltos de linea
#: se respetan. Una prueba (test_garantia_pdf.py) comprueba los dos
#: casos.
CONDICIONES_DE_GARANTIA = ""


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

    con_garantia = [
        linea
        for linea in venta.items.select_related("producto").prefetch_related("unidades").order_by("id")
        if linea.meses_garantia > 0
    ]
    if not con_garantia:
        raise VentaSinGarantia()

    if es_garantia_por_unidad(venta):
        # RF-104 y RN-VEN-20 (v1.5): una fila por unidad, con SU codigo.
        return [
            {
                "producto": linea.producto_nombre,
                "codigo": unidad.codigo,
                "meses": linea.meses_garantia,
                "vence": vencimiento(venta.fecha_hora, linea.meses_garantia),
            }
            for linea in con_garantia
            for unidad in linea.unidades.all()
        ]

    # Venta anterior a la v1.5, sin codigos de unidad (RNF-30): el
    # formato de siempre, una fila por linea.
    return [
        {
            "producto": linea.producto_nombre,
            # El codigo no se congela: no cambia nunca (RN-CAT-08), asi
            # que leerlo del producto da siempre el mismo (plan.md 3.5).
            "codigo": linea.producto.codigo,
            "cantidad": linea.cantidad,
            "meses": linea.meses_garantia,
            "vence": vencimiento(venta.fecha_hora, linea.meses_garantia),
        }
        for linea in con_garantia
    ]


def es_garantia_por_unidad(venta):
    """RN-VEN-20 — si la venta tiene codigos de unidad (desde la v1.5).

    Lo decide la venta guardada, no la fecha: una venta de la v1.5 los
    tiene siempre (RN-VEN-18), y una anterior no los tendra nunca.
    """
    return UnidadVendida.objects.filter(detalle__venta=venta).exists()
