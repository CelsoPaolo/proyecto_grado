"""Rutas de autenticacion y cuenta propia."""

from django.urls import path

from usuarios.views import (
    CambiarPasswordPropiaView,
    LoginView,
    YoView,
)

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("me", YoView.as_view(), name="yo"),
    path("me/password", CambiarPasswordPropiaView.as_view(), name="cambiar-password"),
]
