"""T-1.6 — Protecciones de la cuenta de administrador.

RN-USU-02 (nadie cambia su propio rol), RN-USU-03 (nadie se bloquea a
si mismo) y RN-USU-04 (el sistema nunca queda sin administradores
activos).

Un fallo aqui puede dejar el sistema **sin ningun administrador**, sin
forma de repararlo desde la interfaz: crear cuentas exige ser
administrador. Es una de las cinco tareas criticas de tasks.md.
"""

import pytest

from usuarios.models import Rol, Usuario
from usuarios.services import (
    AutomodificacionProhibida,
    UltimoAdministrador,
    actualizar_usuario,
    bloquear_usuario,
    crear_usuario,
    desbloquear_usuario,
    restablecer_password,
)

from .factories import AdministradorFactory, TecnicoFactory, VendedorFactory

pytestmark = pytest.mark.django_db


# ─────────────────────────────────────────────────────────────────────
# RN-USU-02 — nadie cambia su propio rol
# ─────────────────────────────────────────────────────────────────────
def test_un_administrador_no_puede_cambiar_su_propio_rol():
    admin = AdministradorFactory()
    AdministradorFactory()  # otro administrador, para aislar de RN-USU-04

    with pytest.raises(AutomodificacionProhibida):
        actualizar_usuario(usuario=admin, ejecutor=admin, rol=Rol.VENTAS)

    admin.refresh_from_db()
    assert admin.rol == Rol.ADMINISTRADOR


def test_si_puede_cambiar_el_rol_de_otro():
    admin = AdministradorFactory()
    vendedor = VendedorFactory()

    actualizar_usuario(usuario=vendedor, ejecutor=admin, rol=Rol.SERVICIOS)

    vendedor.refresh_from_db()
    assert vendedor.rol == Rol.SERVICIOS


def test_puede_editar_su_propio_nombre_sin_tocar_el_rol():
    """La prohibicion es sobre el rol, no sobre la cuenta entera."""
    admin = AdministradorFactory()

    actualizar_usuario(usuario=admin, ejecutor=admin, nombre_completo="Nuevo Nombre")

    admin.refresh_from_db()
    assert admin.nombre_completo == "Nuevo Nombre"
    assert admin.rol == Rol.ADMINISTRADOR


def test_asignar_el_mismo_rol_que_ya_tiene_no_se_considera_cambio():
    admin = AdministradorFactory()

    actualizar_usuario(usuario=admin, ejecutor=admin, rol=Rol.ADMINISTRADOR)

    admin.refresh_from_db()
    assert admin.rol == Rol.ADMINISTRADOR


# ─────────────────────────────────────────────────────────────────────
# RN-USU-03 — nadie se bloquea a si mismo
# ─────────────────────────────────────────────────────────────────────
def test_un_administrador_no_puede_bloquearse_a_si_mismo():
    admin = AdministradorFactory()
    AdministradorFactory()

    with pytest.raises(AutomodificacionProhibida):
        bloquear_usuario(usuario=admin, ejecutor=admin)

    admin.refresh_from_db()
    assert admin.is_active


def test_si_puede_bloquear_a_otro():
    admin = AdministradorFactory()
    vendedor = VendedorFactory()

    bloquear_usuario(usuario=vendedor, ejecutor=admin)

    vendedor.refresh_from_db()
    assert not vendedor.is_active


# ─────────────────────────────────────────────────────────────────────
# RN-USU-04 — nunca cero administradores activos
# ─────────────────────────────────────────────────────────────────────
def test_no_se_puede_bloquear_al_unico_administrador():
    """El escenario que dejaria el sistema inaccesible."""
    unico = AdministradorFactory()
    otro_admin_que_ejecuta = AdministradorFactory()
    # Se bloquea primero al ejecutor para dejar a `unico` realmente solo.
    bloquear_usuario(usuario=otro_admin_que_ejecuta, ejecutor=unico)

    with pytest.raises(UltimoAdministrador):
        bloquear_usuario(usuario=unico, ejecutor=otro_admin_que_ejecuta)

    unico.refresh_from_db()
    assert unico.is_active


def test_no_se_puede_degradar_de_rol_al_unico_administrador():
    unico = AdministradorFactory()
    ejecutor = AdministradorFactory()
    bloquear_usuario(usuario=ejecutor, ejecutor=unico)

    with pytest.raises(UltimoAdministrador):
        actualizar_usuario(usuario=unico, ejecutor=ejecutor, rol=Rol.VENTAS)

    unico.refresh_from_db()
    assert unico.rol == Rol.ADMINISTRADOR


