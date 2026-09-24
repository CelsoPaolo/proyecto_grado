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

    Conceder este permiso alcanza para actuar sobre CUALQUIER solicitud
    abierta: PA-04 hizo de los servicios un espacio compartido
    (RN-SER-15). El tecnico asignado indica de quien es el trabajo, no
    quien tiene permiso.
    """

    roles_permitidos = (Rol.ADMINISTRADOR, Rol.SERVICIOS)


class EsDuenoDeLaVentaOAdmin(BasePermission):
    """Autorizacion a nivel de objeto para las ventas (RF-27).

    Contrasta a proposito con PuedeAtenderServicios: el historial de
    ventas es **privado por usuario**, mientras que el de servicios es
    compartido. La asimetria es intencional (spec.md seccion 11): un
    servicio es trabajo en curso que cambia de manos, una venta es un
    hecho consumado imputable a quien la registro.
    """

    message = "Solo puede operar sobre las ventas que usted registró."

    def has_object_permission(self, request, view, obj):
        usuario = request.user
        if usuario.es_administrador:
            return True
        return obj.usuario_id == usuario.id
