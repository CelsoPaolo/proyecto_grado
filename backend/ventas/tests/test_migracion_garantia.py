"""T-10.1 — Migraciones de los meses de garantia (RNF-29, RN-VEN-12).

Las lineas de venta anteriores a la v1.4 quedan en CERO aunque su
producto tenga hoy garantia: asignarsela seria inventar un dato que no
existia cuando se vendio (plan.md 3.5). Las dos migraciones se aplican y
se revierten sin tocar ningun otro dato.

Con modelos historicos: los actuales tienen columnas que en el estado
anterior no existen.
"""

from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

ANTES = [("catalogo", "0005_codigo_fabrica"), ("ventas", "0001_initial")]
PRODUCTO_CON_GARANTIA = [("catalogo", "0006_meses_garantia"), ("ventas", "0001_initial")]
DESPUES = [("catalogo", "0006_meses_garantia"), ("ventas", "0002_meses_garantia_congelados")]


def _migrar(destino):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(destino)


def _apps_en(estado):
    executor = MigrationExecutor(connection)
    return executor.loader.project_state(estado).apps


def _columnas(tabla):
    with connection.cursor() as cursor:
        return {c.name for c in connection.introspection.get_table_description(cursor, tabla)}


def _filas(tabla):
    columnas = sorted(_columnas(tabla))
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {', '.join(columnas)} FROM {tabla} ORDER BY id")
        return [dict(zip(columnas, f)) for f in cursor.fetchall()]


@pytest.fixture
def ventas_anteriores():
    """Dos lineas de venta registradas antes de la v1.4."""
    _migrar(ANTES)
    apps = _apps_en(ANTES)
    Categoria = apps.get_model("catalogo", "Categoria")
    Producto = apps.get_model("catalogo", "Producto")
    Usuario = apps.get_model("usuarios", "Usuario")
    Venta = apps.get_model("ventas", "Venta")
    Detalle = apps.get_model("ventas", "DetalleVenta")

    categoria = Categoria.objects.create(nombre="Garantía", descripcion="")
    vendedor = Usuario.objects.create(username="vendedor_antiguo", nombre_completo="Vendedor", rol="VENTAS")
    venta = Venta.objects.create(
        usuario=vendedor, cliente_nombre="Cliente", cliente_telefono="70000000", total=Decimal("300.00")
    )
    for i in range(2):
        producto = Producto.objects.create(
            nombre=f"Antiguo con garantía {i}",
            precio=150,
            stock=1,
            categoria=categoria,
            codigo=f"200000009{i:03d}0",
        )
        Detalle.objects.create(
            venta=venta,
            producto=producto,
            producto_nombre=producto.nombre,
            precio_unitario=Decimal("150.00"),
            cantidad=1,
            subtotal=Decimal("150.00"),
        )
    yield
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


def test_las_lineas_anteriores_quedan_en_cero_aunque_el_producto_tenga_garantia(ventas_anteriores):
    antes = _filas("ventas_detalleventa")

    _migrar(PRODUCTO_CON_GARANTIA)
    with connection.cursor() as cursor:
        cursor.execute("UPDATE catalogo_producto SET meses_garantia = 24")
    _migrar(DESPUES)

    despues = _filas("ventas_detalleventa")
    assert [f["meses_garantia"] for f in despues] == [0, 0]
    # RNF-29: ningun otro dato de las lineas cambia.
    assert [{k: v for k, v in f.items() if k != "meses_garantia"} for f in despues] == antes


def test_las_dos_migraciones_se_revierten_sin_perder_datos(ventas_anteriores):
    lineas = _filas("ventas_detalleventa")
    productos = _filas("catalogo_producto")

    _migrar(DESPUES)
    _migrar(ANTES)

    assert "meses_garantia" not in _columnas("ventas_detalleventa")
    assert "meses_garantia" not in _columnas("catalogo_producto")
    assert _filas("ventas_detalleventa") == lineas
    assert _filas("catalogo_producto") == productos
