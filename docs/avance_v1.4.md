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
| 2026-10-09 | T-10.3 Cálculo del vencimiento | `7a23f75` | B 852 / 20 · F 184 / 0 | Módulo nuevo `ventas/garantia.py`. Además de `sumar_meses`, incluye `vencimiento()`, que parte de la fecha de la venta en hora de Bolivia, como exige RN-VEN-13. |
| 2026-10-09 | T-10.4 Plantilla base de documentos PDF | `3b9b431` | B 854 / 20 · F 184 / 0 | Los «mismos colores en su flujo» se verifican comparando los operadores `rg`/`RG` del PDF con los registrados **antes** de la extracción. El pie admite una leyenda propia por documento (bloque `leyenda`), con la del informe por defecto. |
| 2026-10-09 | T-10.5 Endpoint de la garantía | `3730ac7` | B 875 / 18 · F 184 / 0 | Dos códigos de error distintos para los dos 409, de modo que la interfaz pueda distinguirlos. El documento se titula «Certificado de garantía». Incluye una frase neutra («Conserve este certificado…»), pero **no condiciones de garantía, que la spec no define**. La fecha que se imprime es la de la venta en hora de Bolivia. |
| 2026-10-09 | T-10.6 Garantía en la interfaz | `e519c21` | B 876 / 17 · F 190 / 0 | La oferta de RF-77 se hace en el detalle de la venta, al que ya se llegaba tras confirmar, marcado con `?recien=1`: no hace falta otra pantalla. Se actualizó la prueba de navegación de T-4.9 porque el comportamiento cambia por RF-77; no se silenció. |
| 2026-10-09 | T-10.7 Revisión del bloque 10 | `7936c95` | B 878 / 17 · F 190 / 0 | Punto de extensión para las condiciones de la garantía, como pediste: la constante `CONDICIONES_DE_GARANTIA` en `ventas/garantia.py`, que se lee en cada petición y cuya sección solo aparece si tiene texto. |
| 2026-10-09 | T-11.1 App `clientes` y modelo `Cliente` | `7a74c37` | B 894 / 17 · F 190 / 0 | `actualizado_por` es obligatorio: al registrar un cliente coincide con `creado_por`. La dirección es un `CharField(255)` en blanco. Se retiraron tres citas prematuras (RF-84, RF-89 y RNF-26), que se implementan en la API (T-11.3). |
| 2026-10-09 | T-11.2 Servicio de clientes | `4ebc392` | B 908 / 13 · F 190 / 0 | Desactivar un cliente ya inactivo no es un error, solo no cambia nada. El mensaje de carnet duplicado **no dice a qué cliente pertenece**, para no revelar un dato personal (RN-CLI-06). Hay dos defensas ante el duplicado; la mutación de una sola sobrevive, y es lo esperado. |
| 2026-10-09 | T-11.3 API de clientes | `db558b2` | B 952 / 10 · F 190 / 0 | Sin `?activo=`, la lista incluye a los inactivos, porque el Administrador los necesita para reactivarlos; el selector de la venta pedirá `activo=true`. El carnet se busca **solo por coincidencia exacta**, para que no se pueda adivinar cifra a cifra. La edición es solo `PATCH`, sin `PUT`. |
| 2026-10-09 | T-11.4 Cliente en la venta ⚠️ | `39a782b` | B 964 / 8 · F 190 / 0 | La fila del cliente se bloquea con `select_for_update` para que una desactivación simultánea no se cuele. Un `cliente_id` inexistente responde 400 junto al campo. **Incidente corregido:** al insertar la función auxiliar quedó bajo el `@transaction.atomic` de `registrar_venta`, y la venta dejó de ser atómica. Lo detectaron las pruebas de concurrencia de T-8.5 (6 fallos) y se corrigió antes del commit. Se actualizó la prueba de firma de T-4.2 para incluir `cliente_id`; sigue garantizando que no entra precio. |
| 2026-10-09 | T-11.5 Pantallas de clientes | `d093179` | B 964 / 8 · F 200 / 0 | La lista muestra los activos por defecto; el filtro se puede limpiar para ver todos. Tras registrar un cliente desde la lista se abre su detalle. El formulario avisa junto al carnet de que es un dato personal. |
| 2026-10-09 | T-11.6 Selector de cliente en la venta | `30f8d92` | B 964 / 8 · F 205 / 0 | El modo por defecto es «Cliente ocasional», para que la pantalla funcione igual que en la v1.3. Con un cliente registrado solo se envía su id, porque el nombre y el teléfono los copia el servidor. |
| 2026-10-09 | T-11.7 Revisión del bloque 11 | `2462a59` | B 965 / 8 · F 205 / 0 | El ciclo comprueba también que la garantía no lleva el carnet **de un cliente real**: la prueba de T-10.5 solo podía buscar la palabra. |
| 2026-10-09 | T-12.1 Cálculo del reporte por rango | `ac88414` | B 973 / 7 · F 205 / 0 | `calcular()` devuelve también `desde` y `hasta`, para que las tres salidas rotulen el rango igual. Los detalles (más vendidos, por usuario, por estado) se añaden en T-12.3 a esta misma función. |
| 2026-10-09 | T-12.2 El panel diario como reporte de un día | `fa41efe` | B 975 / 7 · F 205 / 0 | **Precisión en `tasks.md` (RNF-22):** la prueba estructural del panel, que buscaba `Sum(` en `panel/services.py`, pasa a leer también `panel/reportes.py`, adonde se movió la suma. Su intención no cambia. No dejé un `Sum(` artificial en `services.py` para que pasara sin tocarla. Se quitaron imports que quedaron sin uso. |
| 2026-10-09 | T-12.3 Detalles del reporte | `2b5c934` | B 983 / 4 · F 205 / 0 | `calcular(..., con_detalles=False)` para el panel, que no usa las tablas. Ventas por usuario ordenadas por importe descendente. Desempate final por id en las dos tablas, para que el orden sea estable entre la pantalla, el PDF y el Excel. |
| 2026-10-09 | T-12.4 API del reporte | `6c4481b` | B 998 / 3 · F 205 / 0 | La validación del rango vive en `panel/reportes.py` y la usarán también el PDF y el Excel, así que las tres salidas rechazan lo mismo. No se pone un tope al rango (RNF-28 habla de rendimiento con hasta un año, no de un límite). |
| 2026-10-09 | T-12.5 Exportación a PDF | `572292d` | B 1008 / 2 · F 205 / 0 | Título «Reporte de operación», con el rango en el lugar del número. Leyenda propia en el pie: «Reporte interno de operación, no válido como documento fiscal». Las secciones vacías dicen «Sin ventas en el período». |
| 2026-10-09 | T-12.6 Exportación a Excel | `5597dba` | B 1017 / 1 · F 205 / 0 | `openpyxl` fijado en 3.1.5 en el entorno; en `requirements/base.txt` queda como `>=3.1.5`, al estilo del resto. Trae una sola dependencia, `et-xmlfile`, también Python puro. Las fechas del rango van como fechas de Excel con formato `DD/MM/YYYY`, y el archivo se sirve como `attachment`. |
| 2026-10-09 | T-12.7 Coherencia de las tres salidas ⚠️ | `08bcd97` | **B 1026 / 0** · F 205 / 0 | **El guardián de trazabilidad llega a 0 fallos.** Hallazgo de rendimiento: con estadísticas viejas, `productos_mas_vendidos` (que usaba `venta__in=<subconsulta>`) tardaba 213 s por petición en la suite completa. Se reescribe como join, y la prueba ejecuta `ANALYZE` tras la carga, porque RNF-28 habla de «carga normal» y dentro de la transacción de la prueba autovacuum no ve las filas. El comando de importación (T-OP.2) ejecutará `ANALYZE` al aplicar. Hubo además una parada aislada de 214 s en una ejecución suelta que no se reprodujo, con el mismo origen. |
| 2026-10-09 | T-12.8 Pantalla de reportes | `feb94c8` | B 1026 / 0 · F 217 / 0 | Al abrir se muestra «Este mes». Al elegir un rango a mano se quita el atajo, y al revés. Los atajos se calculan con la fecha del navegador, que es la de Bolivia en el equipo de la tienda. `useDescarga.guardar()` acepta `{tipo, extension, descripcion}`. |
| 2026-10-09 | T-13.1 Matriz de permisos y guardianes | `ae7e7d6` | B 1063 / 0 · F 217 / 0 | Las 17 reglas v1.4 de `plan.md` §9 se añaden al guardián de cobertura, apuntando a pruebas que ya existían. La de RN-CAT-10 se completó con la comprobación de «no crea movimiento» que exigía el plan y no estaba escrita. |
| 2026-10-09 | T-13.2 Usabilidad de lo nuevo | `2d54513` | B 1063 / 0 · F 217 / 0 | Sin cambios de código. Se marca hecha la parte automatizable; el recorrido en tres anchos queda abajo. «Registrar cliente» no pide confirmación, igual que el resto de altas del sistema: RNF-14 se aplica a modificar y desactivar, no a crear. |
| 2026-10-09 | T-13.3 Coherencia y documentación | siguiente commit | B 1064 / 0 · F 217 / 0 | `plan.md` pasa a la v1.4 con una tabla §11.4 de precisiones de implementación (ninguna cambia un requerimiento, así que `spec.md` no se toca). README y guion actualizados. Esquema OpenAPI sin avisos y vigilado por una prueba. |

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
- **T-10.5, texto de la garantía:** revisar la frase «Conserve este
  certificado: lo necesitará para hacer valer la garantía…». Si
  PC-Solution tiene condiciones de garantía propias (qué cubre, dónde
  presentarla), habría que decidir si van en el documento: hoy la spec
  no las define y no las inventé.
