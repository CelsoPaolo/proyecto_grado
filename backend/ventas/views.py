"""Endpoints de ventas (/api/v1/ventas).

NO existen PUT, PATCH ni DELETE sobre una venta: **la ausencia de esos
verbos es la implementacion de RN-VEN-06 y RF-26**. Una venta
confirmada no se edita ni se elimina, y el unico cambio posible es la
anulacion, que es una accion con nombre propio y no un borrado.
"""

from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response

from core.pdf import imagen_incrustada, render_a_pdf

from core.permissions import EsDuenoDeLaVentaOAdmin, PuedeVender
from ventas.models import Venta
from ventas.serializers import (
    AnularVentaSerializer,
    RegistrarVentaSerializer,
    VentaResumenSerializer,
    VentaSerializer,
)
from ventas import garantia as modulo_garantia
from ventas.garantia import fecha_local, lineas_con_garantia
from ventas.services import anular_venta, registrar_venta


class VentaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """CU-VEN-01 a CU-VEN-03 (RF-15 a RF-27, RF-54)."""

    permission_classes = [PuedeVender, EsDuenoDeLaVentaOAdmin]
    # Respaldo para la introspeccion del esquema (T-7.4): en
    # ejecucion siempre manda get_queryset().
    queryset = Venta.objects.none()

    def get_serializer_class(self):
        if self.action == "list":
            return VentaResumenSerializer
        return VentaSerializer

    def get_queryset(self):
        """RF-21, RF-22 y RF-27 - filtrado por rol.

        Un Encargado de Ventas solo ve las suyas; el Administrador ve
        todas (RN-VEN-09).

        SolicitudViewSet (bloque 5) aplica el MISMO criterio desde la
        revision de PA-04 en spec.md v1.2: ambos modulos son privados
        por usuario.
        """
        # El order_by explicito no es redundante: annotate() con
        # agregacion descarta el orden por defecto del Meta, y una
        # consulta sin orden hace que la paginacion repita o salte
        # filas entre paginas (RNF-18). Ya ocurrio en el catalogo.
        consulta = (
            Venta.objects.select_related("usuario", "anulada_por")
            .annotate(cantidad_items=Count("items"))
            .order_by("-fecha_hora", "-id")
        )

        if not self.request.user.es_administrador:
            consulta = consulta.filter(usuario=self.request.user)

        parametros = self.request.query_params

        if estado := parametros.get("estado"):
            consulta = consulta.filter(estado=estado)

        if desde := parse_date(parametros.get("desde", "")):
            consulta = consulta.filter(fecha_hora__date__gte=desde)

        if hasta := parse_date(parametros.get("hasta", "")):
            consulta = consulta.filter(fecha_hora__date__lte=hasta)

        if self.action == "retrieve":
            consulta = consulta.prefetch_related("items")

        return consulta

    def create(self, request):
        """POST /ventas - CU-VEN-01 (RF-15 a RF-20).

        Si falta stock, el servicio levanta StockInsuficiente y la
        transaccion se revierte entera: ningun producto queda
        descontado (RN-VEN-02).
        """
        entrada = RegistrarVentaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        venta = registrar_venta(
            usuario=request.user,
            cliente_nombre=entrada.validated_data["cliente_nombre"],
            cliente_telefono=entrada.validated_data["cliente_telefono"],
            items=entrada.validated_data["items"],
        )

        venta = self.get_queryset().prefetch_related("items").get(pk=venta.pk)
        return Response(VentaSerializer(venta).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        """POST /ventas/{id}/anular - CU-VEN-03 (RF-24, RF-25, RF-54).

        get_object() aplica EsDuenoDeLaVentaOAdmin: un Encargado de
        Ventas no puede anular la venta de otro (RF-27).

        Sin limite de plazo (RN-VEN-11).
        """
        venta = self.get_object()

        entrada = AnularVentaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        venta = anular_venta(
            venta=venta,
            usuario=request.user,
            motivo=entrada.validated_data["motivo"],
        )

        venta = self.get_queryset().prefetch_related("items").get(pk=venta.pk)
        return Response(VentaSerializer(venta).data)

    @extend_schema(
        summary="Garantía de la venta en PDF",
        responses={
            (200, "application/pdf"): OpenApiResponse(
                description="El certificado de garantía, listo para entregar."
            )
        },
    )
    @action(detail=True, methods=["get"])
    def garantia(self, request, pk=None):
        """GET /ventas/{id}/garantia - CU-VEN-04 (RF-76, RF-78).

        Sin permiso propio, igual que el informe de servicio: usa
        get_object(), que pasa por get_queryset() y por
        EsDuenoDeLaVentaOAdmin. La garantia la emite exactamente quien
        puede ver la venta, y la venta ajena responde 404 (RN-VEN-16).

        409 si la venta esta anulada o no tiene ninguna linea con
        garantia (RN-VEN-14). El contenido sale de la venta guardada:
        emitirla dos veces da lo mismo salvo la fecha de generacion.
        """
        venta = self.get_object()
        lineas = lineas_con_garantia(venta)

        contenido = render_a_pdf(
            "ventas/garantia.html",
            {
                "venta": venta,
                "lineas": lineas,
                "fecha_venta": fecha_local(venta.fecha_hora),
                # Se lee del modulo en cada peticion, no al importar:
                # asi cambiarlo no exige tocar esta vista.
                "condiciones": modulo_garantia.CONDICIONES_DE_GARANTIA.strip(),
                # Fecha y autor los pone el SERVIDOR (RN-VEN-15).
                "generado_en": timezone.localtime(),
                "generado_por": request.user.nombre_completo,
                "logo": imagen_incrustada("img/logo-pcsolution.png"),
            },
        )

        respuesta = HttpResponse(contenido, content_type="application/pdf")
        respuesta["Content-Disposition"] = f'inline; filename="garantia-venta-{venta.pk}.pdf"'
        return respuesta
