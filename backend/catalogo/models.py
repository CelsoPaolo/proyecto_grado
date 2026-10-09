"""Catalogo e inventario (spec.md seccion 5.2 y 6.3).

Las restricciones se declaran en la BASE, no solo en Python. Son los
invariantes que deben cumplirse pase lo que pase: `choices` y las
validaciones de Django solo actuan a traves del ORM, y una escritura
directa o un error de programacion futuro las saltaria. La base no.
"""

from django.db import models
from django.db.models.functions import Lower


class Categoria(models.Model):
    """Agrupacion de productos del catalogo (CU-CAT-01)."""

    nombre = models.CharField("nombre", max_length=100)
    descripcion = models.TextField("descripción", blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["nombre"]
        constraints = [
            # RN-CAT-03. Se compara en minusculas: permitir "Laptops" y
            # "laptops" a la vez dejaria el catalogo con dos categorias
            # que el personal leeria como la misma.
            models.UniqueConstraint(
                Lower("nombre"),
                name="categoria_nombre_unico",
                violation_error_message="Ya existe una categoría con ese nombre.",
            ),
        ]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Articulo del catalogo (CU-CAT-02 a CU-CAT-05).

    El borrado es SUAVE (campo `activo`): CU-CAT-04 retira el producto
    de la oferta vigente, pero la fila permanece. Combinado con
    on_delete=PROTECT en el detalle de venta, esto garantiza que las
    existencias de una venta anulada siempre puedan devolverse
    (RN-VEN-07): el producto nunca desaparece de la base.
    """

    nombre = models.CharField("nombre", max_length=150)
    descripcion = models.TextField("descripción", blank=True)
    precio = models.DecimalField(
        "precio",
        max_digits=10,
        decimal_places=2,
        help_text="En bolivianos (Bs).",
    )
    stock = models.IntegerField("existencias", default=0)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,  # RN-CAT-04
        related_name="productos",
        verbose_name="categoría",
    )
    imagen = models.ImageField(
        "imagen",
        upload_to="productos/",
        blank=True,
        null=True,
        help_text="Opcional (RN-CAT-06).",
    )
    activo = models.BooleanField(
        "activo",
        default=True,
        help_text="Un producto inactivo fue retirado del catálogo (CU-CAT-04).",
    )
    # RN-CAT-08. Lo asigna save() al insertar y no lo cambia nadie
    # despues: editable=False lo saca de los formularios y el serializer
    # lo declara de solo lectura.
    codigo = models.CharField(
        "código",
        max_length=13,
        unique=True,
        editable=False,
        help_text="EAN-13 interno asignado por el sistema (RN-CAT-08).",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                Lower("nombre"),
                name="producto_nombre_unico",
                violation_error_message="Ya existe un producto con ese nombre.",
            ),
            # RN-CAT-01.
            models.CheckConstraint(
                condition=models.Q(precio__gt=0),
                name="producto_precio_positivo",
                violation_error_message="El precio debe ser mayor que cero.",
            ),
            # RN-CAT-02 y ultima linea de defensa de RNF-08. Es
            # deliberadamente redundante con la validacion del servicio
            # de ventas: si un cambio futuro rompiera esa validacion, la
            # base RECHAZA la operacion en lugar de dejar el inventario
            # en negativo.
            models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name="producto_stock_no_negativo",
                violation_error_message="Las existencias no pueden ser negativas.",
            ),
        ]
        indexes = [
            models.Index(fields=["categoria"], name="producto_categoria_idx"),
            models.Index(fields=["activo"], name="producto_activo_idx"),
            models.Index(fields=["stock"], name="producto_stock_idx"),
        ]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        """RF-69 — el codigo se asigna al crear el producto, por cualquier
        camino que pase por save(): el servicio de alta, las fabricas de
        prueba y la importacion del catalogo anterior.

        Solo al INSERTAR: un producto ya guardado conserva el suyo para
        siempre, y uno que llegara sin el seria un error, no un hueco que
        rellenar.
        """
        if self._state.adding and not self.codigo:
            from catalogo.codigos import generar_codigo

            self.codigo = generar_codigo()
        super().save(*args, **kwargs)

    @property
    def disponible_para_venta(self):
        """RN-CAT-05: sin existencias sigue visible, pero no se vende."""
        return self.activo and self.stock > 0
