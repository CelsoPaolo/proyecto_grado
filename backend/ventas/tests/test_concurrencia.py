"""T-4.4 y T-8.5 — Concurrencia en las existencias y en su libro.

**Criterio de aceptacion ejecutable de RNF-08 y RNF-24.** Es la unica
evidencia de que las dos garantias se cumplen de verdad: el resto de la
suite comprueba que el codigo hace lo que dice, pero solo estas pruebas
demuestran que lo sigue haciendo cuando dos operaciones ocurren a la
vez.

RNF-08 (T-4.4). Dos encargados venden el ultimo teclado en el mismo
instante. Sin proteccion, ambas peticiones leen stock = 1, ambas
validan que alcanza, y ambas descuentan: el inventario queda en -1 y se
vendio dos veces la misma unidad.

RNF-24 (T-8.5). Desde la v1.4 cada cambio de existencias deja un
movimiento, escrito con la fila todavia bloqueada. Las mismas carreras
deben dejar ademas un libro que cuadra: un movimiento por venta
confirmada, ninguno por venta rechazada, la suma igual al stock, y cada
movimiento partiendo del resultante del anterior. Y una carrera nueva:
ajustes de inventario a la vez que ventas (plan.md 6.5).

Por que TransactionTestCase y no pytest.mark.django_db:
`TestCase` envuelve cada prueba en una transaccion que revierte al
terminar, y dentro de esa unica transaccion los hilos no verian los
commits de los demas: el bloqueo de filas quedaria enmascarado y la
prueba pasaria sin demostrar nada. `TransactionTestCase` usa commits
reales, que es lo que hace falta para que la carrera sea autentica.

Los productos se crean con el servicio de alta (catalogo.services), no
con el ORM: asi su libro tiene punto de partida y puede verificarse.
"""

import random
import threading
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase

from catalogo.models import Categoria
from catalogo.services import crear_producto
from inventario.exceptions import AjusteSinDiferencia
from inventario.models import MovimientoStock, TipoMovimiento
from inventario.services import ajustar_existencias
from inventario.verificacion import cadena_rota, libros_descuadrados
from usuarios.models import Rol, Usuario
from ventas.exceptions import StockInsuficiente
from ventas.models import EstadoVenta, Venta
from ventas.services import anular_venta, registrar_venta


