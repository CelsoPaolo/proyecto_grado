"""T-4.6 y T-4.7 — API de ventas (RF-15 a RF-27, RF-54)."""

from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.tests.factories import ProductoFactory
from core.exceptions import Codigo
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)
from ventas.models import EstadoVenta, Venta
from ventas.services import registrar_venta

pytestmark = pytest.mark.django_db

BASE = "/api/v1/ventas"


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
def vendedor():
    return VendedorFactory(username="jperez", nombre_completo="Juan Pérez")


@pytest.fixture
def como_vendedor(vendedor):
    return _autenticar(vendedor)


@pytest.fixture
def como_admin():
    return _autenticar(AdministradorFactory(username="admin"))


def _cuerpo(producto, cantidad=1):
    return {
        "cliente_nombre": "María Gutiérrez",
        "cliente_telefono": "70012345",
        "items": [{"producto_id": producto.id, "cantidad": cantidad}],
    }


# ═════════════════════════════════════════════════════════════════════
# T-4.6 — Registro (RF-15 a RF-20)
# ═════════════════════════════════════════════════════════════════════
def test_registrar_una_venta_devuelve_el_detalle_congelado(como_vendedor):
    producto = ProductoFactory(
        nombre="Teclado mecánico", stock=10, precio=Decimal("350.00")
    )

    respuesta = como_vendedor.post(BASE, _cuerpo(producto, 2), format="json")

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["estado"] == EstadoVenta.CONFIRMADA
    assert respuesta.data["total"] == "700.00"
    linea = respuesta.data["items"][0]
    assert linea["producto_nombre"] == "Teclado mecánico"
    assert linea["precio_unitario"] == "350.00"
    assert linea["subtotal"] == "700.00"


def test_los_importes_viajan_como_cadena_decimal(como_vendedor):
    """plan.md 4.1: nunca coma flotante, para no perder precision en
    el trayecto."""
    producto = ProductoFactory(stock=10, precio=Decimal("33.33"))

    respuesta = como_vendedor.post(BASE, _cuerpo(producto, 3), format="json")

    assert respuesta.data["total"] == "99.99"
    assert isinstance(respuesta.data["total"], str)


def test_el_stock_insuficiente_responde_422_con_el_detalle(como_vendedor):
    """RF-17. Se reserva el 422 para este caso porque es el unico error
    que el frontend debe mostrar enriquecido (plan.md 4.2)."""
    producto = ProductoFactory(nombre="Escaso", stock=2)

    respuesta = como_vendedor.post(BASE, _cuerpo(producto, 5), format="json")

    assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert respuesta.data["codigo"] == Codigo.STOCK_INSUFICIENTE
    faltante = respuesta.data["errores"]["items"][0]
    assert faltante["nombre"] == "Escaso"
    assert faltante["solicitado"] == 5
    assert faltante["disponible"] == 2


