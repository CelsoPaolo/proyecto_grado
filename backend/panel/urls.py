"""Rutas del panel."""

from django.urls import path

from panel.views import ResumenPanelView

urlpatterns = [
    path("panel/resumen", ResumenPanelView.as_view(), name="panel-resumen"),
]
