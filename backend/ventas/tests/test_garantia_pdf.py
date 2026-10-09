"""T-10.5 — Garantia de una venta en PDF (RF-76, RF-78, RN-VEN-14 a 16).

Se lee el TEXTO real del PDF, no el HTML que lo origino: lo que importa
es lo que el cliente se lleva impreso.
"""

from datetime import datetime
from io import BytesIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from pypdf import PdfReader
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.tests.factories import ProductoFactory
from core.exceptions import Codigo
from usuarios.tests.factories import AdministradorFactory, TecnicoFactory, VendedorFactory
from ventas.services import anular_venta, registrar_venta

pytestmark = pytest.mark.django_db

LA_PAZ = ZoneInfo("America/La_Paz")


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
    lector = PdfReader(BytesIO(respuesta.content))
    return "\n".join(pagina.extract_text() for pagina in lector.pages)


@pytest.fixture
def vendedor():
    return VendedorFactory(nombre_completo="Víctor Vendedor")


@pytest.fixture
def productos():
    return {
        "disco": ProductoFactory(nombre="Disco SSD 480 GB", stock=5, meses_garantia=12),
        "monitor": ProductoFactory(nombre="Monitor 24 pulgadas", stock=5, meses_garantia=1),
        "cable": ProductoFactory(nombre="Cable HDMI sin garantía", stock=5, meses_garantia=0),
    }


def _vender(vendedor, items, momento=datetime(2026, 1, 31, 22, 0, tzinfo=LA_PAZ)):
    """La venta se registra el 31 de enero a las 22:00 en La Paz (ya
    1 de febrero en UTC): el vencimiento debe contar desde el 31."""
    with mock.patch("django.utils.timezone.now", return_value=momento):
        return registrar_venta(
            usuario=vendedor,
            cliente_nombre="María Gutiérrez",
            cliente_telefono="70012345",
            items=items,
        )


@pytest.fixture
def venta(vendedor, productos):
    return _vender(
        vendedor,
        [
            {"producto_id": productos["disco"].id, "cantidad": 2},
            {"producto_id": productos["monitor"].id, "cantidad": 1},
            {"producto_id": productos["cable"].id, "cantidad": 3},
        ],
    )


def _garantia(cliente, venta):
    return cliente.get(f"/api/v1/ventas/{venta.pk}/garantia")


# ─────────────────────────────────────────────────────────────────────
# Contenido (RF-76, RN-VEN-13 a 15)
# ─────────────────────────────────────────────────────────────────────
def test_devuelve_un_pdf_con_nombre_de_archivo(vendedor, venta):
    respuesta = _garantia(_autenticar(vendedor), venta)

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta["Content-Type"] == "application/pdf"
    assert respuesta.content.startswith(b"%PDF")
    assert f'garantia-venta-{venta.pk}.pdf' in respuesta["Content-Disposition"]


def test_lista_cliente_codigo_y_vencimiento_de_cada_linea_con_garantia(vendedor, venta, productos):
    texto = _texto(_garantia(_autenticar(vendedor), venta))

    assert "María Gutiérrez" in texto
    assert "70012345" in texto
    assert f"N.º {venta.pk}" in texto
    assert "31/01/2026" in texto  # fecha de la venta en hora de Bolivia
    assert "Disco SSD 480 GB" in texto and productos["disco"].codigo in texto
    assert "31/01/2027" in texto  # 12 meses
    assert "Monitor 24 pulgadas" in texto and productos["monitor"].codigo in texto
    assert "28/02/2026" in texto  # 31/01 + 1 mes → ultimo dia de febrero


def test_no_lista_las_lineas_sin_garantia(vendedor, venta, productos):
    texto = _texto(_garantia(_autenticar(vendedor), venta))

    assert "Cable HDMI" not in texto
    assert productos["cable"].codigo not in texto


