"""Serializers de autenticacion y de cuentas de usuario."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ValidationErrorDjango
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

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
            raise serializers.ValidationError("La contraseña actual no es correcta.")
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


class TokenRefreshSeguroSerializer(TokenRefreshSerializer):
    """Via 2 de plan.md seccion 1.3 — el hueco real de SimpleJWT.

    El serializer de refresco por defecto valida la **firma y la
    caducidad** del token, pero no carga al usuario ni comprueba su
    estado. Sin esto, una cuenta bloqueada podria seguir renovando su
    access token indefinidamente mientras su refresh siguiera vigente,
    y RN-ACC-05 quedaria incumplido por la puerta de atras.
    """

    def validate(self, attrs):
        # Se comprueba al usuario ANTES de delegar en super(), y se lee
        # el token con UntypedToken en lugar de RefreshToken por dos
        # motivos, ambos deliberados:
        #
        #  1. RefreshToken comprueba la lista negra al construirse. Como
        #     bloquear una cuenta ya deja sus refresh en esa lista
        #     (via 3), usarlo aqui haria que la via 3 se adelantara
        #     siempre a la via 2 y el titular recibiria un 401 generico
        #     en lugar de saber que su cuenta fue inhabilitada.
        #  2. Las dos vias deben ser INDEPENDIENTES: esta debe seguir
        #     cerrando el paso aunque la lista negra no se hubiera
        #     actualizado, por ejemplo si la cuenta se desactivara
        #     desde el panel de administracion de Django.
        #
        # UntypedToken valida firma y caducidad, que es lo que hace
        # falta para saber de quien es el token; la validacion completa
        # del refresco la sigue haciendo super().
        try:
            token = UntypedToken(attrs["refresh"])
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc

        usuario = Usuario.objects.filter(
            pk=token.get(api_settings.USER_ID_CLAIM)
        ).first()

        if usuario is None or not usuario.is_active:
            raise CuentaBloqueada()

        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer):
    """CU-AUT-02 — Cerrar sesion (RF-04).

    Anade el refresh token a la lista negra. Sin este paso, cerrar
    sesion solo borraria el token del navegador: seguiria siendo
    valido para cualquiera que lo hubiera copiado.
    """

    refresh = serializers.CharField()

    def validate_refresh(self, valor):
        try:
            self.token = RefreshToken(valor)
        except TokenError as exc:
            raise serializers.ValidationError("El token no es válido.") from exc
        return valor

    def save(self, **kwargs):
        self.token.blacklist()


# ─────────────────────────────────────────────────────────────────────
# Gestion de cuentas por el Administrador (CU-USU-01 a CU-USU-05)
# ─────────────────────────────────────────────────────────────────────
class UsuarioSerializer(serializers.ModelSerializer):
    """Lectura de una cuenta (RF-43).

    `password` no figura: RNF-03 exige que no aparezca en ninguna
    respuesta.
    """

    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    bloqueado = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "nombre_completo",
            "rol",
            "rol_display",
            "is_active",
            "bloqueado",
            "date_joined",
            "last_login",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField)
    def get_bloqueado(self, obj):
        """Expone el bloqueo con el nombre del dominio.

        La interfaz habla de cuentas bloqueadas, no de cuentas
        inactivas: `is_active` es el mecanismo, `bloqueado` es el
        concepto de spec.md.
        """
        return not obj.is_active


class CrearUsuarioSerializer(serializers.Serializer):
    """CU-USU-01 (RF-39, RF-47)."""

    username = serializers.CharField(max_length=150)
    nombre_completo = serializers.CharField(max_length=150)
    rol = RolChoiceField()
    password = serializers.CharField(write_only=True)

    def validate_username(self, valor):
        if Usuario.objects.filter(username__iexact=valor).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con ese identificador de acceso."
            )
        return valor

    def validate_password(self, valor):
        try:
            validate_password(valor)
        except ValidationErrorDjango as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return valor


class ActualizarUsuarioSerializer(serializers.Serializer):
    """CU-USU-02 (RF-40)."""

    nombre_completo = serializers.CharField(max_length=150, required=False)
    rol = RolChoiceField(required=False)


class RestablecerPasswordSerializer(serializers.Serializer):
    """CU-USU-04 (RF-42)."""

    password_nueva = serializers.CharField(write_only=True)

    def validate_password_nueva(self, valor):
        try:
            validate_password(valor)
        except ValidationErrorDjango as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return valor
