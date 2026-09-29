"""Solicitudes de servicio tecnico (spec.md seccion 5.4 y 6.5).

Tres rasgos definen este modulo tras la revision de spec.md v1.2:

  - `registrada_por` es el UNICO responsable con identidad; el tecnico
    es una anotacion de texto libre del Administrador (RN-SER-09).
  - El monto lo COTIZA el Administrador tras la revision, no el tecnico
    al cerrar (RN-SER-13).
  - Cada solicitud la ven solo su registrador y el Administrador
    (RN-SER-15), igual que en ventas.
"""

from django.conf import settings
from django.db import models


class TipoServicio(models.TextChoices):
    """RN-SER-01."""

    MANTENIMIENTO = "MANTENIMIENTO", "Mantenimiento"
    REPARACION = "REPARACION", "Reparación"
    REDES = "REDES", "Instalación de redes"
    VIDEOVIGILANCIA = "VIDEOVIGILANCIA", "Videovigilancia"


class Modalidad(models.TextChoices):
    """Donde se atiende el servicio (RN-SER-01)."""

    TALLER = "TALLER", "En taller"
    DOMICILIO = "DOMICILIO", "A domicilio"


#: Que tipos se atienden a domicilio. Lo decide el SISTEMA a partir del
#: tipo, no el usuario (RN-SER-01), y de ahi sale si la direccion es
#: obligatoria (RN-SER-04).
MODALIDAD_POR_TIPO = {
    TipoServicio.MANTENIMIENTO: Modalidad.TALLER,
    TipoServicio.REPARACION: Modalidad.TALLER,
    TipoServicio.REDES: Modalidad.DOMICILIO,
    TipoServicio.VIDEOVIGILANCIA: Modalidad.DOMICILIO,
}


class EstadoSolicitud(models.TextChoices):
    """RN-SER-02. Finalizada y Cancelada son terminales."""

    REGISTRADA = "REGISTRADA", "Registrada"
    EN_ATENCION = "EN_ATENCION", "En atención"
    FINALIZADA = "FINALIZADA", "Finalizada"
    CANCELADA = "CANCELADA", "Cancelada"


ESTADOS_TERMINALES = (EstadoSolicitud.FINALIZADA, EstadoSolicitud.CANCELADA)
ESTADOS_PENDIENTES = (EstadoSolicitud.REGISTRADA, EstadoSolicitud.EN_ATENCION)


