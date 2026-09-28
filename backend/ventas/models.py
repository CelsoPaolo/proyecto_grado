"""Registro de ventas (spec.md seccion 5.3 y 6.4).

El nucleo de este modulo es el **congelado** de RN-VEN-04: el nombre y
el precio del producto se copian a columnas propias del detalle al
confirmar la venta, y no se vuelven a calcular nunca. Si manana el
producto cambia de precio o se retira del catalogo, la venta historica
sigue diciendo lo que costo ESE dia.
"""

from django.conf import settings
from django.db import models


class EstadoVenta(models.TextChoices):
    """RN-VEN-06: una venta confirmada no se edita ni se elimina.

    El unico cambio posible es la anulacion, que no borra nada.
    """

    CONFIRMADA = "CONFIRMADA", "Confirmada"
    ANULADA = "ANULADA", "Anulada"


class Venta(models.Model):
    """Una transaccion de venta (CU-VEN-01 a CU-VEN-03)."""

    # Datos de contacto del cliente. Son un dato DE LA VENTA
    # (RN-VEN-10): no crean cuenta ni acceso, y por eso no hay tabla de
    # clientes ni relacion alguna.
    cliente_nombre = models.CharField("nombre del cliente", max_length=150)
    cliente_telefono = models.CharField("teléfono del cliente", max_length=30)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # RN-USU-05: no se pierde la autoria
        related_name="ventas",
        verbose_name="registrada por",
    )
    fecha_hora = models.DateTimeField("fecha y hora", auto_now_add=True)

    estado = models.CharField(
        "estado",
        max_length=12,
        choices=EstadoVenta.choices,
        default=EstadoVenta.CONFIRMADA,
    )
    total = models.DecimalField("total", max_digits=12, decimal_places=2)

    # Anulacion (CU-VEN-03, RN-VEN-07).
    motivo_anulacion = models.TextField("motivo de la anulación", blank=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ventas_anuladas",
        verbose_name="anulada por",
    )
    fecha_anulacion = models.DateTimeField(
        "fecha de anulación", null=True, blank=True
    )

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha_hora"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="venta_total_no_negativo",
                violation_error_message="El total no puede ser negativo.",
            ),
            # RN-VEN-07: la anulacion exige motivo, autor y momento. Sin
            # esta restriccion se podria dejar una venta anulada sin
            # rastro de quien lo hizo, y RN-VEN-11 (anular sin limite de
            # plazo) se apoya justamente en esa trazabilidad.
            models.CheckConstraint(
                condition=(
                    ~models.Q(estado=EstadoVenta.ANULADA)
                    | (
                        ~models.Q(motivo_anulacion="")
                        & models.Q(anulada_por__isnull=False)
                        & models.Q(fecha_anulacion__isnull=False)
                    )
                ),
                name="venta_anulada_con_trazabilidad",
                violation_error_message=(
                    "Una venta anulada debe registrar motivo, autor y fecha."
                ),
            ),
        ]
        indexes = [
            # Historial propio del encargado (RF-21).
            models.Index(
                fields=["usuario", "-fecha_hora"], name="venta_usuario_fecha_idx"
            ),
            # Filtros e indicador del dia (RF-22, RF-48).
            models.Index(fields=["-fecha_hora"], name="venta_fecha_idx"),
            models.Index(fields=["estado"], name="venta_estado_idx"),
        ]

    def __str__(self):
        return f"Venta #{self.pk} - {self.cliente_nombre}"

    @property
    def esta_anulada(self):
        return self.estado == EstadoVenta.ANULADA


class DetalleVenta(models.Model):
    """Una linea de la venta, con los datos CONGELADOS (RN-VEN-04).

    `producto_nombre`, `precio_unitario` y `subtotal` son columnas
    propias, copiadas al confirmar. NO se calculan al leer.

    La clave foranea a Producto es meramente informativa: sirve para
    devolver las existencias al anular (RN-VEN-07), no para mostrar el
    detalle. Por eso es PROTECT y no SET_NULL: combinada con el borrado
    suave del catalogo, garantiza que el producto nunca desaparezca y
    que la devolucion siempre pueda hacerse.
    """

    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,  # el detalle no existe sin su venta
        related_name="items",
        verbose_name="venta",
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        related_name="lineas_de_venta",
        verbose_name="producto",
    )

    # ── Datos congelados al confirmar (RN-VEN-04) ────────────────────
    producto_nombre = models.CharField(
        "nombre del producto",
        max_length=150,
        help_text="Congelado al confirmar la venta.",
    )
    precio_unitario = models.DecimalField(
        "precio unitario",
        max_digits=10,
        decimal_places=2,
        help_text="Congelado al confirmar la venta.",
    )
    cantidad = models.PositiveIntegerField("cantidad")
    subtotal = models.DecimalField(
        "subtotal",
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Se almacena, no se recalcula al leer: asi el total de la "
            "venta es reproducible aunque cambie la forma de calcularlo."
        ),
    )

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
        ordering = ["id"]
        constraints = [
            # RN-VEN-01.
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="detalle_cantidad_positiva",
                violation_error_message="La cantidad debe ser mayor que cero.",
            ),
            # RN-VEN-05.
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gt=0),
                name="detalle_precio_positivo",
                violation_error_message="El precio debe ser mayor que cero.",
            ),
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name="detalle_subtotal_no_negativo",
                violation_error_message="El subtotal no puede ser negativo.",
            ),
        ]
        indexes = [
            models.Index(fields=["venta"], name="detalle_venta_idx"),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.producto_nombre}"
