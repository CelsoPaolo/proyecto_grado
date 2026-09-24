"""Serializers de autenticacion y de cuentas de usuario."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ValidationErrorDjango
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from core.exceptions import CredencialesInvalidas, CuentaBloqueada
from usuarios.models import Rol, Usuario


class UsuarioResumenSerializer(serializers.ModelSerializer):
    """Datos del usuario que viajan junto al token y en /auth/me."""

    rol_display = serializers.CharField(source="get_rol_display", read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "username", "nombre_completo", "rol", "rol_display"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    """CU-AUT-01 — Iniciar sesion.

    No hereda de TokenObtainPairSerializer porque su mensaje de error
    por defecto no distingue lo que aqui hace falta distinguir:
    RNF-06 exige el mismo mensaje generico para usuario inexistente y
    contrasena incorrecta, pero CU-AUT-01 pide informar explicitamente
    cuando la cuenta esta bloqueada, que es informacion que el
    administrador ya le dio al titular.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        username = attrs["username"]
        password = attrs["password"]

        # authenticate() devuelve None tanto si el usuario no existe
        # como si la contrasena es incorrecta, y ademas si la cuenta
        # esta inactiva. Hay que separar ese ultimo caso.
        usuario = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        )

        if usuario is None:
            # Se distingue "bloqueada" solo si las credenciales eran
            # correctas: de lo contrario, probar un usuario bloqueado
            # con cualquier contrasena revelaria que esa cuenta existe.
            candidato = Usuario.objects.filter(username=username).first()
            if (
                candidato is not None
                and not candidato.is_active
                and candidato.check_password(password)
            ):
                raise CuentaBloqueada()
            raise CredencialesInvalidas()

        attrs["usuario"] = usuario
        return attrs

    def crear_tokens(self, usuario):
        refresh = TokenObtainPairSerializer.get_token(usuario)
        # El rol viaja en el token SOLO como dato informativo para la
        # interfaz. Ninguna clase de permiso lo lee (plan.md 1.3,
        # via 4): la autorizacion siempre consulta la base.
        refresh["rol"] = usuario.rol
        refresh["nombre_completo"] = usuario.nombre_completo
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "usuario": UsuarioResumenSerializer(usuario).data,
        }


class CambiarPasswordPropiaSerializer(serializers.Serializer):
    """CU-AUT-03 — Cambiar la propia contrasena (RF-05)."""

    password_actual = serializers.CharField(write_only=True)
    password_nueva = serializers.CharField(write_only=True)

    def validate_password_actual(self, valor):
        usuario = self.context["request"].user
        if not usuario.check_password(valor):
            raise serializers.ValidationError("La contrasena actual no es correcta.")
        return valor

    def validate_password_nueva(self, valor):
        usuario = self.context["request"].user
        try:
            validate_password(valor, user=usuario)
        except ValidationErrorDjango as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return valor

    def save(self, **kwargs):
        usuario = self.context["request"].user
        usuario.set_password(self.validated_data["password_nueva"])
        usuario.save(update_fields=["password"])
        return usuario


class RolChoiceField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(choices=Rol.choices, **kwargs)
