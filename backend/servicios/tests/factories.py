"""Fabricas de servicios para las pruebas."""

import factory

from servicios.models import (
    EstadoSolicitud,
    MODALIDAD_POR_TIPO,
    SolicitudServicio,
    TipoServicio,
)
from usuarios.tests.factories import TecnicoFactory


class SolicitudFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SolicitudServicio

    cliente_nombre = factory.Sequence(lambda n: f"Cliente {n}")
    cliente_telefono = "70012345"
    tipo = TipoServicio.MANTENIMIENTO
    modalidad = factory.LazyAttribute(lambda o: MODALIDAD_POR_TIPO[o.tipo])
    direccion = factory.LazyAttribute(
        lambda o: "Calle Falsa 123" if MODALIDAD_POR_TIPO[o.tipo] == "DOMICILIO" else ""
    )
    descripcion = "El equipo no enciende."
    estado = EstadoSolicitud.REGISTRADA
    registrada_por = factory.SubFactory(TecnicoFactory)
