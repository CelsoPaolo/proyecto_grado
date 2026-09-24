"""Rutas de gestion de cuentas.

Se usa SimpleRouter y no DefaultRouter, y se desactivan los sufijos de
formato, para que las URLs publicadas sean **exactamente** las del
contrato de plan.md seccion 4.4: sin vista raiz de la API y sin
variantes .json de cada ruta. En un proyecto dirigido por la
especificacion, lo publicado y lo documentado no deben divergir.
"""

from rest_framework.routers import SimpleRouter

from usuarios.views_usuarios import UsuarioViewSet

router = SimpleRouter(trailing_slash=False, use_regex_path=False)
router.register("usuarios", UsuarioViewSet, basename="usuario")

urlpatterns = router.urls
