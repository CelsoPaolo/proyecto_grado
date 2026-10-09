"""T-11.3 — API de clientes (RF-84 a RF-89, RN-CLI-06, RN-CLI-07, RNF-26).

Lo central: el carnet NO aparece en la lista, en ninguna fila, y solo
el Administrador desactiva o reactiva.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from clientes.models import Cliente
from clientes.tests.factories import ClienteFactory
from core.exceptions import Codigo
from usuarios.tests.factories import AdministradorFactory, TecnicoFactory, VendedorFactory

pytestmark = pytest.mark.django_db

CLIENTES = "/api/v1/clientes"


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
def ventas():
    return _autenticar(VendedorFactory())


@pytest.fixture
def admin():
    return _autenticar(AdministradorFactory())


@pytest.fixture
def registrados():
    return [
        ClienteFactory(nombre="María Gutiérrez", telefono="70012345", carnet="1234567-1A"),
        ClienteFactory(nombre="Juan Pérez", telefono="71111111", carnet="7654321"),
        ClienteFactory(nombre="Ana Rojas", telefono="72222222", activo=False),
    ]


# ─────────────────────────────────────────────────────────────────────
# Minimizacion del carnet (RN-CLI-06, RNF-26)
# ─────────────────────────────────────────────────────────────────────
def test_la_lista_no_contiene_la_clave_carnet_en_ninguna_fila(ventas, registrados):
    filas = ventas.get(CLIENTES).data["results"]

    assert len(filas) == 3
    assert all("carnet" not in fila for fila in filas)


def test_el_valor_del_carnet_no_aparece_en_ninguna_parte_de_la_lista(ventas, registrados):
    """Ni bajo otra clave: se busca el valor en la respuesta entera."""
    cuerpo = ventas.get(CLIENTES).content.decode()

    assert "1234567-1A" not in cuerpo and "7654321" not in cuerpo


def test_el_detalle_si_trae_el_carnet(ventas, registrados):
    detalle = ventas.get(f"{CLIENTES}/{registrados[0].pk}").data

    assert detalle["carnet"] == "1234567-1A"


# ─────────────────────────────────────────────────────────────────────
# Busqueda (RF-86)
# ─────────────────────────────────────────────────────────────────────
def _nombres(cliente, **params):
    return sorted(c["nombre"] for c in cliente.get(CLIENTES, params).data["results"])


def test_busca_por_parte_del_nombre_o_del_telefono(ventas, registrados):
    assert _nombres(ventas, buscar="gutié") == ["María Gutiérrez"]
    assert _nombres(ventas, buscar="1111") == ["Juan Pérez"]


def test_busca_por_carnet_exacto_normalizado(ventas, registrados):
    assert _nombres(ventas, buscar="1234567-1a") == ["María Gutiérrez"]


def test_un_carnet_parcial_no_encuentra_a_nadie(ventas, registrados):
    """Una coincidencia parcial permitiria adivinar carnets cifra a cifra."""
    assert _nombres(ventas, buscar="765432") == []


def test_filtra_activos_e_inactivos(ventas, registrados):
    assert _nombres(ventas, activo="true") == ["Juan Pérez", "María Gutiérrez"]
    assert _nombres(ventas, activo="false") == ["Ana Rojas"]


def test_la_lista_esta_paginada(ventas):
    for _ in range(25):
        ClienteFactory()

    datos = ventas.get(CLIENTES).data

    assert datos["count"] == 25 and len(datos["results"]) == 20


# ─────────────────────────────────────────────────────────────────────
# Alta y edicion (RF-84, RF-85, RF-88)
# ─────────────────────────────────────────────────────────────────────
def test_el_encargado_de_ventas_registra_y_edita(ventas):
    alta = ventas.post(
        CLIENTES, {"nombre": "Carlos", "telefono": "73333333", "carnet": "555 lp"}, format="json"
    )
    assert alta.status_code == status.HTTP_201_CREATED
    assert alta.data["carnet"] == "555LP"

    edicion = ventas.patch(f"{CLIENTES}/{alta.data['id']}", {"telefono": "74444444"}, format="json")
    assert edicion.status_code == 200
    assert edicion.data["telefono"] == "74444444"


def test_sin_nombre_o_telefono_400_junto_al_campo(ventas):
    respuesta = ventas.post(CLIENTES, {"nombre": " ", "telefono": ""}, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert {"nombre", "telefono"} <= set(respuesta.data["errores"])


def test_un_carnet_repetido_responde_409_carnet_duplicado(ventas, registrados):
    respuesta = ventas.post(
        CLIENTES, {"nombre": "Otro", "telefono": "1", "carnet": "7654321"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.CARNET_DUPLICADO
    # No revela de quien es el carnet.
    assert "Juan" not in str(respuesta.data)


# ─────────────────────────────────────────────────────────────────────
# Permisos (RN-CLI-07, PA-06) y ausencia de DELETE (RN-CLI-03)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("accion", ["desactivar", "reactivar"])
def test_el_encargado_de_ventas_recibe_403_al_desactivar_o_reactivar(ventas, registrados, accion):
    respuesta = ventas.post(f"{CLIENTES}/{registrados[0].pk}/{accion}")

    assert respuesta.status_code == status.HTTP_403_FORBIDDEN


def test_el_administrador_desactiva_y_reactiva(admin, registrados):
    cliente = registrados[0]

    assert admin.post(f"{CLIENTES}/{cliente.pk}/desactivar").data["activo"] is False
    assert admin.post(f"{CLIENTES}/{cliente.pk}/reactivar").data["activo"] is True


def test_el_encargado_de_servicios_recibe_403_en_todos(registrados):
    servicios = _autenticar(TecnicoFactory())
    pk = registrados[0].pk

    for metodo, url in [
        ("get", CLIENTES),
        ("post", CLIENTES),
        ("get", f"{CLIENTES}/{pk}"),
        ("patch", f"{CLIENTES}/{pk}"),
        ("post", f"{CLIENTES}/{pk}/desactivar"),
    ]:
        assert getattr(servicios, metodo)(url, {}, format="json").status_code == 403, (metodo, url)


@pytest.mark.parametrize("metodo", ["delete", "put"])
def test_no_se_eliminan_ni_se_reemplazan(admin, registrados, metodo):
    respuesta = getattr(admin, metodo)(f"{CLIENTES}/{registrados[0].pk}", {}, format="json")

    assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert Cliente.objects.filter(pk=registrados[0].pk).exists()
