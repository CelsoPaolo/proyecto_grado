"""Rutas del panel."""

from django.urls import path

from panel.views import ReporteView, ResumenPanelView

urlpatterns = [
    path("panel/resumen", ResumenPanelView.as_view(), name="panel-resumen"),
    path("reportes", ReporteView.as_view(), name="reportes"),
]
