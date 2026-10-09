# Evidencia: concurrencia en el libro de movimientos de stock (T-8.5)

**Fecha de las ejecuciones:** 2026-10-09
**Rama:** `feat/v1.4` · commit de T-8.5: `19538b9`
**Entorno:** Windows 11, PostgreSQL 18, Django 5.1, portátil conectado a la corriente
**Requisitos que respalda:** RNF-08, RNF-24, RN-MOV-03, CU-CAT-07

---

## 1. Qué se quería demostrar

Cada cambio de existencias deja un movimiento en el libro (`MovimientoStock`)
en la misma transacción, con la fila del producto bloqueada
(`select_for_update()`), según `specs/plan.md` §6.5. Si el diseño es correcto,
para cada producto se cumplen siempre tres propiedades:

| Propiedad | Qué se comprueba |
|---|---|
| **Suma** | `SUM(cantidad de sus movimientos) == stock` |
| **Último resultante** | `stock_resultante del último movimiento == stock` |
| **Cadena** | cada movimiento cumple `resultante_i == resultante_(i-1) + cantidad_i` |

Las dos primeras las comprueba `libros_descuadrados()` y la tercera
`cadena_rota()`, ambas en `backend/inventario/verificacion.py`.

La carrera peligrosa es la siguiente: un **ajuste** de inventario calcula la
diferencia entre lo contado y el stock vigente. Si lee el stock sin bloquear
la fila, una venta puede colarse entre la lectura y la escritura. La
diferencia queda entonces calculada contra un valor viejo.

## 2. Qué se probó

Prueba: `backend/ventas/tests/test_concurrencia.py`, clase
`ConcurrenciaEntreAjustesYVentas`.

- **Producto:** se crea con 50 unidades a través del servicio de alta (ALTA 50).
- **Hilos:** 30 hilos reales con conexiones independientes a PostgreSQL:
  - 15 venden 1 unidad cada uno;
  - 15 ajustan el stock a una cantidad contada distinta, entre 60 y 199.
- **Arranque simultáneo:** una `threading.Barrier` libera los 30 hilos a la vez.
  El orden de arranque se baraja con una semilla.
- **Rondas:** 3 por ejecución (semillas 1, 2 y 3), cada una con un producto nuevo.
- **Exigencias de la prueba:**
  - no hay errores inesperados;
  - hay un movimiento por cada operación confirmada;
  - suma, último resultante y cadena correctos;
  - cada ajuste deja exactamente lo contado.

Además, las pruebas heredadas de T-4.4 (ventas simultáneas y anulación
simultánea) comprueban ahora el libro:

- hay un movimiento VENTA por cada venta confirmada;
- los resultantes bajan sin repetirse;
- una anulación simultánea deja un solo movimiento ANULACION.

**Mutación:** para comprobar que la prueba detecta el fallo, se sustituyó
temporalmente en `inventario/services.py`

```python
Producto.objects.select_for_update(), pk=producto_id
```

por

```python
Producto.objects.all(), pk=producto_id
```

Después se restauró el archivo con `git checkout`, y `git status` quedó
limpio.

## 3. Resultados de la prueba de la suite

| Código | Ejecuciones | Resultado |
|---|---|---|
| Con bloqueo (código real), `test_concurrencia.py` completo | 5 seguidas | **5/5 pasan**: 7 pruebas y 3 subpruebas, entre 6,7 s y 7,7 s cada ejecución |
| Sin bloqueo (mutante), prueba de ajustes y ventas | 5 seguidas | **5/5 fallan**: las 3 rondas fallan en cada ejecución |

La suite completa del backend (697 pruebas) pasa también con el guardián
del libro activo tras cada prueba. Las únicas pruebas que fallan son las
31 de trazabilidad de requisitos de v1.4 que aún no se han implementado.

## 4. Detalle ronda a ronda (sonda de diagnóstico)

La prueba de la suite se detiene en el primer fallo de cada ronda. Para ver
**todas** las propiedades a la vez, se ejecutó una sonda temporal que repite
la misma carrera y anota cada propiedad sin detenerse. Hubo 5 ejecuciones
con bloqueo y 5 sin bloqueo, cada una de 3 rondas: 30 rondas en total.

