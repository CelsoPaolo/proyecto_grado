"""Reglas de negocio de ventas.

Este modulo concentra lo tecnicamente mas delicado del sistema
(plan.md seccion 6): el descuento de existencias seguro ante
concurrencia (RNF-08), la confirmacion todo-o-nada (RN-VEN-02) y el
congelado de precios (RN-VEN-04).

Ninguna de esas tres reglas puede vivir en un serializer ni en una
vista: las tres combinan varias tablas dentro de una transaccion.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from catalogo.models import Producto
from inventario.models import TipoMovimiento
from inventario.services import registrar_movimiento
from ventas.exceptions import (
    ProductoNoDisponible,
    StockInsuficiente,
    VentaSinItems,
    VentaYaAnulada,
)
from ventas.models import DetalleVenta, EstadoVenta, Venta


def _bloquear_productos(ids):
    """Bloquea las filas de producto SIEMPRE en orden ascendente de pk.

    El orden no es un detalle estetico: si dos ventas simultaneas
    tomaran los mismos productos en orden inverso, cada una esperaria
    la fila que la otra ya tiene y quedarian en interbloqueo. Ordenar
    por clave primaria da a todas las transacciones la misma secuencia
    y lo hace imposible.

    `select_for_update()` mantiene las filas bloqueadas hasta el final
    de la transaccion: una segunda venta del mismo producto espera y,
    al pasar, lee el stock ya actualizado.
    """
    ordenados = sorted(set(ids))
    productos = Producto.objects.select_for_update().filter(id__in=ordenados)
    return {p.id: p for p in productos.order_by("id")}


@transaction.atomic
def registrar_venta(*, usuario, cliente_nombre, cliente_telefono, items):
    """CU-VEN-01 — Registrar y confirmar una venta.

    Implementa las tres capas de plan.md 6.3:

      1. transaction.atomic() + select_for_update() en orden de pk.
      2. Validacion con las filas YA bloqueadas: mientras se comprueba,
         nadie mas puede cambiarlas.
      3. Descuento con F() (RF-18), congelado de nombre y precio
         (RF-19) y un movimiento de stock por producto, escrito con la
         fila todavia bloqueada (RN-MOV-01, RNF-24).

    El precio lo toma el SERVIDOR del catalogo, nunca del cliente:
    aceptarlo del navegador permitiria alterarlo desde alli.

    Levanta StockInsuficiente si falta cualquier producto, y entonces
    la transaccion se revierte entera: la confirmacion es todo o nada
    (RN-VEN-02).
    """
    if not items:
        raise VentaSinItems()

    # ── 1. Bloqueo de filas, en orden determinista ───────────────────
    cantidades = {}
    for item in items:
        producto_id = item["producto_id"]
        cantidades[producto_id] = cantidades.get(producto_id, 0) + item["cantidad"]

    productos = _bloquear_productos(cantidades.keys())

    # ── 2. Validacion con las filas ya bloqueadas ────────────────────
    inexistentes = [pid for pid in cantidades if pid not in productos]
    if inexistentes:
        raise ProductoNoDisponible([f"#{pid}" for pid in inexistentes])

    retirados = [p.nombre for p in productos.values() if not p.activo]
    if retirados:
        raise ProductoNoDisponible(retirados)

    faltantes = [
        {
            "producto_id": pid,
            "nombre": productos[pid].nombre,
            "solicitado": cantidad,
            "disponible": productos[pid].stock,
        }
        for pid, cantidad in cantidades.items()
        if productos[pid].stock < cantidad
    ]
    if faltantes:
        # Nada se ha escrito todavia; el atomic revierte igualmente.
        raise StockInsuficiente(faltantes)

    # ── 3. Descuento, congelado y guardado ───────────────────────────
    venta = Venta.objects.create(
        cliente_nombre=cliente_nombre.strip(),
        cliente_telefono=cliente_telefono.strip(),
        usuario=usuario,
        estado=EstadoVenta.CONFIRMADA,
        total=Decimal("0.00"),
    )

    detalles = []
    total = Decimal("0.00")

    for producto_id, cantidad in cantidades.items():
        producto = productos[producto_id]
        precio = producto.precio  # precio vigente HOY
        subtotal = precio * cantidad
        total += subtotal

        detalles.append(
            DetalleVenta(
                venta=venta,
                producto=producto,
                # Congelado (RN-VEN-04): estas tres columnas no se
                # recalculan nunca al leer.
                producto_nombre=producto.nombre,
                precio_unitario=precio,
                cantidad=cantidad,
                subtotal=subtotal,
            )
        )

        # F() hace el descuento en la propia sentencia SQL. Con la fila
        # ya bloqueada y validada, no puede llevar el stock a negativo;
        # la restriccion CHECK de la base es la red final por si un
        # cambio futuro rompiera esta validacion (RNF-08).
        Producto.objects.filter(pk=producto_id).update(
            stock=F("stock") - cantidad
        )

        # El movimiento va en la MISMA transaccion y con la fila aun
        # bloqueada (RNF-24). `producto.stock` se leyo bajo ese bloqueo,
        # asi que restarle la cantidad da el resultante exacto: nadie
        # mas puede haber cambiado la fila entre medias.
        registrar_movimiento(
            producto=producto,
            tipo=TipoMovimiento.VENTA,
            cantidad=-cantidad,
            stock_resultante=producto.stock - cantidad,
            usuario=usuario,
            venta=venta,
        )

    DetalleVenta.objects.bulk_create(detalles)

    venta.total = total
    venta.save(update_fields=["total"])

    return venta


@transaction.atomic
def anular_venta(*, venta, usuario, motivo):
    """CU-VEN-03 — Anular una venta devolviendo las existencias.

    Mismo patron que el registro, en sentido inverso: bloqueo ordenado,
    devolucion con F(), un movimiento de anulacion por producto y todo
    dentro de una transaccion (RNF-10, RN-MOV-01, RNF-24).

    Sin limite de plazo (RN-VEN-11): la trazabilidad de quien anulo,
    cuando y por que es el control que sustituye a cualquier
    restriccion temporal.
    """
    # Se relee la venta con bloqueo: si dos anulaciones simultaneas
    # llegaran a la vez, la segunda vera el estado ya cambiado y sera
    # rechazada, en lugar de devolver las existencias por duplicado.
    venta = Venta.objects.select_for_update().get(pk=venta.pk)

    if venta.esta_anulada:
        raise VentaYaAnulada()

    # Se agrupa por producto, como al registrar: un movimiento por
    # producto devuelto, aunque la venta tuviera dos lineas del mismo.
    devoluciones = {}
    for linea in venta.items.all():
        devoluciones[linea.producto_id] = (
            devoluciones.get(linea.producto_id, 0) + linea.cantidad
        )

    # Antes se descartaba el resultado del bloqueo. Ahora hace falta: el
    # stock leido bajo bloqueo es lo que da el resultante exacto.
    productos = _bloquear_productos(devoluciones.keys())

    for producto_id in sorted(devoluciones):
        cantidad = devoluciones[producto_id]
        producto = productos[producto_id]

        Producto.objects.filter(pk=producto_id).update(
            stock=F("stock") + cantidad
        )
        registrar_movimiento(
            producto=producto,
            tipo=TipoMovimiento.ANULACION,
            cantidad=cantidad,
            stock_resultante=producto.stock + cantidad,
            usuario=usuario,
            venta=venta,
        )

    venta.estado = EstadoVenta.ANULADA
    venta.motivo_anulacion = motivo.strip()
    venta.anulada_por = usuario
    venta.fecha_anulacion = timezone.now()
    venta.save(
        update_fields=[
            "estado",
            "motivo_anulacion",
            "anulada_por",
            "fecha_anulacion",
        ]
    )

    return venta
