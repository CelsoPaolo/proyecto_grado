"""T-11.1 y T-15.9 — Modelo Cliente (RN-CLI-01 a RN-CLI-03, RNF-07).

Desde la v1.5 el carnet es obligatorio, de 7 u 8 digitos y sin
complemento (PA-10), y el telefono tiene 8 digitos (RN-CLI-09).

Las restricciones se prueban contra la BASE: objects.create() no ejecuta
full_clean(), y el SQL crudo no pasa ni por el ORM.
"""

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from clientes.models import Cliente, normalizar_carnet
from clientes.tests.factories import ClienteFactory


@pytest.mark.parametrize(
    ("entrada", "normalizado"),
    [(" 1234 5678 ", "12345678"), ("1234567", "1234567"), ("", ""), (None, "")],
)
def test_normalizar_carnet(entrada, normalizado):
    assert normalizar_carnet(entrada) == normalizado


@pytest.mark.django_db
def test_el_carnet_se_guarda_normalizado():
    cliente = ClienteFactory(carnet=" 1234 5678 ")

    cliente.refresh_from_db()
    assert cliente.carnet == "12345678"


@pytest.mark.django_db
def test_dos_clientes_con_el_mismo_carnet_los_rechaza_la_base():
    ClienteFactory(carnet="1234567")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ClienteFactory(carnet="1234567")


@pytest.mark.django_db
def test_el_carnet_es_unico_aunque_el_otro_cliente_este_inactivo():
    ClienteFactory(carnet="1234567", activo=False)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ClienteFactory(carnet="1234567")


@pytest.mark.django_db
@pytest.mark.parametrize("carnet", ["", "123456", "123456789", "1234567-1A", "1234567LP", "1234567a"])
def test_la_base_rechaza_un_carnet_fuera_de_formato(carnet):
    """RF-101 y RN-CLI-02 (v1.5): vacio, 6 o 9 digitos, o con complemento."""
    cliente = ClienteFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("UPDATE clientes_cliente SET carnet = %s WHERE id = %s", [carnet, cliente.pk])


@pytest.mark.django_db
@pytest.mark.parametrize("carnet", ["1234567", "12345678"])
def test_la_base_acepta_siete_u_ocho_digitos(carnet):
    cliente = ClienteFactory(carnet=carnet)

    cliente.refresh_from_db()
    assert cliente.carnet == carnet


@pytest.mark.django_db
@pytest.mark.parametrize("telefono", ["7001234", "700123456", "7001234a"])
def test_la_base_rechaza_un_telefono_fuera_de_formato_en_todos_los_clientes(telefono):
    """RN-CLI-09: en clientes se comprueban todas las filas (plan.md 3.6)."""
    cliente = ClienteFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("UPDATE clientes_cliente SET telefono = %s WHERE id = %s", [telefono, cliente.pk])


@pytest.mark.django_db
def test_nombre_y_telefono_no_son_unicos():
    """RN-CLI-02: dos personas pueden llamarse igual y una familia
    compartir telefono."""
    ClienteFactory(nombre="Juan Pérez", telefono="70000000")
    ClienteFactory(nombre="Juan Pérez", telefono="70000000")


@pytest.mark.django_db
@pytest.mark.parametrize("campo", ["nombre", "telefono"])
@pytest.mark.parametrize("valor", ["", "   "])
def test_nombre_y_telefono_son_obligatorios_en_la_base(campo, valor):
    cliente = ClienteFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f"UPDATE clientes_cliente SET {campo} = %s WHERE id = %s", [valor, cliente.pk])


@pytest.mark.django_db
def test_la_unicidad_del_carnet_vive_en_la_base_y_no_en_python():
    ClienteFactory(carnet="9999999")
    otro = ClienteFactory()

    with pytest.raises(IntegrityError):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("UPDATE clientes_cliente SET carnet = '9999999' WHERE id = %s", [otro.pk])


@pytest.mark.django_db(transaction=True)
def test_la_migracion_inicial_se_aplica_y_se_revierte():
    def migrar(destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)

    def existe():
        with connection.cursor() as cursor:
            return "clientes_cliente" in connection.introspection.table_names(cursor)

    try:
        migrar([("clientes", None)])
        assert not existe()
        migrar([("clientes", "0001_initial")])
        assert existe()
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_la_migracion_del_carnet_obligatorio_es_reversible():
    """RNF-29: sin ella, un cliente sin carnet vuelve a aceptarse."""

    def migrar(destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)

    def restricciones():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT conname FROM pg_constraint WHERE conname IN "
                "('cliente_carnet_formato', 'cliente_telefono_formato')"
            )
            return {fila[0] for fila in cursor.fetchall()}

    try:
        migrar([("clientes", "0001_initial")])
        assert restricciones() == set()
        migrar([("clientes", "0002_carnet_obligatorio")])
        assert restricciones() == {"cliente_carnet_formato", "cliente_telefono_formato"}
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())
