"""Serializers del panel de indicadores."""

from rest_framework import serializers


class ImporteYCantidadSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField()
    importe = serializers.DecimalField(max_digits=14, decimal_places=2)


class IngresoTotalSerializer(serializers.Serializer):
    """RN-IND-05 — el total NUNCA viaja sin su desglose.

    Los tres campos son obligatorios en la respuesta: no existe una
    forma de pedir solo el agregado, que es lo que la regla busca
    impedir.
    """

    importe = serializers.DecimalField(max_digits=14, decimal_places=2)
    de_ventas = serializers.DecimalField(max_digits=14, decimal_places=2)
    de_servicios = serializers.DecimalField(max_digits=14, decimal_places=2)


class ServiciosPendientesSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    registradas = serializers.IntegerField()
    en_atencion = serializers.IntegerField()
    sin_cotizar = serializers.IntegerField()


class ProductoEscasoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    stock = serializers.IntegerField()


class StockBajoSerializer(serializers.Serializer):
    umbral = serializers.IntegerField()
    cantidad = serializers.IntegerField()
    productos = ProductoEscasoSerializer(many=True)


class ResumenPanelSerializer(serializers.Serializer):
    """CU-PAN-01 (RF-48 a RF-51, RF-65, RF-66)."""

    fecha = serializers.DateField()
    ventas_dia = ImporteYCantidadSerializer()
    servicios_dia = ImporteYCantidadSerializer()
    ingreso_total = IngresoTotalSerializer()
    servicios_pendientes = ServiciosPendientesSerializer()
    stock_bajo = StockBajoSerializer()


# ─────────────────────────────────────────────────────────────────────
# Reporte por rango (plan.md 4.4, v1.3)
# ─────────────────────────────────────────────────────────────────────
class ProductoVendidoSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    unidades = serializers.IntegerField()
    importe = serializers.DecimalField(max_digits=14, decimal_places=2)


class VentasDeUsuarioSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField()
    nombre_completo = serializers.CharField()
    cantidad = serializers.IntegerField()
    importe = serializers.DecimalField(max_digits=14, decimal_places=2)


class ReporteSerializer(serializers.Serializer):
    """La forma del reporte en JSON. El PDF y el Excel presentan EL MISMO
    diccionario que produce panel.reportes.calcular() (RN-REP-07)."""

    desde = serializers.DateField()
    hasta = serializers.DateField()
    ventas = ImporteYCantidadSerializer()
    servicios = ImporteYCantidadSerializer()
    ingreso_total = IngresoTotalSerializer()
    productos_mas_vendidos = ProductoVendidoSerializer(many=True)
    ventas_por_usuario = VentasDeUsuarioSerializer(many=True)
    servicios_por_estado = serializers.DictField(child=serializers.IntegerField())

