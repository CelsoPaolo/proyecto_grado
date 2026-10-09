"""T-8.6 — API del libro de movimientos y del ajuste.

RF-73 (ajustar), RF-82 (consultar con filtros), RF-83 (historial del
producto), RN-MOV-06 (solo el Administrador) y RNF-18 (paginado).

Quien puede entrar a cada ruta ya lo recorre la matriz de T-1.8 para
los tres roles; aqui se repite solo el criterio de T-8.6 sobre el
Encargado de Ventas, que es el caso con mas riesgo: el catalogo si es
suyo, el libro no.
"""

from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.models import Producto
from catalogo.services import crear_producto, retirar_producto
from catalogo.tests.factories import CategoriaFactory
from core.exceptions import Codigo
from inventario.models import MovimientoStock, TipoMovimiento
from inventario.services import ajustar_existencias
from usuarios.tests.factories import (
    AdministradorFactory,
    TecnicoFactory,
    VendedorFactory,
)
from ventas.services import registrar_venta

pytestmark = pytest.mark.django_db

MOVIMIENTOS = "/api/v1/movimientos-stock"
LA_PAZ = ZoneInfo("America/La_Paz")


def _ajustar_url(producto):
    return f"/api/v1/productos/{producto.pk}/ajustar-existencias"


def _historial_url(producto):
    return f"/api/v1/productos/{producto.pk}/movimientos"


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
def admin():
    return AdministradorFactory(nombre_completo="Ana Administradora")


@pytest.fixture
def cliente(admin):
    return _autenticar(admin)


@pytest.fixture
def categoria():
    return CategoriaFactory()


def _producto(admin, categoria, nombre="Disco SSD 480 GB", stock=10):
    return crear_producto(
        usuario=admin,
        nombre=nombre,
        descripcion="Prueba",
        precio=250,
        stock=stock,
        categoria=categoria,
    )


@pytest.fixture
def producto(admin, categoria):
    return _producto(admin, categoria)


def _vender(producto, usuario, cantidad=1):
    return registrar_venta(
        usuario=usuario,
        cliente_nombre="Cliente",
        cliente_telefono="70000000",
        items=[{"producto_id": producto.pk, "cantidad": cantidad}],
    )


# ─────────────────────────────────────────────────────────────────────
# Acceso (RN-MOV-06) y ausencia de escritura (RNF-25)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("fabrica", [VendedorFactory, TecnicoFactory], ids=["ventas", "servicios"])
def test_solo_el_administrador_entra_al_libro(producto, fabrica):
    otro = _autenticar(fabrica())

    assert otro.get(MOVIMIENTOS).status_code == status.HTTP_403_FORBIDDEN
    assert otro.get(_historial_url(producto)).status_code == status.HTTP_403_FORBIDDEN
    respuesta = otro.post(
        _ajustar_url(producto), {"cantidad_real": 3, "motivo": "Recuento"}, format="json"
    )
    assert respuesta.status_code == status.HTTP_403_FORBIDDEN

    producto.refresh_from_db()
    assert producto.stock == 10


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_el_libro_no_tiene_verbos_de_escritura(cliente, producto, metodo):
    """RNF-25 en la API: ni siquiera el Administrador escribe el libro."""
    respuesta = getattr(cliente, metodo)(MOVIMIENTOS, {}, format="json")

    assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.parametrize("metodo", ["get", "put", "patch", "delete"])
def test_un_movimiento_suelto_no_tiene_ruta(cliente, producto, metodo):
    """No hay detalle: no hay un recurso individual que editar o borrar."""
    movimiento = MovimientoStock.objects.get(producto=producto)

    respuesta = getattr(cliente, metodo)(f"{MOVIMIENTOS}/{movimiento.pk}", {}, format="json")

    assert respuesta.status_code == status.HTTP_404_NOT_FOUND
    assert MovimientoStock.objects.filter(pk=movimiento.pk).exists()


