"""T-12.5 — Reporte por rango en PDF (RF-95).

Se lee el TEXTO real del PDF. Debe contener todas las secciones del
reporte, con las cifras del calculo, y ningun resto de plantilla.
"""

from decimal import Decimal
from io import BytesIO

import pytest
from django.utils import timezone
from pypdf import PdfReader
from rest_framework.test import APIClient

from catalogo.tests.factories import ProductoFactory
from servicios.models import EstadoSolicitud
from servicios.tests.factories import SolicitudFactory
from usuarios.tests.factories import AdministradorFactory, TecnicoFactory, VendedorFactory
from ventas.services import registrar_venta

pytestmark = pytest.mark.django_db

URL = "/api/v1/reportes/pdf"


def _autenticar(usuario):
    cliente = APIClient()
    respuesta = cliente.post(
        "/api/v1/auth/login",
        {"username": usuario.username, "password": "ClaveSegura123"},
        format="json",
    )
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return cliente


def _texto(respuesta):
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(respuesta.content)).pages)


@pytest.fixture
def hoy():
    return timezone.localdate().isoformat()


@pytest.fixture
def datos():
    producto = ProductoFactory(nombre="Teclado mecánico", stock=10, precio=Decimal("350.00"))
    registrar_venta(
        usuario=VendedorFactory(nombre_completo="Juan Pérez"),
        cliente_nombre="C",
        cliente_telefono="1",
        items=[{"producto_id": producto.pk, "cantidad": 2}],
    )
    tecnico = TecnicoFactory()
    SolicitudFactory(
        registrada_por=tecnico,
        estado=EstadoSolicitud.CANCELADA,
        motivo_cancelacion="Desistió",
        fecha_cierre=timezone.now(),
        cerrada_por=tecnico,
    )
    return producto


def test_devuelve_un_pdf_con_el_rango_en_el_nombre(hoy, datos):
    respuesta = _autenticar(AdministradorFactory()).get(URL, {"desde": hoy, "hasta": hoy})

    assert respuesta.status_code == 200
    assert respuesta.content.startswith(b"%PDF")
    assert f"reporte-{hoy}_{hoy}.pdf" in respuesta["Content-Disposition"]


def test_contiene_todas_las_secciones_con_sus_cifras(hoy, datos):
    texto = _texto(_autenticar(AdministradorFactory()).get(URL, {"desde": hoy, "hasta": hoy}))
    plano = " ".join(texto.split())

    for seccion in (
        "RESUMEN DEL PERÍODO",
        "PRODUCTOS MÁS VENDIDOS",
        "VENTAS POR USUARIO",
        "SERVICIOS REGISTRADOS POR ESTADO",
    ):
        assert seccion in plano.upper(), seccion
    assert "Teclado mecánico" in plano and datos.codigo in plano
    assert "Juan Pérez" in plano
    assert "700,00" in plano or "700.00" in plano
    # Los cuatro estados, la cancelada incluida (PA-08).
    for estado in ("Registrada", "En atención", "Finalizada", "Cancelada"):
        assert estado in plano, estado


def test_no_se_escapa_sintaxis_de_plantilla(hoy, datos):
    texto = _texto(_autenticar(AdministradorFactory()).get(URL, {"desde": hoy, "hasta": hoy}))

    for resto in ("{#", "#}", "{%", "%}", "{{", "}}"):
        assert resto not in texto


def test_un_rango_invertido_no_genera_pdf():
    respuesta = _autenticar(AdministradorFactory()).get(URL, {"desde": "2026-10-08", "hasta": "2026-10-01"})

    assert respuesta.status_code == 400


def test_solo_el_administrador(hoy):
    assert _autenticar(VendedorFactory()).get(URL, {"desde": hoy, "hasta": hoy}).status_code == 403
