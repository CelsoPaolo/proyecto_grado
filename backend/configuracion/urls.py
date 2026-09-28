"""Ruta de configuracion del sistema."""

from django.urls import path

from configuracion.views import ConfiguracionView

urlpatterns = [
    path("configuracion", ConfiguracionView.as_view(), name="configuracion"),
]
