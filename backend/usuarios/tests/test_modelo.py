"""T-1.1 — Modelo Usuario y arranque del primer administrador."""

import pytest
from django.db import IntegrityError, transaction

from usuarios.models import Rol, Usuario

from .factories import AdministradorFactory, TecnicoFactory, VendedorFactory

pytestmark = pytest.mark.django_db


# ─────────────────────────────────────────────────────────────────────
# Arranque del sistema (plan.md 11.1)
# ─────────────────────────────────────────────────────────────────────
def test_createsuperuser_produce_un_administrador_utilizable():
    """El criterio central de T-1.1.

    Con la base vacia nadie puede crear la primera cuenta (RN-USU-01).
    createsuperuser es la salida, y debe dejar una cuenta que pase las
    comprobaciones de rol, no solo que pueda autenticarse.
    """
    usuario = Usuario.objects.create_superuser(
        username="admin", password="ClaveSegura123"
    )

    assert usuario.rol == Rol.ADMINISTRADOR
    assert usuario.es_administrador
    assert usuario.is_active


def test_el_superusuario_no_queda_sin_rol_aunque_no_se_indique():
    """Un superusuario sin rol podria autenticarse pero no pasaria
    ninguna clase de permiso: seria un administrador inutil."""
    usuario = Usuario.objects.create_superuser(
        username="admin2", password="ClaveSegura123"
    )

    assert usuario.rol != ""
    assert usuario.rol is not None


def test_el_rol_no_se_puede_forzar_a_otro_valor_en_createsuperuser():
    usuario = Usuario.objects.create_superuser(
        username="admin3", password="ClaveSegura123", rol=Rol.VENTAS
    )

    assert usuario.rol == Rol.ADMINISTRADOR


# ─────────────────────────────────────────────────────────────────────
# RN-USU-06 — identificador unico
# ─────────────────────────────────────────────────────────────────────
def test_no_se_pueden_crear_dos_cuentas_con_el_mismo_username():
    VendedorFactory(username="jperez")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VendedorFactory(username="jperez")


# ─────────────────────────────────────────────────────────────────────
# RN-ACC-02 y RN-ACC-03 — un rol por usuario, con herencia del Administrador
# ─────────────────────────────────────────────────────────────────────
def test_la_base_rechaza_un_rol_que_no_esta_en_el_catalogo():
    """RN-ACC-02 declarado como restriccion, no solo como choices.

    `choices` solo valida en formularios de Django; una escritura
    directa lo saltaria. La restriccion CHECK no.
    """
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.create(
                username="raro", nombre_completo="Rol Invalido", rol="GERENTE"
            )


def test_el_administrador_hereda_las_capacidades_de_los_otros_roles():
    """RN-ACC-03: puede hacer todo lo que hacen los otros dos."""
    admin = AdministradorFactory()

    assert admin.es_administrador
    assert admin.puede_vender
    assert admin.puede_atender_servicios


def test_el_vendedor_solo_puede_vender():
    vendedor = VendedorFactory()

    assert not vendedor.es_administrador
    assert vendedor.puede_vender
    assert not vendedor.puede_atender_servicios


def test_el_tecnico_solo_puede_atender_servicios():
    tecnico = TecnicoFactory()

    assert not tecnico.es_administrador
    assert not tecnico.puede_vender
    assert tecnico.puede_atender_servicios


# ─────────────────────────────────────────────────────────────────────
# RNF-03 — contrasenas cifradas
# ─────────────────────────────────────────────────────────────────────
def test_la_contrasena_se_guarda_cifrada_y_nunca_en_texto_plano():
    usuario = VendedorFactory(password="ClaveSegura123")

    assert usuario.password != "ClaveSegura123"
    assert usuario.password.startswith("pbkdf2_")
    assert usuario.check_password("ClaveSegura123")


# ─────────────────────────────────────────────────────────────────────
# RN-USU-05 — el bloqueo reutiliza is_active
# ─────────────────────────────────────────────────────────────────────
def test_bloquear_una_cuenta_conserva_sus_datos():
    usuario = VendedorFactory(nombre_completo="Juan Pérez")

    usuario.is_active = False
    usuario.save()
    usuario.refresh_from_db()

    assert usuario.nombre_completo == "Juan Pérez"
    assert Usuario.objects.filter(pk=usuario.pk).exists()
