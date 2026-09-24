"""T-2.1 — Modelos de catalogo y sus restricciones en la base.

El criterio central de la tarea: la base debe rechazar los datos
invalidos **aunque se salte la validacion de Django**. Una regla que
solo vive en el ORM no es una garantia, es una costumbre.
"""

import pytest
from django.db import IntegrityError, connection, transaction

from catalogo.models import Categoria, Producto

from .factories import CategoriaFactory, ProductoFactory

pytestmark = pytest.mark.django_db


def _escribir_saltando_django(sql, parametros):
    """Escribe directamente en la base, sin pasar por el ORM.

    Es la unica forma honesta de comprobar que la restriccion vive en
    la base y no solo en Python.
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, parametros)


# ─────────────────────────────────────────────────────────────────────
# RN-CAT-02 — existencias nunca negativas (y ultima defensa de RNF-08)
# ─────────────────────────────────────────────────────────────────────
def test_la_base_rechaza_stock_negativo_aunque_se_salte_django():
    """El criterio central de T-2.1.

    Si un cambio futuro rompiera la validacion del servicio de ventas,
    esta restriccion es lo que impide que el inventario quede en
    negativo (RNF-08).
    """
    producto = ProductoFactory(stock=5)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _escribir_saltando_django(
                "UPDATE catalogo_producto SET stock = %s WHERE id = %s",
                [-1, producto.id],
            )

    producto.refresh_from_db()
    assert producto.stock == 5


def test_stock_cero_es_valido():
    """RN-CAT-05: sin existencias el producto sigue en el catalogo."""
    producto = ProductoFactory(stock=0)

    producto.refresh_from_db()
    assert producto.stock == 0
    assert producto.activo


# ─────────────────────────────────────────────────────────────────────
# RN-CAT-01 — precio mayor que cero
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("precio_invalido", [0, -1, -150.50])
def test_la_base_rechaza_precios_no_positivos(precio_invalido):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProductoFactory(precio=precio_invalido)


def test_un_precio_con_centavos_se_conserva_exacto():
    """RN-VEN-05 depende de esto.

    Con coma flotante, 1250.10 podria guardarse como 1250.0999...,
    y los totales de las ventas acumularian el error. DecimalField
    sobre NUMERIC lo evita.
    """
    from decimal import Decimal

    producto = ProductoFactory(precio=Decimal("1250.10"))
    producto.refresh_from_db()

    assert producto.precio == Decimal("1250.10")
    assert isinstance(producto.precio, Decimal)


# ─────────────────────────────────────────────────────────────────────
# RN-CAT-03 — nombres unicos, sin distinguir mayusculas
# ─────────────────────────────────────────────────────────────────────
def test_no_puede_haber_dos_categorias_con_el_mismo_nombre():
    CategoriaFactory(nombre="Laptops")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CategoriaFactory(nombre="Laptops")


def test_la_unicidad_de_categoria_ignora_mayusculas():
    """Permitir "Laptops" y "laptops" a la vez dejaria el catalogo con
    dos categorias que el personal leeria como la misma."""
    CategoriaFactory(nombre="Laptops")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CategoriaFactory(nombre="LAPTOPS")


def test_no_puede_haber_dos_productos_con_el_mismo_nombre():
    categoria = CategoriaFactory()
    ProductoFactory(nombre="Teclado mecánico", categoria=categoria)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProductoFactory(nombre="teclado mecánico", categoria=categoria)


# ─────────────────────────────────────────────────────────────────────
# RN-CAT-04 — una categoria con productos no se elimina
# ─────────────────────────────────────────────────────────────────────
def test_no_se_puede_eliminar_una_categoria_con_productos():
    from django.db.models import ProtectedError

    categoria = CategoriaFactory()
    ProductoFactory(categoria=categoria)

    with pytest.raises(ProtectedError):
        categoria.delete()

    assert Categoria.objects.filter(pk=categoria.pk).exists()


def test_una_categoria_sin_productos_si_se_elimina():
    categoria = CategoriaFactory()

    categoria.delete()

    assert not Categoria.objects.filter(pk=categoria.pk).exists()


def test_la_proteccion_sigue_valiendo_con_productos_retirados():
    """Matiz que el borrado suave introduce.

    Un producto retirado del catalogo sigue siendo una fila con su
    categoria: eliminarla rompería el historial de ventas que lo
    incluya (RN-VEN-04).
    """
    from django.db.models import ProtectedError

    categoria = CategoriaFactory()
    ProductoFactory(categoria=categoria, activo=False)

    with pytest.raises(ProtectedError):
        categoria.delete()


# ─────────────────────────────────────────────────────────────────────
# CU-CAT-04 — borrado suave
# ─────────────────────────────────────────────────────────────────────
def test_un_producto_retirado_conserva_su_fila():
    """Es lo que garantiza que RN-VEN-07 siempre pueda devolver stock:
    el producto nunca desaparece de la base."""
    producto = ProductoFactory(activo=True)

    producto.activo = False
    producto.save(update_fields=["activo"])

    assert Producto.objects.filter(pk=producto.pk).exists()
    assert not producto.disponible_para_venta


# ─────────────────────────────────────────────────────────────────────
# RN-CAT-05 y RN-CAT-06
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("activo", "stock", "disponible"),
    [
        (True, 10, True),
        (True, 0, False),   # sin existencias no se vende
        (False, 10, False),  # retirado del catalogo
        (False, 0, False),
    ],
)
def test_disponibilidad_para_venta(activo, stock, disponible):
    producto = ProductoFactory(activo=activo, stock=stock)

    assert producto.disponible_para_venta is disponible


def test_la_imagen_es_opcional():
    """RN-CAT-06."""
    producto = ProductoFactory()

    assert not producto.imagen


# ─────────────────────────────────────────────────────────────────────
# Indices declarados (plan.md 3.4)
# ─────────────────────────────────────────────────────────────────────
def test_existen_los_indices_que_el_plan_declara():
    """RNF-17 depende de ellos para el catalogo filtrado y el panel."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'catalogo_producto'"
        )
        indices = {fila[0] for fila in cursor.fetchall()}

    assert "producto_categoria_idx" in indices
    assert "producto_activo_idx" in indices
    assert "producto_stock_idx" in indices
