"""Generacion de PDF a partir de plantillas Django (RF-67).

Vive en `core` y no en `servicios` porque no sabe nada de solicitudes:
recibe una plantilla y un contexto. Si manana se quiere el comprobante
de una venta, se reutiliza tal cual.

Se genera en el SERVIDOR y no en el navegador por dos razones. La
primera es que la plantilla queda en un solo sitio, en HTML, y no
maquetada a mano dentro de JavaScript. La segunda pesa mas: la fecha de
generacion y el nombre de quien genera el informe los pone el servidor,
que ya sabe quien esta autenticado. Generado en el cliente, ese pie
seria un dato que el propio cliente escribe.
"""

import base64
import logging
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa

from core.exceptions import ErrorAlGenerarPdf

logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def imagen_incrustada(ruta_relativa):
    """Devuelve una imagen de `static/` como URI de datos.

    Se incrusta en el HTML en lugar de dejar que el generador resuelva
    una ruta de archivo. Resolver rutas obliga a un `link_callback` que
    traduce URLs a rutas del disco, y eso se rompe en cuanto cambia
    STATIC_URL o el informe se genera desde otro directorio de trabajo.
    Un URI de datos no depende de nada del entorno.

    El resultado se cachea porque el archivo no cambia mientras el
    proceso vive, y leerlo y codificarlo en cada descarga seria gasto
    puro.
    """
    ruta = Path(settings.BASE_DIR) / "static" / ruta_relativa
    datos = base64.b64encode(ruta.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{datos}"


def render_a_pdf(plantilla, contexto):
    """Renderiza una plantilla y devuelve los bytes del PDF.

    Un fallo aqui no es un error de validacion del usuario: significa
    que la plantilla esta mal. Se traduce a ErrorDeNegocio para que
    salga con el formato uniforme de la API (RNF-06) en lugar de un 500
    con traza, que ademas revelaria rutas internas.
    """
    html = render_to_string(plantilla, contexto)
    salida = BytesIO()

    resultado = pisa.CreatePDF(
        html, dest=salida, encoding="utf-8", raise_exception=False
    )
    if resultado.err:
        logger.error("La plantilla %s no pudo renderizarse a PDF", plantilla)
        raise ErrorAlGenerarPdf()

    return salida.getvalue()
