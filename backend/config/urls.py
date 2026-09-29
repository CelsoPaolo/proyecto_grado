"""Rutas del proyecto.

Toda la API cuelga de /api/v1/ (plan.md seccion 4.1). El versionado en
la URL permite evolucionar el contrato sin romper el frontend ya
desplegado.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("usuarios.urls")),
    path("api/v1/", include("usuarios.urls_usuarios")),
    path("api/v1/", include("catalogo.urls")),
    path("api/v1/", include("configuracion.urls")),
    path("api/v1/", include("ventas.urls")),
    path("api/v1/", include("servicios.urls")),
    path("api/v1/", include("panel.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
