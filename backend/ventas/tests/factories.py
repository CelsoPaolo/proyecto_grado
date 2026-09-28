"""Fabricas de ventas para las pruebas."""

import factory

from catalogo.tests.factories import ProductoFactory
from usuarios.tests.factories import VendedorFactory
from ventas.models import DetalleVenta, EstadoVenta, Venta


class VentaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Venta

    cliente_nombre = factory.Sequence(lambda n: f"Cliente {n}")
    cliente_telefono = "70012345"
    usuario = factory.SubFactory(VendedorFactory)
    estado = EstadoVenta.CONFIRMADA
    total = 0


class DetalleVentaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DetalleVenta

    venta = factory.SubFactory(VentaFactory)
    producto = factory.SubFactory(ProductoFactory)
    producto_nombre = factory.LazyAttribute(lambda o: o.producto.nombre)
    precio_unitario = factory.LazyAttribute(lambda o: o.producto.precio)
    cantidad = 1
    subtotal = factory.LazyAttribute(lambda o: o.precio_unitario * o.cantidad)
