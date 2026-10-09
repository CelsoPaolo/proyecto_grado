"""T-8.8 — El ciclo del bloque 8 recorrido entero por la API.

Crear producto → vender → anular → ajustar, con las mismas peticiones
que hace la interfaz, y comprobar que el historial muestra los cuatro
movimientos con el libro cuadrado (RN-MOV-03).

Las pruebas de cada tarea ya cubren cada paso por separado; esta
comprueba que encajan: que el movimiento de cada camino aparece en el
historial que lee la pantalla, con su autor, en orden y sin huecos. La
comprobacion visual en el navegador queda para revision humana.
"""

import pytest
from rest_framework.test import APIClient

from catalogo.tests.factories import CategoriaFactory
from inventario.models import TipoMovimiento
from inventario.verificacion import cadena_rota, libros_descuadrados
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


def test_crear_vender_anular_y_ajustar_deja_cuatro_movimientos_y_el_libro_cuadrado():
    admin = AdministradorFactory(nombre_completo="Ana Administradora")
    vendedor = VendedorFactory(nombre_completo="Víctor Vendedor")
    como_admin = _autenticar(admin)
    como_vendedor = _autenticar(vendedor)

    # 1. Alta con 10 unidades
    respuesta = como_admin.post(
        "/api/v1/productos",
        {
            "nombre": "Disco SSD 480 GB",
            "descripcion": "Ciclo del bloque 8",
            "precio": "250.00",
            "stock": 10,
            "categoria": CategoriaFactory().pk,
        },
        format="json",
    )
    assert respuesta.status_code == 201, respuesta.data
    producto_id = respuesta.data["id"]

    # 2. Venta de 3
    respuesta = como_vendedor.post(
        "/api/v1/ventas",
        {
            "cliente_nombre": "María Gutiérrez",
            "cliente_telefono": "70012345",
            "items": [{"producto_id": producto_id, "cantidad": 3}],
        },
        format="json",
    )
    assert respuesta.status_code == 201, respuesta.data
    venta_id = respuesta.data["id"]

    # 3. Anulacion: vuelven las 3
    respuesta = como_vendedor.post(
        f"/api/v1/ventas/{venta_id}/anular", {"motivo": "Cliente desistió"}, format="json"
    )
    assert respuesta.status_code == 200, respuesta.data

    # 4. Ajuste a lo contado: 8
    respuesta = como_admin.post(
        f"/api/v1/productos/{producto_id}/ajustar-existencias",
        {"cantidad_real": 8, "motivo": "Recuento físico"},
        format="json",
    )
    assert respuesta.status_code == 201, respuesta.data

    # El historial que lee la pantalla
    historial = como_admin.get(f"/api/v1/productos/{producto_id}/movimientos").data
    filas = [
        (f["tipo"], f["cantidad"], f["stock_resultante"], f["usuario_nombre"], f["venta"])
        for f in reversed(historial["results"])
    ]
    assert filas == [
        (TipoMovimiento.ALTA, 10, 10, "Ana Administradora", None),
        (TipoMovimiento.VENTA, -3, 7, "Víctor Vendedor", venta_id),
        (TipoMovimiento.ANULACION, 3, 10, "Víctor Vendedor", venta_id),
        (TipoMovimiento.AJUSTE, -2, 8, "Ana Administradora", None),
    ]
    assert historial["results"][0]["motivo"] == "Recuento físico"

    # Y lo que muestra el catalogo coincide con el libro
    producto = como_admin.get(f"/api/v1/productos/{producto_id}").data
    assert producto["stock"] == 8
    assert libros_descuadrados([producto_id]) == []
    assert cadena_rota(producto_id) is None

    # El vendedor no ve nada de esto (RN-MOV-06)
    assert como_vendedor.get(f"/api/v1/productos/{producto_id}/movimientos").status_code == 403
