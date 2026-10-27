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
        carnet=" 1234 5678 ",
    )

    cliente.refresh_from_db()
    assert (cliente.nombre, cliente.telefono, cliente.carnet) == ("María Gutiérrez", "70012345", "12345678")
    assert cliente.creado_por == vendedor and cliente.actualizado_por == vendedor
    assert cliente.activo


def test_registrar_un_cliente_no_crea_ningun_usuario(vendedor):
    """RN-CLI-04: un cliente no tiene cuenta ni acceso."""
    antes = Usuario.objects.count()

    registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000000", carnet="7654321")

    assert Usuario.objects.count() == antes


@pytest.mark.parametrize("campo", ["nombre", "telefono", "carnet"])
def test_nombre_telefono_y_carnet_son_obligatorios(vendedor, campo):
    """RN-CLI-01: el carnet, desde la v1.5."""
    datos = {"nombre": "Juan", "telefono": "70000000", "carnet": "1234567", campo: "   "}

    with pytest.raises(ErrorDeNegocio) as error:
        registrar_cliente(usuario=vendedor, **datos)

    assert campo in error.value.errores
    assert not Cliente.objects.exists()


def test_un_carnet_repetido_da_carnet_duplicado(vendedor):
    registrar_cliente(usuario=vendedor, nombre="Uno", telefono="70000001", carnet="1234567")

    with pytest.raises(CarnetDuplicado):
        registrar_cliente(usuario=vendedor, nombre="Dos", telefono="70000002", carnet=" 1234567 ")


def test_editar_cambia_los_datos_y_registra_quien_lo_hizo(vendedor):
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000000", carnet="1111111")
    admin = AdministradorFactory()

    editar_cliente(cliente=cliente, usuario=admin, telefono="71111111", carnet="5555555")

    cliente.refresh_from_db()
    assert (cliente.telefono, cliente.carnet) == ("71111111", "5555555")
    assert cliente.actualizado_por == admin and cliente.creado_por == vendedor


def test_editar_con_su_propio_carnet_no_es_un_duplicado(vendedor):
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000001", carnet="5555555")

    editar_cliente(cliente=cliente, usuario=vendedor, nombre="Juan Carlos", carnet="5555555")


def test_editar_al_carnet_de_otro_da_carnet_duplicado(vendedor):
    registrar_cliente(usuario=vendedor, nombre="Uno", telefono="70000001", carnet="1111111")
    otro = registrar_cliente(usuario=vendedor, nombre="Dos", telefono="70000002", carnet="2222222")

    with pytest.raises(CarnetDuplicado):
        editar_cliente(cliente=otro, usuario=vendedor, carnet="1111111")


def test_desactivar_no_elimina_y_se_puede_reactivar(vendedor):
    admin = AdministradorFactory()
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000001", carnet="3333333")

    cambiar_estado_cliente(cliente=cliente, usuario=admin, activo=False)
    assert Cliente.objects.filter(pk=cliente.pk, activo=False).exists()

    cambiar_estado_cliente(cliente=cliente, usuario=admin, activo=True)
    cliente.refresh_from_db()
    assert cliente.activo and cliente.actualizado_por == admin


def test_pedir_el_estado_que_ya_tiene_no_registra_un_cambio(vendedor):
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000001", carnet="3333333")

    cambiar_estado_cliente(cliente=cliente, usuario=AdministradorFactory(), activo=True)

    cliente.refresh_from_db()
    assert cliente.actualizado_por == vendedor


# ─────────────────────────────────────────────────────────────────────
# T-15.9 — Formato del carnet (RF-101, RN-CLI-02)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("carnet", ["123456", "123456789", "1234567-1A", "1234567 LP", "1234567a", "٧٦٥٤٣٢١"])
def test_un_carnet_fuera_de_formato_se_rechaza_junto_al_campo(vendedor, carnet):
    with pytest.raises(ErrorDeNegocio) as error:
        registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000000", carnet=carnet)

    assert error.value.errores == {"carnet": ["El carnet debe tener 7 u 8 dígitos, solo números."]}
    assert not Cliente.objects.exists()


@pytest.mark.parametrize("carnet", ["1234567", "12345678"])
def test_siete_u_ocho_digitos_se_aceptan(vendedor, carnet):
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000000", carnet=carnet)

    assert cliente.carnet == carnet


def test_editar_no_permite_quitar_el_carnet(vendedor):
    cliente = registrar_cliente(usuario=vendedor, nombre="Juan", telefono="70000000", carnet="1234567")

    with pytest.raises(ErrorDeNegocio) as error:
        editar_cliente(cliente=cliente, usuario=vendedor, carnet="")

    assert "carnet" in error.value.errores
    cliente.refresh_from_db()
    assert cliente.carnet == "1234567"


def test_el_carnet_es_unico_aunque_el_otro_este_desactivado(vendedor):
    otro = registrar_cliente(usuario=vendedor, nombre="Uno", telefono="70000001", carnet="7654321")
    cambiar_estado_cliente(cliente=otro, usuario=AdministradorFactory(), activo=False)

    with pytest.raises(CarnetDuplicado):
        registrar_cliente(usuario=vendedor, nombre="Dos", telefono="70000002", carnet="7654321")
