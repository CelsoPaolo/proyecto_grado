"""Errores de negocio del inventario (plan.md 4.3)."""

from rest_framework import status

from core.exceptions import Codigo, ErrorDeNegocio


class AjusteSinDiferencia(ErrorDeNegocio):
    """RN-MOV-05: la cantidad contada ya es la registrada.

    409 y no 400: el dato es valido, pero no hay nada que ajustar. Un
    movimiento de cantidad cero no explicaria ningun cambio y solo
    ensuciaria el libro; por eso tambien lo rechaza la base (T-8.1).
    """

    status_code = status.HTTP_409_CONFLICT
    codigo = Codigo.AJUSTE_SIN_DIFERENCIA
    default_detail = (
        "La cantidad indicada ya es la registrada: no hay nada que ajustar."
    )
