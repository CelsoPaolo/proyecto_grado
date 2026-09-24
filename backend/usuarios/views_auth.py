"""Vistas de token: refresco seguro y cierre de sesion."""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from usuarios.serializers import (
    LogoutSerializer,
    TokenRefreshSeguroSerializer,
)


class TokenRefreshSeguroView(TokenRefreshView):
    """POST /auth/refresh (via 2 de plan.md 1.3).

    Rechaza el refresco si la cuenta fue bloqueada o eliminada.
    """

    serializer_class = TokenRefreshSeguroSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class LogoutView(APIView):
    """CU-AUT-02 - POST /auth/logout (RF-04)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
