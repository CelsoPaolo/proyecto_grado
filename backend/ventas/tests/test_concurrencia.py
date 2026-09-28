"""T-4.4 — Concurrencia en el descuento de existencias (RNF-08).

**Criterio de aceptacion ejecutable de RNF-08.** Es la unica evidencia
de que la garantia se cumple de verdad: el resto de la suite comprueba
que el codigo hace lo que dice, pero solo esta prueba demuestra que lo
sigue haciendo cuando dos ventas ocurren a la vez.

El escenario que se ataca (plan.md 6.1): dos encargados venden el
ultimo teclado en el mismo instante. Sin proteccion, ambas peticiones
leen stock = 1, ambas validan que alcanza, y ambas descuentan: el
inventario queda en -1 y se vendio dos veces la misma unidad.

Por que TransactionTestCase y no pytest.mark.django_db:
`TestCase` envuelve cada prueba en una transaccion que revierte al
terminar, y dentro de esa unica transaccion los hilos no verian los
commits de los demas: el bloqueo de filas quedaria enmascarado y la
prueba pasaria sin demostrar nada. `TransactionTestCase` usa commits
reales, que es lo que hace falta para que la carrera sea autentica.
"""

import threading
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase

from catalogo.models import Categoria, Producto
from usuarios.models import Rol, Usuario
from ventas.exceptions import StockInsuficiente
from ventas.models import EstadoVenta, Venta
from ventas.services import anular_venta, registrar_venta


