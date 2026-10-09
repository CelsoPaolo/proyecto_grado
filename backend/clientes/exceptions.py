"""Errores de negocio de clientes (plan.md 4.3)."""

from rest_framework import status

from core.exceptions import Codigo, ErrorDeNegocio


class CarnetDuplicado(ErrorDeNegocio):
    """RN-CLI-02 y RF-88 — el carnet ya pertenece a otro cliente.

    409 y no 400, como en plan.md 4.4: el dato es valido, pero choca con
    uno existente. El mensaje NO dice de quien es el carnet: seria
    revelar un dato personal a quien solo lo tecleo (RN-CLI-06).
    """

    status_code = status.HTTP_409_CONFLICT
    codigo = Codigo.CARNET_DUPLICADO
    default_detail = "Ya hay un cliente registrado con ese carnet."

    def __init__(self):
        super().__init__(self.default_detail, errores={"carnet": [self.default_detail]})


class ClienteInactivo(ErrorDeNegocio):
    """RN-CLI-03 — un cliente inactivo no se elige en ventas nuevas."""

    status_code = status.HTTP_409_CONFLICT
    codigo = Codigo.CLIENTE_INACTIVO
    default_detail = "El cliente está desactivado y no puede elegirse en una venta nueva."
