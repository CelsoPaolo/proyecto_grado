"""Reglas de negocio de cuentas y sesiones.

Las reglas viven aqui y no en los serializers ni en las vistas: varias
combinan mas de una tabla o exigen atomicidad, y desde una vista serian
imposibles de probar en aislamiento y se duplicarian en cuanto hubiera
un segundo punto de entrada (plan.md seccion 2.2).

Las protecciones de la cuenta de administrador (RN-USU-02 a RN-USU-04)
son el motivo principal de que esta capa exista: RN-USU-04 no se puede
comprobar en un serializer porque exige consultar el estado global del
sistema, no el del objeto que se esta editando.
"""

from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from core.exceptions import Codigo, ErrorDeNegocio
from usuarios.models import Rol, Usuario


# ─────────────────────────────────────────────────────────────────────
# Errores propios del modulo
# ─────────────────────────────────────────────────────────────────────
class UltimoAdministrador(ErrorDeNegocio):
    """RN-USU-04: el sistema nunca queda sin administradores activos."""

    codigo = Codigo.ULTIMO_ADMINISTRADOR
    default_detail = "La operacion dejaria al sistema sin ningun administrador activo."


class AutomodificacionProhibida(ErrorDeNegocio):
    """RN-USU-02 y RN-USU-03: nadie se cambia el rol ni se bloquea."""

    codigo = Codigo.AUTOMODIFICACION_PROHIBIDA
    default_detail = "No puede realizar esta operacion sobre su propia cuenta."


# ─────────────────────────────────────────────────────────────────────
# Sesiones
# ─────────────────────────────────────────────────────────────────────
def invalidar_sesiones(usuario):
    """Via 3 de plan.md seccion 1.3 - lista negra al bloquear.

    Anade a la lista negra todos los refresh tokens pendientes de la
    cuenta.

    Sin este paso, desbloquear una cuenta mas tarde **resucitaria** las
    sesiones antiguas que siguieran dentro de su ventana de 8 horas:
    el titular recuperaria el acceso sin volver a autenticarse, con
    tokens emitidos antes de que el administrador decidiera bloquearlo.
    """
    tokens = OutstandingToken.objects.filter(user=usuario)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)
    return tokens.count()


# ─────────────────────────────────────────────────────────────────────
# Protecciones de la cuenta de administrador
# ─────────────────────────────────────────────────────────────────────
def _validar_no_es_uno_mismo(usuario, ejecutor, mensaje):
    """RN-USU-02 y RN-USU-03."""
    if usuario.pk == ejecutor.pk:
        raise AutomodificacionProhibida(mensaje)


def _validar_queda_un_administrador(usuario, *, nuevo_rol=None, bloqueando=False):
    """RN-USU-04 - el sistema nunca queda sin administradores activos.

    La consulta se hace con `select_for_update()` sobre las cuentas de
    administrador activas, dentro de la transaccion de la operacion.

    Sin ese bloqueo, dos administradores que se bloquean mutuamente
    **a la vez** podrian pasar ambos la validacion y dejar el sistema
    sin acceso. Es el mismo problema de concurrencia que el del stock
    (RNF-08), con una consecuencia peor: nadie podria repararlo desde
    la interfaz, porque crear cuentas exige ser administrador.
    """
    if not usuario.es_administrador:
        # Quien no es administrador no puede ser el ultimo.
        return

    deja_de_ser_admin = bloqueando or (
        nuevo_rol is not None and nuevo_rol != Rol.ADMINISTRADOR
    )
    if not deja_de_ser_admin:
        return

    otros_administradores_activos = (
        Usuario.objects.select_for_update()
        .filter(rol=Rol.ADMINISTRADOR, is_active=True)
        .exclude(pk=usuario.pk)
        .count()
    )

    if otros_administradores_activos == 0:
        raise UltimoAdministrador()


# ─────────────────────────────────────────────────────────────────────
# Operaciones sobre cuentas
# ─────────────────────────────────────────────────────────────────────
@transaction.atomic
def crear_usuario(*, username, nombre_completo, rol, password, ejecutor):
    """CU-USU-01 (RF-39, RF-47).

    Solo el Administrador llega aqui: lo garantiza la clase de permiso
    de la vista (RN-USU-01).
    """
    usuario = Usuario(username=username, nombre_completo=nombre_completo, rol=rol)
    usuario.set_password(password)
    usuario.save()
    return usuario


@transaction.atomic
def actualizar_usuario(*, usuario, ejecutor, nombre_completo=None, rol=None):
    """CU-USU-02 (RF-40, RF-44, RF-46)."""
    if rol is not None and rol != usuario.rol:
        _validar_no_es_uno_mismo(usuario, ejecutor, "No puede cambiar su propio rol.")
        _validar_queda_un_administrador(usuario, nuevo_rol=rol)
        usuario.rol = rol

    if nombre_completo is not None:
        usuario.nombre_completo = nombre_completo

    usuario.save()
    return usuario


@transaction.atomic
def bloquear_usuario(*, usuario, ejecutor):
    """CU-USU-03 (RF-41, RF-45, RF-46) y RN-ACC-05.

    Que el bloqueo y la invalidacion de sesiones compartan transaccion
    no es un detalle: si el bloqueo se guardara y la invalidacion
    fallara, la cuenta quedaria bloqueada pero con sesiones vivas, que
    es exactamente el estado que RN-ACC-05 prohibe.
    """
    _validar_no_es_uno_mismo(usuario, ejecutor, "No puede bloquear su propia cuenta.")
    _validar_queda_un_administrador(usuario, bloqueando=True)

    if usuario.is_active:
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])

    invalidar_sesiones(usuario)
    return usuario


@transaction.atomic
def desbloquear_usuario(*, usuario, ejecutor):
    """CU-USU-03 (RF-41).

    No revive ninguna sesion anterior: los refresh invalidados en el
    bloqueo siguen en la lista negra, asi que el titular debe iniciar
    sesion de nuevo.
    """
    usuario.is_active = True
    usuario.save(update_fields=["is_active"])
    return usuario


@transaction.atomic
def restablecer_password(*, usuario, password_nueva, ejecutor):
    """CU-USU-04 (RF-42).

    Se invalidan ademas las sesiones vigentes: restablecer la clave de
    una cuenta comprometida debe expulsar de verdad a quien la
    estuviera usando, no solo impedir nuevos inicios de sesion.
    """
    usuario.set_password(password_nueva)
    usuario.save(update_fields=["password"])
    invalidar_sesiones(usuario)
    return usuario
