"""Serializers del catalogo."""

from rest_framework import serializers

from catalogo.models import Categoria, Producto

#: Formatos de imagen admitidos y tamano maximo (plan.md 5.4).
FORMATOS_IMAGEN = {"jpeg", "jpg", "png", "webp"}
TAMANO_MAXIMO_IMAGEN = 2 * 1024 * 1024  # 2 MB


class CategoriaSerializer(serializers.ModelSerializer):
    """CU-CAT-01 (RF-07)."""

    cantidad_productos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "cantidad_productos"]

    def validate_nombre(self, valor):
        """RN-CAT-03, sin distinguir mayusculas.

        La base ya lo impide; aqui se anticipa para devolver un error de
        campo legible en lugar de un 409 de integridad (RNF-15).
        """
        consulta = Categoria.objects.filter(nombre__iexact=valor.strip())
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.pk)
        if consulta.exists():
            raise serializers.ValidationError("Ya existe una categoría con ese nombre.")
        return valor.strip()


class ProductoSerializer(serializers.ModelSerializer):
    """CU-CAT-02, CU-CAT-03 y CU-CAT-05 (RF-09, RF-10, RF-12)."""

    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    stock_bajo = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre",
            "descripcion",
            "precio",
            "stock",
            "categoria",
            "categoria_nombre",
            "imagen",
            "activo",
            "stock_bajo",
        ]
        read_only_fields = ["activo"]

    def get_stock_bajo(self, obj):
        """RF-53 — la regla se calcula en el SERVIDOR.

        El frontend no conoce el umbral: recibe el veredicto ya tomado,
        de modo que cambiarlo (T-3.2) surta efecto sin tocar la
        interfaz. Hasta que exista la configuracion (bloque 3) se usa
        un valor provisional.
        """
        from catalogo.services import umbral_stock_bajo

        return obj.stock <= umbral_stock_bajo()

    def validate_nombre(self, valor):
        """RN-CAT-03."""
        consulta = Producto.objects.filter(nombre__iexact=valor.strip())
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.pk)
        if consulta.exists():
            raise serializers.ValidationError("Ya existe un producto con ese nombre.")
        return valor.strip()

    def validate_precio(self, valor):
        """RN-CAT-01."""
        if valor <= 0:
            raise serializers.ValidationError("El precio debe ser mayor que cero.")
        return valor

    def validate_stock(self, valor):
        """RN-CAT-02."""
        if valor < 0:
            raise serializers.ValidationError(
                "Las existencias no pueden ser negativas."
            )
        return valor

    def validate_imagen(self, archivo):
        """RN-CAT-06 y plan.md 5.4.

        Se comprueba el CONTENIDO, no la extension: un archivo
        cualquiera renombrado a .jpg no es una imagen, y aceptarlo
        dejaria el catalogo mostrando un recurso roto.
        """
        if archivo in (None, ""):
            return archivo

        if archivo.size > TAMANO_MAXIMO_IMAGEN:
            raise serializers.ValidationError(
                "La imagen no puede superar los 2 MB."
            )

        # ImageField de Django ya verifica con Pillow que el archivo sea
        # una imagen real; aqui solo se acota el formato.
        formato = getattr(archivo, "image", None)
        nombre_formato = (
            formato.format.lower() if formato is not None and formato.format else None
        )
        if nombre_formato and nombre_formato not in FORMATOS_IMAGEN:
            raise serializers.ValidationError(
                "Formato no admitido. Use JPG, PNG o WebP."
            )
        return archivo