class SolicitudServicio(models.Model):
    """Un trabajo tecnico pedido por un cliente (CU-SER-01 a CU-SER-06)."""

    # Contacto del cliente. Dato DE LA SOLICITUD (RN-SER-05): no crea
    # cuenta ni acceso, igual que en ventas.
    cliente_nombre = models.CharField("nombre del cliente", max_length=150)
    cliente_telefono = models.CharField("teléfono del cliente", max_length=30)

    tipo = models.CharField("tipo", max_length=20, choices=TipoServicio.choices)
    modalidad = models.CharField(
        "modalidad",
        max_length=12,
        choices=Modalidad.choices,
        help_text=(
            "La deriva el sistema del tipo (RN-SER-01). Se almacena en vez "
            "de calcularse para que una reclasificación futura de un tipo "
            "no altere el significado de las solicitudes históricas."
        ),
    )
    direccion = models.CharField(
        "dirección",
        max_length=255,
        blank=True,
        help_text="Obligatoria solo si la modalidad es a domicilio (RN-SER-04).",
    )
    descripcion = models.TextField("descripción del problema")

    estado = models.CharField(
        "estado",
        max_length=12,
        choices=EstadoSolicitud.choices,
        default=EstadoSolicitud.REGISTRADA,
    )

    # ── Responsables ─────────────────────────────────────────────────
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # RN-USU-05
        related_name="solicitudes_registradas",
        verbose_name="registrada por",
        help_text="Fijo desde el alta; nunca cambia (RN-SER-11).",
    )
    tecnico = models.CharField(
        "técnico",
        max_length=150,
        blank=True,
        help_text=(
            "Anotación de texto libre del Administrador (RN-SER-09). NO es "
            "una cuenta del sistema ni concede acceso: es información de "
            "seguimiento."
        ),
    )

    # ── Cotizacion (RN-SER-13, la hace el Administrador) ─────────────
    monto_cobrado = models.DecimalField(
        "monto a cobrar",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Nulo mientras no se cotice. Cero es un valor válido: significa "
            "servicio en garantía o de cortesía, distinto de sin cotizar "
            "(RN-SER-17)."
        ),
    )
    cotizada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitudes_cotizadas",
        verbose_name="cotizada por",
    )
    fecha_cotizacion = models.DateTimeField(
        "fecha de cotización", null=True, blank=True
    )

    # ── Cierre ───────────────────────────────────────────────────────
    observaciones = models.TextField(
        "observaciones del trabajo",
        blank=True,
        help_text="Obligatorias para finalizar (RN-SER-03).",
    )
    motivo_cancelacion = models.TextField("motivo de la cancelación", blank=True)
    cerrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitudes_cerradas",
        verbose_name="cerrada por",
    )

    fecha_registro = models.DateTimeField("fecha de registro", auto_now_add=True)
    fecha_inicio_atencion = models.DateTimeField(
        "inicio de la atención", null=True, blank=True
    )
    fecha_cierre = models.DateTimeField("fecha de cierre", null=True, blank=True)

    class Meta:
        verbose_name = "solicitud de servicio"
        verbose_name_plural = "solicitudes de servicio"
        ordering = ["-fecha_registro"]
        constraints = [
            # RN-SER-04: a domicilio exige direccion.
            models.CheckConstraint(
                condition=(
                    ~models.Q(modalidad=Modalidad.DOMICILIO)
                    | ~models.Q(direccion="")
                ),
                name="solicitud_domicilio_con_direccion",
                violation_error_message=(
                    "Un servicio a domicilio debe registrar la dirección."
                ),
            ),
            # RN-SER-17: el monto, si existe, no es negativo.
            models.CheckConstraint(
                condition=(
                    models.Q(monto_cobrado__isnull=True)
                    | models.Q(monto_cobrado__gte=0)
                ),
                name="solicitud_monto_no_negativo",
                violation_error_message="El monto no puede ser negativo.",
            ),
            # RN-SER-03 y RN-SER-13: no se finaliza sin observaciones ni
            # sin monto cotizado. Declarado en la base para que ningun
            # camino futuro pueda cerrar una solicitud a medias.
            models.CheckConstraint(
                condition=(
                    ~models.Q(estado=EstadoSolicitud.FINALIZADA)
                    | (
                        ~models.Q(observaciones="")
                        & models.Q(monto_cobrado__isnull=False)
                        & models.Q(fecha_cierre__isnull=False)
                    )
                ),
                name="solicitud_finalizada_completa",
                violation_error_message=(
                    "Una solicitud finalizada debe tener observaciones, "
                    "monto cotizado y fecha de cierre."
                ),
            ),
            # RN-SER-07: cancelar exige motivo.
            models.CheckConstraint(
                condition=(
                    ~models.Q(estado=EstadoSolicitud.CANCELADA)
                    | (
                        ~models.Q(motivo_cancelacion="")
                        & models.Q(fecha_cierre__isnull=False)
                    )
                ),
                name="solicitud_cancelada_con_motivo",
                violation_error_message=(
                    "Una solicitud cancelada debe registrar el motivo."
                ),
            ),
        ]
        indexes = [
            models.Index(fields=["estado"], name="solicitud_estado_idx"),
            models.Index(
                fields=["registrada_por", "-fecha_registro"],
                name="solicitud_registrador_idx",
            ),
            models.Index(fields=["-fecha_registro"], name="solicitud_fecha_idx"),
            # Ingresos por servicios del dia (RN-IND-04): la solicitud
            # aporta por su fecha de CIERRE, no la de registro.
            models.Index(
                fields=["estado", "fecha_cierre"], name="solicitud_cierre_idx"
            ),
        ]

    def __str__(self):
        return f"Solicitud #{self.pk} - {self.cliente_nombre}"

    @property
    def esta_abierta(self):
        return self.estado not in ESTADOS_TERMINALES

    @property
    def esta_cotizada(self):
        """RN-SER-13. Cero cuenta como cotizada; nulo no."""
        return self.monto_cobrado is not None

    @property
    def requiere_direccion(self):
        return self.modalidad == Modalidad.DOMICILIO


class TipoEvento(models.TextChoices):
    """Los sucesos que el historial registra (RF-35, RF-59)."""

    CAMBIO_ESTADO = "CAMBIO_ESTADO", "Cambio de estado"
    COTIZACION = "COTIZACION", "Cotización"
    TECNICO = "TECNICO", "Anotación de técnico"
    CIERRE = "CIERRE", "Cierre"


class EventoSolicitud(models.Model):
    """Historial de una solicitud (RN-SER-06).

    Tabla de SOLO INSERCION: nunca se actualiza ni se borra.

    Sobre una misma solicitud actuan dos personas distintas -el
    Administrador cotiza, el registrador cierra-, asi que este historial
    es lo que permite saber quien hizo que, incluso con la visibilidad
    restringida de RN-SER-15.
    """

    solicitud = models.ForeignKey(
        SolicitudServicio,
        on_delete=models.CASCADE,
        related_name="eventos",
        verbose_name="solicitud",
    )
    tipo_evento = models.CharField(
        "tipo de evento", max_length=20, choices=TipoEvento.choices
    )
    estado_anterior = models.CharField("estado anterior", max_length=12, blank=True)
    estado_nuevo = models.CharField("estado nuevo", max_length=12, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="eventos_de_servicio",
        verbose_name="autor",
    )
    fecha_hora = models.DateTimeField("fecha y hora", auto_now_add=True)
    nota = models.TextField("nota", blank=True)

    class Meta:
        verbose_name = "evento de solicitud"
        verbose_name_plural = "eventos de solicitud"
        ordering = ["fecha_hora", "id"]
        indexes = [
            models.Index(
                fields=["solicitud", "fecha_hora"], name="evento_solicitud_idx"
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_evento_display()} - solicitud #{self.solicitud_id}"