- **T-10.6:** confirmar una venta con un producto con garantía. Al llegar al detalle debe aparecer «Emitir garantía»; descargarla, elegir la carpeta y abrir el PDF para revisar membrete, línea morada, tabla de líneas y vencimientos. En una venta anulada no debe haber botón.
- **Condiciones de la garantía (para ti y el dueño):** pegar el texto en
  `backend/ventas/garantia.py`, constante `CONDICIONES_DE_GARANTIA`, que
  es el único lugar. Los saltos de línea se respetan. Mientras esté
  vacía, el PDF no muestra la sección «Condiciones de la garantía».
- **T-10.7:** vender un producto con garantía, emitirla y abrir el PDF.
  Cambiar los meses del producto, emitirla otra vez y comprobar que el
  vencimiento es el mismo.
- **T-11.5, clientes:**
  - Menú «Clientes»: buscar por nombre, por teléfono y por carnet
    exacto; el carnet no debe verse en la lista.
  - Registrar un cliente con un carnet repetido: el error debe aparecer
    junto al campo.
  - En el detalle, como Administrador, desactivar y reactivar con
    confirmación. Como Encargado de Ventas, no debe aparecer esa acción.
- **T-11.6, venta con cliente:**
  - En «Registrar venta», cambiar a «Cliente registrado», buscar uno y
    confirmar la venta.
  - Repetir registrando un cliente nuevo desde el botón del diálogo.
  - Comprobar que un cliente desactivado no aparece en la búsqueda.
