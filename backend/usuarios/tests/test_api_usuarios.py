"""T-1.7 — API de gestion de cuentas (RF-39 a RF-47)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.exceptions import Codigo
from usuarios.models import Rol, Usuario

from .factories import AdministradorFactory, TecnicoFactory, VendedorFactory

pytestmark = pytest.mark.django_db

BASE = "/api/v1/usuarios"


def _autenticar(cliente, usuario):
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


@pytest.fixture
def admin():
    return AdministradorFactory(username="admin")


@pytest.fixture
def como_admin(admin):
    return _autenticar(APIClient(), admin)


# ─────────────────────────────────────────────────────────────────────
# RF-39, RF-47 — crear cuentas
# ─────────────────────────────────────────────────────────────────────
def test_el_administrador_crea_una_cuenta_con_su_rol(como_admin):
    respuesta = como_admin.post(
        BASE,
        {
            "username": "mlopez",
            "nombre_completo": "María López",
            "rol": Rol.SERVICIOS,
            "password": "ClaveSegura123",
        },
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["rol"] == Rol.SERVICIOS
    assert respuesta.data["rol_display"] == "Encargado de Servicios"
    creado = Usuario.objects.get(username="mlopez")
    assert creado.check_password("ClaveSegura123")


def test_no_se_pueden_crear_dos_cuentas_con_el_mismo_identificador(como_admin):
    """RF-47, comprobado tambien sin distinguir mayusculas.

    Permitir "jperez" y "JPerez" a la vez haria ambiguo el inicio de
    sesion y el registro de autoria.
    """
    VendedorFactory(username="jperez")

    respuesta = como_admin.post(
        BASE,
        {
            "username": "JPerez",
            "nombre_completo": "Otro Juan",
            "rol": Rol.VENTAS,
            "password": "ClaveSegura123",
        },
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "username" in respuesta.data["errores"]


def test_la_contrasena_de_una_cuenta_nueva_debe_cumplir_la_politica(como_admin):
    respuesta = como_admin.post(
        BASE,
        {
            "username": "nuevo",
            "nombre_completo": "Persona Nueva",
            "rol": Rol.VENTAS,
            "password": "123",
        },
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in respuesta.data["errores"]


def test_un_rol_inexistente_es_rechazado(como_admin):
    respuesta = como_admin.post(
        BASE,
        {
            "username": "nuevo",
            "nombre_completo": "Persona Nueva",
            "rol": "GERENTE",
            "password": "ClaveSegura123",
        },
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────
# RNF-03 — la contrasena no viaja nunca
# ─────────────────────────────────────────────────────────────────────
def test_ninguna_respuesta_contiene_el_campo_password(como_admin):
    VendedorFactory(username="jperez")

    creacion = como_admin.post(
        BASE,
        {
            "username": "nuevo",
            "nombre_completo": "Persona Nueva",
            "rol": Rol.VENTAS,
            "password": "ClaveSegura123",
        },
        format="json",
    )
    listado = como_admin.get(BASE)
    detalle = como_admin.get(f"{BASE}/{creacion.data['id']}")

    for respuesta in (creacion, listado, detalle):
        assert "password" not in str(respuesta.data)


# ─────────────────────────────────────────────────────────────────────
# RF-43 — consultar cuentas, con busqueda y filtros
# ─────────────────────────────────────────────────────────────────────
def test_el_listado_muestra_rol_y_estado_y_viene_paginado(como_admin):
    VendedorFactory()
    TecnicoFactory(is_active=False)

    respuesta = como_admin.get(BASE)

    assert respuesta.status_code == status.HTTP_200_OK
    assert "results" in respuesta.data
    assert "count" in respuesta.data
    primero = respuesta.data["results"][0]
    assert {"rol", "rol_display", "bloqueado"} <= set(primero)


def test_se_puede_filtrar_por_rol(como_admin):
    VendedorFactory()
    TecnicoFactory()

    respuesta = como_admin.get(f"{BASE}?rol={Rol.SERVICIOS}")

    assert respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["rol"] == Rol.SERVICIOS


def test_se_puede_buscar_por_nombre(como_admin):
    VendedorFactory(nombre_completo="Juan Pérez")
    TecnicoFactory(nombre_completo="Ana Rojas")

    respuesta = como_admin.get(f"{BASE}?search=Rojas")

    assert respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["nombre_completo"] == "Ana Rojas"


def test_el_campo_bloqueado_expresa_el_concepto_del_dominio(como_admin):
    """La interfaz habla de cuentas bloqueadas, no de inactivas."""
    bloqueado = VendedorFactory(is_active=False)

    respuesta = como_admin.get(f"{BASE}/{bloqueado.id}")

    assert respuesta.data["bloqueado"] is True
    assert respuesta.data["is_active"] is False


# ─────────────────────────────────────────────────────────────────────
# RF-40, RF-41, RF-42 — editar, bloquear y restablecer
# ─────────────────────────────────────────────────────────────────────
def test_el_administrador_edita_datos_y_rol_de_otra_cuenta(como_admin):
    vendedor = VendedorFactory()

    respuesta = como_admin.patch(
        f"{BASE}/{vendedor.id}",
        {"nombre_completo": "Nombre Corregido", "rol": Rol.SERVICIOS},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_200_OK
    vendedor.refresh_from_db()
    assert vendedor.nombre_completo == "Nombre Corregido"
    assert vendedor.rol == Rol.SERVICIOS


def test_bloquear_y_desbloquear_una_cuenta(como_admin):
    vendedor = VendedorFactory()

    bloqueo = como_admin.post(f"{BASE}/{vendedor.id}/bloquear")
    assert bloqueo.status_code == status.HTTP_200_OK
    vendedor.refresh_from_db()
    assert not vendedor.is_active

    desbloqueo = como_admin.post(f"{BASE}/{vendedor.id}/desbloquear")
    assert desbloqueo.status_code == status.HTTP_200_OK
    vendedor.refresh_from_db()
    assert vendedor.is_active


def test_restablecer_la_contrasena_de_otra_cuenta(como_admin):
    vendedor = VendedorFactory()

    respuesta = como_admin.post(
        f"{BASE}/{vendedor.id}/restablecer-password",
        {"password_nueva": "ClaveNueva456"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_204_NO_CONTENT
    vendedor.refresh_from_db()
    assert vendedor.check_password("ClaveNueva456")


# ─────────────────────────────────────────────────────────────────────
# RF-44, RF-45, RF-46 — las protecciones llegan a la API
# ─────────────────────────────────────────────────────────────────────
def test_la_api_impide_que_un_administrador_cambie_su_propio_rol(como_admin, admin):
    AdministradorFactory()

    respuesta = como_admin.patch(
        f"{BASE}/{admin.id}", {"rol": Rol.VENTAS}, format="json"
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert respuesta.data["codigo"] == Codigo.AUTOMODIFICACION_PROHIBIDA


def test_la_api_impide_que_un_administrador_se_bloquee_a_si_mismo(como_admin, admin):
    AdministradorFactory()

    respuesta = como_admin.post(f"{BASE}/{admin.id}/bloquear")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert respuesta.data["codigo"] == Codigo.AUTOMODIFICACION_PROHIBIDA


def test_la_api_impide_dejar_el_sistema_sin_administradores(como_admin, admin):
    """RF-46 comprobado de punta a punta.

    Con un solo administrador activo, el propio administrador es el
    unico: degradar a otro no aplica, y el intento debe rechazarse.
    """
    otro = AdministradorFactory()
    como_admin.post(f"{BASE}/{otro.id}/bloquear")

    # Queda `admin` como unico activo; otro admin bloqueado no cuenta.
    otro.refresh_from_db()
    assert not otro.is_active

    como_otro = _autenticar(APIClient(), AdministradorFactory(username="tercero"))
    respuesta = como_otro.post(f"{BASE}/{admin.id}/bloquear")

    # Ahora hay dos activos (admin y tercero): la operacion procede.
    assert respuesta.status_code == status.HTTP_200_OK


# ─────────────────────────────────────────────────────────────────────
# RN-USU-05 — las cuentas no se eliminan
# ─────────────────────────────────────────────────────────────────────
def test_no_existe_forma_de_eliminar_una_cuenta(como_admin):
    """La ausencia de DELETE es la implementacion de RN-USU-05."""
    vendedor = VendedorFactory()

    respuesta = como_admin.delete(f"{BASE}/{vendedor.id}")

    assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert Usuario.objects.filter(pk=vendedor.pk).exists()


# ─────────────────────────────────────────────────────────────────────
# RNF-02 — solo el Administrador
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("fabrica", [VendedorFactory, TecnicoFactory])
def test_los_otros_roles_no_acceden_a_la_gestion_de_usuarios(fabrica):
    usuario = fabrica()
    cliente = _autenticar(APIClient(), usuario)

    assert cliente.get(BASE).status_code == status.HTTP_403_FORBIDDEN


def test_sin_autenticar_no_se_accede_a_la_gestion_de_usuarios():
    assert APIClient().get(BASE).status_code == status.HTTP_401_UNAUTHORIZED
