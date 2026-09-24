from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Rol(models.TextChoices):
    """Roles del personal de PC-Solution (spec.md seccion 4).

    Todos son personal interno: el sistema no tiene actores externos.
    Cada usuario tiene exactamente un rol (RN-ACC-02).
    """

    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
    VENTAS = "VENTAS", "Encargado de Ventas"
    SERVICIOS = "SERVICIOS", "Encargado de Servicios"


#: Roles habilitados para atender solicitudes de servicio (RN-SER-10).
ROLES_QUE_ATIENDEN_SERVICIOS = (Rol.ADMINISTRADOR, Rol.SERVICIOS)

#: Roles habilitados para registrar ventas (RN-ACC-03).
ROLES_QUE_VENDEN = (Rol.ADMINISTRADOR, Rol.VENTAS)


class UsuarioManager(UserManager):
    """Manager del modelo de usuario.

    Su unica particularidad resuelve el arranque del sistema
    (plan.md seccion 11.1): RN-USU-01 dice que solo el Administrador
    crea cuentas, asi que con la base vacia nadie podria crear la
    primera y el sistema recien instalado seria inaccesible.

    `createsuperuser` es la salida: un comando de consola, ejecutado
    una sola vez al preparar el equipo, fuera del flujo de la
    aplicacion. No vulnera RN-USU-01, del mismo modo que tener la llave
    del local no es una funcion del ERP.

    Se fuerza el rol de Administrador porque un superusuario sin rol
    podria autenticarse pero no pasaria ninguna clase de permiso: las
    comprobaciones de T-1.2 miran `rol`, no `is_superuser`.
    """

    def create_superuser(self, username, email=None, password=None, **extra):
        extra["rol"] = Rol.ADMINISTRADOR
        extra.setdefault("nombre_completo", username)
        return super().create_superuser(username, email, password, **extra)


class Usuario(AbstractUser):
    """Cuenta de una persona del personal de PC-Solution.

    Se define como modelo propio desde la primera migracion
    (plan.md seccion 3.2): cambiar AUTH_USER_MODEL despues de migrar
    obligaria a reconstruir la base desde cero.

    El bloqueo de cuentas (RN-ACC-05) reutiliza `is_active` en lugar de
    anadir un campo nuevo: es exactamente su semantica en Django, y asi
    SimpleJWT lo respeta de serie al resolver el usuario en cada
    peticion, sin codigo adicional.

    Las cuentas no se eliminan, se bloquean (RN-USU-05): todas las
    claves foraneas que apunten aqui usaran on_delete=PROTECT, de modo
    que la base impida perder la autoria de una venta o de un servicio.
    """

    # AbstractUser ya aporta: username (unico, RN-USU-06), password,
    # is_active, is_staff, date_joined y last_login.
    # Se descartan first_name y last_name en favor de un unico campo:
    # la especificacion habla siempre del "nombre" del personal.
    first_name = None
    last_name = None

    nombre_completo = models.CharField(
        "nombre completo",
        max_length=150,
    )
    rol = models.CharField(
        "rol",
        max_length=20,
        choices=Rol.choices,
    )

    objects = UsuarioManager()

    # `rol` queda fuera: createsuperuser no lo pregunta porque el
    # manager lo fuerza a ADMINISTRADOR.
    REQUIRED_FIELDS = ["nombre_completo"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["nombre_completo"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rol__in=[r.value for r in Rol]),
                name="usuario_rol_valido",
            ),
        ]

    def __str__(self):
        return f"{self.nombre_completo} ({self.get_rol_display()})"

    @property
    def es_administrador(self):
        return self.rol == Rol.ADMINISTRADOR

    @property
    def puede_vender(self):
        """RN-ACC-03: el Administrador hereda lo del Encargado de Ventas."""
        return self.rol in (Rol.ADMINISTRADOR, Rol.VENTAS)

    @property
    def puede_atender_servicios(self):
        """RN-ACC-03: el Administrador hereda lo del Encargado de Servicios."""
        return self.rol in (Rol.ADMINISTRADOR, Rol.SERVICIOS)
