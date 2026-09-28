"""Errores de negocio de ventas (T-4.2)."""

from rest_framework import status

from core.exceptions import Codigo, ErrorDeNegocio


class StockInsuficiente(ErrorDeNegocio):
    """RN-VEN-02 — la confirmacion es todo o nada.

    Se responde 422 y no 400 porque es el unico error que el frontend
    debe mostrar de forma enriquecida: qué producto falta y cuánto hay
    disponible, no como un mensaje de validacion cualquiera
    (plan.md 4.2).

    Cuando se lanza, la transaccion se revierte entera: NINGUN producto
    queda descontado.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    codigo = Codigo.STOCK_INSUFICIENTE
    default_detail = "No hay existencias suficientes para confirmar la venta."

    def __init__(self, faltantes):
        """`faltantes` lista qué falta de cada producto insuficiente."""
        super().__init__(self.default_detail, errores={"items": faltantes})


class VentaYaAnulada(ErrorDeNegocio):
    """RN-VEN-08 — una venta anulada no se anula otra vez.

    Sin esta comprobacion, anular dos veces devolveria las existencias
    por duplicado e inflaria el inventario.
    """

    status_code = status.HTTP_409_CONFLICT
    codigo = Codigo.VENTA_YA_ANULADA
    default_detail = "Esta venta ya fue anulada."


class VentaSinItems(ErrorDeNegocio):
    """RN-VEN-01 — una venta tiene al menos una linea."""

    codigo = Codigo.VALIDACION
    default_detail = "La venta debe incluir al menos un producto."


class ProductoNoDisponible(ErrorDeNegocio):
    """RN-CAT-05 — un producto retirado no se agrega a una venta nueva."""

    codigo = Codigo.VALIDACION
    default_detail = "Alguno de los productos ya no está disponible para la venta."

    def __init__(self, nombres):
        detalle = (
            "Estos productos ya no están disponibles para la venta: "
            + ", ".join(nombres)
            + "."
        )
        super().__init__(detalle, errores={"items": list(nombres)})
