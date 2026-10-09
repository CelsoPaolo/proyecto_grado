"""T-12.4 — API del reporte (RF-90, RN-REP-01, RN-REP-10)."""

from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.tests.factories import ProductoFactory
from core.exceptions import Codigo
from usuarios.tests.factories import AdministradorFactory, TecnicoFactory, VendedorFactory
from ventas.services import registrar_venta

pytestmark = pytest.mark.django_db

URL = "/api/v1/reportes"


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
def admin():
    return _autenticar(AdministradorFactory())


def test_devuelve_el_reporte_del_rango_con_importes_como_cadena(admin):
    from django.utils import timezone

    hoy = timezone.localdate().isoformat()
    producto = ProductoFactory(stock=5, precio=Decimal("350.00"))
    registrar_venta(
        usuario=VendedorFactory(nombre_completo="Juan Pérez"),
        cliente_nombre="C",
        cliente_telefono="1",
        items=[{"producto_id": producto.pk, "cantidad": 2}],
    )

    datos = admin.get(URL, {"desde": hoy, "hasta": hoy}).data

    assert datos["desde"] == hoy and datos["hasta"] == hoy
    assert datos["ventas"] == {"cantidad": 1, "importe": "700.00"}
    assert datos["ingreso_total"] == {"importe": "700.00", "de_ventas": "700.00", "de_servicios": "0.00"}
    assert datos["productos_mas_vendidos"][0] == {
        "producto_id": producto.pk,
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "unidades": 2,
        "importe": "700.00",
    }
    assert datos["ventas_por_usuario"][0]["nombre_completo"] == "Juan Pérez"
    assert set(datos["servicios_por_estado"]) == {"REGISTRADA", "EN_ATENCION", "FINALIZADA", "CANCELADA"}


def test_desde_posterior_a_hasta_responde_400_rango_invalido(admin):
    respuesta = admin.get(URL, {"desde": "2026-10-08", "hasta": "2026-10-01"})

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert respuesta.data["codigo"] == Codigo.RANGO_INVALIDO
    assert {"desde", "hasta"} <= set(respuesta.data["errores"])


@pytest.mark.parametrize(
    ("params", "campos"),
    [
        ({}, {"desde", "hasta"}),
        ({"desde": "2026-10-01"}, {"hasta"}),
        ({"hasta": "2026-10-01"}, {"desde"}),
        ({"desde": "01/10/2026", "hasta": "2026-10-07"}, {"desde"}),
        ({"desde": "2026-02-30", "hasta": "2026-03-01"}, {"desde"}),
    ],
    ids=["sin-fechas", "sin-hasta", "sin-desde", "formato", "imposible"],
)
def test_una_fecha_que_falta_o_no_vale_responde_400_junto_al_campo(admin, params, campos):
    respuesta = admin.get(URL, params)

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert set(respuesta.data["errores"]) == campos


def test_un_rango_de_un_solo_dia_es_valido(admin):
    assert admin.get(URL, {"desde": "2026-10-01", "hasta": "2026-10-01"}).status_code == 200


@pytest.mark.parametrize("fabrica", [VendedorFactory, TecnicoFactory], ids=["ventas", "servicios"])
def test_los_otros_dos_roles_reciben_403(fabrica):
    respuesta = _autenticar(fabrica()).get(URL, {"desde": "2026-10-01", "hasta": "2026-10-07"})

    assert respuesta.status_code == status.HTTP_403_FORBIDDEN
