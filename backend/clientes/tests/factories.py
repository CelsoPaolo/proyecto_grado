"""Fabricas de clientes para las pruebas."""

import factory

from clientes.models import Cliente
from usuarios.tests.factories import VendedorFactory


class ClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cliente

    nombre = factory.Sequence(lambda n: f"Cliente {n}")
    telefono = factory.Sequence(lambda n: f"7{n:07d}")
    creado_por = factory.SubFactory(VendedorFactory)
    actualizado_por = factory.SelfAttribute("creado_por")
