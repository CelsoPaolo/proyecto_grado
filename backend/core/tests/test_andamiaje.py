"""Pruebas del andamiaje: T-0.6, T-0.7 y T-0.9.

Verifican el comportamiento por defecto del framework, que es la base
sobre la que se apoyan todos los modulos posteriores. Si algo de esto
se rompe, se rompe en silencio y en todos los endpoints a la vez.
"""

import pytest
from django.urls import path
from rest_framework import status
from rest_framework.test import APIClient

from core.exceptions import Codigo

# Las rutas de prueba se montan solo para este modulo.
urlpatterns = [
    path("_prueba/", __import__("django.urls", fromlist=["include"]).include("core.urls_prueba")),
]


@pytest.fixture
def cliente():
    return APIClient()


# ─────────────────────────────────────────────────────────────────────
# T-0.6 — DRF con permisos cerrados por defecto (RNF-01)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.urls(__name__)
def test_endpoint_sin_permisos_declarados_responde_401_sin_token(cliente):
    """El criterio central de T-0.6.

    Una vista que NO declara permission_classes debe quedar cerrada.
    Es lo que convierte un descuido del programador en un 401 en vez de
    en una fuga de datos.
    """
    respuesta = cliente.get("/_prueba/sin-permisos")

    assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.urls(__name__)
def test_el_401_llega_con_el_formato_uniforme_de_error(cliente):
    respuesta = cliente.get("/_prueba/sin-permisos")

    assert respuesta.data["codigo"] == Codigo.NO_AUTENTICADO
    assert "detalle" in respuesta.data


def test_la_configuracion_por_defecto_exige_autenticacion(settings):
    """Refuerza lo anterior desde la configuracion misma.

    Si alguien cambiara el valor por defecto a AllowAny, la prueba
    anterior seguiria pasando solo mientras esa vista concreta
    existiera; esta lo detecta siempre.
    """
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated"
    ]


def test_la_paginacion_por_defecto_esta_activa(settings):
    """RNF-18: los listados extensos se presentan paginados."""
    assert settings.REST_FRAMEWORK["PAGE_SIZE"] == 20
    assert (
        settings.REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]
        == "core.pagination.PaginacionEstandar"
    )


# ─────────────────────────────────────────────────────────────────────
# T-0.7 — Formato uniforme de error (RNF-06, RNF-15)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.urls(__name__)
def test_un_error_de_negocio_y_un_401_comparten_la_misma_forma(cliente):
    """El criterio de T-0.7.

    Dos errores de naturaleza distinta deben llegar al frontend con la
    misma estructura, para que tenga un unico camino de tratamiento.
    """
    error_negocio = cliente.get("/_prueba/error-negocio")
    error_autenticacion = cliente.get("/_prueba/sin-permisos")

    assert error_negocio.status_code == status.HTTP_400_BAD_REQUEST
    assert error_autenticacion.status_code == status.HTTP_401_UNAUTHORIZED

    for respuesta in (error_negocio, error_autenticacion):
        assert set(respuesta.data.keys()) == {"codigo", "detalle"}
        assert isinstance(respuesta.data["codigo"], str)
        assert isinstance(respuesta.data["detalle"], str)


@pytest.mark.urls(__name__)
def test_el_error_de_negocio_conserva_su_codigo(cliente):
    respuesta = cliente.get("/_prueba/error-negocio")

    assert respuesta.data["codigo"] == Codigo.VALIDACION
    assert respuesta.data["detalle"] == "Regla de negocio incumplida."


@pytest.mark.urls(__name__)
def test_ningun_error_expone_trazas_internas(cliente):
    """RNF-06: los mensajes no revelan informacion interna del sistema."""
    respuesta = cliente.get("/_prueba/error-negocio")

    cuerpo = str(respuesta.data)
    for filtracion in ("Traceback", "File \"", "django/", "site-packages"):
        assert filtracion not in cuerpo


# ─────────────────────────────────────────────────────────────────────
# T-0.9 — El entorno de pruebas funciona de punta a punta
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_la_base_de_pruebas_usa_postgresql(settings):
    """RNF-08 depende de esto.

    La prueba de concurrencia de T-4.4 necesita bloqueo por fila, que
    SQLite no ofrece. Si alguien cambiara el motor, esa garantia se
    perderia en silencio: aqui se detecta de inmediato.
    """
    from django.db import connection

    assert connection.vendor == "postgresql"
    assert settings.DATABASES["default"]["ENGINE"] == (
        "django.db.backends.postgresql"
    )


@pytest.mark.django_db
def test_el_modelo_de_usuario_es_el_propio_del_proyecto():
    """T-0.4: la tabla es usuarios_usuario, no auth_user."""
    from django.contrib.auth import get_user_model

    Usuario = get_user_model()

    assert Usuario._meta.label == "usuarios.Usuario"
    assert Usuario._meta.db_table == "usuarios_usuario"
