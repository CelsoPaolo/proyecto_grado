"""Verificacion del libro de movimientos (RN-MOV-03).

Para cada producto que tiene punto de partida en el libro —un ALTA o un
SALDO_INICIAL—, dos igualdades deben cumplirse siempre:

    SUM(cantidad de sus movimientos)        == stock
    stock_resultante de su ultimo movimiento == stock

Si alguna falla, algun camino cambio las existencias sin pasar por
inventario.services, o calculo un resultante contra un valor viejo.

Los productos SIN punto de partida no se juzgan: son los que crean las
fabricas de prueba escribiendo el stock directamente, y para ellos no
hay un libro completo contra el que comparar.

La usan la prueba de concurrencia (T-8.5) y el guardian que se ejecuta
tras cada prueba con base de datos (conftest.py).
"""

from django.db.models import OuterRef, Subquery, Sum

from catalogo.models import Producto
from inventario.models import TIPOS_DE_ORIGEN, MovimientoStock


def libros_descuadrados(productos=None):
    """Devuelve los productos cuyo libro no cuadra, con el detalle.

    Una lista vacia significa que todos cuadran. `productos` acota la
    comprobacion; por defecto se revisan todos los que tienen origen.
    """
    con_origen = MovimientoStock.objects.filter(tipo__in=TIPOS_DE_ORIGEN).values(
        "producto_id"
    )
    ultimo = (
        MovimientoStock.objects.filter(producto=OuterRef("pk"))
        .order_by("-id")
        .values("stock_resultante")[:1]
    )
    consulta = (
        Producto.objects.filter(pk__in=con_origen)
        .annotate(suma=Sum("movimientos__cantidad"), ultimo=Subquery(ultimo))
        .values("id", "nombre", "stock", "suma", "ultimo")
    )
    if productos is not None:
        consulta = consulta.filter(pk__in=[getattr(p, "pk", p) for p in productos])

    return [
        p
        for p in consulta.order_by("id")
        if p["suma"] != p["stock"] or p["ultimo"] != p["stock"]
    ]


def cadena_rota(producto):
    """Comprueba que cada movimiento parte del resultante del anterior.

    Es una propiedad mas fuerte que la suma: la suma puede cuadrar
    aunque un movimiento se haya calculado contra un valor viejo, si la
    escritura del stock compenso el error. La cadena no: si un ajuste
    leyo 10 cuando el stock ya era 9, su resultante no sera el del
    movimiento anterior mas su cantidad.

    El orden es el de insercion (id). Con la fila bloqueada, cada
    transaccion inserta su movimiento despues de obtener el bloqueo, asi
    que ese orden es el de serializacion.

    Devuelve el primer eslabon roto, o None si la cadena es correcta.
    """
    movimientos = MovimientoStock.objects.filter(producto=producto).order_by("id")
    anterior = None
    for m in movimientos:
        if anterior is not None and m.stock_resultante != anterior.stock_resultante + m.cantidad:
            return {
                "movimiento": m.pk,
                "tipo": m.tipo,
                "esperado": anterior.stock_resultante + m.cantidad,
                "registrado": m.stock_resultante,
            }
        anterior = m
    return None
