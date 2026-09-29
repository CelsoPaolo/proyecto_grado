"""Endpoint del panel de indicadores (/api/v1/panel/resumen)."""

from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import EsAdministrador
from panel.serializers import ResumenPanelSerializer
from panel.services import resumen_del_panel


class ResumenPanelView(APIView):
    """CU-PAN-01 (RF-48 a RF-51, RF-65, RF-66). Solo el Administrador.

    Un unico endpoint con todos los indicadores, en vez de cinco: el
    panel se carga de golpe y no muestra cifras que aparecen a
    destiempo.
    """

    permission_classes = [EsAdministrador]

    def get(self, request):
        return Response(ResumenPanelSerializer(resumen_del_panel()).data)
