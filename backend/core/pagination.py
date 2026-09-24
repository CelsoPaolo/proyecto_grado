from rest_framework.pagination import PageNumberPagination


class PaginacionEstandar(PageNumberPagination):
    """Paginacion comun a todos los listados (RNF-18).

    El cliente puede pedir otro tamano con ?page_size=, con un techo de
    100 para que una peticion no pueda forzar al servidor a serializar
    el historial completo.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
