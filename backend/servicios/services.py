"""Reglas de negocio de los servicios tecnicos.

La maquina de estados de RN-SER-02 vive declarada en un solo lugar
(TRANSICIONES) y las guardas se comprueban en un solo sitio. Tenerla
repartida entre vistas seria imposible de verificar de forma
exhaustiva, que es justamente lo que T-5.3 exige.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import status

from core.exceptions import Codigo, ErrorDeNegocio
from servicios.models import (
    ESTADOS_TERMINALES,
    EstadoSolicitud,
    EventoSolicitud,
    MODALIDAD_POR_TIPO,
    SolicitudServicio,
    TipoEvento,
)


# ─────────────────────────────────────────────────────────────────────
# Errores del modulo
# ─────────────────────────────────────────────────────────────────────
class TransicionInvalida(ErrorDeNegocio):
    """RN-SER-02."""

    status_code = status.HTTP_409_CONFLICT
    codigo = Codigo.TRANSICION_INVALIDA
    default_detail = "La solicitud no puede pasar a ese estado."


class SolicitudCerrada(ErrorDeNegocio):
    """RN-SER-12 y RN-SER-16: el cierre es inmutable."""

    status_code = status.HTTP_409_CONFLICT
    codigo = Codigo.SOLICITUD_CERRADA
    default_detail = (
        "La solicitud ya está cerrada y no admite cambios. "
        "Si el cierre fue equivocado, registre una solicitud nueva."
    )


class ObservacionesRequeridas(ErrorDeNegocio):
    """RN-SER-03."""

    codigo = Codigo.OBSERVACIONES_REQUERIDAS
    default_detail = (
        "Debe registrar las observaciones del trabajo realizado para "
        "finalizar el servicio."
    )


class MontoRequerido(ErrorDeNegocio):
    """RN-SER-13 — la guarda que separa cotizar de cerrar.

    Responde 409 y no 400 porque no es un dato que falte en la
    peticion: es un paso previo del proceso que todavia no ocurrio, y
    que ademas debe hacer OTRA persona. El mensaje lo dice, para que
    quien cierra sepa a quien acudir.
    """

    status_code = status.HTTP_409_CONFLICT
    codigo = Codigo.MONTO_REQUERIDO
    default_detail = (
        "No se puede finalizar un servicio sin monto. El administrador "
        "debe cotizarlo primero."
    )


# ─────────────────────────────────────────────────────────────────────
# Maquina de estados (RN-SER-02)
# ─────────────────────────────────────────────────────────────────────
#: Unica fuente de verdad de las transiciones. Lo que no este aqui, no
#: se permite: asi la prueba puede recorrer todas las combinaciones de
#: origen x destino y comprobarlas de forma exhaustiva.
TRANSICIONES = {
    EstadoSolicitud.REGISTRADA: {
        EstadoSolicitud.EN_ATENCION,
        EstadoSolicitud.CANCELADA,
    },
    EstadoSolicitud.EN_ATENCION: {
        EstadoSolicitud.FINALIZADA,
        EstadoSolicitud.CANCELADA,
    },
    # Terminales: sin salida. No se permite retroceder de estado.
    EstadoSolicitud.FINALIZADA: set(),
    EstadoSolicitud.CANCELADA: set(),
}


def transicion_permitida(origen, destino):
    return destino in TRANSICIONES.get(origen, set())


def _validar_transicion(solicitud, destino):
    if not transicion_permitida(solicitud.estado, destino):
        if solicitud.estado in ESTADOS_TERMINALES:
            raise SolicitudCerrada()
        raise TransicionInvalida(
            f"Una solicitud {solicitud.get_estado_display().lower()} no puede "
            f"pasar a {EstadoSolicitud(destino).label.lower()}."
        )


def _validar_abierta(solicitud):
    """RN-SER-12: monto y tecnico solo mientras siga abierta."""
    if not solicitud.esta_abierta:
        raise SolicitudCerrada()


def _registrar_evento(solicitud, *, tipo, usuario, nota="", anterior="", nuevo=""):
    """Anade una linea al historial (RN-SER-06). Solo inserta."""
    return EventoSolicitud.objects.create(
        solicitud=solicitud,
        tipo_evento=tipo,
        usuario=usuario,
        nota=nota,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
    )


# ─────────────────────────────────────────────────────────────────────
# Operaciones
# ─────────────────────────────────────────────────────────────────────
@transaction.atomic
def registrar_solicitud(
    *, usuario, cliente_nombre, cliente_telefono, tipo, descripcion, direccion=""
):
    """CU-SER-01 (RF-28, RF-29, RF-30).

    La modalidad la deriva el SISTEMA del tipo (RN-SER-01); el usuario
    no la elige. De ahi sale si la direccion es obligatoria.
    """
    modalidad = MODALIDAD_POR_TIPO[tipo]

    solicitud = SolicitudServicio.objects.create(
        cliente_nombre=cliente_nombre.strip(),
        cliente_telefono=cliente_telefono.strip(),
        tipo=tipo,
        modalidad=modalidad,
        direccion=direccion.strip(),
        descripcion=descripcion.strip(),
        estado=EstadoSolicitud.REGISTRADA,
        registrada_por=usuario,
    )

    _registrar_evento(
        solicitud,
        tipo=TipoEvento.CAMBIO_ESTADO,
        usuario=usuario,
        nuevo=EstadoSolicitud.REGISTRADA,
        nota="Solicitud registrada.",
    )
    return solicitud


@transaction.atomic
def cotizar_solicitud(*, solicitud, usuario, monto=None, tecnico=None):
    """CU-SER-06 (RF-56, RF-58, RF-59) — solo el Administrador.

    El permiso lo garantiza la vista; aqui se cuidan las reglas: solo
    mientras la solicitud siga abierta (RN-SER-12) y con monto no
    negativo (RN-SER-17).

    El monto puede reajustarse: cotizar es una estimacion tras la
    revision y el trabajo puede resultar distinto (RN-SER-16).
    """
    _validar_abierta(solicitud)

    campos = []

    if monto is not None:
        anterior = solicitud.monto_cobrado
        solicitud.monto_cobrado = Decimal(monto)
        solicitud.cotizada_por = usuario
        solicitud.fecha_cotizacion = timezone.now()
        campos += ["monto_cobrado", "cotizada_por", "fecha_cotizacion"]

        nota = (
            f"Monto cotizado en Bs {solicitud.monto_cobrado}."
            if anterior is None
            else f"Monto ajustado de Bs {anterior} a Bs {solicitud.monto_cobrado}."
        )
        _registrar_evento(
            solicitud, tipo=TipoEvento.COTIZACION, usuario=usuario, nota=nota
        )

    if tecnico is not None:
        solicitud.tecnico = tecnico.strip()
        campos.append("tecnico")
        _registrar_evento(
            solicitud,
            tipo=TipoEvento.TECNICO,
            usuario=usuario,
            nota=(
                f"Técnico anotado: {solicitud.tecnico}."
                if solicitud.tecnico
                else "Se quitó la anotación de técnico."
            ),
        )

    if campos:
        solicitud.save(update_fields=campos)

    return solicitud


@transaction.atomic
def iniciar_atencion(*, solicitud, usuario):
    """CU-SER-02 (RF-31).

    Sin guardas: el trabajo puede empezar antes de que el Administrador
    lo cotice, que es el orden que describe PA-03 (primero se revisa,
    despues se cotiza).
    """
    _validar_transicion(solicitud, EstadoSolicitud.EN_ATENCION)

    anterior = solicitud.estado
    solicitud.estado = EstadoSolicitud.EN_ATENCION
    solicitud.fecha_inicio_atencion = timezone.now()
    solicitud.save(update_fields=["estado", "fecha_inicio_atencion"])

    _registrar_evento(
        solicitud,
        tipo=TipoEvento.CAMBIO_ESTADO,
        usuario=usuario,
        anterior=anterior,
        nuevo=solicitud.estado,
        nota="Se inició la atención.",
    )
    return solicitud


@transaction.atomic
def finalizar_solicitud(*, solicitud, usuario, observaciones):
    """CU-SER-03 (RF-32, RF-33, RF-61, RF-63).

    Dos guardas, en este orden: observaciones (dato de la peticion) y
    monto cotizado (paso previo de otra persona). Comprobar primero lo
    que quien cierra puede resolver por si mismo evita mandarlo a
    buscar al administrador cuando en realidad le falta escribir lo que
    hizo.
    """
    _validar_transicion(solicitud, EstadoSolicitud.FINALIZADA)

    texto = (observaciones or "").strip()
    if not texto:
        raise ObservacionesRequeridas()

    if not solicitud.esta_cotizada:
        raise MontoRequerido()

    anterior = solicitud.estado
    solicitud.observaciones = texto
    solicitud.estado = EstadoSolicitud.FINALIZADA
    solicitud.cerrada_por = usuario
    solicitud.fecha_cierre = timezone.now()
    solicitud.save(
        update_fields=["observaciones", "estado", "cerrada_por", "fecha_cierre"]
    )

    _registrar_evento(
        solicitud,
        tipo=TipoEvento.CIERRE,
        usuario=usuario,
        anterior=anterior,
        nuevo=solicitud.estado,
        nota=f"Servicio finalizado. Monto: Bs {solicitud.monto_cobrado}.",
    )
    return solicitud


@transaction.atomic
def cancelar_solicitud(*, solicitud, usuario, motivo):
    """CU-SER-04 (RF-34, RN-SER-07).

    No borra nada (RN-SER-08) y no cuenta como ingreso aunque estuviera
    cotizada (RN-SER-14).
    """
    _validar_transicion(solicitud, EstadoSolicitud.CANCELADA)

    texto = (motivo or "").strip()
    if not texto:
        raise ErrorDeNegocio("Debe indicar el motivo de la cancelación.")

    anterior = solicitud.estado
    solicitud.estado = EstadoSolicitud.CANCELADA
    solicitud.motivo_cancelacion = texto
    solicitud.cerrada_por = usuario
    solicitud.fecha_cierre = timezone.now()
    solicitud.save(
        update_fields=[
            "estado",
            "motivo_cancelacion",
            "cerrada_por",
            "fecha_cierre",
        ]
    )

    _registrar_evento(
        solicitud,
        tipo=TipoEvento.CAMBIO_ESTADO,
        usuario=usuario,
        anterior=anterior,
        nuevo=solicitud.estado,
        nota=f"Solicitud cancelada. Motivo: {texto}",
    )
    return solicitud
