"""T-8.5 — La verificacion del libro detecta lo que debe (RN-MOV-03).

El guardian de conftest.py y la prueba de concurrencia confian en
`libros_descuadrados` y `cadena_rota`. Si alguna de las dos dejara de
detectar un descuadre, ambos seguirian en verde sin proteger nada: estas
pruebas descuadran el libro a proposito y comprueban que se nota.

Todas llevan `libro_libre`: el descuadre es deliberado y el guardian no
debe juzgarlas.
"""

import pytest
from django.db.models import F

from catalogo.models import Producto
from catalogo.services import crear_producto
from catalogo.tests.factories import CategoriaFactory, ProductoFactory
from inventario.models import TipoMovimiento
from inventario.services import registrar_movimiento
from inventario.verificacion import cadena_rota, libros_descuadrados
from usuarios.tests.factories import AdministradorFactory

pytestmark = [pytest.mark.django_db, pytest.mark.libro_libre]


@pytest.fixture
def admin():
    return AdministradorFactory()


@pytest.fixture
def producto(admin):
    return crear_producto(
        usuario=admin,
        nombre="Disco SSD 480 GB",
        descripcion="Prueba",
        precio=250,
        stock=10,
        categoria=CategoriaFactory(),
    )


def _ajuste_suelto(producto, admin, cantidad, resultante):
    """Cambia el stock y anota el movimiento con el resultante que se le
    indique, sin bloquear: es lo que haria un camino mal escrito."""
    Producto.objects.filter(pk=producto.pk).update(stock=F("stock") + cantidad)
    registrar_movimiento(
        producto=producto,
        tipo=TipoMovimiento.AJUSTE,
        cantidad=cantidad,
        stock_resultante=resultante,
        usuario=admin,
        motivo="Prueba de verificación",
    )


def test_un_libro_sano_cuadra(producto, admin):
    _ajuste_suelto(producto, admin, -3, 7)

    assert libros_descuadrados() == []
    assert cadena_rota(producto) is None


def test_detecta_un_cambio_de_stock_fuera_del_libro(producto):
    """El caso que el guardian existe para atrapar: un camino nuevo que
    escribe el stock sin pasar por inventario.services."""
    Producto.objects.filter(pk=producto.pk).update(stock=99)

    [descuadre] = libros_descuadrados()

    assert descuadre["id"] == producto.pk
    assert (descuadre["stock"], descuadre["suma"], descuadre["ultimo"]) == (99, 10, 10)


def test_detecta_un_resultante_calculado_contra_un_valor_viejo(producto, admin):
    """La suma cuadra (10 - 1 = 9) pero el ultimo resultante no: el
    ajuste se calculo contra el 10 que ya no estaba."""
    _ajuste_suelto(producto, admin, -1, 10)

    [descuadre] = libros_descuadrados()

    assert (descuadre["stock"], descuadre["suma"], descuadre["ultimo"]) == (9, 9, 10)


def test_la_cadena_detecta_lo_que_la_suma_y_el_ultimo_no_ven(producto, admin):
    """Hallazgo de la prueba de mutacion de T-8.5: sin el bloqueo, un
    resultante viejo puede quedar ENTRE dos movimientos correctos. La
    suma y el ultimo resultante cuadran; solo la cadena lo ve."""
    _ajuste_suelto(producto, admin, -1, 10)  # leyo 10, el stock ya era 9
    _ajuste_suelto(producto, admin, -1, 8)

    assert libros_descuadrados() == []
    roto = cadena_rota(producto)
    assert roto is not None
    assert (roto["esperado"], roto["registrado"]) == (9, 10)


def test_un_producto_sin_punto_de_partida_no_se_juzga():
    """Las fabricas escriben el stock sin libro; juzgarlos haria saltar
    el guardian en cientos de pruebas que no tocan existencias."""
    ProductoFactory(stock=42)

    assert libros_descuadrados() == []


def test_se_puede_acotar_a_unos_productos(producto, admin):
    otro = crear_producto(
        usuario=admin,
        nombre="Memoria RAM 8 GB",
        descripcion="Prueba",
        precio=180,
        stock=5,
        categoria=producto.categoria,
    )
    Producto.objects.filter(pk=otro.pk).update(stock=0)

    assert libros_descuadrados([producto]) == []
    assert [p["id"] for p in libros_descuadrados([otro.pk])] == [otro.pk]
