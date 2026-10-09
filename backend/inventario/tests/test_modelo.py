"""T-8.1 — Modelo `MovimientoStock` (RN-MOV-02 a RN-MOV-04, RNF-25).

Dos grupos de pruebas, que protegen las dos propiedades del libro:

  1. La BASE rechaza los movimientos imposibles, aunque se salte toda
     la validacion de Django. `objects.create()` no ejecuta
     `full_clean()`, asi que lo que estas pruebas comprueban es el
     CHECK de PostgreSQL, no un validador de Python.
  2. El libro NO se reescribe: ni la instancia ni el queryset permiten
     modificar o borrar un movimiento ya guardado.
"""

import pytest
from django.db import IntegrityError, connection, transaction

from catalogo.tests.factories import ProductoFactory
from inventario.models import MovimientoInmutable, MovimientoStock, TipoMovimiento
from usuarios.tests.factories import AdministradorFactory
from ventas.tests.factories import VentaFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def producto():
    return ProductoFactory(stock=10)


@pytest.fixture
def admin():
    return AdministradorFactory()


@pytest.fixture
def venta():
    return VentaFactory()


def _movimiento(**campos):
    """Escribe directamente, sin pasar por ninguna validacion de Django."""
    return MovimientoStock.objects.create(**campos)


# ─────────────────────────────────────────────────────────────────────
# Los cinco tipos validos se guardan
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "tipo, cantidad, con_autor, con_venta, motivo",
    [
        (TipoMovimiento.SALDO_INICIAL, 10, False, False, ""),
        (TipoMovimiento.SALDO_INICIAL, 0, False, False, ""),
        (TipoMovimiento.ALTA, 10, True, False, ""),
        (TipoMovimiento.ALTA, 0, True, False, ""),
        (TipoMovimiento.VENTA, -2, True, True, ""),
        (TipoMovimiento.ANULACION, 2, True, True, ""),
        (TipoMovimiento.AJUSTE, -3, True, False, "Recuento físico"),
        (TipoMovimiento.AJUSTE, 4, True, False, "Error de carga"),
    ],
)
def test_cada_tipo_valido_se_guarda(producto, admin, venta, tipo, cantidad, con_autor, con_venta, motivo):
    """RN-MOV-02. Sin esta prueba, un CHECK demasiado estricto pasaria
    desapercibido: las de abajo solo comprueban que se rechaza lo
    invalido, no que se acepta lo valido."""
    movimiento = _movimiento(
        producto=producto,
        tipo=tipo,
        cantidad=cantidad,
        stock_resultante=10,
        usuario=admin if con_autor else None,
        venta=venta if con_venta else None,
        motivo=motivo,
    )

    assert movimiento.pk is not None


# ─────────────────────────────────────────────────────────────────────
# La base rechaza los movimientos imposibles
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "caso, campos",
    [
        # RN-MOV-02: venta y anulacion siempre con su venta...
        ("venta sin venta", dict(tipo=TipoMovimiento.VENTA, cantidad=-1, venta=None)),
        ("anulación sin venta", dict(tipo=TipoMovimiento.ANULACION, cantidad=1, venta=None)),
        # ...y ningun otro tipo con una
        ("ajuste con venta", dict(tipo=TipoMovimiento.AJUSTE, cantidad=1, motivo="x", venta="VENTA")),
        ("alta con venta", dict(tipo=TipoMovimiento.ALTA, cantidad=5, venta="VENTA")),
        # RN-MOV-02: el signo es del libro, no de la interfaz
        ("venta que suma", dict(tipo=TipoMovimiento.VENTA, cantidad=1, venta="VENTA")),
        ("venta de cero", dict(tipo=TipoMovimiento.VENTA, cantidad=0, venta="VENTA")),
        ("anulación que resta", dict(tipo=TipoMovimiento.ANULACION, cantidad=-1, venta="VENTA")),
        ("alta negativa", dict(tipo=TipoMovimiento.ALTA, cantidad=-1)),
        # RN-MOV-05: un ajuste cambia algo y explica por que
        ("ajuste sin motivo", dict(tipo=TipoMovimiento.AJUSTE, cantidad=2, motivo="")),
        ("ajuste sin diferencia", dict(tipo=TipoMovimiento.AJUSTE, cantidad=0, motivo="Recuento")),
        # RN-CAT-02 en el libro
        ("existencias resultantes negativas", dict(tipo=TipoMovimiento.ALTA, cantidad=0, stock_resultante=-1)),
    ],
)
def test_la_base_rechaza_un_movimiento_imposible(producto, admin, venta, caso, campos):
    campos = {"stock_resultante": 5, "usuario": admin, "motivo": "", **campos}
    if campos.get("venta") == "VENTA":
        campos["venta"] = venta

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(producto=producto, **campos)