- **T-11.7, ciclo del bloque 11:**
  - Vender a un cliente registrado y, después, cambiarle el nombre y el
    teléfono en su ficha.
  - Abrir el detalle de la venta: debe conservar los datos originales.
  - Emitir su garantía: no debe aparecer el carnet.
- **Rendimiento tras cargas masivas (T-12.7):** justo después de cargar
  muchos datos de golpe, y antes de que autovacuum actualice las
  estadísticas (normalmente en minutos), un reporte de un año podría ir
  lento. El comando de importación ejecutará `ANALYZE` al aplicar. Si
  alguna vez se restaura una copia grande de la base, conviene ejecutar
  `ANALYZE;` en PostgreSQL.
- **T-12.8, reportes (como Administrador):**
  - Probar los atajos Hoy, Esta semana y Este mes, y un rango con el
    calendario.
  - Comprobar el aviso de «sin actividad» en un rango vacío.
  - Exportar a PDF y a Excel; abrir ambos archivos y comparar las
    cifras con la pantalla.
- **T-13.2, recorrido en tres anchos (1440, 1024 y 768 px):** pantallas
  Movimientos, detalle de producto (con la etiqueta), Registrar venta
  (campo de código y selector de cliente), Clientes, detalle de cliente
  y Reportes. Buscar texto cortado, botones que no caben y tablas
  ilegibles.
- **Dependencias:** `npm audit` informa de 1 vulnerabilidad alta en
  `source-map-js`, una herramienta de desarrollo que ya estaba instalada
  antes de esta versión; no viene de JsBarcode. No apliqué `npm audit
  fix` porque cambiaría otras dependencias sin aprobación.

## Dónde se detuvo la sesión

Bloques 8 a 13 terminados. **Siguiente: T-OP.2** (comando `importar_catalogo` con informe y huella). T-OP.4 (aplicar) espera aprobación expresa.
