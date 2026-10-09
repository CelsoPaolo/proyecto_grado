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
| 2026-10-09 | T-8.8 Revisión del bloque 8 | `59342e8` | B 755 / 28 · F 153 / 0 | La comprobación «en el navegador» se sustituye, en lo automatizable, por una prueba del ciclo completo a través de la API, que verifica el libro cuadrado. La parte visual queda abajo, para revisión humana. Se marca como hecha porque no queda nada automatizable pendiente; si la revisión visual encuentra algo, se reabre. |
| 2026-10-09 | T-9.1 Generación del código EAN-13 | `e6e28b0` | B 783 / 27 · F 153 / 0 | El código se asigna en `Producto.save()` al insertar, y no en el servicio de alta, para que lo reciba todo producto, incluidos los de las fábricas de prueba y la importación. El campo nace nulo en esta tarea porque la migración en tres pasos del plan empieza aquí. `catalogo/codigos.py` no importa modelos, para que la migración de T-9.2 use las mismas funciones. Se retiró una cita prematura a RNF-27, que llega en T-9.5. |
| 2026-10-09 | T-9.2 Migración del código para los productos existentes | `dfbc04b` | B 787 / 27 · F 153 / 0 | **Cambio en `plan.md` §3.5 (RNF-22):** el reverso del paso 2 ya no deja los códigos en nulo, porque reaplicarlo daría códigos distintos a productos ya etiquetados (RN-CAT-08). Revertir los tres pasos sigue dejando la tabla idéntica. Aplicado a la base de desarrollo (7 productos). |
| 2026-10-09 | T-9.3 Búsqueda por código | `923fae7` | B 798 / 26 · F 153 / 0 | `?codigo=` vacío da una lista vacía en lugar de ignorarse: un Intro con el campo vacío no debe traer el catálogo entero. Se mantiene el filtro de activos por defecto del listado; los retirados se buscan con `activo=false`. |
| 2026-10-09 | T-9.7 Código de fábrica opcional (PA-07) | `947a79a` | B 823 / 25 · F 158 / 0 | Se hace antes que T-9.4 porque T-9.5 lo necesita, como indica `tasks.md`. El mensaje de duplicado nombra el producto que ya tiene el código: solo lo ve el Administrador. **Defecto anterior corregido:** el envío multipart omitía las cadenas vacías. Las pruebas de migración pasan a usar los modelos **históricos**, porque los actuales tienen columnas que en los estados intermedios no existen. |
| 2026-10-09 | T-9.4 Código de barras y etiqueta | `091b8da` | B 824 / 24 · F 168 / 0 | JsBarcode fijado en `3.11.6`, sin `^`. Un código de fábrica que no es EAN-13 se dibuja en Code128. Etiqueta impresa con `window.print()` y `@media print`, sin PDF (plan.md §7.9). La etiqueta está para los dos roles (CU-CAT-09). Filtro de código exacto como campo aparte de la búsqueda por nombre, para no confundir un nombre numérico con un código. |
| 2026-10-09 | T-9.5 Entrada por código en la venta | `aebe539` | B 826 / 22 · F 182 / 0 | Dos decisiones que el plan no recogía. **Cola de lecturas y campo vaciado en el mismo Intro:** un lector envía la segunda lectura antes de que responda la primera. **Tope por existencias:** una lectura que excedería el stock avisa en lugar de sumar, en vez de dejar que lo rechace el servidor al confirmar. El campo de código va encima del buscador por nombre y recibe el foco al abrir la pantalla. |
| 2026-10-09 | T-9.6 Revisión del bloque 9 | `061de85` | B 827 / 22 · F 182 / 0 | Igual que en T-8.8: se automatiza el ciclo por la API y la parte visual queda para revisión humana. Todos los requisitos del bloque 9 están citados. |
| 2026-10-09 | T-OP.2 a T-OP.4, cambio de orden | — | — | Las T-OP dependen del bloque 9, pero se harán al final: el bloque 10 añade `meses_garantia` al producto, y así el comando de importación nace con el modelo definitivo. |
| 2026-10-09 | T-10.1 Meses de garantía en producto y detalle | `31c4966` | B 836 / 21 · F 184 / 0 | `IntegerField` con `CHECK (>= 0)` en lugar de `PositiveIntegerField`, para nombrar la restricción como las demás. El formulario no pone tope superior, porque la spec no lo fija. Se retiró una cita prematura a RF-75, que llega en T-10.2. |
| 2026-10-09 | T-10.2 Congelado de la garantía en la venta | `10f4397` | B 840 / 20 · F 184 / 0 | Ninguna decisión nueva: sigue el patrón del precio y el nombre. |
| 2026-10-09 | T-10.3 Cálculo del vencimiento | siguiente commit | B 852 / 20 · F 184 / 0 | Módulo nuevo `ventas/garantia.py`. Además de `sumar_meses`, incluye `vencimiento()`, que parte de la fecha de la venta en hora de Bolivia, como exige RN-VEN-13. |

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
- **T-9.7:** en el formulario de producto, el campo «Código de fábrica»:
  - registrarlo, corregirlo y vaciarlo;
  - con uno repetido, el error debe aparecer junto al campo;
  - repetir la prueba de vaciarlo **subiendo a la vez una imagen nueva**.
- **T-9.4, criterio de aceptación de la tarea:**
  - En el detalle de un producto, «Imprimir etiqueta». La vista previa
    debe mostrar **solo** la etiqueta: barras, cifras y nombre.
  - Imprimirla y escanearla con la app lectora del teléfono: debe
    devolver exactamente el código interno.
  - Comprobar también la columna «Código» y el filtro «Código exacto» de
    la lista.
- **T-9.5, lector en la venta:**
  - Abrir «Registrar venta»: el cursor debe estar en el campo «Código».
  - Teclear un código interno y pulsar Intro: se agrega, el campo queda
    vacío y con el foco.
  - Repetir con un código de fábrica, con un código inexistente (aviso
    en rojo y código seleccionado) y con un producto agotado.
  - Si consigue un lector USB o una app de teléfono que funcione como
    teclado, leer varias etiquetas seguidas.
- **Dependencias:** `npm audit` informa de 1 vulnerabilidad alta en
  `source-map-js`, una herramienta de desarrollo que ya estaba instalada
  antes de esta versión; no viene de JsBarcode. No apliqué `npm audit
  fix` porque cambiaría otras dependencias sin aprobación.
