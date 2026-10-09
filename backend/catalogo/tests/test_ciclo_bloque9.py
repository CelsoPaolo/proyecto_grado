"""T-9.6 — Una venta armada solo con lecturas de codigo, por la API.

Lo que hace la pantalla con cada lectura (plan.md 7.9): consultar
`?codigo=…&activo=true` y agregar el producto encontrado. Aqui se repite
con las mismas peticiones, con codigos internos y de fabrica, hasta
confirmar la venta; y se comprueba que lo vendido es exactamente lo
leido. La parte de teclado y foco la cubre lector-codigo.test.js; la
comprobacion con un lector real queda para revision humana.
"""

from collections import Counter

import pytest
from rest_framework.test import APIClient

from catalogo.services import crear_producto
from catalogo.tests.factories import CategoriaFactory
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


def test_una_venta_se_arma_solo_con_lecturas_de_codigos_internos_y_de_fabrica():
    admin = AdministradorFactory()
    categoria = CategoriaFactory()

    def alta(nombre, stock, codigo_fabrica=""):
        return crear_producto(
            usuario=admin,
            nombre=nombre,
            descripcion="",
            precio=100,
            stock=stock,
            categoria=categoria,
            codigo_fabrica=codigo_fabrica,
        )

    teclado = alta("Teclado", 5)
    mouse = alta("Mouse", 5, codigo_fabrica="7501031311309")
    cable = alta("Cable", 5, codigo_fabrica="ABC-123X")
    retirado = alta("Retirado", 5, codigo_fabrica="012345678905")
    retirado.activo = False
    retirado.save()

    caja = _autenticar(VendedorFactory())
    lecturas = [
        teclado.codigo,  # interno
        "7501031311309",  # fabrica EAN-13
        teclado.codigo,  # el mismo otra vez: suma uno
        "abc-123x",  # fabrica Code128, tecleado en minusculas
        mouse.codigo,  # interno del que ya entro por fabrica
        "012345678905",  # retirado: no debe entrar
        "750103131130",  # incompleto: no debe entrar
    ]

    carrito = Counter()
    for leido in lecturas:
        encontrados = caja.get("/api/v1/productos", {"codigo": leido, "activo": "true"}).data["results"]
        assert len(encontrados) <= 1, f"«{leido}» identificó a más de un producto"
        if encontrados and encontrados[0]["stock"] > 0:
            carrito[encontrados[0]["id"]] += 1

    respuesta = caja.post(
        "/api/v1/ventas",
        {
            "cliente_nombre": "Cliente de mostrador",
            "cliente_telefono": "70000000",
            "items": [{"producto_id": pid, "cantidad": n} for pid, n in carrito.items()],
        },
        format="json",
    )

    assert respuesta.status_code == 201, respuesta.data
    vendido = {linea["producto_id"]: linea["cantidad"] for linea in respuesta.data["items"]}
    assert vendido == {teclado.pk: 2, mouse.pk: 2, cable.pk: 1}
