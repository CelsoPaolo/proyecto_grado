"""Rutas usadas SOLO por las pruebas de T-0.6 y T-0.7.

No se montan en config/urls.py: existen para poder comprobar el
comportamiento por defecto del framework sin depender de endpoints
reales del negocio, que aun no existen en el bloque 0.
"""

from django.urls import path
from rest_framework.views import APIView

from core.exceptions import ErrorDeNegocio


class VistaSinPermisosDeclarados(APIView):
    """A proposito NO declara permission_classes.

    Es la comprobacion de RNF-01: el descuido de no declarar permisos
    debe dejar el endpoint CERRADO, no abierto.
    """

    def get(self, request):  # pragma: no cover - no deberia alcanzarse sin token
        from rest_framework.response import Response

        return Response({"ok": True})


class VistaQueLanzaErrorDeNegocio(APIView):
    permission_classes = []

    def get(self, request):
        raise ErrorDeNegocio("Regla de negocio incumplida.")


urlpatterns = [
    path("sin-permisos", VistaSinPermisosDeclarados.as_view()),
    path("error-negocio", VistaQueLanzaErrorDeNegocio.as_view()),
]