def test_si_hay_dos_administradores_se_puede_bloquear_a_uno():
    primero = AdministradorFactory()
    segundo = AdministradorFactory()

    bloquear_usuario(usuario=segundo, ejecutor=primero)

    segundo.refresh_from_db()
    assert not segundo.is_active
    assert Usuario.objects.filter(rol=Rol.ADMINISTRADOR, is_active=True).count() == 1


def test_un_administrador_bloqueado_no_cuenta_para_la_regla():
    """El matiz que hace la regla correcta.

    Contar administradores sin mirar `is_active` permitiria quedarse
    con un unico administrador bloqueado, es decir, sin acceso real.
    """
    activo = AdministradorFactory()
    bloqueado = AdministradorFactory(is_active=False)
    ejecutor = AdministradorFactory()
    bloquear_usuario(usuario=ejecutor, ejecutor=activo)

    with pytest.raises(UltimoAdministrador):
        bloquear_usuario(usuario=activo, ejecutor=ejecutor)

    assert not bloqueado.is_active


def test_bloquear_a_un_no_administrador_nunca_dispara_la_regla():
    admin = AdministradorFactory()
    tecnico = TecnicoFactory()

    bloquear_usuario(usuario=tecnico, ejecutor=admin)

    tecnico.refresh_from_db()
    assert not tecnico.is_active


def test_desbloquear_restituye_el_acceso():
    admin = AdministradorFactory()
    vendedor = VendedorFactory()
    bloquear_usuario(usuario=vendedor, ejecutor=admin)

    desbloquear_usuario(usuario=vendedor, ejecutor=admin)

    vendedor.refresh_from_db()
    assert vendedor.is_active


# ─────────────────────────────────────────────────────────────────────
# CU-USU-01 y CU-USU-04
# ─────────────────────────────────────────────────────────────────────
def test_crear_usuario_guarda_la_contrasena_cifrada():
    admin = AdministradorFactory()

    usuario = crear_usuario(
        username="nuevo",
        nombre_completo="Persona Nueva",
        rol=Rol.VENTAS,
        password="ClaveSegura123",
        ejecutor=admin,
    )

    assert usuario.password != "ClaveSegura123"
    assert usuario.check_password("ClaveSegura123")
    assert usuario.is_active


def test_restablecer_password_invalida_las_sesiones_vigentes():
    """RF-42: debe expulsar a quien estuviera usando la cuenta.

    Si solo cambiara la clave, un atacante con un token vigente
    seguiria dentro hasta que expirara.
    """
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )
    from rest_framework_simplejwt.tokens import RefreshToken

    admin = AdministradorFactory()
    usuario = VendedorFactory()
    RefreshToken.for_user(usuario)

    restablecer_password(
        usuario=usuario, password_nueva="OtraClave456", ejecutor=admin
    )

    pendientes = OutstandingToken.objects.filter(user=usuario)
    assert pendientes.exists()
    for token in pendientes:
        assert BlacklistedToken.objects.filter(token=token).exists()
    usuario.refresh_from_db()
    assert usuario.check_password("OtraClave456")


# ─────────────────────────────────────────────────────────────────────
# Concurrencia: dos administradores bloqueandose a la vez
# ─────────────────────────────────────────────────────────────────────
def test_la_validacion_bloquea_las_filas_de_administradores_activos():
    """RN-USU-04 bajo concurrencia.

    Sin `select_for_update()`, dos administradores que se bloquean
    mutuamente al mismo tiempo podrian pasar ambos la validacion y
    dejar el sistema sin acceso. Es el mismo problema que el del stock
    (RNF-08), con una consecuencia peor: nadie podria repararlo desde
    la interfaz.

    La prueba de carrera real con hilos se aborda en T-4.4, que monta
    la infraestructura de concurrencia; aqui se comprueba que el
    bloqueo de filas esta puesto, que es lo que la hace imposible.
    """
    import inspect

    from usuarios import services

    codigo = inspect.getsource(services._validar_queda_un_administrador)

    assert "select_for_update" in codigo
    assert "is_active=True" in codigo


@pytest.mark.parametrize(
    "operacion",
    ["actualizar_usuario", "bloquear_usuario", "desbloquear_usuario"],
)
def test_todas_las_operaciones_sobre_cuentas_son_atomicas(operacion):
    """Una validacion que no comparte transaccion con su escritura no
    protege de nada: entre ambas cabe otra operacion."""
    import inspect

    from usuarios import services

    fuente = inspect.getsource(services)
    bloque = fuente.split(f"def {operacion}")[0]

    assert bloque.rstrip().endswith("@transaction.atomic")
