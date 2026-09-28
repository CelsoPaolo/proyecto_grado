"""Reglas de negocio de la configuracion del sistema."""

from django.db import transaction

from configuracion.models import ConfiguracionSistema


def obtener_umbral_stock_bajo():
    """Umbral global vigente (RN-CAT-07, decision PA-01).

    Un unico valor para todo el catalogo, no por producto ni por
    categoria.
    """
    return ConfiguracionSistema.obtener().umbral_stock_bajo


@transaction.atomic
def actualizar_umbral(*, umbral, ejecutor):
    """CU-CAT-06 (RF-52).

    Surte efecto de inmediato y no altera ningun dato historico: el
    umbral solo decide como se MUESTRA el catalogo, nunca modifica
    existencias ni ventas (RN-CAT-07).
    """
    configuracion = ConfiguracionSistema.obtener()
    configuracion.umbral_stock_bajo = umbral
    configuracion.actualizado_por = ejecutor
    configuracion.save(
        update_fields=["umbral_stock_bajo", "actualizado_por", "actualizado_en"]
    )
    return configuracion
