"""T-3.1 a T-3.4 — Configuracion del sistema (RN-CAT-07, RF-52, RF-53)."""

import pytest
from django.db import IntegrityError, connection, transaction
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.services import umbral_stock_bajo
from catalogo.tests.factories import ProductoFactory
from configuracion.models import ConfiguracionSistema
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)

pytestmark = pytest.mark.django_db

URL = "/api/v1/configuracion"
PRODUCTOS = "/api/v1/productos"


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
def como_admin():
    return _autenticar(AdministradorFactory())


# ═════════════════════════════════════════════════════════════════════
# T-3.1 — Fila unica
# ═════════════════════════════════════════════════════════════════════
def test_la_configuracion_existe_tras_migrar():
    """El criterio de T-3.1.

    El catalogo consulta el umbral en cada listado (RF-53) y el panel
    en cada carga: no puede faltar en una base recien migrada.
    """
    assert ConfiguracionSistema.objects.count() == 1
    assert ConfiguracionSistema.obtener().umbral_stock_bajo == 5


def test_la_base_impide_crear_una_segunda_fila():
    """La unicidad no depende de que el codigo recuerde no crearla."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO configuracion_configuracionsistema "
                    "(id, umbral_stock_bajo, actualizado_en) "
                    "VALUES (2, 10, NOW())"
                )

    assert ConfiguracionSistema.objects.count() == 1


def test_la_base_rechaza_un_umbral_negativo():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE configuracion_configuracionsistema "
                    "SET umbral_stock_bajo = -1 WHERE id = 1"
                )


def test_obtener_es_idempotente():
    primera = ConfiguracionSistema.obtener()
    segunda = ConfiguracionSistema.obtener()

    assert primera.pk == segunda.pk == 1
    assert ConfiguracionSistema.objects.count() == 1


# ═════════════════════════════════════════════════════════════════════
# T-3.2 — API (RF-52)
# ═════════════════════════════════════════════════════════════════════
def test_el_administrador_consulta_el_umbral_vigente(como_admin):
    respuesta = como_admin.get(URL)

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta.data["umbral_stock_bajo"] == 5


def test_el_administrador_modifica_el_umbral(como_admin):
    respuesta = como_admin.patch(URL, {"umbral_stock_bajo": 12}, format="json")

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta.data["umbral_stock_bajo"] == 12
    assert ConfiguracionSistema.obtener().umbral_stock_bajo == 12


def test_se_registra_quien_cambio_el_umbral_y_cuando(como_admin):
    """RN-CAT-07 pide dejar constancia del cambio."""
    antes = ConfiguracionSistema.obtener().actualizado_en

    respuesta = como_admin.patch(URL, {"umbral_stock_bajo": 8}, format="json")

    assert respuesta.data["actualizado_por_nombre"] is not None
    configuracion = ConfiguracionSistema.obtener()
    assert configuracion.actualizado_por is not None
    assert configuracion.actualizado_en > antes


def test_el_umbral_cero_es_valido(como_admin):
    """Umbral cero significa avisar solo cuando no queda nada.

    Es un valor legitimo, no un caso a rechazar: una empresa puede
    preferir no recibir avisos anticipados.
    """
    respuesta = como_admin.patch(URL, {"umbral_stock_bajo": 0}, format="json")

    assert respuesta.status_code == status.HTTP_200_OK
    assert ConfiguracionSistema.obtener().umbral_stock_bajo == 0


def test_se_rechaza_un_umbral_negativo(como_admin):
    respuesta = como_admin.patch(URL, {"umbral_stock_bajo": -3}, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "umbral_stock_bajo" in respuesta.data["errores"]
    assert ConfiguracionSistema.obtener().umbral_stock_bajo == 5


def test_no_se_puede_falsificar_quien_hizo_el_cambio(como_admin):
    """El autor lo pone el servidor, no el cliente."""
    otro = VendedorFactory(nombre_completo="Alguien Más")

    respuesta = como_admin.patch(
        URL,
        {"umbral_stock_bajo": 7, "actualizado_por": otro.id},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_200_OK
    assert ConfiguracionSistema.obtener().actualizado_por_id != otro.id


@pytest.mark.parametrize("fabrica", [VendedorFactory, TecnicoFactory])
def test_los_otros_roles_no_acceden_a_la_configuracion(fabrica):
    """spec.md matriz 4.4: configurar el umbral es solo del Administrador."""
    cliente = _autenticar(fabrica())

    assert cliente.get(URL).status_code == status.HTTP_403_FORBIDDEN
    assert (
        cliente.patch(URL, {"umbral_stock_bajo": 99}, format="json").status_code
        == status.HTTP_403_FORBIDDEN
    )


def test_el_recurso_no_admite_creacion_ni_borrado(como_admin):
    """Es un recurso singular: hay exactamente una configuracion."""
    assert como_admin.post(URL, {}, format="json").status_code == (
        status.HTTP_405_METHOD_NOT_ALLOWED
    )
    assert como_admin.delete(URL).status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ═════════════════════════════════════════════════════════════════════
# T-3.4 — El catalogo usa el umbral real (RF-53)
# ═════════════════════════════════════════════════════════════════════
def test_cambiar_el_umbral_cambia_de_inmediato_que_productos_estan_marcados(
    como_admin,
):
    """El criterio central de T-3.4.

    La regla vive en el SERVIDOR: cambiar el umbral altera lo que el
    catalogo informa sin tocar una sola linea del frontend, porque la
    interfaz nunca conoce el numero, solo el veredicto.
    """
    ProductoFactory(nombre="Con ocho", stock=8)

    # Con el umbral inicial de 5, ocho unidades no son pocas.
    antes = como_admin.get(PRODUCTOS)
    assert antes.data["results"][0]["stock_bajo"] is False

    como_admin.patch(URL, {"umbral_stock_bajo": 10}, format="json")

    # Sin cambiar nada del producto ni del cliente.
    despues = como_admin.get(PRODUCTOS)
    assert despues.data["results"][0]["stock_bajo"] is True


def test_el_filtro_de_existencias_bajas_sigue_al_umbral(como_admin):
    ProductoFactory(nombre="Con tres", stock=3)
    ProductoFactory(nombre="Con veinte", stock=20)

    assert como_admin.get(f"{PRODUCTOS}?stock_bajo=true").data["count"] == 1

    como_admin.patch(URL, {"umbral_stock_bajo": 25}, format="json")

    assert como_admin.get(f"{PRODUCTOS}?stock_bajo=true").data["count"] == 2


def test_con_umbral_cero_solo_se_marca_lo_agotado(como_admin):
    ProductoFactory(nombre="Agotado", stock=0)
    ProductoFactory(nombre="Con uno", stock=1)

    como_admin.patch(URL, {"umbral_stock_bajo": 0}, format="json")
    respuesta = como_admin.get(PRODUCTOS)
    por_nombre = {p["nombre"]: p for p in respuesta.data["results"]}

    assert por_nombre["Agotado"]["stock_bajo"] is True
    assert por_nombre["Con uno"]["stock_bajo"] is False


def test_cambiar_el_umbral_no_altera_ningun_dato_del_catalogo(como_admin):
    """RN-CAT-07: el umbral decide como se MUESTRA el catalogo, nunca
    modifica existencias ni precios."""
    producto = ProductoFactory(stock=7, precio=100)

    como_admin.patch(URL, {"umbral_stock_bajo": 50}, format="json")

    producto.refresh_from_db()
    assert producto.stock == 7
    assert producto.precio == 100


def test_el_catalogo_lee_el_umbral_de_la_configuracion_y_no_de_una_constante():
    """Prueba estructural.

    Si alguien volviera a poner un numero fijo en catalogo/services.py,
    el umbral dejaria de ser configurable y RF-52 quedaria incumplido
    en silencio: la pantalla seguiria guardando el valor y el catalogo
    lo ignoraria.
    """
    configuracion = ConfiguracionSistema.obtener()
    configuracion.umbral_stock_bajo = 42
    configuracion.save(update_fields=["umbral_stock_bajo"])

    assert umbral_stock_bajo() == 42
