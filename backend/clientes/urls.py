"""Rutas de clientes. SimpleRouter sin sufijos de formato, como el resto
de la API (plan.md 4.4)."""

from rest_framework.routers import SimpleRouter

from clientes.views import ClienteViewSet

router = SimpleRouter(trailing_slash=False, use_regex_path=False)
router.register("clientes", ClienteViewSet, basename="cliente")

urlpatterns = router.urls
