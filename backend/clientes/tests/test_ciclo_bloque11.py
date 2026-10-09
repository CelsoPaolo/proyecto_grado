"""T-11.7 — El ciclo del bloque 11 por la API.

Registrar un cliente → venderle → editar y desactivar el cliente → la
venta conserva los datos originales (RN-CLI-05). Y el carnet del cliente
no aparece en ninguna respuesta de la venta ni en su garantia
(RN-CLI-06, RN-VEN-15), comprobado con un carnet real: la prueba de
T-10.5 solo podia buscar la palabra.
"""

from io import BytesIO

import pytest
from pypdf import PdfReader
from rest_framework.test import APIClient

from catalogo.tests.factories import ProductoFactory
from usuarios.tests.factories import AdministradorFactory, VendedorFactory

pytestmark = pytest.mark.django_db


def _autenticar(usuario):
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


def test_venta_a_cliente_registrado_editarlo_y_la_venta_conserva_sus_datos():
    caja = _autenticar(VendedorFactory())
    admin = _autenticar(AdministradorFactory())
    disco = ProductoFactory(stock=5, meses_garantia=12)

    alta = caja.post(
        "/api/v1/clientes",
        {"nombre": "María Gutiérrez", "telefono": "70012345", "carnet": "1234567-1a"},
        format="json",
    )
    assert alta.status_code == 201, alta.data
    cliente_id = alta.data["id"]

    venta = caja.post(
        "/api/v1/ventas",
        {"cliente_id": cliente_id, "items": [{"producto_id": disco.pk, "cantidad": 1}]},
        format="json",
    )
    assert venta.status_code == 201, venta.data
    venta_id = venta.data["id"]

    caja.patch(f"/api/v1/clientes/{cliente_id}", {"nombre": "María G. de Pérez", "telefono": "71111111"}, format="json")
    assert admin.post(f"/api/v1/clientes/{cliente_id}/desactivar").status_code == 200

    detalle = caja.get(f"/api/v1/ventas/{venta_id}")
    assert (detalle.data["cliente_nombre"], detalle.data["cliente_telefono"]) == ("María Gutiérrez", "70012345")
    assert detalle.data["cliente"] == cliente_id

    # El carnet no sale por la venta: ni el detalle, ni la lista, ni la garantia.
    garantia = caja.get(f"/api/v1/ventas/{venta_id}/garantia")
    assert garantia.status_code == 200
    texto = "\n".join(p.extract_text() for p in PdfReader(BytesIO(garantia.content)).pages)
    assert "María Gutiérrez" in texto
    for salida in (detalle.content.decode(), caja.get("/api/v1/ventas").content.decode(), texto):
        assert "1234567-1A" not in salida.upper()

    # Desactivado, ya no puede elegirse en una venta nueva.
    otra = caja.post(
        "/api/v1/ventas",
        {"cliente_id": cliente_id, "items": [{"producto_id": disco.pk, "cantidad": 1}]},
        format="json",
    )
    assert otra.status_code == 409
