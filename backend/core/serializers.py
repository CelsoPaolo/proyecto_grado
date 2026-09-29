"""Serializers compartidos entre modulos."""

from rest_framework import serializers


class UsuarioBreveSerializer(serializers.Serializer):
    """Identificacion minima de un usuario dentro de otro recurso.

    Vive en core porque ventas y servicios la necesitan igual. Tenerla
    duplicada hacia que el esquema de la API generara dos componentes
    con el mismo nombre y distinta identidad, lo que producia una
    documentacion incorrecta (T-7.4).
    """

    id = serializers.IntegerField(read_only=True)
    nombre_completo = serializers.CharField(read_only=True)
