"""Endpoints del catalogo (/api/v1/).

Gestion exclusiva del Administrador; consulta tambien para el
Encargado de Ventas (spec.md matriz 4.4).
"""

from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from catalogo.codigos import normalizar_codigo_fabrica
from catalogo.models import Categoria, Producto
from catalogo.serializers import CategoriaSerializer, ProductoSerializer
from catalogo.services import (
    crear_producto,
    eliminar_categoria,
    retirar_producto,
    umbral_stock_bajo,
)
from core.permissions import EsAdministrador, PuedeVender
from inventario.serializers import (
    AjustarExistenciasSerializer,
    MovimientoStockSerializer,
)
from inventario.services import ajustar_existencias
from inventario.views import movimientos_para_listar


class CategoriaViewSet(viewsets.ModelViewSet):
    """CU-CAT-01 (RF-07, RF-08).

    Lectura para quien puede vender; escritura solo para el
    Administrador.
    """

    serializer_class = CategoriaSerializer

    def get_queryset(self):
        # El order_by explicito no es redundante: annotate() con
        # agregacion descarta el orden por defecto del Meta, y una
        # consulta sin orden hace que la paginacion repita o salte
        # filas entre paginas (RNF-18).
        return Categoria.objects.annotate(
            cantidad_productos=Count("productos")
        ).order_by("nombre")

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [PuedeVender()]
        return [EsAdministrador()]

    def destroy(self, request, *args, **kwargs):
        """RF-08: 409 si la categoría tiene productos."""
        eliminar_categoria(categoria=self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """CU-CAT-02 a CU-CAT-05 (RF-09 a RF-14, RF-53)."""

    serializer_class = ProductoSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["categoria", "activo"]
    search_fields = ["nombre", "descripcion"]

    def get_permissions(self):
        # Todo lo que no es consultar el catalogo es del Administrador,
        # incluidos el ajuste y el historial de movimientos (RN-MOV-06).
        if self.action in ("list", "retrieve"):
            return [PuedeVender()]
        return [EsAdministrador()]

    def get_queryset(self):
        """RF-13 y RF-53.

        Por defecto se listan solo los productos vigentes: uno retirado
        (CU-CAT-04) no debe aparecer en el catalogo de trabajo diario.
        Con ?activo=false el Administrador puede revisarlos.
        """
        consulta = Producto.objects.select_related("categoria")

        # El filtro por defecto se aplica SOLO al listado. Aplicarlo
        # tambien al detalle haria que un producto retirado respondiera
        # 404, y su ficha debe seguir siendo consultable: el historial
        # de ventas lo referencia (RN-VEN-04), y editarlo o restituirlo
        # dejaria de ser posible.
        if self.action == "list" and "activo" not in self.request.query_params:
            consulta = consulta.filter(activo=True)

        if self.request.query_params.get("stock_bajo") == "true":
            consulta = consulta.filter(stock__lte=umbral_stock_bajo())

        # RF-70 — coincidencia EXACTA con el codigo interno o con el de
        # fabrica, nunca parcial: un lector que lea mal un digito no debe
        # encontrar otro producto (RN-VEN-17). Un codigo incompleto o
        # inexistente da una lista vacia, no un error. Como el de fabrica
        # no puede tener la forma de un interno (RN-CAT-11), una lectura
        # encuentra como mucho un producto.
        if (codigo := self.request.query_params.get("codigo")) is not None:
            codigo = normalizar_codigo_fabrica(codigo)
            if not codigo:
                # Sin esto, codigo_fabrica="" coincidiria con todos los
                # productos que no tienen codigo de fabrica.
                return consulta.none()
            consulta = consulta.filter(Q(codigo=codigo) | Q(codigo_fabrica=codigo))

        return consulta

    def perform_create(self, serializer):
        """CU-CAT-02 — el alta pasa por el servicio, no por el serializer.

        El serializer solo valida; crear el producto y su movimiento de
        alta, en una sola transaccion, es una regla de negocio y vive en
        catalogo.services (plan.md 2.2).
        """
        serializer.instance = crear_producto(
            usuario=self.request.user, **serializer.validated_data
        )

    def destroy(self, request, *args, **kwargs):
        """RF-11 - borrado suave, no eliminacion.

        El verbo es DELETE porque para el usuario la accion es
        "eliminar del catalogo", pero la fila permanece: es lo que
        mantiene legible el historial de ventas (RN-VEN-04).
        """
        producto = retirar_producto(producto=self.get_object())
        return Response(ProductoSerializer(producto).data)

    @action(detail=True, methods=["post"], url_path="ajustar-existencias")
    def ajustar_existencias(self, request, pk=None):
        """POST /productos/{id}/ajustar-existencias - CU-CAT-07 (RF-73).

        Sustituye a editar el stock con PATCH, que ahora responde 400
        (RN-CAT-10). La diferencia NO se calcula aqui ni en la interfaz:
        la calcula el servicio contra la fila ya bloqueada (plan.md 6.5).

        Vale tambien para un producto retirado (CU-CAT-07): sus unidades
        siguen fisicamente en el almacen y pueden contarse.
        """
        producto = self.get_object()

        entrada = AjustarExistenciasSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        movimiento = ajustar_existencias(
            producto_id=producto.pk,
            cantidad_real=entrada.validated_data["cantidad_real"],
            motivo=entrada.validated_data["motivo"],
            usuario=request.user,
        )

        movimiento = movimientos_para_listar().get(pk=movimiento.pk)
        return Response(
            MovimientoStockSerializer(movimiento).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get"])
    def movimientos(self, request, pk=None):
        """GET /productos/{id}/movimientos - CU-CAT-08 (RF-83).

        El historial del producto, del mas reciente al mas antiguo y
        paginado (RNF-18): un producto de mucha rotacion acumula miles.
        """
        producto = self.get_object()
        consulta = movimientos_para_listar().filter(producto=producto)

        pagina = self.paginate_queryset(consulta)
        return self.get_paginated_response(
            MovimientoStockSerializer(pagina, many=True).data
        )
