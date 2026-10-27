"""T-15.5 — Codigo de unidad al confirmar la venta (RF-102, RN-VEN-18).

Una linea de 7 unidades recibe 7 codigos distintos, EAN-13 con prefijo
21, en la misma operacion que la venta. Una venta rechazada no recibe
ninguno, y dos ventas simultaneas nunca comparten un codigo.
"""

import threading
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from catalogo.codigos import PATRON_UNIDAD, es_ean13_valido, generar_codigos_de_unidad
from catalogo.models import Categoria
from catalogo.services import crear_producto
from catalogo.tests.factories import ProductoFactory
from usuarios.models import Rol, Usuario
from usuarios.tests.factories import VendedorFactory
from ventas.exceptions import StockInsuficiente
from ventas.models import UnidadVendida
from ventas.services import registrar_venta
from ventas.tests.factories import DetalleVentaFactory


def _vender(items, usuario=None):
    return registrar_venta(
        usuario=usuario or VendedorFactory(),
        cliente_nombre="Cliente",
        cliente_telefono="70012345",
        items=items,
    )


@pytest.mark.django_db
def test_cada_unidad_vendida_recibe_su_propio_codigo():
    """El caso de la garantia 17: 7 camaras iguales, 7 codigos."""
    camara = ProductoFactory(nombre="Cámara Bullet Dahua", stock=10)

    venta = _vender([{"producto_id": camara.id, "cantidad": 7}])

    unidades = list(UnidadVendida.objects.filter(detalle__venta=venta))
    codigos = [u.codigo for u in unidades]
    assert len(unidades) == 7
    assert len(set(codigos)) == 7
    assert all(u.detalle.producto_id == camara.id for u in unidades)


@pytest.mark.django_db
def test_los_codigos_son_ean13_validos_con_prefijo_21():
    venta = _vender([{"producto_id": ProductoFactory(stock=5).id, "cantidad": 3}])

    for unidad in UnidadVendida.objects.filter(detalle__venta=venta):
        assert PATRON_UNIDAD.fullmatch(unidad.codigo)
        assert es_ean13_valido(unidad.codigo)
        assert unidad.anulada is False


@pytest.mark.django_db
def test_cada_linea_tiene_tantas_unidades_como_su_cantidad():
    a, b = ProductoFactory(stock=5), ProductoFactory(stock=5)

    venta = _vender(
        [{"producto_id": a.id, "cantidad": 2}, {"producto_id": b.id, "cantidad": 3}]
    )

    for detalle in venta.items.all():
        assert detalle.unidades.count() == detalle.cantidad


@pytest.mark.django_db
def test_dos_ventas_no_comparten_ningun_codigo():
    producto = ProductoFactory(stock=10)

    primera = _vender([{"producto_id": producto.id, "cantidad": 3}])
    segunda = _vender([{"producto_id": producto.id, "cantidad": 3}])

    de = lambda v: {u.codigo for u in UnidadVendida.objects.filter(detalle__venta=v)}  # noqa: E731
    assert de(primera).isdisjoint(de(segunda))


@pytest.mark.django_db
def test_una_venta_rechazada_no_asigna_ningun_codigo():
    """RNF-09: todo o nada, tambien para las unidades."""
    producto = ProductoFactory(stock=2)

    with pytest.raises(StockInsuficiente):
        _vender([{"producto_id": producto.id, "cantidad": 5}])

    assert not UnidadVendida.objects.exists()


@pytest.mark.django_db
def test_una_venta_anterior_no_recibe_codigos():
    """RNF-30: la tabla nace vacia y nada asigna codigos retroactivos."""
    detalle = DetalleVentaFactory(cantidad=4)

    assert detalle.unidades.count() == 0


@pytest.mark.django_db
def test_la_base_no_admite_dos_unidades_con_el_mismo_codigo():
    venta = _vender([{"producto_id": ProductoFactory(stock=5).id, "cantidad": 1}])
    unidad = UnidadVendida.objects.get(detalle__venta=venta)

    with pytest.raises(IntegrityError), transaction.atomic():
        UnidadVendida.objects.create(detalle=unidad.detalle, codigo=unidad.codigo)


@pytest.mark.django_db
def test_la_base_no_admite_un_codigo_sin_el_prefijo_21():
    detalle = DetalleVentaFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        UnidadVendida.objects.create(detalle=detalle, codigo="2000000000084")


@pytest.mark.django_db
def test_la_secuencia_no_repite_numeros_aunque_se_pidan_varios():
    codigos = generar_codigos_de_unidad(50) + generar_codigos_de_unidad(50)

    assert len(set(codigos)) == 100
    assert generar_codigos_de_unidad(0) == []


@pytest.mark.django_db(transaction=True)
def test_la_migracion_es_reversible():
    """RNF-29: ida y vuelta, con la secuencia incluida."""

    def existe(sql):
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchone() is not None

    tabla = "SELECT 1 FROM pg_class WHERE relname = 'ventas_unidadvendida'"
    secuencia = "SELECT 1 FROM pg_class WHERE relname = 'unidad_codigo_seq' AND relkind = 'S'"
    executor = MigrationExecutor(connection)
    try:
        executor.migrate([("ventas", "0004_telefono_formato")])
        assert not existe(tabla) and not existe(secuencia)
        executor = MigrationExecutor(connection)
        executor.migrate([("ventas", "0005_unidad_vendida")])
        assert existe(tabla) and existe(secuencia)
    finally:
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())


class CodigosEnVentasSimultaneas(TransactionTestCase):
    """Veinte ventas a la vez: todas sus unidades con codigos distintos.

    Con commits reales, como las pruebas de concurrencia de T-4.4: dentro
    de una sola transaccion los hilos no se verian entre si.
    """

    def test_ningun_codigo_se_repite_entre_ventas_simultaneas(self):
        admin = Usuario.objects.create(username="admin", nombre_completo="Admin", rol=Rol.ADMINISTRADOR)
        producto = crear_producto(
            usuario=admin,
            nombre="Cámara",
            categoria=Categoria.objects.create(nombre="Cámaras"),
            precio=Decimal("100.00"),
            stock=200,
        )
        vendedores = [
            Usuario.objects.create(username=f"v{i}", nombre_completo=f"V {i}", rol=Rol.VENTAS)
            for i in range(20)
        ]
        listos = threading.Barrier(20)
        errores = []

        def tarea(vendedor):
            listos.wait()
            try:
                _vender([{"producto_id": producto.id, "cantidad": 3}], usuario=vendedor)
            except Exception as exc:  # pragma: no cover - diagnostico
                errores.append(exc)
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=tarea, args=(v,)) for v in vendedores]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=60)

        self.assertEqual(errores, [])
        codigos = list(UnidadVendida.objects.values_list("codigo", flat=True))
        self.assertEqual(len(codigos), 60)
        self.assertEqual(len(set(codigos)), 60)
