"""Endpoint de configuracion del sistema (/api/v1/configuracion)."""

from rest_framework.response import Response
from rest_framework.views import APIView

from configuracion.models import ConfiguracionSistema
from configuracion.serializers import ConfiguracionSerializer
from configuracion.services import actualizar_umbral
from core.permissions import EsAdministrador


class ConfiguracionView(APIView):
    """CU-CAT-06 (RF-52). Solo el Administrador.

    Es un recurso singular, no una coleccion: hay exactamente una
    configuracion, asi que no lleva identificador en la URL ni admite
    POST ni DELETE.
    """

    permission_classes = [EsAdministrador]

    def get(self, request):
        configuracion = ConfiguracionSistema.obtener()
        return Response(ConfiguracionSerializer(configuracion).data)

    def patch(self, request):
        entrada = ConfiguracionSerializer(
            ConfiguracionSistema.obtener(), data=request.data, partial=True
        )
        entrada.is_valid(raise_exception=True)

        configuracion = actualizar_umbral(
            umbral=entrada.validated_data["umbral_stock_bajo"],
            ejecutor=request.user,
        )
        return Response(ConfiguracionSerializer(configuracion).data)
