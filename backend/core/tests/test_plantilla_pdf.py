"""T-10.4 — Plantilla base de los documentos PDF (plan.md 7.10).

El membrete, la linea morada y el pie salen del informe de servicio a
`core/templates/pdf/base.html`, que extienden el informe, la garantia y
el reporte. El informe debe quedar IDENTICO: sus pruebas no cambian
(servicios/tests/test_pdf.py), y aqui se comprueba ademas lo que esas
pruebas no ven, los colores que se pintan en el flujo del PDF.

Los colores esperados se registraron con la plantilla ANTERIOR a la
extraccion. Si la plantilla base perdiera la linea morada, o el aviso
ambar de «Pendiente de cotizacion», el conjunto cambiaria.
"""

import re
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader

from servicios.models import EstadoSolicitud
from servicios.tests.factories import SolicitudFactory
from servicios.tests.test_pdf import _autenticar
from usuarios.tests.factories import TecnicoFactory

pytestmark = pytest.mark.django_db


def colores_del_flujo(pdf):
    """Los operadores de color RGB (relleno `rg` y trazo `RG`) de todas
    las paginas, sin repetir."""
    flujo = b"".join(p.get_contents().get_data() for p in PdfReader(BytesIO(pdf)).pages)
    return sorted({o.decode() for o in re.findall(rb"[0-9.]+ [0-9.]+ [0-9.]+ (?:rg|RG)", flujo)})


def _informe(tecnico, solicitud):
    return _autenticar(tecnico).get(f"/api/v1/solicitudes/{solicitud.pk}/pdf").content


@pytest.fixture
def tecnico():
    return TecnicoFactory()


def test_colores_del_informe_finalizado(tecnico):
    finalizada = SolicitudFactory(
        registrada_por=tecnico,
        estado=EstadoSolicitud.FINALIZADA,
        monto_cobrado=Decimal("250.00"),
        observaciones="Se reemplazó la fuente.",
        tecnico="Pedro Mamani",
        fecha_cierre="2026-09-29T15:00:00Z",
        cerrada_por=tecnico,
    )

    assert colores_del_flujo(_informe(tecnico, finalizada)) == COLORES_FINALIZADO


def test_colores_del_informe_sin_cotizar(tecnico):
    abierta = SolicitudFactory(registrada_por=tecnico, monto_cobrado=None)

    assert colores_del_flujo(_informe(tecnico, abierta)) == COLORES_SIN_COTIZAR


# Registrados con la plantilla anterior a la extraccion (2026-10-09).
COLORES_FINALIZADO = sorted([
    "0 0 0 rg",
    ".094118 .094118 .105882 rg",  # texto #18181b
    ".321569 .321569 .356863 rg",  # etiquetas #52525b
    ".427451 .156863 .85098 rg",  # numero #6d28d9
    ".443137 .443137 .478431 rg",  # pie #71717a
    ".486275 .227451 .929412 RG",  # linea morada #7c3aed
    ".831373 .831373 .847059 RG",  # filetes #d4d4d8
])
COLORES_SIN_COTIZAR = sorted(COLORES_FINALIZADO + [".705882 .32549 .035294 rg"])  # ambar #b45309
