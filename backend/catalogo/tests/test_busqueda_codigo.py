"""T-9.3 / T-9.7 — Busqueda por codigo exacto (RF-70, RN-VEN-17).

`GET /productos?codigo=` es lo que consulta el campo de codigo de la
venta con cada lectura (plan.md 7.9). Lo que no puede pasar nunca es una
coincidencia parcial: un lector que lea mal no debe agregar un producto
equivocado.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.tests.factories import CategoriaFactory, ProductoFactory
from usuarios.tests.factories import VendedorFactory

pytestmark = pytest.mark.django_db

PRODUCTOS = "/api/v1/productos"


@pytest.fixture
def cliente():
    """Quien lo usa de verdad: el Encargado de Ventas, en el mostrador."""
    usuario = VendedorFactory()
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


@pytest.fixture
def productos():
    categoria = CategoriaFactory()
    return [ProductoFactory(categoria=categoria) for _ in range(3)]


def _buscar(cliente, codigo, **extra):
    respuesta = cliente.get(PRODUCTOS, {"codigo": codigo, **extra})
    assert respuesta.status_code == status.HTTP_200_OK
    return respuesta.data["results"]


def test_un_codigo_exacto_devuelve_un_unico_producto(cliente, productos):
    buscado = productos[1]

    [encontrado] = _buscar(cliente, buscado.codigo)

    assert encontrado["id"] == buscado.pk
    assert encontrado["codigo"] == buscado.codigo


def test_los_espacios_alrededor_no_impiden_encontrarlo(cliente, productos):
    """Al pegar o teclear un codigo se cuelan espacios; no son parte de el."""
    [encontrado] = _buscar(cliente, f"  {productos[0].codigo} ")

    assert encontrado["id"] == productos[0].pk


@pytest.mark.parametrize(
    "recorte",
    [
        lambda c: c[:12],  # sin el digito de control
        lambda c: c[1:],  # sin la primera cifra
        lambda c: c[:6],  # un prefijo comun a todos los internos
        lambda c: c[:12] + str((int(c[12]) + 1) % 10),  # control equivocado
    ],
    ids=["sin-control", "sin-primera-cifra", "prefijo", "control-erroneo"],
)
def test_un_codigo_incompleto_o_alterado_no_encuentra_nada(cliente, productos, recorte):
    assert _buscar(cliente, recorte(productos[0].codigo)) == []


def test_un_codigo_inexistente_da_una_lista_vacia_sin_error(cliente, productos):
    assert _buscar(cliente, "2999999999999") == []
    assert _buscar(cliente, "no-es-un-codigo") == []


def test_un_codigo_vacio_no_encuentra_nada(cliente, productos):
    """Un Intro con el campo vacio no debe devolver el catalogo entero."""
    assert _buscar(cliente, "") == []


def test_un_producto_retirado_no_aparece_por_defecto(cliente, productos):
    retirado = productos[2]
    retirado.activo = False
    retirado.save()

    assert _buscar(cliente, retirado.codigo) == []
    assert [p["id"] for p in _buscar(cliente, retirado.codigo, activo="false")] == [retirado.pk]


def test_el_detalle_y_la_lista_traen_el_codigo(cliente, productos):
    detalle = cliente.get(f"{PRODUCTOS}/{productos[0].pk}").data
    lista = cliente.get(PRODUCTOS).data["results"]

    assert detalle["codigo"] == productos[0].codigo
    assert {p["codigo"] for p in lista} == {p.codigo for p in productos}
