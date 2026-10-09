"""T-8.3 — Alta con movimiento y ajuste con bloqueo.

Con esta tarea los cuatro caminos que cambian existencias —alta,
venta, anulacion y ajuste— dejan su movimiento (RF-81). Las pruebas
cubren los dos nuevos y una consecuencia que solo se ve con los cuatro
juntos: el libro de un producto cuadra (RN-MOV-03).
"""

from unittest import mock

import pytest
from django.http import Http404
from rest_framework import status
from rest_framework.test import APIClient

from catalogo.models import Producto
from catalogo.services import crear_producto
from catalogo.tests.factories import CategoriaFactory
from core.exceptions import Codigo, ErrorDeNegocio
from inventario.exceptions import AjusteSinDiferencia
from inventario.models import MovimientoStock, TipoMovimiento
from inventario.services import ajustar_existencias
from usuarios.tests.factories import AdministradorFactory, VendedorFactory
from ventas.services import registrar_venta

pytestmark = pytest.mark.django_db

PRODUCTOS = "/api/v1/productos"


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
    return AdministradorFactory()


def _datos(**extra):
    return {
        "nombre": "Teclado mecánico",
        "descripcion": "Switches rojos",
        "precio": 350,
        "stock": 10,
        "categoria": CategoriaFactory(),
        **extra,
    }


def _libro(producto):
    return sum(MovimientoStock.objects.filter(producto=producto).values_list("cantidad", flat=True))


# ─────────────────────────────────────────────────────────────────────
# Alta (CU-CAT-02)
# ─────────────────────────────────────────────────────────────────────
def test_crear_un_producto_deja_su_movimiento_de_alta(admin):
    producto = crear_producto(usuario=admin, **_datos(stock=10))

    [alta] = MovimientoStock.objects.filter(producto=producto)
    assert alta.tipo == TipoMovimiento.ALTA
    assert alta.cantidad == 10
    assert alta.stock_resultante == 10
    assert alta.usuario == admin


def test_un_producto_creado_sin_existencias_tambien_tiene_su_alta(admin):
    """Todo producto tiene un punto de partida en el libro, aunque sea
    cero (RN-MOV-03). Sin el, sus movimientos posteriores no tendrian
    desde donde sumar."""
    producto = crear_producto(usuario=admin, **_datos(stock=0))

    [alta] = MovimientoStock.objects.filter(producto=producto)
    assert (alta.cantidad, alta.stock_resultante) == (0, 0)


def test_el_alta_por_la_api_registra_al_administrador_como_autor(admin):
    categoria = CategoriaFactory()

    respuesta = _autenticar(admin).post(
        PRODUCTOS,
        {"nombre": "Monitor 24", "precio": "750.00", "stock": 4, "categoria": categoria.id},
        format="json",
    )

    assert respuesta.status_code == status.HTTP_201_CREATED
    alta = MovimientoStock.objects.get(producto_id=respuesta.data["id"])
    assert (alta.tipo, alta.cantidad, alta.usuario) == (TipoMovimiento.ALTA, 4, admin)


def test_si_el_alta_no_puede_registrarse_el_producto_no_se_crea(admin):
    with mock.patch(
        "catalogo.services.registrar_movimiento",
        side_effect=RuntimeError("fallo simulado"),
    ):
        with pytest.raises(RuntimeError):
            crear_producto(usuario=admin, **_datos(nombre="No debe existir"))

    assert not Producto.objects.filter(nombre="No debe existir").exists()


# ─────────────────────────────────────────────────────────────────────
# El PATCH ya no toca existencias (RN-CAT-10)
# ─────────────────────────────────────────────────────────────────────
def test_editar_un_producto_no_crea_movimientos(admin):
    producto = crear_producto(usuario=admin, **_datos(stock=10))

    _autenticar(admin).patch(
        f"{PRODUCTOS}/{producto.id}", {"stock": 99, "nombre": "Otro nombre"}, format="json"
    )

    producto.refresh_from_db()
    assert producto.stock == 10
    assert producto.nombre == "Otro nombre"
    assert MovimientoStock.objects.filter(producto=producto).count() == 1  # solo el alta


# ─────────────────────────────────────────────────────────────────────
# Ajuste (CU-CAT-07, RN-MOV-05)
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("contado, diferencia", [(7, -3), (14, 4), (0, -10)])
def test_un_ajuste_registra_la_diferencia_con_signo(admin, contado, diferencia):
    producto = crear_producto(usuario=admin, **_datos(stock=10))

    movimiento = ajustar_existencias(
        producto_id=producto.pk, cantidad_real=contado, motivo="Recuento físico", usuario=admin
    )

    producto.refresh_from_db()
    assert producto.stock == contado
    assert movimiento.tipo == TipoMovimiento.AJUSTE
    assert movimiento.cantidad == diferencia
    assert movimiento.stock_resultante == contado
    assert movimiento.motivo == "Recuento físico"
    assert movimiento.usuario == admin


@pytest.mark.parametrize("motivo", ["", "   ", None])
def test_un_ajuste_sin_motivo_se_rechaza(admin, motivo):
    producto = crear_producto(usuario=admin, **_datos(stock=10))

    with pytest.raises(ErrorDeNegocio) as error:
        ajustar_existencias(producto_id=producto.pk, cantidad_real=8, motivo=motivo, usuario=admin)

    assert error.value.status_code == 400
    assert "motivo" in error.value.errores
    producto.refresh_from_db()
    assert producto.stock == 10


