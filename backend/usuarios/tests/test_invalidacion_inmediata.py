"""T-1.4 — Invalidacion inmediata de sesiones (RN-ACC-05, decision PT-02).

Criterio de aceptacion ejecutable de la decision PT-02: una cuenta
bloqueada pierde el acceso **al instante**, por todas las vias.

Las cuatro vias de plan.md seccion 1.3:

  1. access token vigente ....... ya cerrada por SimpleJWT
  2. refresh token vigente ...... TokenRefreshSeguroSerializer
  3. sesiones que reviven ....... lista negra al bloquear
  4. rol o contrasena a mitad ... rol de la base; CHECK_REVOKE_TOKEN
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.exceptions import Codigo
from usuarios.models import Rol
from usuarios.services import bloquear_usuario, desbloquear_usuario

from .factories import AdministradorFactory, VendedorFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
YO = "/api/v1/auth/me"


@pytest.fixture
def cliente():
    return APIClient()


def _iniciar_sesion(cliente, username, password="ClaveSegura123"):
    respuesta = cliente.post(
        LOGIN, {"username": username, "password": password}, format="json"
    )
    assert respuesta.status_code == status.HTTP_200_OK
    return respuesta.data["access"], respuesta.data["refresh"]


# ─────────────────────────────────────────────────────────────────────
# Prueba 1 de plan.md 1.3 — via 1: el access token deja de valer YA
# ─────────────────────────────────────────────────────────────────────
def test_bloquear_invalida_el_access_token_en_la_peticion_siguiente(cliente):
    """La prueba central de PT-02.

    Sin esperas ni expiracion: la peticion inmediatamente posterior al
    bloqueo ya debe fallar.
    """
    usuario = VendedorFactory(username="jperez")
    access, _ = _iniciar_sesion(cliente, "jperez")
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    # Antes del bloqueo el token funciona.
    assert cliente.get(YO).status_code == status.HTTP_200_OK

    bloquear_usuario(usuario=usuario, ejecutor=AdministradorFactory())

    # Mismo token, sin esperar nada: ya no vale.
    assert cliente.get(YO).status_code == status.HTTP_401_UNAUTHORIZED


def test_la_invalidacion_no_depende_de_que_expire_el_token(cliente, settings):
    """Refuerza lo anterior desde la configuracion.

    Si el rechazo dependiera de la expiracion, con 30 minutos de vida
    la prueba anterior no podria pasar. Se deja constancia de que el
    access token sigue teniendo vida larga y aun asi se rechaza.
    """
    from datetime import timedelta

    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] >= timedelta(minutes=30)


# ─────────────────────────────────────────────────────────────────────
# Prueba 2 de plan.md 1.3 — via 2: el refresh de una cuenta bloqueada
# ─────────────────────────────────────────────────────────────────────
def test_una_cuenta_bloqueada_no_puede_refrescar_su_token(cliente):
    """El hueco real del comportamiento por defecto de SimpleJWT.

    El serializer de refresco de serie valida firma y caducidad, pero
    no consulta al usuario: sin el serializer propio, una cuenta
    bloqueada renovaria su acceso indefinidamente.
    """
    usuario = VendedorFactory(username="jperez")
    _, refresh = _iniciar_sesion(cliente, "jperez")

    bloquear_usuario(usuario=usuario, ejecutor=AdministradorFactory())

    respuesta = cliente.post(REFRESH, {"refresh": refresh}, format="json")

    assert respuesta.status_code == status.HTTP_403_FORBIDDEN
    assert respuesta.data["codigo"] == Codigo.CUENTA_BLOQUEADA


def test_una_cuenta_activa_si_puede_refrescar_su_token(cliente):
    """Contraprueba: el cierre no debe romper el caso normal."""
    VendedorFactory(username="jperez")
    _, refresh = _iniciar_sesion(cliente, "jperez")

    respuesta = cliente.post(REFRESH, {"refresh": refresh}, format="json")

    assert respuesta.status_code == status.HTTP_200_OK
    assert "access" in respuesta.data


# ─────────────────────────────────────────────────────────────────────
# Prueba 3 de plan.md 1.3 — via 3: las sesiones no reviven
# ─────────────────────────────────────────────────────────────────────
def test_desbloquear_no_revive_las_sesiones_anteriores_al_bloqueo(cliente):
    """La via menos evidente de las cuatro.

    Sin lista negra al bloquear, desbloquear devolveria la validez a
    los refresh emitidos ANTES del bloqueo, que siguen dentro de su
    ventana de 8 horas: el titular recuperaria el acceso con tokens
    emitidos antes de que el administrador decidiera bloquearlo.
    """
    usuario = VendedorFactory(username="jperez")
    _, refresh_anterior = _iniciar_sesion(cliente, "jperez")
    admin = AdministradorFactory()

    bloquear_usuario(usuario=usuario, ejecutor=admin)
    desbloquear_usuario(usuario=usuario, ejecutor=admin)

    respuesta = cliente.post(REFRESH, {"refresh": refresh_anterior}, format="json")

    assert respuesta.status_code != status.HTTP_200_OK


def test_tras_desbloquear_el_usuario_puede_iniciar_sesion_de_nuevo(cliente):
    """Contraprueba: desbloquear debe servir para algo."""
    usuario = VendedorFactory(username="jperez")
    admin = AdministradorFactory()

    bloquear_usuario(usuario=usuario, ejecutor=admin)
    desbloquear_usuario(usuario=usuario, ejecutor=admin)

    access, _ = _iniciar_sesion(cliente, "jperez")
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert cliente.get(YO).status_code == status.HTTP_200_OK


def test_el_bloqueo_y_la_invalidacion_comparten_transaccion():
    """Si el bloqueo se guardara y la invalidacion fallara, la cuenta
    quedaria bloqueada con sesiones vivas: el estado que RN-ACC-05
    prohibe."""
    import inspect

    from usuarios import services

    codigo = inspect.getsource(services.bloquear_usuario)
    decoradores = inspect.getsource(services).split("def bloquear_usuario")[0]

    assert "transaction.atomic" in decoradores
    assert "invalidar_sesiones" in codigo


# ─────────────────────────────────────────────────────────────────────
# Via 4 — rol y contrasena a mitad de sesion
# ─────────────────────────────────────────────────────────────────────
def test_un_cambio_de_rol_surte_efecto_sin_volver_a_iniciar_sesion(cliente):
    """CU-USU-02.

    El token sigue llevando el rol antiguo; la autorizacion lee la
    base, asi que el cambio se aplica de inmediato.
    """
    usuario = VendedorFactory(username="jperez")
    access, _ = _iniciar_sesion(cliente, "jperez")
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert cliente.get(YO).data["rol"] == Rol.VENTAS

    usuario.rol = Rol.ADMINISTRADOR
    usuario.save(update_fields=["rol"])

    # Mismo token de antes, sin refrescar nada.
    assert cliente.get(YO).data["rol"] == Rol.ADMINISTRADOR


def test_cambiar_la_contrasena_invalida_los_tokens_anteriores(cliente):
    """CHECK_REVOKE_TOKEN.

    Es lo que hace que restablecer la contrasena de una cuenta
    comprometida (RF-42) expulse de verdad a quien la estuviera usando.
    """
    usuario = VendedorFactory(username="jperez")
    access, _ = _iniciar_sesion(cliente, "jperez")
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert cliente.get(YO).status_code == status.HTTP_200_OK

    usuario.set_password("OtraClaveSegura456")
    usuario.save(update_fields=["password"])

    assert cliente.get(YO).status_code == status.HTTP_401_UNAUTHORIZED


def test_la_configuracion_activa_check_revoke_token(settings):
    assert settings.SIMPLE_JWT["CHECK_REVOKE_TOKEN"] is True
