"""Errores de negocio y formato uniforme de respuesta.

Toda respuesta de error del sistema tiene la misma forma
(plan.md seccion 4.3), de modo que el frontend tenga un unico camino de
tratamiento:

    {
      "codigo":  "STOCK_INSUFICIENTE",
      "detalle": "No hay existencias suficientes para confirmar la venta.",
      "errores": { ... }          # opcional
    }

Para errores de validacion de campo, `errores` es el diccionario de DRF
({"precio": ["El precio debe ser mayor que cero."]}), que el frontend
mapea directamente al campo correspondiente del formulario (RNF-15).

RNF-06: los mensajes son genericos donde deben serlo y nunca exponen
trazas ni detalles internos del sistema.

RNF-05: toda entrada se valida en el SERVIDOR. Las comprobaciones
del formulario son comodidad para quien escribe, no una garantia:
este manejador existe porque el servidor rechaza por su cuenta lo
que la interfaz podria haber dejado pasar.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as manejador_de_drf

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Catalogo de codigos (plan.md seccion 4.3)
# ─────────────────────────────────────────────────────────────────────
class Codigo:
    CREDENCIALES_INVALIDAS = "CREDENCIALES_INVALIDAS"
    CUENTA_BLOQUEADA = "CUENTA_BLOQUEADA"
    PERMISO_INSUFICIENTE = "PERMISO_INSUFICIENTE"
    NO_AUTENTICADO = "NO_AUTENTICADO"
    NO_ENCONTRADO = "NO_ENCONTRADO"
    VALIDACION = "VALIDACION"
    STOCK_INSUFICIENTE = "STOCK_INSUFICIENTE"
    VENTA_YA_ANULADA = "VENTA_YA_ANULADA"
    TRANSICION_INVALIDA = "TRANSICION_INVALIDA"
    TECNICO_REQUERIDO = "TECNICO_REQUERIDO"
    OBSERVACIONES_REQUERIDAS = "OBSERVACIONES_REQUERIDAS"
    MONTO_REQUERIDO = "MONTO_REQUERIDO"
    SOLICITUD_CERRADA = "SOLICITUD_CERRADA"
    ULTIMO_ADMINISTRADOR = "ULTIMO_ADMINISTRADOR"
    AUTOMODIFICACION_PROHIBIDA = "AUTOMODIFICACION_PROHIBIDA"
    CATEGORIA_CON_PRODUCTOS = "CATEGORIA_CON_PRODUCTOS"
    ERROR_AL_GENERAR_PDF = "ERROR_AL_GENERAR_PDF"
    ERROR_INTERNO = "ERROR_INTERNO"


class ErrorDeNegocio(APIException):
    """Base de las reglas de negocio de spec.md seccion 6.

    Cada regla que puede rechazar una operacion se expresa como una
    subclase con su codigo, su mensaje y su codigo HTTP. Se lanzan desde
    la capa de servicios, nunca desde las vistas.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    codigo = Codigo.VALIDACION
    default_detail = "La operación no pudo completarse."

    def __init__(self, detalle=None, errores=None):
        self.detalle = detalle or self.default_detail
        self.errores = errores
        super().__init__(self.detalle)


def respuesta_de_error(codigo, detalle, errores=None, estado=400):
    """Construye el cuerpo uniforme de error."""
    cuerpo = {"codigo": codigo, "detalle": detalle}
    if errores is not None:
        cuerpo["errores"] = errores
    return Response(cuerpo, status=estado)


def _mensaje_plano(detalle):
    """Reduce el detalle de DRF a una frase legible para el usuario."""
    if isinstance(detalle, str):
        return detalle
    if isinstance(detalle, list) and detalle:
        return _mensaje_plano(detalle[0])
    if isinstance(detalle, dict):
        for valor in detalle.values():
            return _mensaje_plano(valor)
    return "La operación no pudo completarse."


