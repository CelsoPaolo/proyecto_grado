"""Libro de movimientos de stock (spec.md seccion 6.7, plan.md 3.5).

Cada cambio en las existencias de un producto deja aqui una fila:
cuanto cambio, con que signo, en que quedo, quien lo hizo, cuando y
por que. Es la respuesta del sistema al problema que motivo el
proyecto: diferencias entre el inventario registrado y el fisico que
nadie sabia explicar.

Dos propiedades sostienen ese valor, y las dos se protegen aqui:

  - El libro CUADRA (RN-MOV-03): la suma de las cantidades de un
    producto es siempre igual a sus existencias. Lo garantiza que toda
    escritura de stock pase por inventario.services, dentro de la misma
    transaccion que el cambio de existencias.
  - El libro NO SE REESCRIBE (RN-MOV-04, RNF-25): un movimiento no se
    edita ni se borra. Un error se corrige con otro movimiento, igual
    que una venta erronea se corrige anulandola.

Este modulo no importa servicios de ninguna otra app: depende de
`catalogo` y de `ventas` solo a traves de sus modelos, de modo que el
grafo de dependencias queda en una sola direccion (plan.md 2.3).
"""

from django.conf import settings
from django.db import models


class TipoMovimiento(models.TextChoices):
    """RN-MOV-02. El signo y el autor de cada tipo los fija la base."""

    SALDO_INICIAL = "SALDO_INICIAL", "Saldo inicial"
    ALTA = "ALTA", "Alta"
    VENTA = "VENTA", "Venta"
    ANULACION = "ANULACION", "Anulación"
    AJUSTE = "AJUSTE", "Ajuste manual"


#: Los tipos que nacen de una venta y por tanto la referencian.
TIPOS_CON_VENTA = (TipoMovimiento.VENTA, TipoMovimiento.ANULACION)

#: Los tipos que fijan el punto de partida de un producto en el libro.
TIPOS_DE_ORIGEN = (TipoMovimiento.SALDO_INICIAL, TipoMovimiento.ALTA)


class MovimientoInmutable(Exception):
    """Se intento modificar o borrar un movimiento (RN-MOV-04, RNF-25).

    Es un error de programacion, no una regla que el usuario pueda
    incumplir: ninguna pantalla ni endpoint ofrece editar el libro. Por
    eso hereda de Exception y no de ErrorDeNegocio. Si salta, hay un
    camino en el codigo que no deberia existir.
    """


class MovimientoQuerySet(models.QuerySet):
    """Cierra la via masiva de reescritura.

    Proteger solo save() y delete() de la instancia dejaria abierto
    `MovimientoStock.objects.filter(...).update(...)` o `.delete()`, que
    no pasan por la instancia. Este queryset cierra esas dos puertas.
    """

    def update(self, **kwargs):
        raise MovimientoInmutable("Los movimientos de stock no se modifican.")

    def delete(self):
        raise MovimientoInmutable("Los movimientos de stock no se eliminan.")


