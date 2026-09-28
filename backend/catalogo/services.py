"""Reglas de negocio del catalogo."""

from django.db import transaction
from django.db.models import ProtectedError

from core.exceptions import Codigo, ErrorDeNegocio


class CategoriaConProductos(ErrorDeNegocio):
    """RN-CAT-04: una categoria con productos no se elimina."""

    from rest_framework import status

    status_code = status.HTTP_409_CONFLICT
    codigo = Codigo.CATEGORIA_CON_PRODUCTOS
    default_detail = (
        "No se puede eliminar una categoría que tiene productos asociados. "
        "Reasigne o elimine primero esos productos."
    )


def umbral_stock_bajo():
    """Umbral global de existencias bajas (RN-CAT-07).

    Global para todo el catalogo, no por producto: es la decision
    PA-01. Aislarlo en esta funcion permitio que T-3.2 sustituyera el
    valor provisional por la configuracion real sin tocar ninguno de
    sus llamadores: ni el serializer ni la vista del catalogo saben de
    donde sale el numero.
    """
    from configuracion.services import obtener_umbral_stock_bajo

    return obtener_umbral_stock_bajo()


@transaction.atomic
def eliminar_categoria(*, categoria):
    """CU-CAT-01 (RF-08).

    La proteccion ya esta en la base (on_delete=PROTECT); aqui se
    traduce a un error de negocio legible en lugar de un fallo de
    integridad sin contexto.
    """
    try:
        categoria.delete()
    except ProtectedError as exc:
        raise CategoriaConProductos() from exc


@transaction.atomic
def retirar_producto(*, producto):
    """CU-CAT-04 (RF-11) - borrado suave.

    El producto deja de ofrecerse para ventas nuevas, pero su fila
    permanece: el historial que lo incluya sigue siendo legible
    (RN-VEN-04) y una venta anulada siempre puede devolverle las
    existencias (RN-VEN-07).
    """
    producto.activo = False
    producto.save(update_fields=["activo"])
    return producto

