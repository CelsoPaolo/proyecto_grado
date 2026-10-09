"""Escritura en el libro de movimientos de stock (plan.md 6.5).

Es el UNICO punto del sistema que crea movimientos. Los servicios que
cambian existencias —venta, anulacion, alta y ajuste— lo llaman dentro
de su propia transaccion, con la fila del producto ya bloqueada.
"""

from django.db import transaction

from inventario.models import MovimientoStock


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