def manejador_de_errores(exc, context):
    """Normaliza TODA respuesta de error a la misma forma.

    Se registra en REST_FRAMEWORK['EXCEPTION_HANDLER'].
    """
    # 1) Reglas de negocio propias: ya traen codigo y mensaje.
    if isinstance(exc, ErrorDeNegocio):
        return respuesta_de_error(
            exc.codigo, exc.detalle, exc.errores, exc.status_code
        )

    # 2) Excepciones de Django que DRF no traduce por si mismo.
    if isinstance(exc, Http404):
        exc = None
    elif isinstance(exc, PermissionDenied):
        return respuesta_de_error(
            Codigo.PERMISO_INSUFICIENTE,
            "No tiene permiso para realizar esta operación.",
            estado=status.HTTP_403_FORBIDDEN,
        )

    if exc is None:
        return respuesta_de_error(
            Codigo.NO_ENCONTRADO,
            "El recurso solicitado no existe.",
            estado=status.HTTP_404_NOT_FOUND,
        )

    respuesta = manejador_de_drf(exc, context)

    # 3) Nada que DRF sepa traducir: error no controlado.
    #    RNF-06: se registra completo en el log del servidor, pero al
    #    cliente solo le llega un mensaje generico, sin traza.
    if respuesta is None:
        if isinstance(exc, IntegrityError):
            logger.exception("Violacion de integridad en la base de datos")
            return respuesta_de_error(
                Codigo.VALIDACION,
                "La operación viola una restricción de los datos.",
                estado=status.HTTP_409_CONFLICT,
            )
        logger.exception("Error no controlado")
        return respuesta_de_error(
            Codigo.ERROR_INTERNO,
            "Ocurrió un error inesperado. Inténtelo nuevamente.",
            estado=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 4) Excepciones de DRF: se reempaquetan al formato uniforme.
    detalle_original = respuesta.data
    codigo_http = respuesta.status_code

    if codigo_http == status.HTTP_401_UNAUTHORIZED:
        return respuesta_de_error(
            Codigo.NO_AUTENTICADO,
            "Debe iniciar sesión para realizar esta operación.",
            estado=codigo_http,
        )
    if codigo_http == status.HTTP_403_FORBIDDEN:
        return respuesta_de_error(
            Codigo.PERMISO_INSUFICIENTE,
            "No tiene permiso para realizar esta operación.",
            estado=codigo_http,
        )
    if codigo_http == status.HTTP_404_NOT_FOUND:
        return respuesta_de_error(
            Codigo.NO_ENCONTRADO,
            "El recurso solicitado no existe.",
            estado=codigo_http,
        )

    # Validacion: el diccionario de DRF va tal cual en `errores`, para
    # que el frontend lo mapee campo por campo (RNF-15).
    if isinstance(detalle_original, dict) and "detail" not in detalle_original:
        return respuesta_de_error(
            Codigo.VALIDACION,
            "Revise los datos ingresados.",
            errores=detalle_original,
            estado=codigo_http,
        )

    if isinstance(detalle_original, dict):
        mensaje = _mensaje_plano(detalle_original.get("detail"))
    else:
        mensaje = _mensaje_plano(detalle_original)

    return respuesta_de_error(Codigo.VALIDACION, mensaje, estado=codigo_http)


# ─────────────────────────────────────────────────────────────────────
# Reglas transversales de acceso (spec.md seccion 6.1)
# ─────────────────────────────────────────────────────────────────────
class CredencialesInvalidas(ErrorDeNegocio):
    """CU-AUT-01: mismo mensaje exista o no el usuario (RNF-06)."""

    status_code = status.HTTP_401_UNAUTHORIZED
    codigo = Codigo.CREDENCIALES_INVALIDAS
    default_detail = "Usuario o contraseña incorrectos."


class CuentaBloqueada(ErrorDeNegocio):
    """RN-ACC-05: una cuenta bloqueada no accede por ninguna via."""

    status_code = status.HTTP_403_FORBIDDEN
    codigo = Codigo.CUENTA_BLOQUEADA
    default_detail = "Esta cuenta está inhabilitada. Consulte al administrador."


class PermisoInsuficiente(ErrorDeNegocio):
    """RN-ACC-04: el rol no alcanza para esta operacion."""

    status_code = status.HTTP_403_FORBIDDEN
    codigo = Codigo.PERMISO_INSUFICIENTE
    default_detail = "No tiene permiso para realizar esta operación."


class ErrorAlGenerarPdf(ErrorDeNegocio):
    """RF-67: la plantilla del informe no pudo renderizarse.

    No es un error del usuario: no hay nada que pueda corregir en su
    peticion. Es un 500, pero pasa por el formato uniforme de error
    para que el frontend lo trate por el mismo camino que los demas y
    para no devolver una traza (RNF-06).
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    codigo = Codigo.ERROR_AL_GENERAR_PDF
    default_detail = "No se pudo generar el informe en PDF."
