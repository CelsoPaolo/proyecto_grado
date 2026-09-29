"""T-5.1 a T-5.6 — Modelos, maquina de estados y servicios.

Incorpora las decisiones revisadas en spec.md v1.2: el Administrador
cotiza (PA-03), el tecnico es texto libre (PA-05) y cada solicitud la
ve solo su registrador (PA-04, que se verifica en test_api.py).
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction

from servicios.models import (
    EstadoSolicitud,
    EventoSolicitud,
    Modalidad,
    SolicitudServicio,
    TipoEvento,
    TipoServicio,
)
from servicios.services import (
    MontoRequerido,
    ObservacionesRequeridas,
    SolicitudCerrada,
    TRANSICIONES,
    TransicionInvalida,
    cancelar_solicitud,
    cotizar_solicitud,
    finalizar_solicitud,
    iniciar_atencion,
    registrar_solicitud,
    transicion_permitida,
)
from usuarios.tests.factories import AdministradorFactory, TecnicoFactory

from .factories import SolicitudFactory

pytestmark = pytest.mark.django_db


def _registrar(usuario=None, tipo=TipoServicio.MANTENIMIENTO, direccion=""):
    return registrar_solicitud(
        usuario=usuario or TecnicoFactory(),
        cliente_nombre="María Gutiérrez",
        cliente_telefono="70012345",
        tipo=tipo,
        descripcion="El equipo no enciende.",
        direccion=direccion,
    )


def _hasta_atencion(usuario=None):
    usuario = usuario or TecnicoFactory()
    solicitud = _registrar(usuario)
    return iniciar_atencion(solicitud=solicitud, usuario=usuario), usuario


# ═════════════════════════════════════════════════════════════════════
# T-5.1 — Modelo y restricciones
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize(
    ("tipo", "modalidad"),
    [
        (TipoServicio.MANTENIMIENTO, Modalidad.TALLER),
        (TipoServicio.REPARACION, Modalidad.TALLER),
        (TipoServicio.REDES, Modalidad.DOMICILIO),
        (TipoServicio.VIDEOVIGILANCIA, Modalidad.DOMICILIO),
    ],
)
def test_la_modalidad_la_deriva_el_sistema_del_tipo(tipo, modalidad):
    """RN-SER-01: el usuario no la elige."""
    direccion = "Calle Falsa 123" if modalidad == Modalidad.DOMICILIO else ""
    solicitud = _registrar(tipo=tipo, direccion=direccion)

    assert solicitud.modalidad == modalidad


def test_la_base_rechaza_un_servicio_a_domicilio_sin_direccion():
    """RN-SER-04, declarado en la base y no solo en el serializer."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SolicitudFactory(tipo=TipoServicio.REDES, direccion="")


def test_un_servicio_en_taller_no_necesita_direccion():
    solicitud = _registrar(tipo=TipoServicio.REPARACION)

    assert solicitud.direccion == ""
    assert not solicitud.requiere_direccion


def test_la_base_rechaza_un_monto_negativo():
    """RN-SER-17."""
    solicitud = _registrar()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE servicios_solicitudservicio "
                    "SET monto_cobrado = -1 WHERE id = %s",
                    [solicitud.id],
                )


def test_la_base_impide_finalizar_sin_observaciones_ni_monto():
    """RN-SER-03 y RN-SER-13 en la base.

    Asi ningun camino futuro puede cerrar una solicitud a medias,
    aunque alguien saltara el servicio.
    """
    solicitud = _registrar()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE servicios_solicitudservicio "
                    "SET estado = 'FINALIZADA' WHERE id = %s",
                    [solicitud.id],
                )


def test_el_tecnico_no_tiene_ninguna_relacion_con_las_cuentas():
    """El criterio central de PA-05 revisado.

    Si el tecnico volviera a ser una clave foranea, reaparecerian los
    problemas que la revision elimino: validar si la cuenta esta
    activa, reasignar al bloquearla, impedir autoasignaciones.
    """
    campo = SolicitudServicio._meta.get_field("tecnico")

    assert campo.get_internal_type() == "CharField"
    assert not campo.is_relation
    assert campo.blank