### 4.1 Con bloqueo: 15 de 15 rondas correctas

En todas las rondas:

- las 15 ventas y los 15 ajustes se confirmaron;
- la suma, el último resultante y la cadena son correctos;
- cada ajuste dejó exactamente lo contado.

| Ejecución | Ronda 1 (stock final) | Ronda 2 | Ronda 3 |
|---|---|---|---|
| 1 | 170 ✅ | 113 ✅ | 181 ✅ |
| 2 | 67 ✅ | 148 ✅ | 93 ✅ |
| 3 | 157 ✅ | 80 ✅ | 63 ✅ |
| 4 | 186 ✅ | 64 ✅ | 62 ✅ |
| 5 | 90 ✅ | 157 ✅ | 118 ✅ |

El stock final varía porque depende de qué operación obtuvo el bloqueo en
último lugar. En todos los casos coincide con el libro.

### 4.2 Sin bloqueo: 15 de 15 rondas con el libro corrupto

| Ejec. | Ronda | Desenlaces | Stock | Suma | Último | Suma ok | Último ok | Cadena |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 15 ventas, 10 ajustes, 5 IntegrityError | 135 | 135 | 186 | ✅ | ❌ | ❌ rota |
| 1 | 2 | 15 ventas, 14 ajustes, 1 IntegrityError | 523 | 523 | 81 | ✅ | ❌ | ❌ rota |
| 1 | 3 | 14 ventas, 1 sin stock, 13 ajustes, 2 IntegrityError | 0 | 0 | 126 | ✅ | ❌ | ❌ rota |
| 2 | 1 | 15 ventas, 9 ajustes, 6 IntegrityError | 210 | 210 | 125 | ✅ | ❌ | ❌ rota |
| 2 | 2 | 15 ventas, 8 ajustes, 7 IntegrityError | 73 | 73 | 73 | ✅ | ✅ | ❌ **solo la cadena** |
| 2 | 3 | 15 ventas, 15 ajustes | 1420 | 1420 | 161 | ✅ | ❌ | ❌ rota |
| 3 | 1 | 15 ventas, 12 ajustes, 3 IntegrityError | 120 | 120 | 157 | ✅ | ❌ | ❌ rota |
| 3 | 2 | 14 ventas, 1 sin stock, 7 ajustes, 8 IntegrityError | 0 | 0 | 0 | ✅ | ✅ | ❌ **solo la cadena** |
| 3 | 3 | 15 ventas, 14 ajustes, 1 IntegrityError | 567 | 567 | 181 | ✅ | ❌ | ❌ rota |
| 4 | 1 | 15 ventas, 12 ajustes, 3 IntegrityError | 462 | 462 | 462 | ✅ | ✅ | ❌ **solo la cadena** |
| 4 | 2 | 15 ventas, 8 ajustes, 7 IntegrityError | 119 | 119 | 119 | ✅ | ✅ | ❌ **solo la cadena** |
| 4 | 3 | 15 ventas, 15 ajustes | 349 | 349 | 181 | ✅ | ❌ | ❌ rota |
| 5 | 1 | 15 ventas, 15 ajustes | 86 | 86 | 86 | ✅ | ✅ | ❌ **solo la cadena** |
| 5 | 2 | 15 ventas, 14 ajustes, 1 IntegrityError | 351 | 351 | 74 | ✅ | ❌ | ❌ rota |
| 5 | 3 | 15 ventas, 12 ajustes, 3 IntegrityError | 7 | 7 | 7 | ✅ | ✅ | ❌ **solo la cadena** |

**Resumen sin bloqueo:**

| Comprobación | Rondas en que detectó el error |
|---|---|
| Suma (`SUM == stock`) | **0 de 15** |
| Último resultante | 9 de 15 |
| Cadena de resultantes | **15 de 15** |
| Errores de la base (`IntegrityError`) | 12 de 15 rondas, 47 operaciones |

## 5. Interpretación

### 5.1 La suma no detecta la falta de bloqueo

Sin el bloqueo, **la suma cuadró en las 15 rondas.** La razón es que el
stock se escribe con `F("stock") + diferencia`, es decir, sumando en la base
lo mismo que se anota en el movimiento. La suma de movimientos y el stock
avanzan siempre juntos, aunque la diferencia esté calculada contra un valor
viejo.

