"""T-11.2 — Servicio de clientes (RF-84, RF-85, RF-87, RN-CLI-03, RN-CLI-04)."""

import pytest

from clientes.exceptions import CarnetDuplicado
from clientes.models import Cliente
from clientes.services import cambiar_estado_cliente, editar_cliente, registrar_cliente
from core.exceptions import ErrorDeNegocio
from usuarios.models import Usuario
from usuarios.tests.factories import AdministradorFactory, VendedorFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def vendedor():
    return VendedorFactory()


def test_registrar_un_cliente_guarda_sus_datos_y_su_autor(vendedor):
    cliente = registrar_cliente(
        usuario=vendedor,
        nombre="  María Gutiérrez ",
        telefono=" 70012345",
        direccion="Calle Junín 123",
        carnet="1234567-1a",
    )

    cliente.refresh_from_db()
    assert (cliente.nombre, cliente.telefono, cliente.carnet) == ("María Gutiérrez", "70012345", "1234567-1A")
    assert cliente.creado_por == vendedor and cliente.actualizado_por == vendedor
    assert cliente.activo


def test_registrar_un_cliente_no_crea_ningun_usuario(vendedor):
    """RN-CLI-04: un cliente no tiene cuenta ni acceso."""
    antes = Usuario.objects.count()

    registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000000", carnet="7654321")

    assert Usuario.objects.count() == antes


@pytest.mark.parametrize("campo", ["nombre", "telefono"])
def test_nombre_y_telefono_son_obligatorios(vendedor, campo):
    datos = {"nombre": "Juan", "telefono": "70000000", campo: "   "}

    with pytest.raises(ErrorDeNegocio) as error:
        registrar_cliente(usuario=vendedor, **datos)

    assert campo in error.value.errores
    assert not Cliente.objects.exists()


def test_un_carnet_repetido_da_carnet_duplicado(vendedor):
    registrar_cliente(usuario=vendedor, nombre="Uno", telefono="1", carnet="1234567")

    with pytest.raises(CarnetDuplicado):
        registrar_cliente(usuario=vendedor, nombre="Dos", telefono="2", carnet=" 1234567 ")


def test_editar_cambia_los_datos_y_registra_quien_lo_hizo(vendedor):
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000000")
    admin = AdministradorFactory()

    editar_cliente(cliente=cliente, usuario=admin, telefono="71111111", carnet="555")

    cliente.refresh_from_db()
    assert (cliente.telefono, cliente.carnet) == ("71111111", "555")
    assert cliente.actualizado_por == admin and cliente.creado_por == vendedor


def test_editar_con_su_propio_carnet_no_es_un_duplicado(vendedor):
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="1", carnet="555")

    editar_cliente(cliente=cliente, usuario=vendedor, nombre="Juan Carlos", carnet="555")


def test_editar_al_carnet_de_otro_da_carnet_duplicado(vendedor):
    registrar_cliente(usuario=vendedor, nombre="Uno", telefono="1", carnet="111")
    otro = registrar_cliente(usuario=vendedor, nombre="Dos", telefono="2")

    with pytest.raises(CarnetDuplicado):
        editar_cliente(cliente=otro, usuario=vendedor, carnet="111")


def test_desactivar_no_elimina_y_se_puede_reactivar(vendedor):
    admin = AdministradorFactory()
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="1")

    cambiar_estado_cliente(cliente=cliente, usuario=admin, activo=False)
    assert Cliente.objects.filter(pk=cliente.pk, activo=False).exists()

    cambiar_estado_cliente(cliente=cliente, usuario=admin, activo=True)
    cliente.refresh_from_db()
    assert cliente.activo and cliente.actualizado_por == admin


def test_pedir_el_estado_que_ya_tiene_no_registra_un_cambio(vendedor):
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="1")

    cambiar_estado_cliente(cliente=cliente, usuario=AdministradorFactory(), activo=True)

    cliente.refresh_from_db()
    assert cliente.actualizado_por == vendedor
