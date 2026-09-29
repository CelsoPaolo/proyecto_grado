"""Endpoints de servicios tecnicos (/api/v1/solicitudes).

Dos reglas de autorizacion, distintas entre si:

  - ENTRAR al modulo: Administrador o Encargado de Servicios.
  - COTIZAR: solo Administrador (RF-56, RF-57). Es la unica accion del
    modulo con un permiso mas estrecho que el resto.

Y dentro del modulo, cada usuario ve solo lo que registro (RN-SER-15),
igual que en ventas.
"""

from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import EsAdministrador, PuedeAtenderServicios
from servicios.models import ESTADOS_PENDIENTES, SolicitudServicio
from servicios.serializers import (
    CancelarSerializer,
    CotizarSerializer,
    FinalizarSerializer,
    RegistrarSolicitudSerializer,
    SolicitudResumenSerializer,
    SolicitudSerializer,
)
from servicios.services import (
    cancelar_solicitud,
    cotizar_solicitud,
    finalizar_solicitud,
    iniciar_atencion,
    registrar_solicitud,
)


class SolicitudViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """CU-SER-01 a CU-SER-06 (RF-28 a RF-38, RF-55 a RF-64).

    Cada transicion es un endpoint con nombre propio en lugar de un
    PATCH {"estado": "..."}: asi la maquina de estados vive en el
    contrato. `finalizar` puede exigir observaciones y monto, e
    `iniciar` no exige nada, cosa que un PATCH generico no expresaria.

    No hay DELETE: RN-SER-08 dice que las solicitudes se cancelan, no
    se eliminan, y la ausencia del verbo lo hace explicito.
    """

    permission_classes = [PuedeAtenderServicios]
    # Respaldo para la introspeccion del esquema (T-7.4): en
    # ejecucion siempre manda get_queryset().
    queryset = SolicitudServicio.objects.none()

    def get_serializer_class(self):
        if self.action == "list":
            return SolicitudResumenSerializer
        return SolicitudSerializer

    def get_permissions(self):
        """RF-56 y RF-57: cotizar es exclusivo del Administrador."""
        if self.action == "cotizar":
            return [EsAdministrador()]
        return super().get_permissions()

    def get_queryset(self):
        """RN-SER-15 y RF-64 — visibilidad por usuario.

        Un Encargado de Servicios ve solo las solicitudes que registro;
        el Administrador ve todas. Es el MISMO criterio que
        VentaViewSet: desde la revision de PA-04 en spec.md v1.2, los
        dos modulos se comportan igual.

        Filtrar aqui, y no solo en el permiso de objeto, es lo que hace
        que pedir el id de una solicitud ajena devuelva 404 en lugar de
        403: un 403 confirmaria que esa solicitud existe.
        """
        consulta = SolicitudServicio.objects.select_related(
            "registrada_por", "cotizada_por", "cerrada_por"
        ).order_by("-fecha_registro", "-id")

        if not self.request.user.es_administrador:
            consulta = consulta.filter(registrada_por=self.request.user)

        parametros = self.request.query_params

        if estado := parametros.get("estado"):
            consulta = consulta.filter(estado=estado)

        if tipo := parametros.get("tipo"):
            consulta = consulta.filter(tipo=tipo)

        if desde := parse_date(parametros.get("desde", "")):
            consulta = consulta.filter(fecha_registro__date__gte=desde)

        if hasta := parse_date(parametros.get("hasta", "")):
            consulta = consulta.filter(fecha_registro__date__lte=hasta)

        # RF-60: las que esperan cotizacion del Administrador.
        if parametros.get("sin_cotizar") == "true":
            consulta = consulta.filter(
                monto_cobrado__isnull=True, estado__in=ESTADOS_PENDIENTES
            )

        if self.action == "retrieve":
            consulta = consulta.prefetch_related("eventos__usuario")

        return consulta

    def _responder(self, solicitud, codigo=status.HTTP_200_OK):
        completa = (
            self.get_queryset().prefetch_related("eventos__usuario").get(pk=solicitud.pk)
        )
        return Response(SolicitudSerializer(completa).data, status=codigo)

    def create(self, request):
        """POST /solicitudes - CU-SER-01 (RF-28, RF-29, RF-30)."""
        entrada = RegistrarSolicitudSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        solicitud = registrar_solicitud(usuario=request.user, **entrada.validated_data)
        return self._responder(solicitud, status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cotizar(self, request, pk=None):
        """POST /solicitudes/{id}/cotizar - CU-SER-06 (RF-56, RF-58).

        Solo Administrador. Fija el monto, anota el tecnico, o ambos.
        """
        solicitud = self.get_object()

        entrada = CotizarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        solicitud = cotizar_solicitud(
            solicitud=solicitud,
            usuario=request.user,
            monto=entrada.validated_data.get("monto_cobrado"),
            tecnico=entrada.validated_data.get("tecnico"),
        )
        return self._responder(solicitud)

    @action(detail=True, methods=["post"])
    def iniciar(self, request, pk=None):
        """POST /solicitudes/{id}/iniciar - CU-SER-02 (RF-31)."""
        solicitud = iniciar_atencion(solicitud=self.get_object(), usuario=request.user)
        return self._responder(solicitud)

    @action(detail=True, methods=["post"])
    def finalizar(self, request, pk=None):
        """POST /solicitudes/{id}/finalizar - CU-SER-03 (RF-32, RF-61)."""
        solicitud = self.get_object()

        entrada = FinalizarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        solicitud = finalizar_solicitud(
            solicitud=solicitud,
            usuario=request.user,
            observaciones=entrada.validated_data["observaciones"],
        )
        return self._responder(solicitud)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """POST /solicitudes/{id}/cancelar - CU-SER-04 (RF-34)."""
        solicitud = self.get_object()

        entrada = CancelarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        solicitud = cancelar_solicitud(
            solicitud=solicitud,
            usuario=request.user,
            motivo=entrada.validated_data["motivo"],
        )
        return self._responder(solicitud)
