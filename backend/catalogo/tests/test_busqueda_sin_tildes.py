"""T-15.1 — Busqueda de productos sin tildes (RF-98, RN-CAT-12).

El catalogo y el buscador de Registrar venta usan el mismo `?search=`
de `/productos`, asi que estas pruebas cubren los dos.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from rest_framework.test import APIClient

from usuarios.tests.factories import VendedorFactory

from .factories import ProductoFactory

PRODUCTOS = "/api/v1/productos"


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
def como_vendedor(db):
    return _autenticar(VendedorFactory())


def _nombres(respuesta):
    return sorted(p["nombre"] for p in respuesta.data["results"])


@pytest.mark.django_db
@pytest.mark.parametrize("texto", ["camara", "cámara", "CAMARA", "CÁMARA", "Cámara"])
def test_con_o_sin_tilde_encuentra_el_producto(como_vendedor, texto):
    ProductoFactory(nombre="Cámara Bullet Dahua Full-Color 2MP")
    ProductoFactory(nombre="Monitor curvo")

    respuesta = como_vendedor.get(PRODUCTOS, {"search": texto})

    assert _nombres(respuesta) == ["Cámara Bullet Dahua Full-Color 2MP"]


@pytest.mark.django_db
def test_un_nombre_sin_tilde_se_encuentra_buscando_con_tilde(como_vendedor):
    """El otro sentido: la tilde puede estar solo en lo que se busca."""
    ProductoFactory(nombre="Camara IP generica")

    respuesta = como_vendedor.get(PRODUCTOS, {"search": "cámara genérica"})

    assert _nombres(respuesta) == ["Camara IP generica"]


@pytest.mark.django_db
def test_la_enie_equivale_a_la_n(como_vendedor):
    ProductoFactory(nombre="Diseño de red")

    assert _nombres(como_vendedor.get(PRODUCTOS, {"search": "diseno"})) == ["Diseño de red"]


@pytest.mark.django_db
def test_se_sigue_buscando_en_la_descripcion(como_vendedor):
    ProductoFactory(nombre="Kit DVR", descripcion="Incluye 4 cámaras de vigilancia")
    ProductoFactory(nombre="Mouse", descripcion="Óptico")

    assert _nombres(como_vendedor.get(PRODUCTOS, {"search": "camaras"})) == ["Kit DVR"]


@pytest.mark.django_db
def test_cada_palabra_debe_aparecer(como_vendedor):
    """Igual que el SearchFilter de DRF: los terminos se combinan con Y."""
    ProductoFactory(nombre="Cámara Bullet")
    ProductoFactory(nombre="Cámara Domo")

    assert _nombres(como_vendedor.get(PRODUCTOS, {"search": "camara domo"})) == ["Cámara Domo"]


@pytest.mark.django_db
def test_sin_texto_no_filtra(como_vendedor):
    ProductoFactory(nombre="Cámara")
    ProductoFactory(nombre="Teclado")

    assert como_vendedor.get(PRODUCTOS, {"search": ""}).data["count"] == 2


@pytest.mark.django_db
def test_la_busqueda_por_codigo_sigue_siendo_exacta(como_vendedor):
    """RN-CAT-12 no cambia RN-VEN-17: el codigo no se busca por parecido."""
    producto = ProductoFactory(nombre="Cámara")

    exacto = como_vendedor.get(PRODUCTOS, {"codigo": producto.codigo})
    parcial = como_vendedor.get(PRODUCTOS, {"codigo": producto.codigo[:-1]})

    assert exacto.data["count"] == 1
    assert parcial.data["count"] == 0


@pytest.mark.django_db(transaction=True)
def test_la_migracion_de_unaccent_es_reversible():
    """RNF-29. Sin la extension, el lookup no existe en la base."""

    def instalada():
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'unaccent'")
            return cursor.fetchone() is not None

    executor = MigrationExecutor(connection)
    try:
        executor.migrate([("catalogo", "0006_meses_garantia")])
        assert not instalada()
        executor = MigrationExecutor(connection)
        executor.migrate([("catalogo", "0007_extension_unaccent")])
        assert instalada()
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())
