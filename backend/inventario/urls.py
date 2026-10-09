"""Rutas del inventario.

SimpleRouter sin sufijos de formato, igual que el resto de la API: las
URLs publicadas deben ser exactamente las del contrato de plan.md 4.4.
"""

from rest_framework.routers import SimpleRouter

from inventario.views import MovimientoStockViewSet

router = SimpleRouter(trailing_slash=False, use_regex_path=False)
router.register("movimientos-stock", MovimientoStockViewSet, basename="movimiento-stock")

urlpatterns = router.urls
