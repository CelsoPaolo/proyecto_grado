"""Fabricas de catalogo para las pruebas."""

import factory

from catalogo.models import Categoria, Producto


class CategoriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Categoria

    nombre = factory.Sequence(lambda n: f"Categoría {n}")
    descripcion = "Descripción de prueba"


class ProductoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Producto

    nombre = factory.Sequence(lambda n: f"Producto {n}")
    descripcion = "Descripción de prueba"
    precio = 100
    stock = 10
    categoria = factory.SubFactory(CategoriaFactory)
    activo = True
