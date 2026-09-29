"""T-5.7 y T-5.8 — API de servicios (RF-28 a RF-38, RF-56 a RF-64).

Lo central de este archivo son las dos decisiones revisadas en
spec.md v1.2:

  PA-04  cada solicitud la ve solo quien la registro (RF-64)
  PA-03  cotizar es exclusivo del Administrador (RF-57)
"""

from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.exceptions import Codigo
from servicios.models import EstadoSolicitud, TipoServicio
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)

pytestmark = pytest.mark.django_db

BASE = "/api/v1/solicitudes"


def _autenticar(usuario):
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


@pytest.fixture
def tecnico():
    return TecnicoFactory(username="arojas", nombre_completo="Ana Rojas")


@pytest.fixture
def como_tecnico(tecnico):
    return _autenticar(tecnico)


@pytest.fixture
def como_admin():
    return _autenticar(AdministradorFactory(username="admin"))


def _cuerpo(tipo=TipoServicio.MANTENIMIENTO, direccion=None):
    datos = {
        "cliente_nombre": "María Gutiérrez",
        "cliente_telefono": "70012345",
        "tipo": tipo,
        "descripcion": "El equipo no enciende.",
    }
    if direccion is not None:
        datos["direccion"] = direccion
    return datos


def _crear(cliente, **kwargs):
    return cliente.post(BASE, _cuerpo(**kwargs), format="json").data


