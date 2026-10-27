"""Busqueda sin tildes (RF-98, RN-CAT-12, plan.md 3.6 y 7.14).

`SearchFilter` de DRF construye `<campo>__icontains` a partir de
`search_fields`, pero no admite un *transform* como `__unaccent` en
medio: al calcular si hace falta `distinct()` lo trata como un campo
del modelo y falla. Este filtro conserva todo lo demas de
`SearchFilter` —el parametro `?search=`, la division en terminos y el
esquema OpenAPI— y solo cambia la comparacion.

`__unaccent` lo aporta `django.contrib.postgres` y se aplica a los DOS
lados: quita las tildes del valor guardado y del texto buscado, de modo
que «camara», «cámara» y «CAMARA» encuentran «Cámara».
"""

from functools import reduce
from operator import or_

from django.db.models import Q
from rest_framework.filters import SearchFilter


class BusquedaSinTildes(SearchFilter):
    """`?search=` sin distinguir tildes ni mayusculas.

    Cada termino debe aparecer en alguno de los campos, igual que en
    `SearchFilter`: «camara bullet» exige las dos palabras.
    """

    def filter_queryset(self, request, queryset, view):
        campos = self.get_search_fields(view, request)
        terminos = self.get_search_terms(request)
        if not campos or not terminos:
            return queryset
        for termino in terminos:
            queryset = queryset.filter(
                reduce(or_, (Q(**{f"{campo}__unaccent__icontains": termino}) for campo in campos))
            )
        return queryset
