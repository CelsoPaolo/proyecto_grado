"""Endpoints de autenticacion y de cuenta propia (/api/v1/auth/)."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.serializers import (
    CambiarPasswordPropiaSerializer,
    LoginSerializer,
    UsuarioResumenSerializer,
)


class LoginView(APIView):
    """CU-AUT-01 - POST /auth/login (RF-01, RF-02, RF-03).

    Unico endpoint publico del sistema (RNF-01).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=LoginSerializer,
        responses={200: UsuarioResumenSerializer},
        summary="Iniciar sesión",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["usuario"]
        return Response(serializer.crear_tokens(usuario), status=status.HTTP_200_OK)


class YoView(APIView):
    """GET /auth/me - usuario actual y su rol (RF-06).

    El frontend lo usa para construir el menu y decidir que mostrar.
    La autorizacion real sigue viviendo en cada endpoint (RNF-02).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UsuarioResumenSerializer},
        summary="Usuario autenticado y su rol",
    )
    def get(self, request):
        return Response(UsuarioResumenSerializer(request.user).data)


class CambiarPasswordPropiaView(APIView):
    """CU-AUT-03 - POST /auth/me/password (RF-05)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CambiarPasswordPropiaSerializer,
        responses={204: None},
        summary="Cambiar la contraseña propia",
    )
    def post(self, request):
        serializer = CambiarPasswordPropiaSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
