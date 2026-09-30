"""Informe de servicio en PDF (RF-67).

Lo que mas importa aqui no es que el PDF salga, sino que NO salga
cuando no debe: el informe lleva el nombre y el telefono de un cliente,
asi que su visibilidad tiene que ser exactamente la del detalle
(RN-SER-15, RF-64). Un endpoint de descarga que se saltara ese filtro
seria una fuga de datos por la puerta de atras.
"""

from decimal import Decimal

import pytest
from pypdf import PdfReader
from io import BytesIO
from rest_framework import status
from rest_framework.test import APIClient

from servicios.models import EstadoSolicitud
from servicios.tests.factories import SolicitudFactory
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)

pytestmark = pytest.mark.django_db


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
    """El texto real del PDF, no el HTML que lo origino."""
    lector = PdfReader(BytesIO(respuesta.content))
    return "\n".join(pagina.extract_text() for pagina in lector.pages)


@pytest.fixture
def tecnico():
    return TecnicoFactory(username="arojas", nombre_completo="Ana Rojas")


@pytest.fixture
def solicitud(tecnico):
    return SolicitudFactory(
        cliente_nombre="María Gutiérrez",
        cliente_telefono="70012345",
        descripcion="La laptop no enciende tras una subida de tensión.",
        observaciones="Se reemplazó la fuente de poder.",
        tecnico="Pedro Mamani",
        monto_cobrado=Decimal("250.00"),
        estado=EstadoSolicitud.FINALIZADA,
        registrada_por=tecnico,
        fecha_cierre="2026-09-29T15:00:00Z",
        cerrada_por=tecnico,
    )


class TestDescarga:
    def test_devuelve_un_pdf(self, tecnico, solicitud):
        respuesta = _autenticar(tecnico).get(
            f"/api/v1/solicitudes/{solicitud.pk}/pdf"
        )

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta["Content-Type"] == "application/pdf"
        assert respuesta.content[:4] == b"%PDF"

    def test_propone_un_nombre_de_archivo_con_el_numero(self, tecnico, solicitud):
        """Sin esto el cliente acabaria con varios "descarga.pdf"."""
        respuesta = _autenticar(tecnico).get(
            f"/api/v1/solicitudes/{solicitud.pk}/pdf"
        )

        assert (
            f"informe-servicio-{solicitud.pk}.pdf"
            in respuesta["Content-Disposition"]
        )

    def test_el_texto_es_seleccionable_no_una_imagen(self, tecnico, solicitud):
        """El informe se genera como texto real.

        Es la diferencia entre este enfoque y capturar la pantalla:
        un PDF de imagen no se puede buscar, ni copiar, ni leer con un
        lector de pantalla.
        """
        respuesta = _autenticar(tecnico).get(
            f"/api/v1/solicitudes/{solicitud.pk}/pdf"
        )

        assert "PC-SOLUTION" in _texto(respuesta)


