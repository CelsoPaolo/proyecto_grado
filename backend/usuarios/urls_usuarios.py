"""Rutas de gestion de cuentas."""

from rest_framework.routers import DefaultRouter

from usuarios.views_usuarios import UsuarioViewSet

router = DefaultRouter(trailing_slash=False)
router.register("usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = router.urls
