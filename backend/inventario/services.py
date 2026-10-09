"""Escritura en el libro de movimientos de stock (plan.md 6.5).

Es el UNICO punto del sistema que crea movimientos. Los servicios que
cambian existencias —venta, anulacion, alta y ajuste— lo llaman dentro
de su propia transaccion, con la fila del producto ya bloqueada. Con
los cuatro caminos pasando por aqui, todo cambio de existencias deja su
movimiento (RF-81).
"""

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404

from catalogo.models import Producto
from core.exceptions import ErrorDeNegocio
from inventario.exceptions import AjusteSinDiferencia
from inventario.models import MovimientoStock, TipoMovimiento


class MovimientoFueraDeTransaccion(Exception):
    """Se intento registrar un movimiento sin una transaccion abierta.

    RNF-24 exige que el movimiento y el cambio de existencias sean una
    sola operacion atomica. Un movimiento escrito fuera de transaccion
    podria quedar guardado aunque el cambio de stock fallara despues, y
    el libro dejaria de cuadrar. Es un error de programacion, no algo
    que pueda provocar un usuario: por eso no es un ErrorDeNegocio.
    """


def registrar_movimiento(
    *,
    producto,
    tipo,
    cantidad,
    stock_resultante,
    usuario=None,
    venta=None,
    motivo="",
):
    """Anota un cambio de existencias en el libro (RN-MOV-01).

    `stock_resultante` lo calcula quien llama, a partir del valor que
    leyo con la fila BLOQUEADA por select_for_update(). Con la fila
    bloqueada ninguna otra transaccion puede cambiarla hasta el COMMIT,
    asi que ese valor es exacto sin volver a leer (plan.md 6.5).

    Las combinaciones invalidas —una venta sin su venta, un ajuste sin
    motivo, un resultante negativo— las rechaza la base con sus CHECK
    (T-8.1); este servicio no las duplica.
    """
    if not transaction.get_connection().in_atomic_block:
        raise MovimientoFueraDeTransaccion(
            "Un movimiento de stock solo puede registrarse dentro de la "
            "misma transaccion que cambia las existencias (RNF-24)."
        )

    return MovimientoStock.objects.create(
        producto=producto,
        tipo=tipo,
        cantidad=cantidad,
        stock_resultante=stock_resultante,
        usuario=usuario,
        venta=venta,
        motivo=motivo,
    )


def _error_de_campo(campo, mensaje):
    """400 con el error junto al campo que lo origina (RNF-15)."""
    return ErrorDeNegocio(detalle=mensaje, errores={campo: [mensaje]})


@transaction.atomic
def ajustar_existencias(*, producto_id, cantidad_real, motivo, usuario):
    """CU-CAT-07 — Ajustar las existencias a lo contado (RN-MOV-05).

    Sustituye al PATCH generico, que escribia un valor absoluto leido
    antes y SIN bloquear la fila. Con libro de movimientos eso deja de
    ser aceptable: si entre que el Administrador abre el formulario y
    lo confirma se vende una unidad, la diferencia calculada contra el
    valor que vio dejaria esa venta fuera del libro (plan.md 6.5).

    Por eso la diferencia se calcula aqui, contra las existencias de la
    fila YA BLOQUEADA. La que muestre la interfaz es orientativa; la que
    se registra es esta.
    """
    motivo = (motivo or "").strip()
    if not motivo:
        raise _error_de_campo("motivo", "Indique el motivo del ajuste.")

    # bool es subclase de int en Python: sin esta exclusion, True se
    # aceptaria como una existencia de 1.
    if isinstance(cantidad_real, bool) or not isinstance(cantidad_real, int):
        raise _error_de_campo(
            "cantidad_real", "La cantidad real debe ser un número entero."
        )
    if cantidad_real < 0:
        raise _error_de_campo(
            "cantidad_real", "La cantidad real no puede ser negativa."
        )

    # Bloqueo de la fila: una venta simultanea espera a que termine el
    # ajuste, o el ajuste a que termine la venta. En los dos ordenes el
    # libro cuadra (RNF-24).
    producto = get_object_or_404(
        Producto.objects.select_for_update(), pk=producto_id
    )

    diferencia = cantidad_real - producto.stock
    if diferencia == 0:
        raise AjusteSinDiferencia()

    Producto.objects.filter(pk=producto.pk).update(
        stock=F("stock") + diferencia
    )
    movimiento = registrar_movimiento(
        producto=producto,
        tipo=TipoMovimiento.AJUSTE,
        cantidad=diferencia,
        stock_resultante=cantidad_real,
        usuario=usuario,
        motivo=motivo,
    )
    return movimiento