class MovimientoStock(models.Model):
    """Un cambio en las existencias de un producto."""

    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        related_name="movimientos",
        verbose_name="producto",
    )
    tipo = models.CharField("tipo", max_length=15, choices=TipoMovimiento.choices)
    cantidad = models.IntegerField(
        "cantidad",
        help_text="Con signo: negativa si salen unidades, positiva si entran.",
    )
    stock_resultante = models.IntegerField(
        "existencias resultantes",
        help_text="Existencias del producto inmediatamente despues de este movimiento.",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_de_stock",
        verbose_name="autor",
        help_text="Nulo solo en el saldo inicial, que lo genera el sistema.",
    )
    venta = models.ForeignKey(
        "ventas.Venta",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_de_stock",
        verbose_name="venta de referencia",
    )
    motivo = models.TextField("motivo", blank=True)
    fecha_hora = models.DateTimeField("fecha y hora", auto_now_add=True)

    objects = MovimientoQuerySet.as_manager()

    class Meta:
        verbose_name = "movimiento de stock"
        verbose_name_plural = "movimientos de stock"
        ordering = ["-fecha_hora", "-id"]
        constraints = [
            # RN-CAT-02 llevado al libro: ningun movimiento puede dejar
            # las existencias en negativo.
            models.CheckConstraint(
                condition=models.Q(stock_resultante__gte=0),
                name="movimiento_resultante_no_negativo",
                violation_error_message=(
                    "Un movimiento no puede dejar existencias negativas."
                ),
            ),
            # RN-MOV-02: venta y anulacion referencian SU venta, y solo
            # ellas. Un ajuste con venta, o una venta sin ella, seria un
            # movimiento imposible de auditar.
            models.CheckConstraint(
                condition=(
                    models.Q(tipo__in=TIPOS_CON_VENTA, venta__isnull=False)
                    | (~models.Q(tipo__in=TIPOS_CON_VENTA) & models.Q(venta__isnull=True))
                ),
                name="movimiento_venta_solo_en_venta_y_anulacion",
                violation_error_message=(
                    "Solo las ventas y las anulaciones referencian una venta, "
                    "y siempre lo hacen."
                ),
            ),
            # RN-MOV-02: una venta saca unidades; una anulacion las
            # devuelve. El signo no es una convencion de la interfaz,
            # es una propiedad del libro.
            models.CheckConstraint(
                condition=~models.Q(tipo=TipoMovimiento.VENTA) | models.Q(cantidad__lt=0),
                name="movimiento_venta_resta",
                violation_error_message="Un movimiento de venta debe restar unidades.",
            ),
            models.CheckConstraint(
                condition=~models.Q(tipo=TipoMovimiento.ANULACION) | models.Q(cantidad__gt=0),
                name="movimiento_anulacion_suma",
                violation_error_message="Un movimiento de anulación debe sumar unidades.",
            ),
            # RN-MOV-05: un ajuste cambia algo y explica por que.
            models.CheckConstraint(
                condition=(
                    ~models.Q(tipo=TipoMovimiento.AJUSTE)
                    | (~models.Q(cantidad=0) & ~models.Q(motivo=""))
                ),
                name="movimiento_ajuste_con_diferencia_y_motivo",
                violation_error_message=(
                    "Un ajuste debe cambiar las existencias e indicar el motivo."
                ),
            ),
            # RN-MOV-02: el origen de un producto en el libro nunca es
            # negativo. Puede ser cero: un producto creado sin unidades
            # tambien necesita su punto de partida.
            models.CheckConstraint(
                condition=~models.Q(tipo__in=TIPOS_DE_ORIGEN) | models.Q(cantidad__gte=0),
                name="movimiento_origen_no_negativo",
                violation_error_message=(
                    "El saldo inicial y el alta no pueden ser negativos."
                ),
            ),
            # RN-MOV-02 y RNF-07: todo movimiento tiene autor, salvo el
            # saldo inicial, que lo crea la migracion y no una persona.
            # Cualquier otro movimiento sin autor seria un agujero en la
            # trazabilidad.
            models.CheckConstraint(
                condition=(
                    models.Q(tipo=TipoMovimiento.SALDO_INICIAL, usuario__isnull=True)
                    | (~models.Q(tipo=TipoMovimiento.SALDO_INICIAL) & models.Q(usuario__isnull=False))
                ),
                name="movimiento_autor_salvo_saldo_inicial",
                violation_error_message=(
                    "Todo movimiento tiene autor, salvo el saldo inicial."
                ),
            ),
        ]
        indexes = [
            # Historial de un producto, del mas reciente al mas antiguo
            # que consulta el detalle de producto. Las FK a producto y
            # a venta ya tienen su indice.
            models.Index(
                fields=["producto", "-fecha_hora"], name="movimiento_producto_idx"
            ),
            models.Index(fields=["tipo"], name="movimiento_tipo_idx"),
            models.Index(fields=["-fecha_hora"], name="movimiento_fecha_idx"),
        ]

    def __str__(self):
        signo = "+" if self.cantidad > 0 else ""
        return f"{self.get_tipo_display()} {signo}{self.cantidad} - producto #{self.producto_id}"

    def save(self, *args, **kwargs):
        """RN-MOV-04: se inserta una vez y no se toca nunca mas."""
        if not self._state.adding:
            raise MovimientoInmutable("Los movimientos de stock no se modifican.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """RN-MOV-04: un error se corrige con otro movimiento, no borrando."""
        raise MovimientoInmutable("Los movimientos de stock no se eliminan.")
