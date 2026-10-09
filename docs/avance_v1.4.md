# Avance de la v1.4

Rama: `feat/v1.4`. Una línea por tarea terminada. Si la sesión se corta,
se retoma desde la primera tarea sin línea aquí y sin `[x]` en
`specs/tasks.md`.

En la columna de pruebas, «B» es el backend (pytest) y «F» el frontend
(vitest). Los fallos del backend son siempre del guardián de
trazabilidad (`core/tests/test_trazabilidad.py`): requisitos de la v1.4
que aún no tienen código. El objetivo es que lleguen a 0 al cerrar el
bloque 13.

| Fecha | Tarea | Commit | Pruebas (pasan / fallan) | Decisiones y por qué |
|---|---|---|---|---|
| 2026-10-08 | T-8.1 Modelo `MovimientoStock` | `83f9aa8`, `8e372f9` | B 642 / 33 | Inmutable en tres niveles: instancia, queryset y `CHECK` de la base. Se añadió el guardián `test_recoleccion.py`, porque `inventario` había quedado fuera de `testpaths`. |
| 2026-10-08 | T-8.2 Movimientos en la venta y la anulación | `ad2ca1f` | B ≈660 / 33 | El resultante se calcula con el valor leído bajo bloqueo, sin volver a leer. |
| 2026-10-09 | T-OP.1 Exportar el catálogo antiguo a CSV | `4b7658a` | — | Los CSV quedan fuera de Git (`/datos_importacion/`). Se exportaron desde una copia de la copia de seguridad, nunca desde XAMPP. |
| 2026-10-09 | T-8.3 Alta con movimiento y ajuste con bloqueo | `4ed0d17`, `09dd9fd` | B ≈680 / 32 | Editar con `stock` responde 400 en lugar de ignorarse (decisión del usuario). |
| 2026-10-09 | T-8.4 Migración de saldos iniciales | `9bdab10` | B 690 / 31 | Idempotente: los productos que ya tienen origen no reciben otro saldo. Probada en los dos sentidos con 165 productos. |
| 2026-10-09 | T-8.5 Concurrencia y guardián del libro | `19538b9`, `73c39c0` | B 697 / 31 · F 137 / 0 | Además de la suma, se verifica la cadena de resultantes: sin el bloqueo, la suma cuadra siempre (ver `docs/evidencia_concurrencia.md`). |
| 2026-10-09 | T-8.6 API de movimientos y ajuste | `9edfd1c` | B 754 / 28 | Un filtro inválido responde 400 en lugar de ignorarse. Las fechas se filtran en hora de Bolivia. |

| 2026-10-09 | T-8.7 Pantallas de movimientos y ajuste | `d2e2f88` | B 754 / 28 · F 153 / 0 | La confirmación (RNF-14) se hace en dos pasos dentro del diálogo, no con un `ConfirmDialog` encima: así la revisión muestra la diferencia y el motivo. Detalle de producto nuevo en `/catalogo/:id` (Administrador y Ventas; historial y ajuste solo Administrador). Menú «Movimientos» en `/movimientos`. El filtro de producto busca también entre los retirados, porque su historial sigue siendo auditable. Utilidad compartida `src/utils/fechas.js`; las vistas antiguas mantienen su copia local para no tocarlas sin necesidad. |
| 2026-10-09 | T-8.8 Revisión del bloque 8 | siguiente commit | B 755 / 28 · F 153 / 0 | La comprobación «en el navegador» se sustituye, en lo automatizable, por una prueba del ciclo completo a través de la API, que verifica el libro cuadrado. La parte visual queda abajo, para revisión humana. Se marca como hecha porque no queda nada automatizable pendiente; si la revisión visual encuentra algo, se reabre. |

## Pendiente para revisión humana

- **T-8.5:** ninguna comprobación manual; la evidencia está en
  `docs/evidencia_concurrencia.md`.
- **T-8.7, en el navegador, como Administrador:**
  - Catálogo → clic en el nombre de un producto → se abre su detalle con
    el historial.
  - «Ajustar existencias»: comprobar que la diferencia orientativa
    cambia al escribir, «Revisar ajuste», el texto «de X a Y», «Volver»
    y «Confirmar ajuste».
  - Tras confirmar, el aviso y el historial actualizado.
  - Menú «Movimientos»: los filtros de producto (autocompletar), tipo y
    rango de fechas (calendario de rango), y la paginación.
  - Como Encargado de Ventas: no aparece «Movimientos» en el menú, y en
    el detalle de producto no hay historial ni botón de ajuste.
- **T-8.8, ciclo del bloque 8 en el navegador:**
  - Crear un producto con 10 unidades, venderle 3, anular esa venta y
    ajustar a 8.
  - En su detalle deben verse cuatro movimientos: Alta +10, Venta −3,
    Anulación +3 y Ajuste −2, y las existencias deben quedar en 8.