def test_declara_que_no_es_un_documento_fiscal(vendedor, venta):
    texto = _texto(_garantia(_autenticar(vendedor), venta))

    assert "no es una factura ni un comprobante fiscal" in texto
    assert "Documento no fiscal" in texto


def test_dice_quien_la_genero_y_cuando(vendedor, venta):
    texto = _texto(_garantia(_autenticar(vendedor), venta))

    assert "Generado el" in texto
    assert "por Víctor Vendedor" in texto


def test_no_se_escapa_sintaxis_de_plantilla(vendedor, venta):
    texto = _texto(_garantia(_autenticar(vendedor), venta))

    for resto in ("{#", "#}", "{%", "%}", "{{", "}}"):
        assert resto not in texto, f"La garantía imprime «{resto}»"


def test_no_lleva_carnet(vendedor, venta):
    """RN-VEN-15: ni siquiera la palabra. Cuando la venta tenga cliente
    registrado (bloque 11) se comprueba tambien con su carnet real."""
    texto = _texto(_garantia(_autenticar(vendedor), venta)).lower()

    assert "carnet" not in texto and "c.i." not in texto


def test_emitirla_dos_veces_da_el_mismo_contenido_salvo_la_fecha_de_generacion(vendedor, venta):
    cliente = _autenticar(vendedor)

    def sin_pie(texto):
        return [linea for linea in texto.splitlines() if "Generado el" not in linea]

    assert sin_pie(_texto(_garantia(cliente, venta))) == sin_pie(_texto(_garantia(cliente, venta)))


# ─────────────────────────────────────────────────────────────────────
# Rechazos (RF-78, RN-VEN-14)
# ─────────────────────────────────────────────────────────────────────
def test_una_venta_anulada_no_emite_garantia(vendedor, venta):
    anular_venta(venta=venta, usuario=vendedor, motivo="Devolución")

    respuesta = _garantia(_autenticar(vendedor), venta)

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.GARANTIA_DE_VENTA_ANULADA


def test_una_venta_sin_lineas_con_garantia_no_la_emite(vendedor, productos):
    sin = _vender(vendedor, [{"producto_id": productos["cable"].id, "cantidad": 1}])

    respuesta = _garantia(_autenticar(vendedor), sin)

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.VENTA_SIN_GARANTIA


# ─────────────────────────────────────────────────────────────────────
# Quien la emite (RN-VEN-16)
# ─────────────────────────────────────────────────────────────────────
def test_otro_encargado_de_ventas_recibe_404_como_si_no_existiera(venta):
    otro = VendedorFactory()

    respuesta = _garantia(_autenticar(otro), venta)

    assert respuesta.status_code == status.HTTP_404_NOT_FOUND


def test_el_administrador_emite_la_de_cualquier_venta(venta):
    assert _garantia(_autenticar(AdministradorFactory()), venta).status_code == 200


def test_el_encargado_de_servicios_no_entra_al_modulo(venta):
    assert _garantia(_autenticar(TecnicoFactory()), venta).status_code == 403


def test_sin_sesion_no_hay_garantia(venta):
    assert APIClient().get(f"/api/v1/ventas/{venta.pk}/garantia").status_code == 401


def test_cambiar_los_meses_del_producto_despues_no_cambia_la_garantia(vendedor, venta, productos):
    """RN-VEN-12: la garantia se calcula con los meses CONGELADOS en la
    linea, no con los que el producto tenga al emitirla."""
    cliente = _autenticar(vendedor)
    antes = _texto(_garantia(cliente, venta))

    productos["disco"].meses_garantia = 36
    productos["disco"].save()
    productos["cable"].meses_garantia = 6  # ahora tiene, pero no al vender
    productos["cable"].save()
    despues = _texto(_garantia(cliente, venta))

    assert "31/01/2027" in despues and "31/01/2029" not in despues
    assert "Cable HDMI" not in despues
    assert [l for l in antes.splitlines() if "Generado el" not in l] == [
        l for l in despues.splitlines() if "Generado el" not in l
    ]