class _ConLibro(TransactionTestCase):
    """Piezas comunes: productos con su alta y verificacion del libro."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Periféricos")
        self.admin = Usuario.objects.create(
            username="admin", nombre_completo="Administrador", rol=Rol.ADMINISTRADOR
        )

    def _producto(self, nombre, stock, precio="100.00"):
        return crear_producto(
            usuario=self.admin,
            nombre=nombre,
            categoria=self.categoria,
            precio=Decimal(precio),
            stock=stock,
        )

    def _verificar_libro(self, producto):
        """RNF-24: el libro cuadra y su cadena no tiene eslabones rotos."""
        self.assertEqual(libros_descuadrados([producto]), [])
        self.assertIsNone(cadena_rota(producto))

    def _movimientos(self, producto, tipo):
        return MovimientoStock.objects.filter(producto=producto, tipo=tipo).order_by("id")


class ConcurrenciaEnElDescuentoDeStock(_ConLibro):
    """Varias ventas simultaneas del mismo producto."""

    def setUp(self):
        super().setUp()
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

    def _verificar_ventas_en_el_libro(self, producto, confirmadas, cantidad):
        """T-8.5: lo que las ventas simultaneas dejan en el libro.

        - un movimiento VENTA por venta confirmada, y ninguno por las
          rechazadas;
        - sus resultantes, en orden, bajan exactamente `cantidad` cada
          vez: si dos ventas hubieran leido el mismo stock, aparecerian
          dos resultantes iguales.
        """
        ventas = list(self._movimientos(producto, TipoMovimiento.VENTA))
        self.assertEqual(len(ventas), confirmadas)
        resultantes = [m.stock_resultante for m in ventas]
        esperados = [
            producto.stock + cantidad * (confirmadas - 1 - i) for i in range(confirmadas)
        ]
        self.assertEqual(resultantes, esperados)
        self.assertEqual(len(set(resultantes)), len(resultantes), "resultantes repetidos")
        self._verificar_libro(producto)

    # ─────────────────────────────────────────────────────────────────
    # El caso central: mas compradores que unidades
    # ─────────────────────────────────────────────────────────────────
    def test_diez_ventas_simultaneas_de_tres_unidades_confirman_solo_tres(self):
        """Los tres criterios de tasks.md T-4.4, en una sola prueba."""
        producto = self._producto("Teclado mecánico", stock=3, precio="350.00")

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

        # T-8.5: y el libro lo refleja, sin rastro de las siete rechazadas.
        self._verificar_ventas_en_el_libro(producto, confirmadas=3, cantidad=1)

    def test_veinte_hilos_sobre_una_sola_unidad_solo_uno_gana(self):
        """El caso mas extremo: una unidad, veinte compradores."""
        producto = self._producto("Última laptop", stock=1, precio="5400.00")

        resultados = self._lanzar(producto, hilos=20, cantidad=1)

        self.assertEqual(resultados.count("confirmada"), 1)
        self.assertEqual(resultados.count("sin_stock"), 19)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 0)
        self._verificar_ventas_en_el_libro(producto, confirmadas=1, cantidad=1)

    def test_con_stock_suficiente_todas_las_ventas_simultaneas_confirman(self):
        """Contraprueba imprescindible, y ademas RNF-19.

        Diez ventas a la vez se completan todas: el sistema soporta
        el uso simultaneo de todo el personal sin degradarse.

        Sin ella, un bug que rechazara TODAS las ventas pasaria las dos
        pruebas anteriores: cero ventas confirmadas nunca deja el stock
        en negativo.
        """
        producto = self._producto("Mouse inalámbrico", stock=10, precio="120.00")

        resultados = self._lanzar(producto, hilos=10, cantidad=1)

        self.assertEqual(resultados.count("confirmada"), 10)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 0)
        self._verificar_ventas_en_el_libro(producto, confirmadas=10, cantidad=1)

    def test_ventas_simultaneas_de_varias_unidades_cada_una(self):
        """Cantidades mayores que uno, para que el reparto no sea
        trivialmente divisible."""
        producto = self._producto("Router", stock=7, precio="420.00")

        resultados = self._lanzar(producto, hilos=6, cantidad=3)

        # Con 7 unidades y pedidos de 3, caben exactamente dos.
        self.assertEqual(resultados.count("confirmada"), 2)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 1)
        self._verificar_ventas_en_el_libro(producto, confirmadas=2, cantidad=3)

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
        primero = self._producto("Producto A", stock=50)
        segundo = self._producto("Producto B", stock=50, precio="200.00")

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
        # T-8.5: cada venta de dos productos deja dos movimientos, uno
        # por producto, y los dos libros cuadran.
        self.assertEqual(self._movimientos(primero, TipoMovimiento.VENTA).count(), 10)
        self.assertEqual(self._movimientos(segundo, TipoMovimiento.VENTA).count(), 10)
        self._verificar_libro(primero)
        self._verificar_libro(segundo)


class ConcurrenciaEnLaAnulacion(_ConLibro):
    """RNF-10 — la devolucion de existencias tambien es atomica."""

    def setUp(self):
        super().setUp()
        self.vendedor = Usuario.objects.create(
            username="vendedor", nombre_completo="Vendedor", rol=Rol.VENTAS
        )

    def test_anular_la_misma_venta_a_la_vez_devuelve_el_stock_una_sola_vez(self):
        """RN-VEN-08 bajo concurrencia.

        Sin bloquear la venta al anularla, dos anulaciones simultaneas
        pasarian ambas la comprobacion de estado y devolverian las
        existencias por duplicado, inflando el inventario.
        """
        producto = self._producto("Monitor", stock=10, precio="1250.00")
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

        # T-8.5: una sola devolucion tambien en el libro.
        self.assertEqual(self._movimientos(producto, TipoMovimiento.ANULACION).count(), 1)
        self._verificar_libro(producto)


class ConcurrenciaEntreAjustesYVentas(_ConLibro):
    """T-8.5 — la carrera de plan.md 6.5, con hilos de verdad.

    Un ajuste calcula su diferencia contra las existencias vigentes. Si
    las leyera sin bloquear la fila, una venta podria colarse entre la
    lectura y la escritura: el ajuste registraria una diferencia
    calculada contra un valor viejo, y su resultante no seria el del
    movimiento anterior mas su cantidad. La cadena del libro se
    romperia aunque, por usar F() al escribir, la suma pudiera seguir
    cuadrando. Por eso aqui se exige la cadena entera, no solo la suma.
    """

    HILOS_VENTA = 15
    HILOS_AJUSTE = 15

    def setUp(self):
        super().setUp()
        self.vendedores = [
            Usuario.objects.create(
                username=f"vendedor{i}", nombre_completo=f"Vendedor {i}", rol=Rol.VENTAS
            )
            for i in range(self.HILOS_VENTA)
        ]

    def _carrera(self, producto, semilla):
        azar = random.Random(semilla)
        # Cantidades reales distintas entre si y del stock inicial, para
        # que casi ningun ajuste quede sin diferencia.
        contados = azar.sample(range(60, 200), self.HILOS_AJUSTE)
        total = self.HILOS_VENTA + self.HILOS_AJUSTE
        resultados = [None] * total
        listos = threading.Barrier(total)

        def vender(indice):
            listos.wait()
            try:
                registrar_venta(
                    usuario=self.vendedores[indice],
                    cliente_nombre="Cliente",
                    cliente_telefono="70000000",
                    items=[{"producto_id": producto.id, "cantidad": 1}],
                )
                resultados[indice] = "venta"
            except StockInsuficiente:
                resultados[indice] = "sin_stock"
            except Exception as exc:  # pragma: no cover - diagnostico
                resultados[indice] = f"error:{type(exc).__name__}:{exc}"
            finally:
                connections.close_all()

        def ajustar(indice, contado):
            listos.wait()
            try:
                ajustar_existencias(
                    producto_id=producto.id,
                    cantidad_real=contado,
                    # Lo contado viaja en el motivo para poder comprobar
                    # despues que el ajuste dejo exactamente eso.
                    motivo=f"Recuento simultáneo: {contado}",
                    usuario=self.admin,
                )
                resultados[indice] = "ajuste"
            except AjusteSinDiferencia:
                resultados[indice] = "sin_diferencia"
            except Exception as exc:  # pragma: no cover - diagnostico
                resultados[indice] = f"error:{type(exc).__name__}:{exc}"
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=vender, args=(i,)) for i in range(self.HILOS_VENTA)]
        hilos += [
            threading.Thread(target=ajustar, args=(self.HILOS_VENTA + i, contados[i]))
            for i in range(self.HILOS_AJUSTE)
        ]
        azar.shuffle(hilos)
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=60)

        self.assertTrue(all(not h.is_alive() for h in hilos), "Algún hilo no terminó.")
        return resultados

    def test_ajustes_y_ventas_simultaneos_dejan_el_libro_cuadrado(self):
        """Tres rondas con distinto orden de arranque."""
        for semilla in (1, 2, 3):
            with self.subTest(ronda=semilla):
                producto = self._producto(f"Disco {semilla}", stock=50)

                resultados = self._carrera(producto, semilla)

                errores = [r for r in resultados if r and r.startswith("error:")]
                self.assertEqual(errores, [], f"Errores inesperados: {errores}")
                producto.refresh_from_db()

                # Cada operacion que prospero dejo exactamente un movimiento.
                self.assertEqual(
                    self._movimientos(producto, TipoMovimiento.VENTA).count(),
                    resultados.count("venta"),
                )
                self.assertEqual(
                    self._movimientos(producto, TipoMovimiento.AJUSTE).count(),
                    resultados.count("ajuste"),
                )
                # La carrera ocurrio de verdad: hubo de las dos.
                self.assertGreater(resultados.count("venta"), 0)
                self.assertGreater(resultados.count("ajuste"), 0)

                # RNF-24: el libro cuadra y ningun eslabon esta roto.
                self._verificar_libro(producto)

                # Cada ajuste dejo las existencias exactamente en lo
                # contado, aunque hubiera ventas alrededor (CU-CAT-07).
                for ajuste in self._movimientos(producto, TipoMovimiento.AJUSTE):
                    contado = int(ajuste.motivo.rsplit(":", 1)[1])
                    self.assertEqual(ajuste.stock_resultante, contado)
