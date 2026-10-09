"""Migraciones del codigo de producto (RNF-29, RN-CAT-08, plan.md 3.5).

- T-9.1: el paso 1 (secuencia y columna nula) se aplica y se revierte.
- T-9.2: sobre mas de 160 productos sin codigo, los pasos 2 y 3 dan a
  cada uno un EAN-13 valido y distinto, sin tocar ningun otro dato.
  Revertir los tres pasos devuelve la tabla a su estado anterior, y
  revertir y reaplicar el paso 2 no cambia ningun codigo.

Se usa el mismo MigrationExecutor que `manage.py migrate`, con
`transaction=True`: una migracion cambia la base de verdad y no puede
probarse dentro de la transaccion que pytest-django revierte.
"""

import random

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from catalogo.codigos import PATRON_INTERNO, es_ean13_valido
from catalogo.models import Producto
from catalogo.tests.factories import CategoriaFactory, ProductoFactory

pytestmark = pytest.mark.django_db(transaction=True)

INICIAL = [("catalogo", "0001_initial")]
PASO_1 = [("catalogo", "0002_codigo_paso1_secuencia_y_columna")]
PASO_2 = [("catalogo", "0003_codigo_paso2_asignacion")]
PASO_3 = [("catalogo", "0004_codigo_paso3_obligatorio_y_unico")]

CANTIDAD = 165


def _migrar(destino):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(destino)


def _al_final():
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.fixture
def migraciones():
    """Devuelve la base a la ultima migracion al terminar, pase lo que pase."""
    yield _migrar
    _al_final()


def _existe_secuencia():
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('producto_codigo_seq')")
        return cursor.fetchone()[0] is not None


def _columnas_de_producto():
    with connection.cursor() as cursor:
        return {
            c.name for c in connection.introspection.get_table_description(cursor, "catalogo_producto")
        }


def _filas():
    """La tabla entera en SQL crudo, sin pasar por el modelo actual, que
    no coincide con el esquema en los estados intermedios."""
    columnas = sorted(_columnas_de_producto())
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {', '.join(columnas)} FROM catalogo_producto ORDER BY id")
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def _sin_codigo(filas):
    return [{k: v for k, v in f.items() if k != "codigo"} for f in filas]


@pytest.fixture
def catalogo_sin_codigos(migraciones):
    """165 productos en el estado del paso 1, todos con el codigo nulo,
    como quedan los productos que existian antes de la v1.4."""
    migraciones(PASO_1)
    azar = random.Random(20261009)
    categoria = CategoriaFactory()
    ids = [
        ProductoFactory(categoria=categoria, stock=azar.randint(0, 60), activo=azar.random() > 0.1).pk
        for _ in range(CANTIDAD)
    ]
    # El modelo actual asigna codigo al crear; aqui se borra para
    # reproducir la base anterior a la migracion.
    with connection.cursor() as cursor:
        cursor.execute("UPDATE catalogo_producto SET codigo = NULL")
    return ids


def test_el_paso_1_se_aplica_y_se_revierte(migraciones):
    migraciones(PASO_1)
    assert _existe_secuencia()
    assert "codigo" in _columnas_de_producto()

    migraciones(INICIAL)
    assert not _existe_secuencia()
    assert "codigo" not in _columnas_de_producto()

    migraciones(PASO_1)
    assert _existe_secuencia()
    assert "codigo" in _columnas_de_producto()


def test_todos_los_productos_existentes_reciben_un_codigo_valido_y_distinto(
    catalogo_sin_codigos, migraciones
):
    antes = _filas()
    assert len(antes) == CANTIDAD
    assert all(f["codigo"] is None for f in antes)

    migraciones(PASO_3)

    despues = _filas()
    codigos = [f["codigo"] for f in despues]
    assert all(es_ean13_valido(c) and PATRON_INTERNO.match(c) for c in codigos)
    assert len(set(codigos)) == CANTIDAD
    # Por id ascendente: el producto mas antiguo, el numero mas bajo.
    assert codigos == sorted(codigos)
    # RNF-29: ningun otro dato cambia.
    assert _sin_codigo(despues) == _sin_codigo(antes)


def test_revertir_los_tres_pasos_devuelve_la_tabla_a_su_estado_anterior(
    catalogo_sin_codigos, migraciones
):
    antes = _sin_codigo(_filas())

    migraciones(PASO_3)
    migraciones(INICIAL)

    assert "codigo" not in _columnas_de_producto()
    assert not _existe_secuencia()
    # Mismas filas y mismos datos que antes de empezar, columna a columna.
    assert _filas() == antes


def test_revertir_y_reaplicar_el_paso_2_no_cambia_ningun_codigo(catalogo_sin_codigos, migraciones):
    """plan.md 3.5, revisado en T-9.2: si el reverso borrara los
    codigos, reaplicarlo daria otros, y las etiquetas impresas dejarian
    de corresponder a su producto (RN-CAT-08)."""
    migraciones(PASO_3)
    asignados = {f["id"]: f["codigo"] for f in _filas()}

    migraciones(PASO_1)
    migraciones(PASO_3)

    assert {f["id"]: f["codigo"] for f in _filas()} == asignados


def test_el_paso_2_respeta_los_codigos_que_ya_existen(catalogo_sin_codigos, migraciones):
    """Idempotente: un producto con codigo lo conserva, y el resto recibe
    numeros que no chocan con el."""
    primero = catalogo_sin_codigos[0]
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE catalogo_producto SET codigo = %s WHERE id = %s", ["2000000099992", primero]
        )

    migraciones(PASO_3)

    codigos = {f["id"]: f["codigo"] for f in _filas()}
    assert codigos[primero] == "2000000099992"
    assert len(set(codigos.values())) == CANTIDAD


def test_un_producto_creado_despues_de_migrar_sigue_la_secuencia(catalogo_sin_codigos, migraciones):
    migraciones(PASO_3)
    ultimo = max(f["codigo"] for f in _filas())

    nuevo = ProductoFactory(categoria=Producto.objects.first().categoria)

    assert nuevo.codigo > ultimo