def test_una_solicitud_nace_sin_cotizar():
    solicitud = _registrar()

    assert solicitud.monto_cobrado is None
    assert not solicitud.esta_cotizada
    assert solicitud.cotizada_por is None


# ═════════════════════════════════════════════════════════════════════
# T-5.2 — Historial
# ═════════════════════════════════════════════════════════════════════
def test_el_registro_deja_su_evento_en_el_historial():
    solicitud = _registrar()

    eventos = solicitud.eventos.all()
    assert len(eventos) == 1
    assert eventos[0].tipo_evento == TipoEvento.CAMBIO_ESTADO
    assert eventos[0].estado_nuevo == EstadoSolicitud.REGISTRADA


def test_el_historial_registra_a_las_dos_personas_que_intervienen():
    """El motivo de que el historial siga siendo necesario.

    El Administrador cotiza y el registrador cierra: sobre una misma
    solicitud actuan dos personas distintas.
    """
    tecnico = TecnicoFactory(nombre_completo="Ana Rojas")
    admin = AdministradorFactory(nombre_completo="Carlos Vargas")

    solicitud = _registrar(tecnico)
    iniciar_atencion(solicitud=solicitud, usuario=tecnico)
    cotizar_solicitud(solicitud=solicitud, usuario=admin, monto="250.00")
    finalizar_solicitud(
        solicitud=solicitud, usuario=tecnico, observaciones="Se cambió la fuente."
    )

    autores = [e.usuario.nombre_completo for e in solicitud.eventos.all()]
    assert "Ana Rojas" in autores
    assert "Carlos Vargas" in autores

    cotizacion = solicitud.eventos.filter(tipo_evento=TipoEvento.COTIZACION).first()
    assert cotizacion.usuario == admin


def test_el_historial_es_de_solo_insercion():
    """RN-SER-06: nunca se actualiza ni se borra."""
    import inspect

    from servicios import services

    codigo = inspect.getsource(services)

    assert "EventoSolicitud.objects.create" in codigo
    for prohibido in (
        "EventoSolicitud.objects.filter",
        "evento.delete",
        "eventos.delete",
        "eventos.update",
    ):
        assert prohibido not in codigo


# ═════════════════════════════════════════════════════════════════════
# T-5.3 — Maquina de estados (RN-SER-02)
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("origen", list(EstadoSolicitud))
@pytest.mark.parametrize("destino", list(EstadoSolicitud))
def test_solo_se_permiten_las_transiciones_del_diagrama(origen, destino):
    """Recorre TODAS las combinaciones de origen x destino.

    Comprobar solo las validas dejaria sin verificar precisamente lo
    que la regla prohibe.
    """
    permitidas = {
        (EstadoSolicitud.REGISTRADA, EstadoSolicitud.EN_ATENCION),
        (EstadoSolicitud.REGISTRADA, EstadoSolicitud.CANCELADA),
        (EstadoSolicitud.EN_ATENCION, EstadoSolicitud.FINALIZADA),
        (EstadoSolicitud.EN_ATENCION, EstadoSolicitud.CANCELADA),
    }

    assert transicion_permitida(origen, destino) is ((origen, destino) in permitidas)


@pytest.mark.parametrize(
    "terminal", [EstadoSolicitud.FINALIZADA, EstadoSolicitud.CANCELADA]
)
def test_los_estados_terminales_no_tienen_salida(terminal):
    assert TRANSICIONES[terminal] == set()


def test_no_se_puede_retroceder_de_estado():
    solicitud, tecnico = _hasta_atencion()

    with pytest.raises(TransicionInvalida):
        iniciar_atencion(solicitud=solicitud, usuario=tecnico)


# ═════════════════════════════════════════════════════════════════════
# T-5.5 — Cotizacion (PA-03 revisado)
# ═════════════════════════════════════════════════════════════════════
def test_el_administrador_cotiza_una_solicitud():
    solicitud = _registrar()
    admin = AdministradorFactory()

    cotizar_solicitud(solicitud=solicitud, usuario=admin, monto="250.00")

    solicitud.refresh_from_db()
    assert solicitud.monto_cobrado == Decimal("250.00")
    assert solicitud.cotizada_por == admin
    assert solicitud.fecha_cotizacion is not None