# ═════════════════════════════════════════════════════════════════════
# CU-SER-01 — registro (RF-28, RF-29, RF-30)
# ═════════════════════════════════════════════════════════════════════
def test_registrar_una_solicitud_en_taller(como_tecnico):
    respuesta = como_tecnico.post(
        BASE, _cuerpo(TipoServicio.REPARACION), format="json"
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["estado"] == EstadoSolicitud.REGISTRADA
    assert respuesta.data["modalidad"] == "TALLER"
    assert respuesta.data["direccion"] == ""
    assert respuesta.data["monto_cobrado"] is None


def test_un_servicio_a_domicilio_exige_direccion(como_tecnico):
    """RF-29, con el error asociado a su campo (RNF-15)."""
    respuesta = como_tecnico.post(BASE, _cuerpo(TipoServicio.REDES), format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "direccion" in respuesta.data["errores"]


def test_un_servicio_a_domicilio_con_direccion_se_registra(como_tecnico):
    respuesta = como_tecnico.post(
        BASE,
        _cuerpo(TipoServicio.VIDEOVIGILANCIA, direccion="Av. Siempre Viva 742"),
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["modalidad"] == "DOMICILIO"
    assert respuesta.data["direccion"] == "Av. Siempre Viva 742"


def test_la_direccion_enviada_para_un_servicio_en_taller_se_descarta(como_tecnico):
    """RN-SER-04: en taller la dirección no se pide.

    Guardarla porque el cliente la mandó almacenaría un dato que la
    especificación no contempla.
    """
    respuesta = como_tecnico.post(
        BASE,
        _cuerpo(TipoServicio.MANTENIMIENTO, direccion="Calle Falsa 123"),
        format="json",
    )

    assert respuesta.data["direccion"] == ""


def test_el_cliente_no_puede_imponer_la_modalidad(como_tecnico):
    """RN-SER-01: la deriva el sistema del tipo."""
    datos = _cuerpo(TipoServicio.MANTENIMIENTO)
    datos["modalidad"] = "DOMICILIO"

    respuesta = como_tecnico.post(BASE, datos, format="json")

    assert respuesta.data["modalidad"] == "TALLER"


def test_el_cliente_no_puede_colar_monto_ni_tecnico_al_registrar(como_tecnico):
    """RF-57: ambos son del Administrador."""
    datos = _cuerpo()
    datos["monto_cobrado"] = "500.00"
    datos["tecnico"] = "Yo mismo"

    respuesta = como_tecnico.post(BASE, datos, format="json")

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["monto_cobrado"] is None
    assert respuesta.data["tecnico"] == ""


# ═════════════════════════════════════════════════════════════════════
# PA-04 revisado — visibilidad por usuario (RN-SER-15, RF-36, RF-64)
# ═════════════════════════════════════════════════════════════════════
def test_el_tecnico_solo_ve_sus_propias_solicitudes(como_tecnico):
    """El criterio central de PA-04 revisado."""
    propia = _crear(como_tecnico)
    ajena = _crear(_autenticar(TecnicoFactory(username="otro")))

    respuesta = como_tecnico.get(BASE)

    ids = [s["id"] for s in respuesta.data["results"]]
    assert propia["id"] in ids
    assert ajena["id"] not in ids


def test_el_tecnico_no_accede_al_detalle_de_una_solicitud_ajena(como_tecnico):
    """RF-64: ni siquiera pidiendo el id directamente.

    Se responde 404 y no 403 a propósito: un 403 confirmaría que esa
    solicitud existe.
    """
    ajena = _crear(_autenticar(TecnicoFactory(username="otro")))

    respuesta = como_tecnico.get(f"{BASE}/{ajena['id']}")

    assert respuesta.status_code == status.HTTP_404_NOT_FOUND


def test_el_tecnico_no_puede_actuar_sobre_una_solicitud_ajena(como_tecnico):
    ajena = _crear(_autenticar(TecnicoFactory(username="otro")))

    for accion in ("iniciar", "cancelar", "finalizar"):
        respuesta = como_tecnico.post(
            f"{BASE}/{ajena['id']}/{accion}",
            {"motivo": "x", "observaciones": "x"},
            format="json",
        )
        assert respuesta.status_code == status.HTTP_404_NOT_FOUND


def test_el_administrador_ve_todas_las_solicitudes(como_admin, como_tecnico):
    """RF-36."""
    del_tecnico = _crear(como_tecnico)
    del_admin = _crear(como_admin)

    respuesta = como_admin.get(BASE)

    ids = [s["id"] for s in respuesta.data["results"]]
    assert del_tecnico["id"] in ids
    assert del_admin["id"] in ids


# ═════════════════════════════════════════════════════════════════════
# PA-03 revisado — cotizar es del Administrador (RF-56, RF-57)
# ═════════════════════════════════════════════════════════════════════
def test_el_administrador_cotiza_una_solicitud(como_admin, como_tecnico):
    solicitud = _crear(como_tecnico)

    respuesta = como_admin.post(
        f"{BASE}/{solicitud['id']}/cotizar",
        {"monto_cobrado": "250.00", "tecnico": "Pedro Mamani"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta.data["monto_cobrado"] == "250.00"
    assert respuesta.data["tecnico"] == "Pedro Mamani"
    assert respuesta.data["cotizada_por"]["nombre_completo"] is not None


def test_el_tecnico_no_puede_cotizar_ni_su_propia_solicitud(como_tecnico):
    """El criterio central de PA-03 revisado (RF-57).

    Quien decide el precio no es quien ejecuta el trabajo. La
    restricción se aplica incluso sobre las solicitudes propias.
    """
    propia = _crear(como_tecnico)

    respuesta = como_tecnico.post(
        f"{BASE}/{propia['id']}/cotizar",
        {"monto_cobrado": "999.00"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_403_FORBIDDEN


def test_el_monto_cero_es_una_cotizacion_valida(como_admin, como_tecnico):
    """RN-SER-17: garantía o cortesía."""
    solicitud = _crear(como_tecnico)

    respuesta = como_admin.post(
        f"{BASE}/{solicitud['id']}/cotizar", {"monto_cobrado": "0"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta.data["esta_cotizada"] is True
    assert respuesta.data["monto_cobrado"] == "0.00"


def test_un_monto_negativo_se_rechaza(como_admin, como_tecnico):
    solicitud = _crear(como_tecnico)

    respuesta = como_admin.post(
        f"{BASE}/{solicitud['id']}/cotizar", {"monto_cobrado": "-5"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "monto_cobrado" in respuesta.data["errores"]


def test_cotizar_sin_datos_se_rechaza(como_admin, como_tecnico):
    solicitud = _crear(como_tecnico)

    respuesta = como_admin.post(
        f"{BASE}/{solicitud['id']}/cotizar", {}, format="json"
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST


# ═════════════════════════════════════════════════════════════════════
# Ciclo de vida (RF-31 a RF-34, RF-61)
# ═════════════════════════════════════════════════════════════════════
def test_iniciar_no_exige_cotizacion(como_tecnico):
    """PA-03: primero se revisa, después se cotiza."""
    solicitud = _crear(como_tecnico)

    respuesta = como_tecnico.post(f"{BASE}/{solicitud['id']}/iniciar")

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta.data["estado"] == EstadoSolicitud.EN_ATENCION
    assert respuesta.data["monto_cobrado"] is None


def test_no_se_finaliza_sin_monto_cotizado(como_tecnico):
    """RF-61 y RN-SER-13.

    Responde 409 y no 400 porque no falta un dato de la petición: falta
    un paso previo del proceso, que además hace otra persona.
    """
    solicitud = _crear(como_tecnico)
    como_tecnico.post(f"{BASE}/{solicitud['id']}/iniciar")

    respuesta = como_tecnico.post(
        f"{BASE}/{solicitud['id']}/finalizar",
        {"observaciones": "Se cambió la fuente."},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.MONTO_REQUERIDO
    assert "administrador" in respuesta.data["detalle"].lower()


def test_no_se_finaliza_sin_observaciones(como_admin, como_tecnico):
    """RF-33."""
    solicitud = _crear(como_tecnico)
    como_tecnico.post(f"{BASE}/{solicitud['id']}/iniciar")
    como_admin.post(
        f"{BASE}/{solicitud['id']}/cotizar", {"monto_cobrado": "100"}, format="json"
    )

    respuesta = como_tecnico.post(
        f"{BASE}/{solicitud['id']}/finalizar", {"observaciones": "  "}, format="json"
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST


def test_el_ciclo_completo_con_dos_personas(como_admin, como_tecnico):
    """El flujo que describe PA-03: el técnico atiende, el
    Administrador cotiza, el técnico cierra."""
    solicitud = _crear(como_tecnico)

    como_tecnico.post(f"{BASE}/{solicitud['id']}/iniciar")
    como_admin.post(
        f"{BASE}/{solicitud['id']}/cotizar",
        {"monto_cobrado": "250.00", "tecnico": "Pedro Mamani"},
        format="json",
    )
    respuesta = como_tecnico.post(
        f"{BASE}/{solicitud['id']}/finalizar",
        {"observaciones": "Se reemplazó la fuente de poder."},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta.data["estado"] == EstadoSolicitud.FINALIZADA
    assert respuesta.data["monto_cobrado"] == "250.00"
    assert respuesta.data["cerrada_por"]["nombre_completo"] == "Ana Rojas"
    # El historial guarda a ambos.
    autores = {e["usuario"]["nombre_completo"] for e in respuesta.data["eventos"]}
    assert len(autores) == 2


def test_una_solicitud_cerrada_no_admite_cambios(como_admin, como_tecnico):
    """RN-SER-16."""
    solicitud = _crear(como_tecnico)
    como_tecnico.post(f"{BASE}/{solicitud['id']}/cancelar",
                      {"motivo": "El cliente desistió"}, format="json")

    respuesta = como_admin.post(
        f"{BASE}/{solicitud['id']}/cotizar", {"monto_cobrado": "100"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.SOLICITUD_CERRADA


def test_cancelar_exige_motivo(como_tecnico):
    solicitud = _crear(como_tecnico)

    respuesta = como_tecnico.post(
        f"{BASE}/{solicitud['id']}/cancelar", {"motivo": "   "}, format="json"
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST


def test_una_transicion_invalida_responde_409(como_tecnico):
    """RF-31."""
    solicitud = _crear(como_tecnico)

    respuesta = como_tecnico.post(
        f"{BASE}/{solicitud['id']}/finalizar",
        {"observaciones": "Sin haber iniciado"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.TRANSICION_INVALIDA


def test_no_existe_forma_de_eliminar_una_solicitud(como_admin, como_tecnico):
    """RN-SER-08: se cancelan, no se borran."""
    solicitud = _crear(como_tecnico)

    respuesta = como_admin.delete(f"{BASE}/{solicitud['id']}")

    assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ═════════════════════════════════════════════════════════════════════
# T-5.8 — Filtros (RF-37, RF-60)
# ═════════════════════════════════════════════════════════════════════
def test_se_filtra_por_estado_y_por_tipo(como_tecnico):
    _crear(como_tecnico, tipo=TipoServicio.MANTENIMIENTO)
    reparacion = _crear(como_tecnico, tipo=TipoServicio.REPARACION)
    como_tecnico.post(f"{BASE}/{reparacion['id']}/iniciar")

    por_tipo = como_tecnico.get(f"{BASE}?tipo={TipoServicio.REPARACION}")
    por_estado = como_tecnico.get(f"{BASE}?estado={EstadoSolicitud.EN_ATENCION}")

    assert por_tipo.data["count"] == 1
    assert por_estado.data["count"] == 1
    assert por_estado.data["results"][0]["id"] == reparacion["id"]


def test_el_administrador_filtra_las_pendientes_de_cotizar(como_admin, como_tecnico):
    """RF-60: las que esperan su intervención."""
    sin_cotizar = _crear(como_tecnico)
    cotizada = _crear(como_tecnico)
    como_admin.post(
        f"{BASE}/{cotizada['id']}/cotizar", {"monto_cobrado": "100"}, format="json"
    )

    respuesta = como_admin.get(f"{BASE}?sin_cotizar=true")

    ids = [s["id"] for s in respuesta.data["results"]]
    assert sin_cotizar["id"] in ids
    assert cotizada["id"] not in ids


def test_una_solicitud_cerrada_no_figura_como_pendiente_de_cotizar(
    como_admin, como_tecnico
):
    """Una cancelada sin cotizar ya no espera nada."""
    cancelada = _crear(como_tecnico)
    como_tecnico.post(
        f"{BASE}/{cancelada['id']}/cancelar", {"motivo": "Desistió"}, format="json"
    )

    respuesta = como_admin.get(f"{BASE}?sin_cotizar=true")

    ids = [s["id"] for s in respuesta.data["results"]]
    assert cancelada["id"] not in ids


def test_el_listado_viene_paginado_y_sin_el_historial(como_tecnico):
    """RNF-18."""
    for _ in range(3):
        _crear(como_tecnico)

    respuesta = como_tecnico.get(BASE)

    assert "results" in respuesta.data
    assert "eventos" not in respuesta.data["results"][0]


# ═════════════════════════════════════════════════════════════════════
# RNF-02 — el Encargado de Ventas no accede a servicios
# ═════════════════════════════════════════════════════════════════════
def test_el_encargado_de_ventas_no_accede_a_servicios():
    """spec.md matriz 4.4."""
    cliente = _autenticar(VendedorFactory())

    assert cliente.get(BASE).status_code == status.HTTP_403_FORBIDDEN
