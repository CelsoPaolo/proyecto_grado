"""Gestion de cuentas del personal (/api/v1/usuarios/).

Solo el Administrador (RN-USU-01). No existe DELETE: RN-USU-05 prohibe
eliminar cuentas, y su ausencia en el contrato lo hace explicito.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from core.permissions import EsAdministrador
from usuarios.models import Usuario
from usuarios.serializers import (
    ActualizarUsuarioSerializer,
    CrearUsuarioSerializer,
    RestablecerPasswordSerializer,
    UsuarioSerializer,
)
from usuarios.services import (
    actualizar_usuario,
    bloquear_usuario,
    crear_usuario,
    desbloquear_usuario,
    restablecer_password,
)


class UsuarioViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """CU-USU-01 a CU-USU-05.

    La vista traduce HTTP a llamadas al servicio y nada mas: toda la
    logica de negocio vive en usuarios/services.py (plan.md 2.2).
    """

    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [EsAdministrador]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["rol", "is_active"]
    search_fields = ["nombre_completo", "username"]

    def create(self, request):
        """POST /usuarios - CU-USU-01 (RF-39, RF-47)."""
        entrada = CrearUsuarioSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        usuario = crear_usuario(**entrada.validated_data, ejecutor=request.user)

        return Response(
            UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, pk=None):
        """PATCH /usuarios/{id} - CU-USU-02 (RF-40, RF-44, RF-46)."""
        usuario = self.get_object()
        entrada = ActualizarUsuarioSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)

        usuario = actualizar_usuario(
            usuario=usuario, ejecutor=request.user, **entrada.validated_data
        )

        return Response(UsuarioSerializer(usuario).data)

    @action(detail=True, methods=["post"])
    def bloquear(self, request, pk=None):
        """POST /usuarios/{id}/bloquear - CU-USU-03 (RF-41, RF-45, RF-46)."""
        usuario = bloquear_usuario(usuario=self.get_object(), ejecutor=request.user)
        return Response(UsuarioSerializer(usuario).data)

    @action(detail=True, methods=["post"])
    def desbloquear(self, request, pk=None):
        """POST /usuarios/{id}/desbloquear - CU-USU-03 (RF-41)."""
        usuario = desbloquear_usuario(usuario=self.get_object(), ejecutor=request.user)
        return Response(UsuarioSerializer(usuario).data)

    @action(detail=True, methods=["post"], url_path="restablecer-password")
    def restablecer_password(self, request, pk=None):
        """POST /usuarios/{id}/restablecer-password - CU-USU-04 (RF-42)."""
        entrada = RestablecerPasswordSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        restablecer_password(
            usuario=self.get_object(),
            password_nueva=entrada.validated_data["password_nueva"],
            ejecutor=request.user,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