def test_el_monto_cero_es_una_cotizacion_valida():
    """RN-SER-17: garantía o cortesía. Distinto de no cotizar."""
    solicitud = _registrar()

    cotizar_solicitud(
        solicitud=solicitud, usuario=AdministradorFactory(), monto="0.00"
    )

    solicitud.refresh_from_db()
    assert solicitud.monto_cobrado == Decimal("0.00")
    assert solicitud.esta_cotizada  # cero SÍ cuenta como cotizada


def test_el_monto_se_puede_reajustar_mientras_siga_abierta():
    """RN-SER-16: cotizar es una estimación tras la revisión."""
    solicitud = _registrar()
    admin = AdministradorFactory()
    cotizar_solicitud(solicitud=solicitud, usuario=admin, monto="250.00")

    cotizar_solicitud(solicitud=solicitud, usuario=admin, monto="400.00")

    solicitud.refresh_from_db()
    assert solicitud.monto_cobrado == Decimal("400.00")
    notas = [e.nota for e in solicitud.eventos.filter(tipo_evento=TipoEvento.COTIZACION)]
    assert any("ajustado" in n for n in notas)


def test_no_se_puede_cotizar_una_solicitud_cerrada():
    """RN-SER-12."""
    solicitud, tecnico = _hasta_atencion()
    admin = AdministradorFactory()
    cotizar_solicitud(solicitud=solicitud, usuario=admin, monto="100.00")
    finalizar_solicitud(solicitud=solicitud, usuario=tecnico, observaciones="Listo.")

    with pytest.raises(SolicitudCerrada):
        cotizar_solicitud(solicitud=solicitud, usuario=admin, monto="999.00")


def test_el_administrador_anota_el_tecnico_como_texto_libre():
    """PA-05 revisado: sin validar que exista como cuenta."""
    solicitud = _registrar()

    cotizar_solicitud(
        solicitud=solicitud,
        usuario=AdministradorFactory(),
        tecnico="Pedro Mamani (externo)",
    )

    solicitud.refresh_from_db()
    assert solicitud.tecnico == "Pedro Mamani (externo)"


def test_cotizar_y_anotar_tecnico_son_independientes():
    """Se puede anotar el técnico sin cotizar, y al revés."""
    solicitud = _registrar()
    admin = AdministradorFactory()

    cotizar_solicitud(solicitud=solicitud, usuario=admin, tecnico="Ana")
    solicitud.refresh_from_db()
    assert solicitud.tecnico == "Ana"
    assert not solicitud.esta_cotizada

    cotizar_solicitud(solicitud=solicitud, usuario=admin, monto="150.00")
    solicitud.refresh_from_db()
    assert solicitud.esta_cotizada
    assert solicitud.tecnico == "Ana"


# ═════════════════════════════════════════════════════════════════════
# T-5.6 — Inicio, finalizacion y cancelacion
# ═════════════════════════════════════════════════════════════════════
def test_iniciar_la_atencion_no_exige_cotizacion():
    """PA-03: primero se revisa, después se cotiza.

    Exigir el monto para empezar invertiría el orden del proceso y
    dejaría al técnico esperando al administrador para poder mirar el
    equipo.
    """
    solicitud = _registrar()
    tecnico = solicitud.registrada_por

    iniciar_atencion(solicitud=solicitud, usuario=tecnico)

    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.EN_ATENCION
    assert not solicitud.esta_cotizada
    assert solicitud.fecha_inicio_atencion is not None


def test_no_se_finaliza_sin_observaciones():
    """RN-SER-03."""
    solicitud, tecnico = _hasta_atencion()
    cotizar_solicitud(
        solicitud=solicitud, usuario=AdministradorFactory(), monto="100.00"
    )

    with pytest.raises(ObservacionesRequeridas):
        finalizar_solicitud(solicitud=solicitud, usuario=tecnico, observaciones="   ")


def test_no_se_finaliza_sin_monto_cotizado():
    """El criterio central de PA-03 revisado (RN-SER-13).

    Sin esta guarda, un servicio podría cerrarse sin importe y los
    ingresos del panel dejarían de reflejar lo realmente cobrado.
    """
    solicitud, tecnico = _hasta_atencion()

    with pytest.raises(MontoRequerido) as excepcion:
        finalizar_solicitud(
            solicitud=solicitud, usuario=tecnico, observaciones="Se cambió la fuente."
        )

    # El mensaje dice a quién acudir.
    assert "administrador" in str(excepcion.value.detalle).lower()
    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.EN_ATENCION


