"""Rutas de autenticacion y cuenta propia."""

from django.urls import path

from usuarios.views import (
    CambiarPasswordPropiaView,
    LoginView,
    YoView,
)
from usuarios.views_auth import LogoutView, TokenRefreshSeguroView

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("refresh", TokenRefreshSeguroView.as_view(), name="refresh"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("me", YoView.as_view(), name="yo"),
    path("me/password", CambiarPasswordPropiaView.as_view(), name="cambiar-password"),
]
