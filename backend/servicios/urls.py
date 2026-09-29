"""Rutas de servicios tecnicos."""

from rest_framework.routers import SimpleRouter

from servicios.views import SolicitudViewSet

router = SimpleRouter(trailing_slash=False, use_regex_path=False)
router.register("solicitudes", SolicitudViewSet, basename="solicitud")

urlpatterns = router.urls
