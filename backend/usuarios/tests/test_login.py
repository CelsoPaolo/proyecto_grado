"""T-1.3 — Inicio de sesion (CU-AUT-01, RF-01 a RF-03)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.exceptions import Codigo

from .factories import AdministradorFactory, VendedorFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/login"


@pytest.fixture
def cliente():
    return APIClient()


# ─────────────────────────────────────────────────────────────────────
# RF-01 — inicio de sesion correcto
# ─────────────────────────────────────────────────────────────────────
def test_credenciales_validas_devuelven_tokens_y_datos_del_usuario(cliente):
    VendedorFactory(
        username="jperez", nombre_completo="Juan Pérez", password="ClaveSegura123"
    )

    respuesta = cliente.post(
        URL, {"username": "jperez", "password": "ClaveSegura123"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_200_OK
    assert "access" in respuesta.data
    assert "refresh" in respuesta.data
    assert respuesta.data["usuario"]["nombre_completo"] == "Juan Pérez"
    assert respuesta.data["usuario"]["rol"] == "VENTAS"
    assert respuesta.data["usuario"]["rol_display"] == "Encargado de Ventas"


def test_la_respuesta_nunca_incluye_la_contrasena(cliente):
    """RNF-03: el campo password no aparece en ninguna respuesta."""
    VendedorFactory(username="jperez", password="ClaveSegura123")

    respuesta = cliente.post(
        URL, {"username": "jperez", "password": "ClaveSegura123"}, format="json"
    )

    assert "password" not in str(respuesta.data)


def test_el_token_sirve_para_acceder_a_un_endpoint_protegido(cliente):
    VendedorFactory(username="jperez", password="ClaveSegura123")
    login = cliente.post(
        URL, {"username": "jperez", "password": "ClaveSegura123"}, format="json"
    )

    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    yo = cliente.get("/api/v1/auth/me")

    assert yo.status_code == status.HTTP_200_OK
    assert yo.data["username"] == "jperez"


# ─────────────────────────────────────────────────────────────────────
# RF-02 — mensaje generico (RNF-06)
# ─────────────────────────────────────────────────────────────────────
def test_usuario_inexistente_y_contrasena_incorrecta_dan_el_mismo_mensaje(cliente):
    """El criterio central de RF-02.

    Si los mensajes difirieran, probar usuarios uno a uno revelaria
    cuales existen en el sistema.
    """
    VendedorFactory(username="jperez", password="ClaveSegura123")

    inexistente = cliente.post(
        URL, {"username": "noexiste", "password": "loquesea"}, format="json"
    )
    contrasena_mala = cliente.post(
        URL, {"username": "jperez", "password": "incorrecta"}, format="json"
    )

    assert inexistente.status_code == contrasena_mala.status_code
    assert inexistente.data["codigo"] == contrasena_mala.data["codigo"]
    assert inexistente.data["detalle"] == contrasena_mala.data["detalle"]
    assert inexistente.data["codigo"] == Codigo.CREDENCIALES_INVALIDAS


def test_credenciales_invalidas_responden_401(cliente):
    respuesta = cliente.post(
        URL, {"username": "noexiste", "password": "loquesea"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────────────────────────────────────────────────
# RF-03 — cuenta bloqueada
# ─────────────────────────────────────────────────────────────────────
def test_una_cuenta_bloqueada_no_puede_iniciar_sesion(cliente):
    VendedorFactory(username="bloqueado", password="ClaveSegura123", is_active=False)

    respuesta = cliente.post(
        URL, {"username": "bloqueado", "password": "ClaveSegura123"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_403_FORBIDDEN
    assert respuesta.data["codigo"] == Codigo.CUENTA_BLOQUEADA


def test_una_cuenta_bloqueada_con_contrasena_incorrecta_no_revela_que_existe(cliente):
    """Matiz de RNF-06 que es facil pasar por alto.

    Informar "cuenta bloqueada" ante cualquier contrasena convertiria
    el mensaje en un detector de cuentas existentes. Solo se informa
    el bloqueo a quien demuestra conocer la contrasena, que es el
    titular, y a quien el administrador ya se lo comunico.
    """
    VendedorFactory(username="bloqueado", password="ClaveSegura123", is_active=False)

    respuesta = cliente.post(
        URL, {"username": "bloqueado", "password": "adivinanza"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
    assert respuesta.data["codigo"] == Codigo.CREDENCIALES_INVALIDAS


# ─────────────────────────────────────────────────────────────────────
# Formato de error y campos obligatorios
# ─────────────────────────────────────────────────────────────────────
def test_faltar_campos_da_un_error_de_validacion_por_campo(cliente):
    """RNF-15: el frontend mapea `errores` al campo correspondiente."""
    respuesta = cliente.post(URL, {"username": "jperez"}, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert respuesta.data["codigo"] == Codigo.VALIDACION
    assert "password" in respuesta.data["errores"]


def test_el_login_es_el_unico_endpoint_publico(cliente):
    """RNF-01: todo lo demas exige autenticacion."""
    assert cliente.get("/api/v1/auth/me").status_code == status.HTTP_401_UNAUTHORIZED


def test_el_rol_viaja_en_el_token_solo_como_dato_informativo(cliente):
    """plan.md 1.3, via 4.

    Se documenta que el reclamo existe para la interfaz; las pruebas
    de T-1.2 verifican que la autorizacion no lo usa.
    """
    from rest_framework_simplejwt.tokens import AccessToken

    AdministradorFactory(username="admin", password="ClaveSegura123")
    respuesta = cliente.post(
        URL, {"username": "admin", "password": "ClaveSegura123"}, format="json"
    )

    token = AccessToken(respuesta.data["access"])

    assert token["rol"] == "ADMINISTRADOR"
