"""Serializers de ventas."""

from rest_framework import serializers

from core.serializers import UsuarioBreveSerializer

from ventas.models import DetalleVenta, Venta


class DetalleVentaSerializer(serializers.ModelSerializer):
    """Linea de venta con sus datos CONGELADOS (RN-VEN-04).

    Se exponen producto_nombre y precio_unitario, no los del producto
    actual: el historial debe mostrar lo que costo ese dia.
    """

    producto_id = serializers.IntegerField(source="producto.id", read_only=True)

    class Meta:
        model = DetalleVenta
        fields = [
            "producto_id",
            "producto_nombre",
            "precio_unitario",
            "cantidad",
            "subtotal",
        ]
        read_only_fields = fields


class VentaSerializer(serializers.ModelSerializer):
    """Detalle completo de una venta (RF-23)."""

    items = DetalleVentaSerializer(many=True, read_only=True)
    usuario = UsuarioBreveSerializer(read_only=True)
    anulada_por = UsuarioBreveSerializer(read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Venta
        fields = [
            "id",
            "fecha_hora",
            "cliente_nombre",
            "cliente_telefono",
            "estado",
            "estado_display",
            "total",
            "usuario",
            "items",
            "motivo_anulacion",
            "anulada_por",
            "fecha_anulacion",
        ]
        read_only_fields = fields


class VentaResumenSerializer(serializers.ModelSerializer):
    """Fila del historial (RF-21, RF-22). Sin el detalle, que no hace
    falta para listar y multiplicaria las consultas."""

    usuario = UsuarioBreveSerializer(read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    cantidad_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Venta
        fields = [
            "id",
            "fecha_hora",
            "cliente_nombre",
            "cliente_telefono",
            "estado",
            "estado_display",
            "total",
            "usuario",
            "cantidad_items",
        ]
        read_only_fields = fields


class ItemVentaEntradaSerializer(serializers.Serializer):
    """Una linea del cuerpo de POST /ventas.

    NO acepta precio: el servidor lo toma del catalogo al confirmar
    (RN-VEN-04). Aceptarlo del navegador permitiria alterarlo.
    """

    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)


class RegistrarVentaSerializer(serializers.Serializer):
    """CU-VEN-01 (RF-15)."""

    cliente_nombre = serializers.CharField(max_length=150)
    cliente_telefono = serializers.CharField(max_length=30)
    items = ItemVentaEntradaSerializer(many=True, allow_empty=False)

    def validate_items(self, valor):
        """RN-VEN-01."""
        if not valor:
            raise serializers.ValidationError(
                "La venta debe incluir al menos un producto."
            )
        return valor


class AnularVentaSerializer(serializers.Serializer):
    """CU-VEN-03 (RF-24). El motivo es obligatorio (RN-VEN-07)."""

    motivo = serializers.CharField(max_length=500)

    def validate_motivo(self, valor):
        if not valor.strip():
            raise serializers.ValidationError(
                "Debe indicar el motivo de la anulación."
            )
        return valor
