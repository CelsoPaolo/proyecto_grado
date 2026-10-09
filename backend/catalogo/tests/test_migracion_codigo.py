"""Migraciones del codigo de producto (RNF-29, plan.md 3.5).

T-9.1: el paso 1 (secuencia y columna nula) se aplica y se revierte.

Se usa el mismo MigrationExecutor que `manage.py migrate`, con
`transaction=True`: una migracion cambia la base de verdad y no puede
probarse dentro de la transaccion que pytest-django revierte.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

INICIAL = [("catalogo", "0001_initial")]
PASO_1 = [("catalogo", "0002_codigo_paso1_secuencia_y_columna")]


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
