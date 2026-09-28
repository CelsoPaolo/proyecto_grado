"""Rutas de ventas."""

from rest_framework.routers import SimpleRouter

from ventas.views import VentaViewSet

router = SimpleRouter(trailing_slash=False, use_regex_path=False)
router.register("ventas", VentaViewSet, basename="venta")

urlpatterns = router.urls
