"""Serializers del libro de movimientos (plan.md 4.4)."""

from rest_framework import serializers

from inventario.models import MovimientoStock


class MovimientoStockSerializer(serializers.ModelSerializer):
    """Un movimiento tal como lo consulta el Administrador (CU-CAT-08).

    Solo lectura de punta a punta: el libro no se escribe desde la API
    (RNF-25). El nombre del producto y el del autor viajan ya resueltos
    para que la tabla no tenga que hacer una consulta por fila.
    """

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    # Nulo solo en el saldo inicial, que lo creo la migracion y no una
    # persona (RN-MOV-02).
    usuario_nombre = serializers.CharField(
        source="usuario.nombre_completo", read_only=True, default=None
    )

    class Meta:
        model = MovimientoStock
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "tipo",
            "tipo_display",
            "cantidad",
            "stock_resultante",
            "usuario",
            "usuario_nombre",
            "venta",
            "motivo",
            "fecha_hora",
        ]
        read_only_fields = fields


class AjustarExistenciasSerializer(serializers.Serializer):
    """Entrada de CU-CAT-07 (RF-73).

    Valida la forma de la peticion con mensajes junto a cada campo
    (RNF-15). Las reglas de negocio —motivo no vacio, cantidad distinta
    de la vigente— las vuelve a aplicar el servicio, que es quien
    responde por ellas aunque se le llame sin pasar por la API.
    """

    cantidad_real = serializers.IntegerField(
        min_value=0,
        error_messages={
            "required": "Indique la cantidad real contada.",
            "null": "Indique la cantidad real contada.",
            "invalid": "La cantidad real debe ser un número entero.",
            "min_value": "La cantidad real no puede ser negativa.",
        },
    )
    motivo = serializers.CharField(
        max_length=500,
        error_messages={
            "required": "Indique el motivo del ajuste.",
            "null": "Indique el motivo del ajuste.",
            "blank": "Indique el motivo del ajuste.",
            "max_length": "El motivo no puede superar los 500 caracteres.",
        },
    )