def test_el_saldo_inicial_no_tiene_autor(producto, admin):
    """RN-MOV-02: lo genera la migracion, no una persona."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(
                producto=producto,
                tipo=TipoMovimiento.SALDO_INICIAL,
                cantidad=10,
                stock_resultante=10,
                usuario=admin,
            )


@pytest.mark.parametrize(
    "tipo", [TipoMovimiento.ALTA, TipoMovimiento.AJUSTE, TipoMovimiento.VENTA]
)
def test_ningun_otro_movimiento_queda_sin_autor(producto, venta, tipo):
    """RNF-07: un movimiento sin autor que no sea el saldo inicial seria
    un cambio de existencias que nadie hizo."""
    campos = {
        TipoMovimiento.ALTA: dict(cantidad=5),
        TipoMovimiento.AJUSTE: dict(cantidad=5, motivo="Recuento"),
        TipoMovimiento.VENTA: dict(cantidad=-1, venta=venta),
    }[tipo]

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(
                producto=producto, tipo=tipo, stock_resultante=5, usuario=None, **campos
            )


def test_la_restriccion_vive_en_la_base_y_no_en_python(producto):
    """El caso mas importante, escrito en SQL crudo.

    `objects.create()` ya salta la validacion de Django, pero sigue
    pasando por el ORM. Este INSERT no pasa por nada: si la base no
    tuviera el CHECK, entraria.
    """
    with pytest.raises(IntegrityError):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {MovimientoStock._meta.db_table} "
                "(producto_id, tipo, cantidad, stock_resultante, motivo, fecha_hora) "
                "VALUES (%s, 'VENTA', -1, 9, '', NOW())",
                [producto.pk],
            )


# ─────────────────────────────────────────────────────────────────────
# El libro no se reescribe (RN-MOV-04, RNF-25)
# ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def movimiento(producto, admin):
    return _movimiento(
        producto=producto,
        tipo=TipoMovimiento.AJUSTE,
        cantidad=-2,
        stock_resultante=8,
        usuario=admin,
        motivo="Unidad dañada",
    )


def test_un_movimiento_guardado_no_se_modifica(movimiento):
    movimiento.cantidad = -5

    with pytest.raises(MovimientoInmutable):
        movimiento.save()

    movimiento.refresh_from_db()
    assert movimiento.cantidad == -2


def test_un_movimiento_no_se_borra(movimiento):
    with pytest.raises(MovimientoInmutable):
        movimiento.delete()

    assert MovimientoStock.objects.filter(pk=movimiento.pk).exists()


def test_la_via_masiva_tampoco_modifica(movimiento):
    """Sin el queryset propio, esta linea reescribiria el libro entero
    sin pasar por save()."""
    with pytest.raises(MovimientoInmutable):
        MovimientoStock.objects.filter(pk=movimiento.pk).update(cantidad=-99)

    movimiento.refresh_from_db()
    assert movimiento.cantidad == -2


def test_la_via_masiva_tampoco_borra(movimiento):
    with pytest.raises(MovimientoInmutable):
        MovimientoStock.objects.all().delete()

    assert MovimientoStock.objects.filter(pk=movimiento.pk).exists()


def test_un_producto_con_movimientos_no_puede_borrarse(movimiento, producto):
    """`PROTECT` en la relacion. Los productos se retiran (RN-CAT-04),
    no se borran; pero si algun dia un camino intentara borrar uno, la
    base no dejaria el libro con movimientos huerfanos."""
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        producto.delete()
