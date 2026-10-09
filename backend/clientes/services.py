"""Reglas de negocio de clientes (spec.md 6.8).

Registrar, editar, desactivar y reactivar, siempre con autor (RNF-07).
Un cliente es un registro de contacto: nada de lo que hay aqui crea un
Usuario ni concede acceso alguno (RN-CLI-04).
"""

from django.db import IntegrityError, transaction

from clientes.exceptions import CarnetDuplicado
from clientes.models import Cliente, normalizar_carnet
from core.exceptions import ErrorDeNegocio

CAMPOS_EDITABLES = ("nombre", "telefono", "direccion", "carnet")


def _limpiar(datos):
    """RN-CLI-01: nombre y telefono obligatorios; todo sin espacios en los
    extremos y el carnet normalizado."""
    limpio = {}
    for campo in CAMPOS_EDITABLES:
        if campo in datos:
            valor = datos[campo]
            limpio[campo] = normalizar_carnet(valor) if campo == "carnet" else (valor or "").strip()
    errores = {}
    for campo, nombre in (("nombre", "el nombre"), ("telefono", "el teléfono")):
        if campo in limpio and not limpio[campo]:
            errores[campo] = [f"Indique {nombre} del cliente."]
    if errores:
        raise ErrorDeNegocio(detalle="Revise los datos del cliente.", errores=errores)
    return limpio


def _guardar(cliente, excluir_pk=None):
    """Guarda traduciendo el choque de carnet a un error de negocio.

    Se comprueba antes para dar el 409 legible, y se captura el
    IntegrityError por si otra peticion registro el mismo carnet entre la
    comprobacion y el INSERT: la base es la que decide (RN-CLI-02).
    """
    if cliente.carnet:
        repetido = Cliente.objects.filter(carnet=cliente.carnet)
        if excluir_pk is not None:
            repetido = repetido.exclude(pk=excluir_pk)
        if repetido.exists():
            raise CarnetDuplicado()
    try:
        with transaction.atomic():
            cliente.save()
    except IntegrityError as exc:
        if "cliente_carnet_unico" in str(exc):
            raise CarnetDuplicado() from exc
        raise
    return cliente


@transaction.atomic
def registrar_cliente(*, usuario, **datos):
    """RF-84 — nombre y telefono obligatorios; direccion y carnet opcionales."""
    limpio = _limpiar({"nombre": "", "telefono": "", **datos})
    cliente = Cliente(**limpio, creado_por=usuario, actualizado_por=usuario)
    return _guardar(cliente)


@transaction.atomic
def editar_cliente(*, cliente, usuario, **datos):
    """RF-85 — editar sus datos no altera ninguna venta (RN-CLI-05): las
    ventas guardan su propia copia del nombre y el telefono."""
    for campo, valor in _limpiar(datos).items():
        setattr(cliente, campo, valor)
    cliente.actualizado_por = usuario
    return _guardar(cliente, excluir_pk=cliente.pk)


@transaction.atomic
def cambiar_estado_cliente(*, cliente, usuario, activo):
    """RF-87 y RN-CLI-03 — desactivar o reactivar, nunca eliminar.

    Pedir el estado que ya tiene no es un error: el resultado es el
    pedido. No se registra un cambio que no ocurrio.
    """
    if cliente.activo != activo:
        cliente.activo = activo
        cliente.actualizado_por = usuario
        cliente.save(update_fields=["activo", "actualizado_por", "actualizado_en"])
    return cliente
