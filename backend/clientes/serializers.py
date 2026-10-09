"""Serializers de clientes (plan.md 4.4).

DOS serializers de salida, no uno con campos condicionales (plan.md
4.4): `ClienteResumenSerializer` no DECLARA el carnet, asi que ninguna
lista ni selector puede filtrarlo por descuido; `ClienteDetalleSerializer`
si lo declara, y es la unica respuesta de toda la API que lo incluye
(RN-CLI-06, RF-89, RNF-26).
"""

from rest_framework import serializers

from clientes.models import Cliente


class ClienteResumenSerializer(serializers.ModelSerializer):
    """Lista y selector de la venta. SIN carnet."""

    class Meta:
        model = Cliente
        fields = ["id", "nombre", "telefono", "direccion", "activo"]
        read_only_fields = fields


class ClienteDetalleSerializer(serializers.ModelSerializer):
    """Detalle del cliente: el unico sitio con el carnet (RF-89)."""

    creado_por = serializers.CharField(source="creado_por.nombre_completo", read_only=True)
    actualizado_por = serializers.CharField(source="actualizado_por.nombre_completo", read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id",
            "nombre",
            "telefono",
            "direccion",
            "carnet",
            "activo",
            "creado_por",
            "creado_en",
            "actualizado_por",
            "actualizado_en",
        ]
        read_only_fields = fields


class ClienteEntradaSerializer(serializers.Serializer):
    """Forma de la peticion de alta y edicion. Las reglas (obligatorios,
    carnet unico y normalizado) las aplica el servicio."""

    nombre = serializers.CharField(max_length=150, allow_blank=True)
    telefono = serializers.CharField(max_length=30, allow_blank=True)
    direccion = serializers.CharField(max_length=255, allow_blank=True, required=False)
    carnet = serializers.CharField(max_length=20, allow_blank=True, required=False)
