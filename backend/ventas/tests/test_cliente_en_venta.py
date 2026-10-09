"""T-11.4 — Cliente en la venta (RN-VEN-10, RN-CLI-05, RF-79, RF-80).

La venta guarda SU PROPIA copia del nombre y el telefono, aunque haya un
cliente registrado detras. Lo que se comprueba aqui es que esa copia no
se mueve: ni por lo que traiga la peticion, ni por lo que le pase despues
al cliente.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.tests.factories import ProductoFactory
from clientes.exceptions import ClienteInactivo
from clientes.services import cambiar_estado_cliente, editar_cliente
from clientes.tests.factories import ClienteFactory
from core.exceptions import Codigo
from usuarios.tests.factories import AdministradorFactory, VendedorFactory
from ventas.models import Venta
from ventas.services import registrar_venta

pytestmark = pytest.mark.django_db

VENTAS = "/api/v1/ventas"


def _autenticar(usuario):
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


@pytest.fixture
def vendedor():
    return VendedorFactory()


@pytest.fixture
def producto():
    return ProductoFactory(stock=10)


@pytest.fixture
def maria():
    return ClienteFactory(nombre="María Gutiérrez", telefono="70012345", carnet="1234567-1A")


def _items(producto, cantidad=1):
    return [{"producto_id": producto.id, "cantidad": cantidad}]


def test_con_cliente_id_la_venta_copia_sus_datos_aunque_la_peticion_traiga_otros(vendedor, producto, maria):
    respuesta = _autenticar(vendedor).post(
        VENTAS,
        {
            "cliente_id": maria.pk,
            "cliente_nombre": "Otro nombre",
            "cliente_telefono": "79999999",
            "items": _items(producto),
        },
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.data
    assert respuesta.data["cliente"] == maria.pk
    assert (respuesta.data["cliente_nombre"], respuesta.data["cliente_telefono"]) == (
        "María Gutiérrez",
        "70012345",
    )


def test_con_cliente_id_no_hace_falta_escribir_nombre_ni_telefono(vendedor, producto, maria):
    respuesta = _autenticar(vendedor).post(
        VENTAS, {"cliente_id": maria.pk, "items": _items(producto)}, format="json"
    )

    assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.data


def test_editar_y_desactivar_el_cliente_no_altera_las_ventas_anteriores(vendedor, producto, maria):
    """RN-CLI-05, el criterio central de la tarea."""
    venta = registrar_venta(usuario=vendedor, cliente_id=maria.pk, items=_items(producto))
    admin = AdministradorFactory()

    editar_cliente(cliente=maria, usuario=admin, nombre="María G. de Pérez", telefono="71111111")
    cambiar_estado_cliente(cliente=maria, usuario=admin, activo=False)

    venta.refresh_from_db()
    assert (venta.cliente_nombre, venta.cliente_telefono) == ("María Gutiérrez", "70012345")
    assert venta.cliente_id == maria.pk


def test_un_cliente_inactivo_da_409_y_no_descuenta_nada(vendedor, producto, maria):
    maria.activo = False
    maria.save()

    respuesta = _autenticar(vendedor).post(
        VENTAS, {"cliente_id": maria.pk, "items": _items(producto, 3)}, format="json"
    )

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.CLIENTE_INACTIVO
    producto.refresh_from_db()
    assert producto.stock == 10
    assert not Venta.objects.exists()


def test_el_servicio_tambien_rechaza_al_cliente_inactivo(vendedor, producto, maria):
    maria.activo = False
    maria.save()

    with pytest.raises(ClienteInactivo):
        registrar_venta(usuario=vendedor, cliente_id=maria.pk, items=_items(producto))


def test_un_cliente_inexistente_400_junto_al_campo(vendedor, producto):
    respuesta = _autenticar(vendedor).post(
        VENTAS, {"cliente_id": 999999, "items": _items(producto)}, format="json"
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "cliente_id" in respuesta.data["errores"]
    producto.refresh_from_db()
    assert producto.stock == 10


def test_sin_cliente_id_es_un_cliente_ocasional_como_en_la_v13(vendedor, producto):
    respuesta = _autenticar(vendedor).post(
        VENTAS,
        {"cliente_nombre": "Ocasional", "cliente_telefono": "70000000", "items": _items(producto)},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["cliente"] is None
    assert respuesta.data["cliente_nombre"] == "Ocasional"


def test_sin_cliente_id_ni_datos_del_ocasional_400(vendedor, producto):
    respuesta = _autenticar(vendedor).post(VENTAS, {"items": _items(producto)}, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert {"cliente_nombre", "cliente_telefono"} <= set(respuesta.data["errores"])


def test_el_detalle_de_la_venta_no_contiene_el_carnet(vendedor, producto, maria):
    """RN-CLI-06: ni la clave, ni el valor."""
    venta = registrar_venta(usuario=vendedor, cliente_id=maria.pk, items=_items(producto))

    respuesta = _autenticar(vendedor).get(f"{VENTAS}/{venta.pk}")
    lista = _autenticar(vendedor).get(VENTAS)

    for cuerpo in (respuesta.content.decode(), lista.content.decode()):
        assert "carnet" not in cuerpo
        assert "1234567-1A" not in cuerpo


@pytest.mark.django_db(transaction=True)
def test_la_migracion_de_la_referencia_se_aplica_y_se_revierte_sin_tocar_las_ventas():
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    def migrar(destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)

    def columnas():
        with connection.cursor() as cursor:
            return {c.name for c in connection.introspection.get_table_description(cursor, "ventas_venta")}

    venta = registrar_venta(
        usuario=VendedorFactory(), cliente_nombre="Ocasional", cliente_telefono="1",
        items=_items(ProductoFactory(stock=5)),
    )
    try:
        migrar([("ventas", "0002_meses_garantia_congelados")])
        assert "cliente_id" not in columnas()
        migrar([("ventas", "0003_cliente_registrado")])
        assert "cliente_id" in columnas()
        venta.refresh_from_db()
        assert (venta.cliente_id, venta.cliente_nombre) == (None, "Ocasional")
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())
