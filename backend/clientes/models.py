"""Clientes de PC-Solution (spec.md seccion 6.8, plan.md 3.5).

Un cliente es un REGISTRO DE CONTACTO, no un usuario: no tiene cuenta,
no inicia sesion y no accede al sistema por ninguna via (RN-CLI-04). Por
eso este modelo no hereda ni referencia a `Usuario` salvo para la
auditoria de quien lo registro y quien lo cambio.

El carnet es un dato personal (RN-CLI-06): solo lo declara el serializer
del detalle de esta app. Ningun otro serializer del proyecto lo
menciona, de modo que la minimizacion queda en la forma de los datos y
no en la disciplina de quien escriba la proxima vista.
"""

from django.conf import settings
from django.db import models


def normalizar_carnet(texto):
    """RN-CLI-02 — sin espacios y en mayusculas.

    Un carnet boliviano puede llevar complemento o extension
    (1234567-1A, 1234567 LP). Sin normalizar, 1234567-1a y 1234567-1A
    serian dos clientes distintos para la base.
    """
    return "".join((texto or "").split()).upper()


class Cliente(models.Model):
    """Registro de contacto de un cliente (spec.md 6.8)."""

    nombre = models.CharField("nombre", max_length=150)
    telefono = models.CharField("teléfono", max_length=30)
    direccion = models.CharField("dirección", max_length=255, blank=True, default="")
    # Cadena vacia, no NULL: el UNIQUE parcial de Meta deja convivir a
    # todos los clientes sin carnet.
    carnet = models.CharField(
        "carnet de identidad",
        max_length=20,
        blank=True,
        default="",
        help_text="Opcional. Dato personal: solo visible en el detalle (RN-CLI-06).",
    )
    activo = models.BooleanField(
        "activo",
        default=True,
        help_text="Un cliente inactivo no se elige en ventas nuevas (RN-CLI-03).",
    )

    # Auditoria (RNF-07): toda alta y toda modificacion tiene autor.
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clientes_registrados",
        verbose_name="registrado por",
    )
    creado_en = models.DateTimeField("registrado el", auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clientes_actualizados",
        verbose_name="actualizado por",
    )
    actualizado_en = models.DateTimeField("actualizado el", auto_now=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre", "id"]
        constraints = [
            # RN-CLI-02: unico si se informa, entre activos e inactivos.
            models.UniqueConstraint(
                fields=["carnet"],
                condition=~models.Q(carnet=""),
                name="cliente_carnet_unico",
                violation_error_message="Ya hay un cliente registrado con ese carnet.",
            ),
            # RN-CLI-01: nombre y telefono obligatorios. Se exige un
            # caracter que no sea espacio: «   » no es un nombre.
            models.CheckConstraint(
                condition=models.Q(nombre__regex=r"\S"),
                name="cliente_nombre_obligatorio",
                violation_error_message="El nombre del cliente es obligatorio.",
            ),
            models.CheckConstraint(
                condition=models.Q(telefono__regex=r"\S"),
                name="cliente_telefono_obligatorio",
                violation_error_message="El teléfono del cliente es obligatorio.",
            ),
        ]
        indexes = [
            models.Index(fields=["activo", "nombre"], name="cliente_activo_nombre_idx"),
            models.Index(fields=["telefono"], name="cliente_telefono_idx"),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        """El carnet se guarda siempre normalizado, venga de donde venga."""
        self.carnet = normalizar_carnet(self.carnet)
        super().save(*args, **kwargs)
