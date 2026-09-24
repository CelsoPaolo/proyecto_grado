"""T-1.5 — Cierre de sesion y cambio de contrasena propia.

CU-AUT-02 (RF-04) y CU-AUT-03 (RF-05), mas RNF-03 y RNF-04.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from .factories import VendedorFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
REFRESH = "/api/v1/auth/refresh"
YO = "/api/v1/auth/me"
PASSWORD = "/api/v1/auth/me/password"


@pytest.fixture
def cliente():
    return APIClient()


@pytest.fixture
def sesion(cliente):
    """Devuelve (cliente autenticado, usuario, refresh)."""
    usuario = VendedorFactory(username="jperez", password="ClaveSegura123")
    respuesta = cliente.post(
        LOGIN, {"username": "jperez", "password": "ClaveSegura123"}, format="json"
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente, usuario, respuesta.data["refresh"]


# ─────────────────────────────────────────────────────────────────────
# RF-04 — cerrar sesion
# ─────────────────────────────────────────────────────────────────────
def test_cerrar_sesion_invalida_el_refresh_token(sesion):
    """El criterio de CU-AUT-02.

    Sin lista negra, cerrar sesion solo borraria el token del
    navegador: seguiria siendo valido para quien lo hubiera copiado.
    """
    cliente, _, refresh = sesion

    salida = cliente.post(LOGOUT, {"refresh": refresh}, format="json")
    assert salida.status_code == status.HTTP_204_NO_CONTENT

    reintento = cliente.post(REFRESH, {"refresh": refresh}, format="json")
    assert reintento.status_code != status.HTTP_200_OK


def test_cerrar_sesion_exige_estar_autenticado(cliente):
    respuesta = cliente.post(LOGOUT, {"refresh": "loquesea"}, format="json")

    assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED


def test_un_refresh_invalido_al_cerrar_sesion_da_error_de_validacion(sesion):
    cliente, _, _ = sesion

    respuesta = cliente.post(LOGOUT, {"refresh": "no-es-un-token"}, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "refresh" in respuesta.data["errores"]


# ─────────────────────────────────────────────────────────────────────
# RF-05 — cambiar la propia contrasena
# ─────────────────────────────────────────────────────────────────────
def test_cambiar_la_contrasena_propia_verificando_la_anterior(sesion):
    cliente, usuario, _ = sesion

    respuesta = cliente.post(
        PASSWORD,
        {"password_actual": "ClaveSegura123", "password_nueva": "NuevaClave456"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_204_NO_CONTENT
    usuario.refresh_from_db()
    assert usuario.check_password("NuevaClave456")


def test_no_se_puede_cambiar_la_contrasena_sin_acertar_la_anterior(sesion):
    """Evita que un token robado baste para secuestrar la cuenta."""
    cliente, usuario, _ = sesion

    respuesta = cliente.post(
        PASSWORD,
        {"password_actual": "equivocada", "password_nueva": "NuevaClave456"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "password_actual" in respuesta.data["errores"]
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveSegura123")


def test_cambiar_la_contrasena_cierra_las_sesiones_anteriores(sesion):
    """CHECK_REVOKE_TOKEN aplicado al caso de RF-05.

    Es lo que hace util cambiar la contrasena ante una sospecha: si el
    token anterior siguiera valiendo, el cambio no expulsaria a nadie.
    """
    cliente, _, _ = sesion
    assert cliente.get(YO).status_code == status.HTTP_200_OK

    cliente.post(
        PASSWORD,
        {"password_actual": "ClaveSegura123", "password_nueva": "NuevaClave456"},
        format="json",
    )

    assert cliente.get(YO).status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────────────────────────────────────────────────
# RNF-04 — politica minima de contrasenas
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("password_nueva", "motivo"),
    [
        ("abc", "demasiado corta"),
        ("12345678", "solo numerica"),
        ("password", "demasiado comun"),
    ],
)
def test_la_contrasena_nueva_debe_cumplir_la_politica(sesion, password_nueva, motivo):
    cliente, usuario, _ = sesion

    respuesta = cliente.post(
        PASSWORD,
        {"password_actual": "ClaveSegura123", "password_nueva": password_nueva},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST, motivo
    assert "password_nueva" in respuesta.data["errores"]
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveSegura123")


def test_la_contrasena_no_puede_parecerse_al_nombre_de_usuario(sesion):
    cliente, _, _ = sesion

    respuesta = cliente.post(
        PASSWORD,
        {"password_actual": "ClaveSegura123", "password_nueva": "jperez"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST


def test_cambiar_la_contrasena_exige_estar_autenticado(cliente):
    respuesta = cliente.post(
        PASSWORD,
        {"password_actual": "a", "password_nueva": "b"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────────────────────────────────────────────────
# RF-06 — /auth/me
# ─────────────────────────────────────────────────────────────────────
def test_auth_me_devuelve_el_usuario_y_su_rol_sin_la_contrasena(sesion):
    cliente, usuario, _ = sesion

    respuesta = cliente.get(YO)

    assert respuesta.data["username"] == "jperez"
    assert respuesta.data["rol"] == "VENTAS"
    assert respuesta.data["rol_display"] == "Encargado de Ventas"
    assert "password" not in respuesta.data