def test_una_venta_sin_items_se_rechaza(como_vendedor):
    """RN-VEN-01."""
    respuesta = como_vendedor.post(
        BASE,
        {"cliente_nombre": "X", "cliente_telefono": "7", "items": []},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "items" in respuesta.data["errores"]


def test_una_cantidad_cero_o_negativa_se_rechaza(como_vendedor):
    producto = ProductoFactory(stock=10)

    respuesta = como_vendedor.post(BASE, _cuerpo(producto, 0), format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST


def test_faltan_los_datos_del_cliente(como_vendedor):
    """RN-VEN-10: nombre y telefono son obligatorios."""
    producto = ProductoFactory(stock=10)

    respuesta = como_vendedor.post(
        BASE,
        {"items": [{"producto_id": producto.id, "cantidad": 1}]},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "cliente_nombre" in respuesta.data["errores"]
    assert "cliente_telefono" in respuesta.data["errores"]


def test_el_cliente_no_puede_imponer_el_precio(como_vendedor):
    """RN-VEN-04. Enviar un precio en el cuerpo no tiene efecto: el
    servidor lo toma del catalogo."""
    producto = ProductoFactory(stock=10, precio=Decimal("350.00"))

    respuesta = como_vendedor.post(
        BASE,
        {
            "cliente_nombre": "María Gutiérrez",
            "cliente_telefono": "70012345",
            "items": [
                {"producto_id": producto.id, "cantidad": 1, "precio_unitario": "1.00"}
            ],
        },
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["items"][0]["precio_unitario"] == "350.00"
    assert respuesta.data["total"] == "350.00"


# ═════════════════════════════════════════════════════════════════════
# RN-VEN-06 y RF-26 — la venta no se edita ni se elimina
# ═════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("metodo", ["put", "patch", "delete"])
def test_no_existen_verbos_de_escritura_sobre_una_venta(
    como_admin, vendedor, metodo
):
    """El criterio de T-4.6.

    La AUSENCIA de estos verbos es la implementacion de RN-VEN-06: el
    contrato mismo expresa que una venta confirmada no se toca.
    """
    producto = ProductoFactory(stock=10)
    venta = registrar_venta(
        usuario=vendedor,
        cliente_nombre="X",
        cliente_telefono="7",
        items=[{"producto_id": producto.id, "cantidad": 1}],
    )

    respuesta = getattr(como_admin, metodo)(f"{BASE}/{venta.id}", {}, format="json")

    assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ═════════════════════════════════════════════════════════════════════
# T-4.7 — Historial filtrado por rol (RF-21, RF-22, RF-27)
# ═════════════════════════════════════════════════════════════════════
def _venta_de(usuario, stock=10, cantidad=1):
    producto = ProductoFactory(stock=stock)
    return registrar_venta(
        usuario=usuario,
        cliente_nombre="Cliente",
        cliente_telefono="70000000",
        items=[{"producto_id": producto.id, "cantidad": cantidad}],
    )


def test_el_vendedor_solo_ve_sus_propias_ventas(como_vendedor, vendedor):
    """RF-21 y RN-VEN-09."""
    propia = _venta_de(vendedor)
    ajena = _venta_de(VendedorFactory(username="otro"))

    respuesta = como_vendedor.get(BASE)

    ids = [v["id"] for v in respuesta.data["results"]]
    assert propia.id in ids
    assert ajena.id not in ids


def test_el_vendedor_no_accede_al_detalle_de_una_venta_ajena(como_vendedor):
    """El criterio duro de RF-27: ni siquiera pidiendo el id directo."""
    ajena = _venta_de(VendedorFactory(username="otro"))

    respuesta = como_vendedor.get(f"{BASE}/{ajena.id}")

    assert respuesta.status_code == status.HTTP_404_NOT_FOUND


def test_el_vendedor_no_puede_anular_una_venta_ajena(como_vendedor):
    """RF-27."""
    ajena = _venta_de(VendedorFactory(username="otro"))

    respuesta = como_vendedor.post(
        f"{BASE}/{ajena.id}/anular", {"motivo": "Intento"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_404_NOT_FOUND
    ajena.refresh_from_db()
    assert ajena.estado == EstadoVenta.CONFIRMADA


def test_el_administrador_ve_todas_las_ventas(como_admin, vendedor):
    """RF-21."""
    primera = _venta_de(vendedor)
    segunda = _venta_de(VendedorFactory(username="otro"))

    respuesta = como_admin.get(BASE)

    ids = [v["id"] for v in respuesta.data["results"]]
    assert primera.id in ids
    assert segunda.id in ids


def test_el_administrador_puede_anular_una_venta_de_otro(como_admin, vendedor):
    venta = _venta_de(vendedor)

    respuesta = como_admin.post(
        f"{BASE}/{venta.id}/anular", {"motivo": "Error detectado"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta.data["estado"] == EstadoVenta.ANULADA


def test_se_filtra_por_estado(como_admin, vendedor):
    """RF-22."""
    confirmada = _venta_de(vendedor)
    anulada = _venta_de(vendedor)
    como_admin.post(
        f"{BASE}/{anulada.id}/anular", {"motivo": "Prueba"}, format="json"
    )

    respuesta = como_admin.get(f"{BASE}?estado=CONFIRMADA")

    ids = [v["id"] for v in respuesta.data["results"]]
    assert confirmada.id in ids
    assert anulada.id not in ids


def test_se_filtra_por_rango_de_fechas(como_admin, vendedor):
    """RF-22."""
    from datetime import timedelta

    from django.utils import timezone

    antigua = _venta_de(vendedor)
    Venta.objects.filter(pk=antigua.pk).update(
        fecha_hora=timezone.now() - timedelta(days=30)
    )
    reciente = _venta_de(vendedor)

    hoy = timezone.localdate().isoformat()
    respuesta = como_admin.get(f"{BASE}?desde={hoy}")

    ids = [v["id"] for v in respuesta.data["results"]]
    assert reciente.id in ids
    assert antigua.id not in ids


def test_el_historial_viene_paginado_y_sin_el_detalle(como_admin, vendedor):
    """RNF-18. El listado no incluye `items`: no hace falta para listar
    y multiplicaria las consultas."""
    for _ in range(3):
        _venta_de(vendedor)

    respuesta = como_admin.get(BASE)

    assert "results" in respuesta.data
    fila = respuesta.data["results"][0]
    assert "items" not in fila
    assert fila["cantidad_items"] == 1


def test_el_detalle_incluye_las_lineas_congeladas(como_vendedor, vendedor):
    """RF-23."""
    venta = _venta_de(vendedor)

    respuesta = como_vendedor.get(f"{BASE}/{venta.id}")

    assert respuesta.status_code == status.HTTP_200_OK
    assert len(respuesta.data["items"]) == 1
    assert "producto_nombre" in respuesta.data["items"][0]


# ═════════════════════════════════════════════════════════════════════
# Anulacion por la API (RF-24, RF-25, RF-54)
# ═════════════════════════════════════════════════════════════════════
def test_anular_devuelve_las_existencias(como_vendedor, vendedor):
    """RF-25."""
    producto = ProductoFactory(stock=10)
    venta = registrar_venta(
        usuario=vendedor,
        cliente_nombre="Cliente",
        cliente_telefono="7",
        items=[{"producto_id": producto.id, "cantidad": 4}],
    )
    producto.refresh_from_db()
    assert producto.stock == 6

    respuesta = como_vendedor.post(
        f"{BASE}/{venta.id}/anular", {"motivo": "Cliente se arrepintió"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_200_OK
    producto.refresh_from_db()
    assert producto.stock == 10


def test_la_anulacion_exige_motivo(como_vendedor, vendedor):
    """RN-VEN-07."""
    venta = _venta_de(vendedor)

    respuesta = como_vendedor.post(
        f"{BASE}/{venta.id}/anular", {"motivo": "   "}, format="json"
    )

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert "motivo" in respuesta.data["errores"]


def test_anular_dos_veces_responde_409(como_vendedor, vendedor):
    """RN-VEN-08."""
    venta = _venta_de(vendedor)
    como_vendedor.post(
        f"{BASE}/{venta.id}/anular", {"motivo": "Primera"}, format="json"
    )

    respuesta = como_vendedor.post(
        f"{BASE}/{venta.id}/anular", {"motivo": "Segunda"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.VENTA_YA_ANULADA


def test_la_respuesta_de_anulacion_incluye_la_trazabilidad(como_admin, vendedor):
    """RN-VEN-07."""
    venta = _venta_de(vendedor)

    respuesta = como_admin.post(
        f"{BASE}/{venta.id}/anular", {"motivo": "Error de registro"}, format="json"
    )

    assert respuesta.data["motivo_anulacion"] == "Error de registro"
    assert respuesta.data["anulada_por"]["nombre_completo"] is not None
    assert respuesta.data["fecha_anulacion"] is not None


# ═════════════════════════════════════════════════════════════════════
# RNF-02 — el Encargado de Servicios no accede a ventas
# ═════════════════════════════════════════════════════════════════════
def test_el_encargado_de_servicios_no_accede_a_ventas():
    """spec.md matriz 4.4."""
    cliente = _autenticar(TecnicoFactory())

    assert cliente.get(BASE).status_code == status.HTTP_403_FORBIDDEN


def test_la_paginacion_del_historial_es_estable(como_admin, vendedor):
    """RNF-18.

    annotate() con agregacion descarta el orden por defecto del modelo,
    y sin orden la paginacion repite o salta filas entre paginas. Ya
    ocurrio en el catalogo (T-2.2); aqui queda cubierto.

    Se desempata ademas por id porque varias ventas creadas en la misma
    prueba pueden compartir el mismo instante y solo con la fecha el
    orden seguiria siendo ambiguo.
    """
    for _ in range(25):
        _venta_de(vendedor)

    pagina1 = como_admin.get(f"{BASE}?page=1")
    pagina2 = como_admin.get(f"{BASE}?page=2")

    ids1 = {v["id"] for v in pagina1.data["results"]}
    ids2 = {v["id"] for v in pagina2.data["results"]}

    assert len(ids1) == 20
    assert len(ids2) == 5
    assert ids1.isdisjoint(ids2)