Por eso una verificación basada solo en `SUM(cantidad) == stock`, que es la
comprobación habitual de un kardex, habría dado por bueno un libro corrupto
en el 100 % de los casos.

### 5.2 El caso que solo detecta la cadena

En 6 de las 15 rondas sin bloqueo, la suma **y** el último resultante
coincidían con el stock. El libro parecía perfecto mirando su final, y solo
la cadena reveló el error.

Ejemplo, ejecución 4, ronda 2:

- stock final 119, suma 119, último resultante 119: todo parece correcto;
- pero en el movimiento 32 (un AJUSTE), el anterior resultante más la
  cantidad da **286**, mientras que el registrado es **199**.

Ese ajuste anotó «el stock queda en 199», que era lo contado. Sin embargo,
calculó su diferencia contra un stock que otra operación ya había cambiado,
así que el stock real tras él no fue 199. Por coincidencia, los movimientos
posteriores llevaron el último resultante a coincidir con el stock, y el
error quedó oculto en el estado final.

Una prueba de mutación de pocos segundos es lo que reveló esta clase de
defecto. Sin ella, la verificación por suma se habría considerado
suficiente.

### 5.3 Consecuencias visibles para el negocio

- **Existencias inventadas.** En la ejecución 2, ronda 3, el último recuento
  físico registrado fue de 161 unidades, pero el sistema terminó con **1420**:
  varios ajustes calcularon su diferencia contra stocks ya superados y cada uno sumó la suya.
- **Operaciones rechazadas.** 47 operaciones fallaron con `IntegrityError`
  (`producto_stock_no_negativo`). Un ajuste con diferencia negativa,
  calculada antes de varias ventas, habría dejado el stock bajo cero, y la
  restricción `CHECK` de PostgreSQL lo impidió. Es la segunda línea de
  defensa (RN-CAT-02). Evita un stock negativo, pero no evita el descuadre.

### 5.4 Con el bloqueo

Con el bloqueo, la venta y el ajuste se serializan sobre la fila del
producto. El ajuste calcula su diferencia contra el valor que nadie más
puede cambiar hasta su `COMMIT`. Las tres propiedades se cumplieron en las
15 de 15 rondas y en las 5 de 5 ejecuciones de la suite.

## 6. Protección permanente

- **La prueba de concurrencia** forma parte de la suite y exige las tres
  propiedades.
- **Un guardián automático** en `backend/conftest.py` comprueba suma y
  último resultante al terminar **cada** prueba que usa la base de datos.
  Si un camino futuro cambia el stock sin pasar por
  `inventario.services`, la prueba que lo ejerza falla aunque no estuviera
  pensada para el libro.
  - Se verificó que el guardián salta en los dos modos de prueba: normal y
    `transaction=True`.
  - Las pruebas que descuadran el libro a propósito llevan la marca
    `libro_libre`.
- **`backend/inventario/tests/test_verificacion.py`** descuadra el libro a
  propósito para comprobar que la verificación lo detecta. Uno de sus casos
  reproduce el de §5.2: la suma y el último resultante cuadran, y solo la
  cadena lo ve.

## 7. Cómo reproducirlo

```bash
cd backend
# Con bloqueo: debe pasar
for i in 1 2 3 4 5; do python -m pytest ventas/tests/test_concurrencia.py; done

# Sin bloqueo: aplicar la mutación de §2 y ejecutar la prueba de ajustes
python -m pytest ventas/tests/test_concurrencia.py -k ajustes_y_ventas   # debe fallar
git checkout -- inventario/services.py                                    # restaurar
```

La sonda de §4 era un archivo temporal y no se versionó. Para cada ronda
llamaba a la misma carrera (`ConcurrenciaEntreAjustesYVentas._carrera`) y
registraba lo siguiente:

- los desenlaces;
- `libros_descuadrados([producto])`;
- `cadena_rota(producto)`;
- si cada ajuste dejó lo contado.

Los números exactos de stock varían en cada ejecución, porque dependen del
planificador de hilos. Lo que no varía es el patrón: con bloqueo, todo
correcto; sin bloqueo, la suma siempre cuadra y la cadena siempre se rompe.
