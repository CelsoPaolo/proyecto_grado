"""Rutas del panel."""

from django.urls import path

from panel.views import ReportePdfView, ReporteView, ReporteXlsxView, ResumenPanelView

urlpatterns = [
    path("panel/resumen", ResumenPanelView.as_view(), name="panel-resumen"),
    path("reportes", ReporteView.as_view(), name="reportes"),
    path("reportes/pdf", ReportePdfView.as_view(), name="reportes-pdf"),
    path("reportes/xlsx", ReporteXlsxView.as_view(), name="reportes-xlsx"),
]