class ConcurrenciaEnElDescuentoDeStock(TransactionTestCase):
    """Varias ventas simultaneas del mismo producto."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Periféricos")
        self.vendedores = [
            Usuario.objects.create(
                username=f"vendedor{i}",
                nombre_completo=f"Vendedor {i}",
                rol=Rol.VENTAS,
            )
            for i in range(20)
        ]

    def _vender_en_hilo(self, producto_id, cantidad, vendedor, resultados, indice):
        """Ejecuta una venta en su propio hilo y anota el resultado.

        Cada hilo cierra su conexion al terminar: Django abre una por
        hilo y, sin cerrarlas, la prueba dejaria conexiones colgando y
        el teardown podria bloquearse esperandolas.
        """
        try:
            registrar_venta(
                usuario=vendedor,
                cliente_nombre="Cliente simultáneo",
                cliente_telefono="70000000",
                items=[{"producto_id": producto_id, "cantidad": cantidad}],
            )
            resultados[indice] = "confirmada"
        except StockInsuficiente:
            resultados[indice] = "sin_stock"
        except Exception as exc:  # pragma: no cover - diagnostico
            resultados[indice] = f"error:{type(exc).__name__}:{exc}"
        finally:
            connections.close_all()

    def _lanzar(self, producto, hilos, cantidad=1):
        resultados = [None] * hilos
        listos = threading.Barrier(hilos)

        def tarea(indice):
            # La barrera hace que todos los hilos arranquen a la vez:
            # sin ella podrian serializarse por casualidad y la carrera
            # no llegaria a producirse.
            listos.wait()
            self._vender_en_hilo(
                producto.id, cantidad, self.vendedores[indice], resultados, indice
            )

        lista = [threading.Thread(target=tarea, args=(i,)) for i in range(hilos)]
        for hilo in lista:
            hilo.start()
        for hilo in lista:
            hilo.join(timeout=30)

        return resultados

    # ─────────────────────────────────────────────────────────────────
    # El caso central: mas compradores que unidades
    # ─────────────────────────────────────────────────────────────────
    def test_diez_ventas_simultaneas_de_tres_unidades_confirman_solo_tres(self):
        """Los tres criterios de tasks.md T-4.4, en una sola prueba."""
        producto = Producto.objects.create(
            nombre="Teclado mecánico",
            categoria=self.categoria,
            precio=Decimal("350.00"),
            stock=3,
        )

        resultados = self._lanzar(producto, hilos=10, cantidad=1)

        confirmadas = resultados.count("confirmada")
        sin_stock = resultados.count("sin_stock")
        errores = [r for r in resultados if r and r.startswith("error:")]

        self.assertEqual(errores, [], f"Errores inesperados: {errores}")

        # 1. Las ventas confirmadas son exactamente el stock disponible.
        self.assertEqual(confirmadas, 3)

        # 2. El stock final es exactamente 0, nunca negativo.
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 0)

        # 3. Las peticiones sobrantes fueron rechazadas.
        self.assertEqual(sin_stock, 7)

        # Y no se vendio la misma unidad dos veces.
        self.assertEqual(Venta.objects.count(), 3)

    def test_veinte_hilos_sobre_una_sola_unidad_solo_uno_gana(self):
        """El caso mas extremo: una unidad, veinte compradores."""
        producto = Producto.objects.create(
            nombre="Última laptop",
            categoria=self.categoria,
            precio=Decimal("5400.00"),
            stock=1,
        )

        resultados = self._lanzar(producto, hilos=20, cantidad=1)

        self.assertEqual(resultados.count("confirmada"), 1)
        self.assertEqual(resultados.count("sin_stock"), 19)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 0)

    def test_con_stock_suficiente_todas_las_ventas_simultaneas_confirman(self):
        """Contraprueba imprescindible.

        Sin ella, un bug que rechazara TODAS las ventas pasaria las dos
        pruebas anteriores: cero ventas confirmadas nunca deja el stock
        en negativo.
        """
        producto = Producto.objects.create(
            nombre="Mouse inalámbrico",
            categoria=self.categoria,
            precio=Decimal("120.00"),
            stock=10,
        )

        resultados = self._lanzar(producto, hilos=10, cantidad=1)

        self.assertEqual(resultados.count("confirmada"), 10)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 0)

    def test_ventas_simultaneas_de_varias_unidades_cada_una(self):
        """Cantidades mayores que uno, para que el reparto no sea
        trivialmente divisible."""
        producto = Producto.objects.create(
            nombre="Router",
            categoria=self.categoria,
            precio=Decimal("420.00"),
            stock=7,
        )

        resultados = self._lanzar(producto, hilos=6, cantidad=3)

        # Con 7 unidades y pedidos de 3, caben exactamente dos.
        self.assertEqual(resultados.count("confirmada"), 2)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 1)

    # ─────────────────────────────────────────────────────────────────
    # Interbloqueo: el motivo del orden por clave primaria
    # ─────────────────────────────────────────────────────────────────
    def test_ventas_cruzadas_de_dos_productos_no_se_interbloquean(self):
        """Comprueba la decision de ordenar el bloqueo por pk.

        Dos ventas que tomaran los mismos dos productos en orden
        inverso quedarian esperandose mutuamente para siempre. Aqui se
        provocan a proposito: si el orden no fuera determinista, los
        hilos no terminarian y el join agotaria su tiempo.
        """
        primero = Producto.objects.create(
            nombre="Producto A",
            categoria=self.categoria,
            precio=Decimal("100.00"),
            stock=50,
        )
        segundo = Producto.objects.create(
            nombre="Producto B",
            categoria=self.categoria,
            precio=Decimal("200.00"),
            stock=50,
        )

        resultados = [None] * 10
        listos = threading.Barrier(10)

        def tarea(indice):
            # Los hilos pares piden A y luego B; los impares al reves.
            orden = (
                [primero.id, segundo.id]
                if indice % 2 == 0
                else [segundo.id, primero.id]
            )
            listos.wait()
            try:
                registrar_venta(
                    usuario=self.vendedores[indice],
                    cliente_nombre="Cliente cruzado",
                    cliente_telefono="70000000",
                    items=[
                        {"producto_id": orden[0], "cantidad": 1},
                        {"producto_id": orden[1], "cantidad": 1},
                    ],
                )
                resultados[indice] = "confirmada"
            except Exception as exc:  # pragma: no cover - diagnostico
                resultados[indice] = f"error:{type(exc).__name__}:{exc}"
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=tarea, args=(i,)) for i in range(10)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=30)

        self.assertTrue(
            all(not h.is_alive() for h in hilos),
            "Algún hilo no terminó: posible interbloqueo.",
        )
        self.assertEqual(resultados.count("confirmada"), 10)
        primero.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(primero.stock, 40)
        self.assertEqual(segundo.stock, 40)


class ConcurrenciaEnLaAnulacion(TransactionTestCase):
    """RNF-10 — la devolucion de existencias tambien es atomica."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Periféricos")
        self.vendedor = Usuario.objects.create(
            username="vendedor", nombre_completo="Vendedor", rol=Rol.VENTAS
        )

    def test_anular_la_misma_venta_a_la_vez_devuelve_el_stock_una_sola_vez(self):
        """RN-VEN-08 bajo concurrencia.

        Sin bloquear la venta al anularla, dos anulaciones simultaneas
        pasarian ambas la comprobacion de estado y devolverian las
        existencias por duplicado, inflando el inventario.
        """
        producto = Producto.objects.create(
            nombre="Monitor",
            categoria=self.categoria,
            precio=Decimal("1250.00"),
            stock=10,
        )
        venta = registrar_venta(
            usuario=self.vendedor,
            cliente_nombre="Cliente",
            cliente_telefono="70000000",
            items=[{"producto_id": producto.id, "cantidad": 4}],
        )
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 6)

        resultados = [None] * 5
        listos = threading.Barrier(5)

        def tarea(indice):
            listos.wait()
            try:
                anular_venta(
                    venta=venta, usuario=self.vendedor, motivo=f"Intento {indice}"
                )
                resultados[indice] = "anulada"
            except Exception as exc:
                resultados[indice] = type(exc).__name__
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=tarea, args=(i,)) for i in range(5)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=30)

        # Solo una anulacion prospera.
        self.assertEqual(resultados.count("anulada"), 1)
        self.assertEqual(resultados.count("VentaYaAnulada"), 4)

        # Y el stock vuelve exactamente al valor previo, no al doble.
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 10)
        venta.refresh_from_db()
        self.assertEqual(venta.estado, EstadoVenta.ANULADA)
