"""Endpoint del panel de indicadores (/api/v1/panel/resumen)."""

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import EsAdministrador
from panel import reportes
from panel.serializers import ReporteSerializer, ResumenPanelSerializer
from panel.services import resumen_del_panel


class ResumenPanelView(APIView):
    """CU-PAN-01 (RF-48 a RF-51, RF-65, RF-66). Solo el Administrador.

    Un unico endpoint con todos los indicadores, en vez de cinco: el
    panel se carga de golpe y no muestra cifras que aparecen a
    destiempo.
    """

    permission_classes = [EsAdministrador]

    @extend_schema(
        responses={200: ResumenPanelSerializer},
        summary="Indicadores del día",
    )
    def get(self, request):
        return Response(ResumenPanelSerializer(resumen_del_panel()).data)


class ReporteView(APIView):
    """GET /reportes?desde=&hasta= — RF-90 a RF-94. Solo el
    Administrador (RN-REP-10).

    400 si falta una fecha o no es valida, y 400 RANGO_INVALIDO si
    «desde» es posterior a «hasta».
    """

    permission_classes = [EsAdministrador]

    @extend_schema(responses={200: ReporteSerializer}, summary="Reporte por rango de fechas")
    def get(self, request):
        desde, hasta = reportes.rango_de_la_peticion(request.query_params)
        return Response(ReporteSerializer(reportes.calcular(desde, hasta)).data)

