"""Fabricas de datos para las pruebas (factory-boy)."""

import factory

from usuarios.models import Rol, Usuario


class UsuarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"usuario{n}")
    nombre_completo = factory.Sequence(lambda n: f"Persona {n}")
    rol = Rol.VENTAS
    is_active = True

    @factory.post_generation
    def password(obj, create, valor, **kwargs):
        obj.set_password(valor or "ClaveSegura123")
        if create:
            obj.save()


class AdministradorFactory(UsuarioFactory):
    rol = Rol.ADMINISTRADOR


class VendedorFactory(UsuarioFactory):
    rol = Rol.VENTAS


class TecnicoFactory(UsuarioFactory):
    rol = Rol.SERVICIOS