def test_faltan_observaciones_se_avisa_antes_que_el_monto():
    """Orden deliberado de las guardas.

    Se comprueba primero lo que quien cierra puede resolver por sí
    mismo; mandarlo a buscar al administrador cuando en realidad le
    falta escribir lo que hizo sería un rodeo inútil.
    """
    solicitud, tecnico = _hasta_atencion()

    with pytest.raises(ObservacionesRequeridas):
        finalizar_solicitud(solicitud=solicitud, usuario=tecnico, observaciones="")


def test_finalizar_con_observaciones_y_monto():
    solicitud, tecnico = _hasta_atencion()
    cotizar_solicitud(
        solicitud=solicitud, usuario=AdministradorFactory(), monto="250.00"
    )

    finalizar_solicitud(
        solicitud=solicitud, usuario=tecnico, observaciones="Se cambió la fuente."
    )

    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.FINALIZADA
    assert solicitud.observaciones == "Se cambió la fuente."
    assert solicitud.cerrada_por == tecnico
    assert solicitud.fecha_cierre is not None


def test_se_finaliza_un_servicio_cotizado_en_cero():
    """Garantía o cortesía."""
    solicitud, tecnico = _hasta_atencion()
    cotizar_solicitud(solicitud=solicitud, usuario=AdministradorFactory(), monto="0")

    finalizar_solicitud(
        solicitud=solicitud, usuario=tecnico, observaciones="Cubierto por garantía."
    )

    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.FINALIZADA
    assert solicitud.monto_cobrado == Decimal("0.00")


def test_una_solicitud_finalizada_no_admite_cambios():
    """RN-SER-16: el cierre es inmutable."""
    solicitud, tecnico = _hasta_atencion()
    cotizar_solicitud(solicitud=solicitud, usuario=AdministradorFactory(), monto="100")
    finalizar_solicitud(solicitud=solicitud, usuario=tecnico, observaciones="Listo.")

    with pytest.raises(SolicitudCerrada):
        cancelar_solicitud(solicitud=solicitud, usuario=tecnico, motivo="Tarde")


def test_cancelar_exige_motivo():
    """RN-SER-07."""
    from core.exceptions import ErrorDeNegocio

    solicitud = _registrar()

    with pytest.raises(ErrorDeNegocio):
        cancelar_solicitud(
            solicitud=solicitud, usuario=solicitud.registrada_por, motivo="  "
        )

    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.REGISTRADA


def test_cancelar_registra_el_motivo_y_cierra():
    solicitud = _registrar()

    cancelar_solicitud(
        solicitud=solicitud,
        usuario=solicitud.registrada_por,
        motivo="El cliente no volvió",
    )

    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.CANCELADA
    assert solicitud.motivo_cancelacion == "El cliente no volvió"
    assert solicitud.fecha_cierre is not None


def test_una_solicitud_cotizada_y_cancelada_no_cuenta_como_ingreso():
    """RN-SER-14.

    El monto queda registrado por trazabilidad, pero el estado es lo
    que decide si aporta al panel.
    """
    solicitud = _registrar()
    cotizar_solicitud(solicitud=solicitud, usuario=AdministradorFactory(), monto="500")

    cancelar_solicitud(
        solicitud=solicitud, usuario=solicitud.registrada_por, motivo="Desistió"
    )

    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.CANCELADA
    assert solicitud.monto_cobrado == Decimal("500.00")
    # El panel filtra por estado FINALIZADA (RN-IND-04), no por monto.
    finalizadas = SolicitudServicio.objects.filter(
        estado=EstadoSolicitud.FINALIZADA
    )
    assert solicitud not in finalizadas


def test_una_solicitud_no_se_elimina_nunca():
    """RN-SER-08: se cancela, no se borra."""
    solicitud = _registrar()
    cancelar_solicitud(
        solicitud=solicitud, usuario=solicitud.registrada_por, motivo="X"
    )

    assert SolicitudServicio.objects.filter(pk=solicitud.pk).exists()
    assert EventoSolicitud.objects.filter(solicitud=solicitud).exists()
