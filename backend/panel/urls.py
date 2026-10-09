"""Rutas del panel."""

from django.urls import path

from panel.views import ReportePdfView, ReporteView, ResumenPanelView

urlpatterns = [
    path("panel/resumen", ResumenPanelView.as_view(), name="panel-resumen"),
    path("reportes", ReporteView.as_view(), name="reportes"),
    path("reportes/pdf", ReportePdfView.as_view(), name="reportes-pdf"),
]
