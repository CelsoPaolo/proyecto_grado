"""Serializers de servicios tecnicos."""

from rest_framework import serializers

from servicios.models import (
    EventoSolicitud,
    MODALIDAD_POR_TIPO,
    Modalidad,
    SolicitudServicio,
    TipoServicio,
)


class UsuarioBreveSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre_completo = serializers.CharField(read_only=True)


class EventoSerializer(serializers.ModelSerializer):
    """Linea del historial (RF-38)."""

    usuario = UsuarioBreveSerializer(read_only=True)
    tipo_evento_display = serializers.CharField(
        source="get_tipo_evento_display", read_only=True
    )

    class Meta:
        model = EventoSolicitud
        fields = [
            "id",
            "tipo_evento",
            "tipo_evento_display",
            "estado_anterior",
            "estado_nuevo",
            "usuario",
            "fecha_hora",
            "nota",
        ]
        read_only_fields = fields


class SolicitudSerializer(serializers.ModelSerializer):
    """Detalle completo (RF-38)."""

    registrada_por = UsuarioBreveSerializer(read_only=True)
    cotizada_por = UsuarioBreveSerializer(read_only=True)
    cerrada_por = UsuarioBreveSerializer(read_only=True)
    eventos = EventoSerializer(many=True, read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    modalidad_display = serializers.CharField(
        source="get_modalidad_display", read_only=True
    )
    esta_cotizada = serializers.BooleanField(read_only=True)

    class Meta:
        model = SolicitudServicio
        fields = [
            "id",
            "cliente_nombre",
            "cliente_telefono",
            "tipo",
            "tipo_display",
            "modalidad",
            "modalidad_display",
            "direccion",
            "descripcion",
            "estado",
            "estado_display",
            "registrada_por",
            "tecnico",
            "monto_cobrado",
            "esta_cotizada",
            "cotizada_por",
            "fecha_cotizacion",
            "observaciones",
            "motivo_cancelacion",
            "cerrada_por",
            "fecha_registro",
            "fecha_inicio_atencion",
            "fecha_cierre",
            "eventos",
        ]
        read_only_fields = fields


class SolicitudResumenSerializer(serializers.ModelSerializer):
    """Fila del listado (RF-36, RF-37). Sin el historial, que no hace
    falta para listar y multiplicaria las consultas."""

    registrada_por = UsuarioBreveSerializer(read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    esta_cotizada = serializers.BooleanField(read_only=True)

    class Meta:
        model = SolicitudServicio
        fields = [
            "id",
            "cliente_nombre",
            "cliente_telefono",
            "tipo",
            "tipo_display",
            "modalidad",
            "estado",
            "estado_display",
            "registrada_por",
            "tecnico",
            "monto_cobrado",
            "esta_cotizada",
            "fecha_registro",
            "fecha_cierre",
        ]
        read_only_fields = fields


class RegistrarSolicitudSerializer(serializers.Serializer):
    """CU-SER-01 (RF-28, RF-29).

    No acepta `modalidad`: la deriva el sistema del tipo (RN-SER-01).
    Tampoco acepta monto ni tecnico: son del Administrador (RF-57).
    """

    cliente_nombre = serializers.CharField(max_length=150)
    cliente_telefono = serializers.CharField(max_length=30)
    tipo = serializers.ChoiceField(choices=TipoServicio.choices)
    descripcion = serializers.CharField()
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        """RN-SER-04: la direccion es obligatoria solo a domicilio.

        Se comprueba aqui ademas de en la base para devolver un error
        asociado al campo (RNF-15) en lugar de un fallo de integridad.
        """
        modalidad = MODALIDAD_POR_TIPO[attrs["tipo"]]
        direccion = (attrs.get("direccion") or "").strip()

        if modalidad == Modalidad.DOMICILIO and not direccion:
            raise serializers.ValidationError(
                {
                    "direccion": (
                        "Este tipo de servicio se atiende a domicilio: "
                        "debe indicar la dirección."
                    )
                }
            )

        # En taller la direccion no se pide; si llega, se descarta para
        # no guardar un dato que la especificacion no contempla.
        attrs["direccion"] = direccion if modalidad == Modalidad.DOMICILIO else ""
        return attrs


class CotizarSerializer(serializers.Serializer):
    """CU-SER-06 (RF-56, RF-62). Solo Administrador."""

    monto_cobrado = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False
    )
    tecnico = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )

    def validate(self, attrs):
        if "monto_cobrado" not in attrs and "tecnico" not in attrs:
            raise serializers.ValidationError(
                "Indique el monto a cobrar, el técnico, o ambos."
            )
        return attrs


class FinalizarSerializer(serializers.Serializer):
    """CU-SER-03 (RF-32, RF-33)."""

    observaciones = serializers.CharField()

    def validate_observaciones(self, valor):
        if not valor.strip():
            raise serializers.ValidationError(
                "Debe describir el trabajo realizado."
            )
        return valor


class CancelarSerializer(serializers.Serializer):
    """CU-SER-04 (RF-34)."""

    motivo = serializers.CharField(max_length=500)

    def validate_motivo(self, valor):
        if not valor.strip():
            raise serializers.ValidationError(
                "Debe indicar el motivo de la cancelación."
            )
        return valor
