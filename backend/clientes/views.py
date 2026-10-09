"""Endpoints de clientes (/api/v1/clientes).

NO existe DELETE: la ausencia de ese verbo es la implementacion de
RN-CLI-03. Un cliente se desactiva, nunca se elimina, igual que las
cuentas del personal.

El Encargado de Servicios no entra al modulo en esta version (PA-06):
PuedeVender admite solo al Administrador y al Encargado de Ventas.
"""

from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from clientes.models import Cliente, normalizar_carnet
from clientes.serializers import (
    ClienteDetalleSerializer,
    ClienteEntradaSerializer,
    ClienteResumenSerializer,
)
from clientes.services import cambiar_estado_cliente, editar_cliente, registrar_cliente
from core.permissions import EsAdministrador, PuedeVender


class ClienteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Gestion de clientes (RF-84 a RF-89)."""

    queryset = Cliente.objects.none()  # respaldo para el esquema

    def get_permissions(self):
        # RN-CLI-07: desactivar y reactivar son solo del Administrador.
        if self.action in ("desactivar", "reactivar"):
            return [EsAdministrador()]
        return [PuedeVender()]

    def get_serializer_class(self):
        # RN-CLI-06: el carnet solo sale en el detalle.
        return ClienteResumenSerializer if self.action == "list" else ClienteDetalleSerializer

    def get_queryset(self):
        """RF-86 — busqueda y filtro de activos.

        `?buscar=`: nombre o telefono que CONTIENEN el texto, o carnet
        EXACTO. El carnet se busca pero no se muestra: quien lo teclea ya
        lo conoce, y una coincidencia parcial permitiria ir adivinando
        carnets ajenos cifra a cifra.

        `?activo=true|false`. Sin el, se listan todos: el Administrador
        necesita ver los inactivos para reactivarlos. El selector de la
        venta pide `activo=true`.
        """
        consulta = Cliente.objects.select_related("creado_por", "actualizado_por")
        parametros = self.request.query_params

        texto = parametros.get("buscar", "").strip()
        if texto:
            consulta = consulta.filter(
                Q(nombre__icontains=texto)
                | Q(telefono__icontains=texto)
                | Q(carnet=normalizar_carnet(texto))
            )

        activo = parametros.get("activo")
        if activo in ("true", "false"):
            consulta = consulta.filter(activo=activo == "true")

        return consulta.order_by("nombre", "id")

    def _detalle(self, cliente, estado=status.HTTP_200_OK):
        return Response(ClienteDetalleSerializer(cliente).data, status=estado)

    def create(self, request):
        """POST /clientes - RF-84, RF-88 (409 CARNET_DUPLICADO)."""
        entrada = ClienteEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cliente = registrar_cliente(usuario=request.user, **entrada.validated_data)
        return self._detalle(cliente, status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        """PATCH /clientes/{id} - RF-85. No hay PUT: la edicion es parcial."""
        cliente = self.get_object()
        entrada = ClienteEntradaSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        cliente = editar_cliente(cliente=cliente, usuario=request.user, **entrada.validated_data)
        return self._detalle(cliente)

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """POST /clientes/{id}/desactivar - RF-87, solo Administrador."""
        cliente = cambiar_estado_cliente(cliente=self.get_object(), usuario=request.user, activo=False)
        return self._detalle(cliente)

    @action(detail=True, methods=["post"])
    def reactivar(self, request, pk=None):
        """POST /clientes/{id}/reactivar - RF-87, solo Administrador."""
        cliente = cambiar_estado_cliente(cliente=self.get_object(), usuario=request.user, activo=True)
        return self._detalle(cliente)
