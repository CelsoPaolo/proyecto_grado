"""Parametros del sistema (spec.md RN-CAT-07, decision PA-01)."""

from django.conf import settings
from django.db import models

#: Valor con el que nace la configuracion en una base vacia.
UMBRAL_INICIAL = 5


class ConfiguracionSistema(models.Model):
    """Fila unica con los parametros configurables del sistema.

    Se modela como tabla de UNA sola fila, y no como variable de
    entorno ni constante, porque RF-52 exige que el Administrador pueda
    cambiar el umbral desde la interfaz sin redesplegar, y RN-CAT-07
    pide registrar quien lo cambio y cuando.

    La unicidad la garantiza la base con CheckConstraint(id=1): no
    depende de que el codigo recuerde no crear una segunda fila.
    """

    id = models.SmallIntegerField(primary_key=True, default=1, editable=False)

    umbral_stock_bajo = models.PositiveIntegerField(
        "umbral de existencias bajas",
        default=UMBRAL_INICIAL,
        help_text=(
            "Un producto se considera con existencias bajas cuando su "
            "cantidad es menor o igual a este valor. Es global para todo "
            "el catálogo (PA-01)."
        ),
    )

    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # RN-USU-05: no se pierde la autoria
        null=True,
        blank=True,
        related_name="configuraciones_actualizadas",
        verbose_name="actualizado por",
    )
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "configuración del sistema"
        verbose_name_plural = "configuración del sistema"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(id=1),
                name="configuracion_fila_unica",
                violation_error_message=(
                    "Solo puede existir una configuración del sistema."
                ),
            ),
        ]

    def __str__(self):
        return f"Umbral de existencias bajas: {self.umbral_stock_bajo}"

    @classmethod
    def obtener(cls):
        """Devuelve la configuracion vigente, creandola si no existiera.

        La migracion de datos ya deja la fila creada; este respaldo
        existe para que una base restaurada a medias no deje el sistema
        sin poder leer su propia configuracion.
        """
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion
