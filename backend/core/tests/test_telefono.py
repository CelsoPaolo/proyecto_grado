"""T-15.3 — Telefono de 8 digitos en los registros nuevos (RF-100).

RN-CLI-09 en sus tres lugares —cliente registrado, cliente ocasional de
la venta y contacto de la solicitud—, en las tres capas: serializer,
servicio y base de datos. Y RNF-30: las ventas y solicitudes ANTERIORES
con telefonos fuera de formato siguen pudiendo anularse y atenderse.
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.tests.factories import ProductoFactory
from clientes.models import Cliente
from clientes.services import editar_cliente, registrar_cliente
from clientes.tests.factories import ClienteFactory
from core.exceptions import ErrorDeNegocio
from core.validadores import MENSAJE_TELEFONO, telefono_valido
from servicios.models import EstadoSolicitud, SolicitudServicio, TipoServicio
from servicios.services import registrar_solicitud
from servicios.tests.factories import SolicitudFactory
from usuarios.tests.factories import TecnicoFactory, VendedorFactory
from ventas.models import EstadoVenta, Venta
from ventas.services import registrar_venta
from ventas.tests.factories import VentaFactory

INVALIDOS = ["7001234", "700123456", "7001234a", "7001 2345", "7001-234", "٧٠٠١٢٣٤٥"]


def _autenticar(usuario):
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


# ─────────────────────────────────────────────────────────────────────
# El validador comun
# ─────────────────────────────────────────────────────────────────────
def test_ocho_digitos_es_valido():
    assert telefono_valido("70012345")


@pytest.mark.parametrize("valor", INVALIDOS + ["", None])
def test_lo_demas_no_lo_es(valor):
    """Incluidos los digitos arabigo-indicos, que `\\d` aceptaria."""
    assert not telefono_valido(valor)


# ─────────────────────────────────────────────────────────────────────
# Cliente registrado
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
@pytest.mark.parametrize("telefono", INVALIDOS)
def test_la_api_de_clientes_rechaza_un_telefono_fuera_de_formato(telefono):
    respuesta = _autenticar(VendedorFactory()).post(
        "/api/v1/clientes", {"nombre": "Ana", "telefono": telefono}, format="json"
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert respuesta.data["errores"]["telefono"] == [MENSAJE_TELEFONO]
    assert not Cliente.objects.exists()


@pytest.mark.django_db
def test_el_servicio_de_clientes_acepta_ocho_digitos():
    cliente = registrar_cliente(usuario=VendedorFactory(), nombre="Ana", telefono=" 70012345 ")

    assert cliente.telefono == "70012345"


@pytest.mark.django_db
def test_editar_el_telefono_exige_el_formato():
    cliente = ClienteFactory()

    with pytest.raises(ErrorDeNegocio) as error:
        editar_cliente(cliente=cliente, usuario=VendedorFactory(), telefono="123")

    assert error.value.errores == {"telefono": [MENSAJE_TELEFONO]}


@pytest.mark.django_db
def test_editar_otro_dato_de_un_cliente_anterior_no_exige_corregir_su_telefono():
    """Solo se valida el telefono que se envia."""
    cliente = ClienteFactory()
    Cliente.objects.filter(pk=cliente.pk).update(telefono="563563463")
    cliente.refresh_from_db()

    editar_cliente(cliente=cliente, usuario=VendedorFactory(), direccion="Calle 1")

    cliente.refresh_from_db()
    assert cliente.direccion == "Calle 1"


# ─────────────────────────────────────────────────────────────────────
# Cliente ocasional de la venta (RN-VEN-10, PA-09)
# ─────────────────────────────────────────────────────────────────────
def _venta(**cliente):
    producto = ProductoFactory(stock=5)
    return {"items": [{"producto_id": producto.id, "cantidad": 1}], **cliente}


@pytest.mark.django_db
def test_se_vende_a_un_cliente_ocasional_sin_telefono():
    respuesta = _autenticar(VendedorFactory()).post(
        "/api/v1/ventas", _venta(cliente_nombre="Ocasional"), format="json"
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert Venta.objects.get().cliente_telefono == ""


@pytest.mark.django_db
@pytest.mark.parametrize("telefono", INVALIDOS)
def test_si_se_escribe_el_telefono_del_ocasional_debe_tener_ocho_digitos(telefono):
    respuesta = _autenticar(VendedorFactory()).post(
        "/api/v1/ventas",
        _venta(cliente_nombre="Ocasional", cliente_telefono=telefono),
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert respuesta.data["errores"]["cliente_telefono"] == [MENSAJE_TELEFONO]
    assert not Venta.objects.exists()


@pytest.mark.django_db
def test_el_servicio_de_ventas_tambien_lo_comprueba():
    producto = ProductoFactory(stock=5)

    with pytest.raises(ErrorDeNegocio):
        registrar_venta(
            usuario=VendedorFactory(),
            items=[{"producto_id": producto.id, "cantidad": 1}],
            cliente_nombre="Ocasional",
            cliente_telefono="123",
        )

    assert not Venta.objects.exists()


@pytest.mark.django_db
def test_no_se_vende_a_un_cliente_registrado_con_telefono_fuera_de_formato():
    """La venta copiaria ese telefono y la base la rechazaria: se avisa
    antes, junto al cliente, y no se descuenta nada."""
    cliente = ClienteFactory()
    Cliente.objects.filter(pk=cliente.pk).update(telefono="563563463")
    producto = ProductoFactory(stock=5)

    respuesta = _autenticar(VendedorFactory()).post(
        "/api/v1/ventas",
        {"cliente_id": cliente.pk, "items": [{"producto_id": producto.id, "cantidad": 1}]},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "Corríjalo en Clientes" in respuesta.data["errores"]["cliente_id"][0]
    producto.refresh_from_db()
    assert producto.stock == 5


# ─────────────────────────────────────────────────────────────────────
# Contacto de la solicitud de servicio (RN-SER-05)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
@pytest.mark.parametrize("telefono", INVALIDOS)
def test_la_api_de_servicios_rechaza_un_telefono_fuera_de_formato(telefono):
    respuesta = _autenticar(TecnicoFactory()).post(
        "/api/v1/solicitudes",
        {
            "cliente_nombre": "Ana",
            "cliente_telefono": telefono,
            "tipo": TipoServicio.MANTENIMIENTO,
            "descripcion": "No enciende.",
        },
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert respuesta.data["errores"]["cliente_telefono"] == [MENSAJE_TELEFONO]
    assert not SolicitudServicio.objects.exists()


@pytest.mark.django_db
def test_el_servicio_de_solicitudes_tambien_lo_comprueba():
    with pytest.raises(ErrorDeNegocio):
        registrar_solicitud(
            usuario=TecnicoFactory(),
            cliente_nombre="Ana",
            cliente_telefono="123",
            tipo=TipoServicio.MANTENIMIENTO,
            descripcion="No enciende.",
        )


@pytest.mark.django_db
def test_la_solicitud_se_registra_con_ocho_digitos():
    solicitud = registrar_solicitud(
        usuario=TecnicoFactory(),
        cliente_nombre="Ana",
        cliente_telefono="70012345",
        tipo=TipoServicio.MANTENIMIENTO,
        descripcion="No enciende.",
    )

    assert solicitud.cliente_telefono == "70012345"


# ─────────────────────────────────────────────────────────────────────
# La base de datos, ultima red (en la base de pruebas rige para todas)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
def test_la_base_rechaza_una_venta_nueva_con_telefono_fuera_de_formato():
    with pytest.raises(IntegrityError), transaction.atomic():
        VentaFactory(cliente_telefono="123")


@pytest.mark.django_db
def test_la_base_acepta_una_venta_nueva_sin_telefono():
    VentaFactory(cliente_telefono="")


@pytest.mark.django_db
def test_la_base_rechaza_una_solicitud_nueva_con_telefono_fuera_de_formato():
    with pytest.raises(IntegrityError), transaction.atomic():
        SolicitudFactory(cliente_telefono="123")


# ─────────────────────────────────────────────────────────────────────
# RNF-30 — las filas anteriores no se revisan nunca (plan.md 3.6)
# ─────────────────────────────────────────────────────────────────────
ANTES = [("ventas", "0003_cliente_registrado"), ("servicios", "0001_initial")]
DESPUES = [("ventas", "0004_telefono_formato"), ("servicios", "0002_telefono_formato")]


def _migrar(destino):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(destino)


def _restricciones():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT conname FROM pg_constraint WHERE conname IN "
            "('venta_telefono_formato', 'solicitud_telefono_formato')"
        )
        return {fila[0] for fila in cursor.fetchall()}


@pytest.fixture
def registros_anteriores():
    """Una venta y una solicitud de antes de la v1.5, con telefonos que
    hoy no se aceptarian."""
    _migrar(ANTES)
    apps = MigrationExecutor(connection).loader.project_state(ANTES).apps
    Usuario = apps.get_model("usuarios", "Usuario")
    usuario = Usuario.objects.create(username="antiguo", nombre_completo="Antiguo", rol="ADMINISTRADOR")
    venta = apps.get_model("ventas", "Venta").objects.create(
        usuario=usuario, cliente_nombre="Antiguo", cliente_telefono="34343424234", total=Decimal("0")
    )
    solicitud = apps.get_model("servicios", "SolicitudServicio").objects.create(
        cliente_nombre="Antiguo",
        cliente_telefono="563",
        tipo="MANTENIMIENTO",
        modalidad="TALLER",
        descripcion="Antigua",
        estado="REGISTRADA",
        registrada_por=usuario,
    )
    yield venta.pk, solicitud.pk, usuario.pk
    _migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_las_filas_anteriores_se_siguen_actualizando_y_las_nuevas_no_se_aceptan(registros_anteriores):
    venta_id, solicitud_id, usuario_id = registros_anteriores
    _migrar(DESPUES)

    # Anular la venta antigua y atender la solicitud antigua: UPDATE de
    # filas con telefono fuera de formato. Con NOT VALID fallarian.
    Venta.objects.filter(pk=venta_id).update(
        estado=EstadoVenta.ANULADA,
        motivo_anulacion="Error",
        anulada_por_id=usuario_id,
        fecha_anulacion=timezone.now(),
    )
    SolicitudServicio.objects.filter(pk=solicitud_id).update(estado=EstadoSolicitud.EN_ATENCION)

    assert Venta.objects.get(pk=venta_id).cliente_telefono == "34343424234"
    assert SolicitudServicio.objects.get(pk=solicitud_id).cliente_telefono == "563"

    with pytest.raises(IntegrityError), transaction.atomic():
        Venta.objects.create(usuario_id=usuario_id, cliente_nombre="Nueva", cliente_telefono="123", total=0)


@pytest.mark.django_db(transaction=True)
def test_las_migraciones_del_telefono_son_reversibles(registros_anteriores):
    """RNF-29: ida y vuelta, sin tocar ningun dato."""
    venta_id, _, _ = registros_anteriores

    _migrar(DESPUES)
    assert _restricciones() == {"venta_telefono_formato", "solicitud_telefono_formato"}

    _migrar(ANTES)
    assert _restricciones() == set()
    with connection.cursor() as cursor:
        cursor.execute("SELECT cliente_telefono FROM ventas_venta WHERE id = %s", [venta_id])
        assert cursor.fetchone()[0] == "34343424234"