# ─────────────────────────────────────────────────────────────────────
# Ajustar existencias (CU-CAT-07, RF-73)
# ─────────────────────────────────────────────────────────────────────
def test_ajustar_deja_las_existencias_en_lo_contado(cliente, producto, admin):
    respuesta = cliente.post(
        _ajustar_url(producto),
        {"cantidad_real": 7, "motivo": "Recuento físico"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    assert respuesta.data["tipo"] == TipoMovimiento.AJUSTE
    assert respuesta.data["tipo_display"] == "Ajuste manual"
    assert respuesta.data["cantidad"] == -3
    assert respuesta.data["stock_resultante"] == 7
    assert respuesta.data["motivo"] == "Recuento físico"
    assert respuesta.data["usuario"] == admin.pk
    assert respuesta.data["usuario_nombre"] == "Ana Administradora"
    assert respuesta.data["producto_nombre"] == "Disco SSD 480 GB"
    producto.refresh_from_db()
    assert producto.stock == 7


def test_la_diferencia_se_calcula_contra_las_existencias_vigentes(cliente, producto, admin):
    """CU-CAT-07 paso 3: si se vendio mientras el formulario estaba
    abierto, cuenta lo que hay al confirmar, no lo que se vio. La API ni
    siquiera recibe el valor que mostraba la interfaz."""
    _vender(producto, VendedorFactory(), cantidad=2)  # 10 → 8

    respuesta = cliente.post(
        _ajustar_url(producto), {"cantidad_real": 9, "motivo": "Recuento"}, format="json"
    )

    assert respuesta.data["cantidad"] == 1  # contra 8, no contra 10
    assert respuesta.data["stock_resultante"] == 9


def test_se_puede_ajustar_un_producto_retirado(cliente, producto):
    """CU-CAT-07: precondicion «activo o retirado». Sus unidades siguen
    en el almacen y pueden contarse."""
    retirar_producto(producto=producto)

    respuesta = cliente.post(
        _ajustar_url(producto), {"cantidad_real": 0, "motivo": "Baja por daño"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    ("cuerpo", "campo"),
    [
        ({"cantidad_real": 5}, "motivo"),
        ({"cantidad_real": 5, "motivo": ""}, "motivo"),
        ({"cantidad_real": 5, "motivo": "    "}, "motivo"),
        ({"cantidad_real": 5, "motivo": "x" * 501}, "motivo"),
        ({"motivo": "Recuento"}, "cantidad_real"),
        ({"cantidad_real": -1, "motivo": "Recuento"}, "cantidad_real"),
        ({"cantidad_real": 2.5, "motivo": "Recuento"}, "cantidad_real"),
        ({"cantidad_real": "doce", "motivo": "Recuento"}, "cantidad_real"),
        ({"cantidad_real": True, "motivo": "Recuento"}, "cantidad_real"),
        ({"cantidad_real": None, "motivo": "Recuento"}, "cantidad_real"),
    ],
    ids=[
        "sin-motivo", "motivo-vacio", "motivo-en-blanco", "motivo-largo",
        "sin-cantidad", "negativa", "decimal", "texto", "booleano", "nula",
    ],
)
def test_un_ajuste_invalido_se_rechaza_junto_al_campo(cliente, producto, cuerpo, campo):
    """RN-MOV-05 y RNF-15: 400 con el error en su campo, y nada cambia."""
    respuesta = cliente.post(_ajustar_url(producto), cuerpo, format="json")

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert campo in respuesta.data["errores"]
    producto.refresh_from_db()
    assert producto.stock == 10
    assert not MovimientoStock.objects.filter(producto=producto, tipo=TipoMovimiento.AJUSTE).exists()


def test_ajustar_a_lo_mismo_que_hay_responde_409(cliente, producto):
    respuesta = cliente.post(
        _ajustar_url(producto), {"cantidad_real": 10, "motivo": "Recuento"}, format="json"
    )

    assert respuesta.status_code == status.HTTP_409_CONFLICT
    assert respuesta.data["codigo"] == Codigo.AJUSTE_SIN_DIFERENCIA
    assert not MovimientoStock.objects.filter(producto=producto, tipo=TipoMovimiento.AJUSTE).exists()


@pytest.mark.parametrize("pk", ["999999", "abc"])
def test_ajustar_un_producto_inexistente_responde_404(cliente, pk):
    respuesta = cliente.post(
        f"/api/v1/productos/{pk}/ajustar-existencias",
        {"cantidad_real": 3, "motivo": "Recuento"},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────────────────────────────────────────────────────────
# Historial de un producto (CU-CAT-08, RF-83)
# ─────────────────────────────────────────────────────────────────────
def test_el_historial_muestra_solo_ese_producto_del_mas_reciente_al_mas_antiguo(
    cliente, producto, admin, categoria
):
    otro = _producto(admin, categoria, nombre="Memoria RAM 8 GB", stock=4)
    venta = _vender(producto, VendedorFactory(), cantidad=2)
    ajustar_existencias(producto_id=producto.pk, cantidad_real=5, motivo="Rotura", usuario=admin)
    _vender(otro, VendedorFactory())

    respuesta = cliente.get(_historial_url(producto))

    assert respuesta.status_code == status.HTTP_200_OK
    filas = respuesta.data["results"]
    assert [(f["tipo"], f["cantidad"], f["stock_resultante"]) for f in filas] == [
        (TipoMovimiento.AJUSTE, -3, 5),
        (TipoMovimiento.VENTA, -2, 8),
        (TipoMovimiento.ALTA, 10, 10),
    ]
    assert filas[1]["venta"] == venta.pk
    assert {f["producto"] for f in filas} == {producto.pk}


def test_el_historial_esta_paginado(cliente, producto, admin):
    """RNF-18. 25 ajustes + el alta = 26 movimientos."""
    for contado in range(11, 36):
        ajustar_existencias(
            producto_id=producto.pk, cantidad_real=contado, motivo="Recuento", usuario=admin
        )

    primera = cliente.get(_historial_url(producto)).data
    segunda = cliente.get(_historial_url(producto), {"page": 2}).data

    assert primera["count"] == 26
    assert len(primera["results"]) == 20
    assert len(segunda["results"]) == 6
    ids = [f["id"] for f in primera["results"] + segunda["results"]]
    assert len(set(ids)) == 26  # ni repetidos ni saltados entre paginas


def test_el_saldo_inicial_aparece_sin_autor(cliente, producto):
    """El que crea la migracion de T-8.4 no tiene persona detras."""
    otro = Producto.objects.create(
        nombre="Producto antiguo", descripcion="d", precio=1, stock=3, categoria=producto.categoria
    )
    from django.db import transaction

    from inventario.services import registrar_movimiento

    with transaction.atomic():
        registrar_movimiento(
            producto=otro, tipo=TipoMovimiento.SALDO_INICIAL, cantidad=3, stock_resultante=3
        )

    [fila] = cliente.get(_historial_url(otro)).data["results"]

    assert fila["usuario"] is None
    assert fila["usuario_nombre"] is None
    assert fila["tipo_display"] == "Saldo inicial"


def test_el_historial_de_un_producto_inexistente_responde_404(cliente):
    assert cliente.get("/api/v1/productos/999999/movimientos").status_code == 404


# ─────────────────────────────────────────────────────────────────────
# Listado general con filtros (CU-CAT-08, RF-82)
# ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def libro_variado(admin, categoria):
    """Dos productos con altas, una venta y un ajuste cada uno."""
    disco = _producto(admin, categoria, nombre="Disco", stock=10)
    ram = _producto(admin, categoria, nombre="RAM", stock=6)
    vendedor = VendedorFactory()
    _vender(disco, vendedor)
    _vender(ram, vendedor)
    ajustar_existencias(producto_id=disco.pk, cantidad_real=4, motivo="Rotura", usuario=admin)
    ajustar_existencias(producto_id=ram.pk, cantidad_real=9, motivo="Recuento", usuario=admin)
    return disco, ram


def _tipos(respuesta):
    return sorted((f["producto_nombre"], f["tipo"]) for f in respuesta.data["results"])


def test_sin_filtros_lista_todo_paginado(cliente, libro_variado):
    respuesta = cliente.get(MOVIMIENTOS)

    assert respuesta.status_code == status.HTTP_200_OK
    assert respuesta.data["count"] == 6
    assert {"count", "next", "previous", "results"} <= set(respuesta.data)


def test_filtra_por_producto(cliente, libro_variado):
    disco, _ = libro_variado

    respuesta = cliente.get(MOVIMIENTOS, {"producto": disco.pk})

    assert _tipos(respuesta) == [("Disco", "AJUSTE"), ("Disco", "ALTA"), ("Disco", "VENTA")]


def test_filtra_por_tipo(cliente, libro_variado):
    respuesta = cliente.get(MOVIMIENTOS, {"tipo": "AJUSTE"})

    assert _tipos(respuesta) == [("Disco", "AJUSTE"), ("RAM", "AJUSTE")]


def test_los_filtros_se_combinan(cliente, libro_variado):
    _, ram = libro_variado

    respuesta = cliente.get(MOVIMIENTOS, {"producto": ram.pk, "tipo": "VENTA"})

    assert _tipos(respuesta) == [("RAM", "VENTA")]


def _en(hora_local):
    return mock.patch("django.utils.timezone.now", return_value=hora_local)


def test_filtra_por_rango_de_fechas_en_hora_de_bolivia(cliente, admin, categoria):
    """El 30/09 a las 23:30 en La Paz ya es 01/10 en UTC. Para el
    usuario ese movimiento es del 30, y asi debe filtrarse."""
    with _en(datetime(2026, 9, 29, 12, 0, tzinfo=LA_PAZ)):
        producto = _producto(admin, categoria, stock=10)  # ALTA el 29
    with _en(datetime(2026, 9, 30, 23, 30, tzinfo=LA_PAZ)):
        ajustar_existencias(producto_id=producto.pk, cantidad_real=8, motivo="A", usuario=admin)
    with _en(datetime(2026, 10, 1, 9, 0, tzinfo=LA_PAZ)):
        ajustar_existencias(producto_id=producto.pk, cantidad_real=6, motivo="B", usuario=admin)

    def motivos(**filtros):
        return sorted(f["motivo"] for f in cliente.get(MOVIMIENTOS, filtros).data["results"])

    assert motivos(desde="2026-09-30", hasta="2026-09-30") == ["A"]
    assert motivos(desde="2026-09-30") == ["A", "B"]
    assert motivos(hasta="2026-09-30") == ["", "A"]  # el alta no tiene motivo
    assert motivos(desde="2026-10-01", tipo="AJUSTE") == ["B"]


@pytest.mark.parametrize(
    ("filtros", "campo"),
    [
        ({"producto": "abc"}, "producto"),
        ({"producto": "-1"}, "producto"),
        ({"producto": "²"}, "producto"),
        ({"producto": "9" * 30}, "producto"),
        ({"tipo": "ROBO"}, "tipo"),
        ({"desde": "30/09/2026"}, "desde"),
        ({"hasta": "2026-02-30"}, "hasta"),
    ],
    ids=["texto", "negativo", "superindice", "desborde", "tipo", "formato", "imposible"],
)
def test_un_filtro_invalido_responde_400_en_vez_de_ignorarse(cliente, libro_variado, filtros, campo):
    """En una auditoria, una lista completa porque el filtro no se
    aplico pareceria una respuesta valida y no lo seria."""
    respuesta = cliente.get(MOVIMIENTOS, filtros)

    assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
    assert campo in respuesta.data["errores"]
