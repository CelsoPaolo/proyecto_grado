"""Serializers de la configuracion del sistema."""

from rest_framework import serializers

from configuracion.models import ConfiguracionSistema


class ConfiguracionSerializer(serializers.ModelSerializer):
    """RF-52.

    `umbral_stock_bajo` es el unico campo editable: quien lo cambio y
    cuando los registra el servidor (RN-CAT-07), no el cliente.
    """

    actualizado_por_nombre = serializers.CharField(
        source="actualizado_por.nombre_completo",
        read_only=True,
        default=None,
    )

    class Meta:
        model = ConfiguracionSistema
        fields = [
            "umbral_stock_bajo",
            "actualizado_por_nombre",
            "actualizado_en",
        ]
        read_only_fields = ["actualizado_por_nombre", "actualizado_en"]

    def validate_umbral_stock_bajo(self, valor):
        """RN-CAT-07: entero no negativo.

        PositiveIntegerField ya lo impide, pero validarlo aqui devuelve
        un error de campo legible en vez de un fallo de integridad
        (RNF-15).
        """
        if valor < 0:
            raise serializers.ValidationError(
                "El umbral no puede ser negativo."
            )
        return valor
