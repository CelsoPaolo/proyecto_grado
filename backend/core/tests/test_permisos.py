"""T-1.2 — Clases de permiso por rol (RNF-02, RN-ACC-04)."""

import pytest
from rest_framework.test import APIRequestFactory

from core.permissions import (
    EsAdministrador,
    PuedeAtenderServicios,
    PuedeVender,
)
from usuarios.models import Rol
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def peticion():
    return APIRequestFactory().get("/")


def _evaluar(clase, peticion, usuario):
    peticion.user = usuario
    return clase().has_permission(peticion, view=None)


# ─────────────────────────────────────────────────────────────────────
# Matriz de las tres clases por los tres roles
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("fabrica", "admin", "vende", "atiende"),
    [
        (AdministradorFactory, True, True, True),
        (VendedorFactory, False, True, False),
        (TecnicoFactory, False, False, True),
    ],
    ids=["administrador", "encargado_de_ventas", "encargado_de_servicios"],
)
def test_cada_rol_pasa_solo_las_clases_que_le_corresponden(
    peticion, fabrica, admin, vende, atiende
):
    """RN-ACC-03: el Administrador hereda las capacidades de los otros."""
    usuario = fabrica()

    assert _evaluar(EsAdministrador, peticion, usuario) is admin
    assert _evaluar(PuedeVender, peticion, usuario) is vende
    assert _evaluar(PuedeAtenderServicios, peticion, usuario) is atiende


# ─────────────────────────────────────────────────────────────────────
# RNF-01 y RN-ACC-05
# ─────────────────────────────────────────────────────────────────────
def test_un_usuario_no_autenticado_no_pasa_ninguna_clase(peticion):
    from django.contrib.auth.models import AnonymousUser

    for clase in (EsAdministrador, PuedeVender, PuedeAtenderServicios):
        assert _evaluar(clase, peticion, AnonymousUser()) is False


def test_una_cuenta_bloqueada_no_pasa_ninguna_clase(peticion):
    """RN-ACC-05, defensa en profundidad.

    JWTAuthentication ya rechaza a un usuario inactivo antes de llegar
    aqui. Esta comprobacion existe para que la autorizacion no dependa
    de que la capa de autenticacion siga comportandose asi.
    """
    admin_bloqueado = AdministradorFactory(is_active=False)

    for clase in (EsAdministrador, PuedeVender, PuedeAtenderServicios):
        assert _evaluar(clase, peticion, admin_bloqueado) is False


# ─────────────────────────────────────────────────────────────────────
# PT-02, via 4: el rol se lee de la base, nunca del token
# ─────────────────────────────────────────────────────────────────────
def test_el_rol_se_lee_del_usuario_y_no_de_ningun_dato_de_la_peticion(peticion):
    """Un rol manipulado en el token no debe conceder nada.

    Se simula el peor caso: la peticion trae un rol falsificado de
    administrador, pero el usuario cargado desde la base es un
    vendedor. La autorizacion debe seguir al usuario, no a la peticion.
    """
    vendedor = VendedorFactory()
    peticion.auth = {"rol": Rol.ADMINISTRADOR}  # reclamo falsificado
    peticion.rol = Rol.ADMINISTRADOR

    assert _evaluar(EsAdministrador, peticion, vendedor) is False


def test_un_cambio_de_rol_surte_efecto_de_inmediato(peticion):
    """CU-USU-02: no hace falta volver a iniciar sesion.

    Como el rol se lee de la fila cargada en cada peticion, cambiarlo
    se refleja en la comprobacion siguiente.
    """
    usuario = VendedorFactory()
    assert _evaluar(EsAdministrador, peticion, usuario) is False

    usuario.rol = Rol.ADMINISTRADOR
    usuario.save(update_fields=["rol"])
    usuario.refresh_from_db()

    assert _evaluar(EsAdministrador, peticion, usuario) is True


def test_ninguna_clase_de_permiso_consulta_el_token():
    """Comprobacion estructural, no de comportamiento.

    Si alguien anadiera una lectura del token a core/permissions.py,
    la via 4 de plan.md 1.3 quedaria rota en silencio y ningun caso de
    prueba de arriba lo detectaria necesariamente.
    """
    from pathlib import Path

    import core.permissions as modulo

    codigo = Path(modulo.__file__).read_text(encoding="utf-8")
    cuerpo = "\n".join(
        linea for linea in codigo.splitlines() if not linea.strip().startswith("#")
    )

    for lectura_prohibida in ("request.auth", "token[", "decode(", "payload"):
        assert lectura_prohibida not in cuerpo
