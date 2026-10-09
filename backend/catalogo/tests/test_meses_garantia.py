"""T-10.1 — Meses de garantia del producto (RN-CAT-09, RF-72).

Entero no negativo; cero significa sin garantia. La base lo impone en el
producto y en la copia congelada de la linea de venta.
"""

import pytest
from django.db import IntegrityError, connection, transaction
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.tests.factories import CategoriaFactory, ProductoFactory
from usuarios.tests.factories import AdministradorFactory
from ventas.tests.factories import DetalleVentaFactory

pytestmark = pytest.mark.django_db

PRODUCTOS = "/api/v1/productos"


@pytest.fixture
def admin():
    usuario = AdministradorFactory()
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


def _alta(cliente, **extra):
    return cliente.post(
        PRODUCTOS,
        {
            "nombre": "Disco duro 1 TB",
            "descripcion": "",
            "precio": "420.00",
            "stock": 2,
            "categoria": CategoriaFactory().pk,
            **extra,
        },
        format="json",
    )


def test_sin_indicarlos_el_producto_no_tiene_garantia(admin):
    respuesta = _alta(admin)

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["meses_garantia"] == 0


def test_se_registran_y_se_editan(admin):
    respuesta = _alta(admin, meses_garantia=12)
    assert respuesta.data["meses_garantia"] == 12

    editado = admin.patch(f"{PRODUCTOS}/{respuesta.data['id']}", {"meses_garantia": 6}, format="json")

    assert editado.status_code == 200
    assert editado.data["meses_garantia"] == 6


def test_un_valor_negativo_se_rechaza_junto_al_campo(admin):
    respuesta = _alta(admin, meses_garantia=-1)

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "meses_garantia" in respuesta.data["errores"]


@pytest.mark.parametrize("tabla", ["catalogo_producto", "ventas_detalleventa"])
def test_la_base_rechaza_un_valor_negativo(tabla):
    """En SQL crudo: ni el serializer ni el ORM intervienen."""
    DetalleVentaFactory()
    ProductoFactory()
    with pytest.raises(IntegrityError):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f"UPDATE {tabla} SET meses_garantia = -1")
