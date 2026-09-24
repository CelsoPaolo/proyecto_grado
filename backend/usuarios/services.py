"""Reglas de negocio de cuentas y sesiones.

Las reglas viven aqui y no en los serializers ni en las vistas: varias
combinan mas de una tabla o exigen atomicidad, y desde una vista serian
imposibles de probar en aislamiento y se duplicarian en cuanto hubiera
un segundo punto de entrada (plan.md seccion 2.2).
"""

from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


def invalidar_sesiones(usuario):
    """Via 3 de plan.md seccion 1.3 — lista negra al bloquear.

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


@transaction.atomic
def bloquear_usuario(*, usuario, ejecutor):
    """Bloquea una cuenta e invalida sus sesiones (RN-ACC-05).

    Las protecciones de RN-USU-03 y RN-USU-04 se anaden en T-1.6.

    Que el bloqueo y la invalidacion compartan transaccion no es un
    detalle: si el bloqueo se guardara y la invalidacion fallara, la
    cuenta quedaria bloqueada pero con sesiones vivas, que es
    exactamente el estado que RN-ACC-05 prohibe.
    """
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    invalidar_sesiones(usuario)
    return usuario


@transaction.atomic
def desbloquear_usuario(*, usuario, ejecutor):
    """Restituye el acceso de una cuenta.

    No revive ninguna sesion anterior: los refresh invalidados en el
    bloqueo siguen en la lista negra, asi que el titular debe iniciar
    sesion de nuevo.
    """
    usuario.is_active = True
    usuario.save(update_fields=["is_active"])
    return usuario
