"""Endpoints del libro de movimientos (/api/v1/movimientos-stock).

Solo existe el listado: NO hay POST, PUT, PATCH ni DELETE. **La
ausencia de esos verbos es la implementacion de RNF-25** en la API,
igual que en las ventas (RN-VEN-06). Los movimientos los crean
unicamente los servicios de alta, venta, anulacion y ajuste.

El historial de un producto y el ajuste cuelgan del producto
(/productos/{id}/movimientos y /productos/{id}/ajustar-existencias) y
viven en catalogo.views.
"""

from django.utils.dateparse import parse_date
from rest_framework import mixins, viewsets

from core.exceptions import ErrorDeNegocio
from core.permissions import EsAdministrador
from inventario.models import MovimientoStock, TipoMovimiento
from inventario.serializers import MovimientoStockSerializer


def movimientos_para_listar():
    """Consulta base de los dos listados del libro.

    El orden explicito, con el id como desempate, evita que la
    paginacion repita o salte filas cuando varios movimientos comparten
    instante, que es lo normal en una venta de varios productos (RNF-18).
    """
    return MovimientoStock.objects.select_related("producto", "usuario").order_by(
        "-fecha_hora", "-id"
    )


def _filtro_invalido(campo, mensaje):
    return ErrorDeNegocio(detalle=mensaje, errores={campo: [mensaje]})


class MovimientoStockViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """CU-CAT-08 (RF-82). Solo el Administrador (RN-MOV-06)."""

    permission_classes = [EsAdministrador]
    serializer_class = MovimientoStockSerializer
    # Respaldo para la introspeccion del esquema: manda get_queryset().
    queryset = MovimientoStock.objects.none()

    def get_queryset(self):
        """Filtros combinables: producto, tipo y rango de fechas.

        Un filtro mal escrito responde 400 en lugar de ignorarse: en una
        auditoria, «no hay movimientos» porque el filtro no se aplico
        seria una respuesta falsa.
        """
        consulta = movimientos_para_listar()
        parametros = self.request.query_params

        if producto := parametros.get("producto"):
            # isascii(): isdigit() tambien acepta '²' y otras cifras que
            # int() no convierte; el limite de longitud evita desbordar
            # el bigint de la base, que responderia 500 en vez de 400.
            if not (producto.isascii() and producto.isdigit() and len(producto) <= 18):
                raise _filtro_invalido("producto", "El producto indicado no es válido.")
            consulta = consulta.filter(producto_id=int(producto))

        if tipo := parametros.get("tipo"):
            if tipo not in TipoMovimiento.values:
                raise _filtro_invalido("tipo", "El tipo de movimiento indicado no existe.")
            consulta = consulta.filter(tipo=tipo)

        for campo, operador in (("desde", "gte"), ("hasta", "lte")):
            if texto := parametros.get(campo):
                fecha = _fecha(texto)
                if fecha is None:
                    raise _filtro_invalido(
                        campo, "La fecha debe tener el formato AAAA-MM-DD."
                    )
                # __date convierte a la zona horaria del sistema: un
                # movimiento de las 23:30 en La Paz es de ese dia, aunque
                # en UTC ya sea el siguiente.
                consulta = consulta.filter(**{f"fecha_hora__date__{operador}": fecha})

        return consulta


def _fecha(texto):
    try:
        return parse_date(texto)
    except ValueError:  # formato correcto pero fecha imposible: 2026-02-30
        return None
