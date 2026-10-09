"""Endpoint del panel de indicadores (/api/v1/panel/resumen)."""

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pdf import imagen_incrustada, render_a_pdf
from core.permissions import EsAdministrador
from panel import reportes
from servicios.models import EstadoSolicitud
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


def nombre_de_archivo(desde, hasta, extension):
    """plan.md 7.11: reporte-2026-10-01_2026-10-07.<ext>"""
    return f"reporte-{desde.isoformat()}_{hasta.isoformat()}.{extension}"


class ReportePdfView(APIView):
    """GET /reportes/pdf?desde=&hasta= — RF-95. Solo el Administrador.

    Presenta el MISMO resultado de reportes.calcular() que la vista JSON
    (RN-REP-07): no hay consultas propias aqui.
    """

    permission_classes = [EsAdministrador]

    @extend_schema(
        summary="Reporte por rango en PDF",
        responses={(200, "application/pdf"): OpenApiResponse(description="El reporte con membrete.")},
    )
    def get(self, request):
        desde, hasta = reportes.rango_de_la_peticion(request.query_params)
        reporte = reportes.calcular(desde, hasta)
        contenido = render_a_pdf(
            "panel/reporte.html",
            {
                "reporte": reporte,
                # Las etiquetas en espanol, en el orden del modelo: los
                # cuatro estados siempre (RN-REP-06).
                "estados": [
                    (etiqueta, reporte["servicios_por_estado"][valor])
                    for valor, etiqueta in EstadoSolicitud.choices
                ],
                "generado_en": timezone.localtime(),
                "generado_por": request.user.nombre_completo,
                "logo": imagen_incrustada("img/logo-pcsolution.png"),
            },
        )
        respuesta = HttpResponse(contenido, content_type="application/pdf")
        respuesta["Content-Disposition"] = f'inline; filename="{nombre_de_archivo(desde, hasta, "pdf")}"'
        return respuesta

