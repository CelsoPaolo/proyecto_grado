"""Rutas del catalogo.

SimpleRouter sin sufijos de formato, igual que en usuarios: las URLs
publicadas deben ser exactamente las del contrato de plan.md 4.4.
"""

from rest_framework.routers import SimpleRouter

from catalogo.views import CategoriaViewSet, ProductoViewSet

router = SimpleRouter(trailing_slash=False, use_regex_path=False)
router.register("categorias", CategoriaViewSet, basename="categoria")
router.register("productos", ProductoViewSet, basename="producto")

urlpatterns = router.urls
