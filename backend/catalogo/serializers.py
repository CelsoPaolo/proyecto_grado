"""Serializers del catalogo."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from catalogo.codigos import PATRON_INTERNO, normalizar_codigo_fabrica
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
            "codigo",
            "codigo_fabrica",
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
        # RN-CAT-08: el codigo lo asigna el sistema; si la peticion lo
        # trae, al crear o al editar, se ignora.
        read_only_fields = ["activo", "codigo"]
        # El validador de unicidad que DRF deriva de la restriccion compara
        # el valor SIN normalizar y con un mensaje generico; la unicidad la
        # comprueba validate_codigo_fabrica sobre el valor normalizado.
        extra_kwargs = {"codigo_fabrica": {"validators": []}}

    def get_fields(self):
        """RN-CAT-10: las existencias solo se fijan al crear.

        Despues cambian unicamente por venta, anulacion o ajuste, que
        dejan su movimiento. Al editar, el campo es de solo lectura: su
        valor nunca llega a los datos validados ni, por tanto, al
        producto. Que la peticion lo traiga se rechaza aparte, en
        validate().
        """
        campos = super().get_fields()
        if self.instance is not None:
            campos["stock"].read_only = True
        return campos

    def validate(self, datos):
        """RN-CAT-10 revisada el 2026-10-09: editar con existencias es un
        error, no un dato que se descarta.

        La primera version las ignoraba en silencio, y el formulario de
        producto las enviaba al editar: quien cambiaba ese numero y
        guardaba recibia un 200 y el cambio se perdia sin aviso. Se mira
        la peticion ORIGINAL (`initial_data`) porque el campo, al ser de
        solo lectura, ya no esta en `datos`.

        Se rechaza aunque el valor coincida con el vigente: la regla es
        que las existencias no se editan por esta via, no que no se
        cambien.
        """
        if self.instance is not None and "stock" in self.initial_data:
            raise serializers.ValidationError(
                {
                    "stock": [
                        "Las existencias no se editan aquí: use «Ajustar "
                        "existencias», que exige un motivo y deja constancia "
                        "del cambio."
                    ]
                }
            )
        return super().validate(datos)

    @extend_schema_field(serializers.BooleanField)
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

    def validate_codigo_fabrica(self, valor):
        """RN-CAT-11 y RF-97: opcional, unico y fuera del espacio interno.

        La base ya impide las dos cosas (T-9.7); aqui se anticipan para
        devolver el error junto al campo en lugar de un fallo de
        integridad (RNF-15). Una cadena vacia quita el codigo.
        """
        valor = normalizar_codigo_fabrica(valor)
        if not valor:
            return ""
        if PATRON_INTERNO.match(valor):
            raise serializers.ValidationError(
                "Ese número tiene la forma de un código interno de PC-Solution "
                "(13 cifras que empiezan por 20) y no puede usarse como código "
                "de fábrica."
            )
        consulta = Producto.objects.filter(codigo_fabrica=valor)
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.pk)
        if otro := consulta.first():
            raise serializers.ValidationError(
                f"Ese código de fábrica ya está registrado en «{otro.nombre}»."
            )
        return valor

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
