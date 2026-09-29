"""Autorizacion por rol (RNF-02, RN-ACC-04).

La regla que gobierna todo este modulo: **el rol se lee siempre de
`request.user.rol`, nunca del token**.

`request.user` lo resuelve `JWTAuthentication.get_user()`, que carga la
fila desde la base de datos en cada peticion. Esa es la via 4 de
plan.md seccion 1.3: gracias a ella, un cambio de rol (CU-USU-02) surte
efecto en la peticion siguiente, sin que el usuario tenga que volver a
iniciar sesion, y un rol manipulado dentro del token no concede nada.

El token incluye el rol solo como dato informativo para la interfaz.
Ninguna clase de este archivo lo consulta.
"""

from rest_framework.permissions import BasePermission

from usuarios.models import Rol


class _PermisoPorRol(BasePermission):
    """Base de las comprobaciones de rol.

    `roles_permitidos` se declara en cada subclase. El Administrador
    aparece en todas porque RN-ACC-03 le da las capacidades de los
    otros dos roles.
    """

    roles_permitidos = ()
    message = "No tiene permiso para realizar esta operación."

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario or not usuario.is_authenticated:
            return False
        # is_active se comprueba tambien aqui: defensa en profundidad
        # frente a RN-ACC-05, aunque JWTAuthentication ya lo hace.
        if not usuario.is_active:
            return False
        return usuario.rol in self.roles_permitidos


class EsAdministrador(_PermisoPorRol):
    """Gestion del catalogo, usuarios, configuracion y panel."""

    roles_permitidos = (Rol.ADMINISTRADOR,)


class PuedeVender(_PermisoPorRol):
    """Registro de ventas y consulta del catalogo (RN-ACC-03)."""

    roles_permitidos = (Rol.ADMINISTRADOR, Rol.VENTAS)


class PuedeAtenderServicios(_PermisoPorRol):
    """Solicitudes de servicio tecnico (RN-ACC-03).

    Este permiso concede la ENTRADA al modulo. El alcance dentro de el
    lo decide SolicitudViewSet.get_queryset(): un Encargado de Servicios
    solo ve las solicitudes que registro (RN-SER-15, revisado en
    spec.md v1.2).
    """

    roles_permitidos = (Rol.ADMINISTRADOR, Rol.SERVICIOS)


class EsDuenoDeLaVentaOAdmin(BasePermission):
    """Autorizacion a nivel de objeto para las ventas (RF-27).

    El historial de ventas es privado por usuario: cada encargado opera
    solo sobre lo que registro. Desde spec.md v1.2 los servicios siguen
    el mismo modelo (RN-SER-15), asi que ambos modulos se comportan
    igual y no hay asimetria que justificar.
    """

    message = "Solo puede operar sobre las ventas que usted registró."

    def has_object_permission(self, request, view, obj):
        usuario = request.user
        if usuario.es_administrador:
            return True
        return obj.usuario_id == usuario.id