class TestContenido:
    def test_lleva_los_datos_del_trabajo(self, tecnico, solicitud):
        texto = _texto(
            _autenticar(tecnico).get(f"/api/v1/solicitudes/{solicitud.pk}/pdf")
        )

        assert "María Gutiérrez" in texto
        assert "70012345" in texto
        assert "Pedro Mamani" in texto
        assert "250,00" in texto or "250.00" in texto
        assert "Se reemplazó la fuente de poder." in texto

    def test_no_se_escapa_sintaxis_de_plantilla(self, tecnico, solicitud):
        """Ningun resto del lenguaje de plantillas llega al papel.

        Esta prueba existe por un fallo real: un comentario escrito
        como {#...#} en DOS lineas se imprimio tal cual en el informe.
        Django solo admite esa forma en una linea; en varias, el texto
        pasa a ser contenido. Las pruebas que buscan cadenas concretas
        no lo veian, porque los datos del cliente si salian bien.
        """
        texto = _texto(
            _autenticar(tecnico).get(f"/api/v1/solicitudes/{solicitud.pk}/pdf")
        )

        for resto in ("{#", "#}", "{%", "%}", "{{", "}}"):
            assert resto not in texto, f"El informe imprime «{resto}»"

    def test_dice_quien_lo_genero(self, tecnico, solicitud):
        """RF-67. Lo pone el SERVIDOR, que es la razon de generarlo aqui."""
        texto = _texto(
            _autenticar(tecnico).get(f"/api/v1/solicitudes/{solicitud.pk}/pdf")
        )

        assert "Ana Rojas" in texto

    def test_lo_genera_quien_descarga_no_quien_registro(self, tecnico, solicitud):
        """El pie nombra al que pidio el informe, no al registrador.

        Los dos pueden ser personas distintas: el Administrador
        descarga informes de solicitudes que registro otro.
        """
        admin = AdministradorFactory(
            username="admin", nombre_completo="Carlos Vargas"
        )
        texto = _texto(
            _autenticar(admin).get(f"/api/v1/solicitudes/{solicitud.pk}/pdf")
        )

        assert "Carlos Vargas" in texto

    def test_una_solicitud_sin_cotizar_lo_dice_en_palabras(self, tecnico):
        """RN-SER-17: sin cotizar no es lo mismo que cotizado en cero.

        Si el informe imprimiera "Bs 0,00" para una solicitud que nadie
        cotizo todavia, el cliente se llevaria por escrito que su
        servicio es gratuito.
        """
        abierta = SolicitudFactory(registrada_por=tecnico, monto_cobrado=None)
        texto = _texto(
            _autenticar(tecnico).get(f"/api/v1/solicitudes/{abierta.pk}/pdf")
        )

        assert "Pendiente de cotización" in texto
        assert "Bs 0,00" not in texto

    def test_un_servicio_de_cortesia_imprime_cero(self, tecnico):
        """La otra mitad de RN-SER-17: cero cotizado si es un importe."""
        cortesia = SolicitudFactory(
            registrada_por=tecnico, monto_cobrado=Decimal("0.00")
        )
        texto = _texto(
            _autenticar(tecnico).get(f"/api/v1/solicitudes/{cortesia.pk}/pdf")
        )

        assert "0,00" in texto
        assert "Pendiente de cotización" not in texto

    def test_una_solicitud_en_curso_sirve_de_constancia(self, tecnico):
        """RF-67: el informe no espera a que el servicio termine.

        El cliente deja su equipo y se va; ese es justo el momento en
        que necesita un papel.
        """
        en_curso = SolicitudFactory(
            registrada_por=tecnico, estado=EstadoSolicitud.EN_ATENCION
        )
        texto = _texto(
            _autenticar(tecnico).get(f"/api/v1/solicitudes/{en_curso.pk}/pdf")
        )

        assert "constancia de recepción" in texto

    def test_sin_tecnico_anotado_no_deja_el_hueco_en_blanco(self, tecnico):
        """RN-SER-09: el tecnico es texto libre y puede no estar puesto."""
        sin_tecnico = SolicitudFactory(registrada_por=tecnico, tecnico="")
        texto = _texto(
            _autenticar(tecnico).get(f"/api/v1/solicitudes/{sin_tecnico.pk}/pdf")
        )

        assert "Por asignar" in texto


class TestVisibilidad:
    def test_un_tecnico_no_descarga_el_informe_de_otro(self, solicitud):
        """RN-SER-15 y RF-64 — lo que esta prueba protege de verdad.

        404 y no 403: un 403 confirmaria que esa solicitud existe.
        """
        otro = TecnicoFactory(username="mlopez")

        respuesta = _autenticar(otro).get(
            f"/api/v1/solicitudes/{solicitud.pk}/pdf"
        )

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND

    def test_el_administrador_descarga_cualquiera(self, solicitud):
        admin = AdministradorFactory(username="admin")

        respuesta = _autenticar(admin).get(
            f"/api/v1/solicitudes/{solicitud.pk}/pdf"
        )

        assert respuesta.status_code == status.HTTP_200_OK

    def test_un_vendedor_no_entra_al_modulo(self, solicitud):
        vendedor = VendedorFactory(username="jperez")

        respuesta = _autenticar(vendedor).get(
            f"/api/v1/solicitudes/{solicitud.pk}/pdf"
        )

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN

    def test_sin_sesion_no_hay_informe(self, solicitud):
        """RNF-01."""
        respuesta = APIClient().get(f"/api/v1/solicitudes/{solicitud.pk}/pdf")

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