def test_un_ajuste_sin_diferencia_se_rechaza(admin):
    producto = crear_producto(usuario=admin, **_datos(stock=10))

    with pytest.raises(AjusteSinDiferencia) as error:
        ajustar_existencias(producto_id=producto.pk, cantidad_real=10, motivo="Recuento", usuario=admin)

    assert error.value.status_code == 409
    assert error.value.codigo == Codigo.AJUSTE_SIN_DIFERENCIA
    assert MovimientoStock.objects.filter(tipo=TipoMovimiento.AJUSTE).count() == 0


@pytest.mark.parametrize("cantidad", [-1, 2.5, "8", True])
def test_una_cantidad_real_invalida_se_rechaza(admin, cantidad):
    """`True` incluido: en Python es un int, y sin cuidado se aceptaria
    como una existencia de 1."""
    producto = crear_producto(usuario=admin, **_datos(stock=10))

    with pytest.raises(ErrorDeNegocio) as error:
        ajustar_existencias(producto_id=producto.pk, cantidad_real=cantidad, motivo="x", usuario=admin)

    assert "cantidad_real" in error.value.errores


def test_ajustar_un_producto_inexistente_es_404(admin):
    with pytest.raises(Http404):
        ajustar_existencias(producto_id=999999, cantidad_real=1, motivo="x", usuario=admin)


def test_un_producto_retirado_tambien_puede_ajustarse(admin):
    """CU-CAT-07: el inventario fisico importa aunque el producto ya no
    se ofrezca para ventas nuevas."""
    producto = crear_producto(usuario=admin, **_datos(stock=10))
    producto.activo = False
    producto.save(update_fields=["activo"])

    ajustar_existencias(producto_id=producto.pk, cantidad_real=6, motivo="Recuento", usuario=admin)

    producto.refresh_from_db()
    assert producto.stock == 6


def test_si_el_ajuste_no_puede_registrarse_las_existencias_no_cambian(admin):
    producto = crear_producto(usuario=admin, **_datos(stock=10))

    with mock.patch(
        "inventario.services.registrar_movimiento",
        side_effect=RuntimeError("fallo simulado"),
    ):
        with pytest.raises(RuntimeError):
            ajustar_existencias(producto_id=producto.pk, cantidad_real=4, motivo="x", usuario=admin)

    producto.refresh_from_db()
    assert producto.stock == 10


# ─────────────────────────────────────────────────────────────────────
# Los cuatro caminos juntos: el libro cuadra
# ─────────────────────────────────────────────────────────────────────
def test_el_ajuste_se_calcula_contra_las_existencias_vigentes_no_las_que_se_vieron(admin):
    """El escenario de plan.md 6.5, sin concurrencia real.

    El Administrador abre el formulario con 10 unidades y cuenta 12.
    Antes de que confirme, se vende una. Con el PATCH de la v1.3 el
    movimiento habria sido +2 (12 - 10) y el libro sumaria 11 con 12
    en stock. Calculando contra el valor vigente, es +3 y cuadra.
    """
    producto = crear_producto(usuario=admin, **_datos(stock=10))
    visto_al_abrir = producto.stock  # 10

    registrar_venta(
        usuario=VendedorFactory(),
        cliente_nombre="María",
        cliente_telefono="70012345",
        items=[{"producto_id": producto.pk, "cantidad": 1}],
    )
    movimiento = ajustar_existencias(
        producto_id=producto.pk, cantidad_real=12, motivo="Recuento físico", usuario=admin
    )

    producto.refresh_from_db()
    assert movimiento.cantidad == 3, "se calculo contra lo que se vio y no contra lo vigente"
    assert movimiento.cantidad != 12 - visto_al_abrir
    assert producto.stock == 12
    assert _libro(producto) == producto.stock


def test_alta_venta_anulacion_y_ajuste_dejan_el_libro_cuadrado(admin):
    """RN-MOV-03 con los cuatro tipos que puede producir el sistema."""
    from ventas.services import anular_venta

    producto = crear_producto(usuario=admin, **_datos(stock=20))
    vendedor = VendedorFactory()
    venta = registrar_venta(
        usuario=vendedor,
        cliente_nombre="María",
        cliente_telefono="70012345",
        items=[{"producto_id": producto.pk, "cantidad": 5}],
    )
    anular_venta(venta=venta, usuario=admin, motivo="Error")
    ajustar_existencias(producto_id=producto.pk, cantidad_real=17, motivo="Unidades dañadas", usuario=admin)

    producto.refresh_from_db()
    tipos = list(
        MovimientoStock.objects.filter(producto=producto).order_by("id").values_list("tipo", flat=True)
    )
    assert tipos == [TipoMovimiento.ALTA, TipoMovimiento.VENTA, TipoMovimiento.ANULACION, TipoMovimiento.AJUSTE]
    assert _libro(producto) == producto.stock == 17
    ultimo = MovimientoStock.objects.filter(producto=producto).order_by("-id").first()
    assert ultimo.stock_resultante == producto.stock
