# PC-Solution ERP

Sistema ERP interno para **PC-Solution** (Sucre, Bolivia). Proyecto de
grado.

Centraliza la operación interna de la empresa: catálogo e inventario
con código de barras y libro de movimientos de stock, registro de ventas
con garantía imprimible, registro de clientes, seguimiento de servicios
técnicos, gestión de las cuentas del personal, un panel de indicadores y
reportes por rango de fechas exportables a PDF y Excel.

> **Uso exclusivamente interno.** Solo el personal de PC-Solution accede
> al sistema, siempre con una cuenta creada por un administrador. No hay
> portal de clientes, ni registro público, ni carrito de compras, ni
> checkout. Los clientes son **registros de contacto** (nombre, teléfono
> y, opcionalmente, dirección y carnet): no tienen cuenta ni acceso al
> sistema por ninguna vía. El carnet solo se ve en el detalle del
> cliente.

---

## Metodología: Spec-Driven Development

La especificación escrita es la **fuente de verdad** del proyecto; el
código es un artefacto que se genera a partir de ella, no al revés.

| Documento | Etapa | Contenido |
|---|---|---|
| [`specs/spec.md`](specs/spec.md) | 1 — Especificación | Actores, casos de uso, 66 requerimientos funcionales, 23 no funcionales y las reglas de negocio. Sin detalles de implementación. |
| [`specs/plan.md`](specs/plan.md) | 2 — Plan técnico | Arquitectura, modelo de datos, contrato de la API, concurrencia. |
| [`specs/tasks.md`](specs/tasks.md) | 3 — Tareas | 73 tareas atómicas con sus criterios de verificación. |

Son **documentos vivos**: cuando algo cambió durante el desarrollo, se
editó primero la especificación y después el código. La `spec.md` va por
la versión **1.2**; su sección 11 registra las decisiones tomadas y las
que se revisaron a mitad de camino.

Cada commit cita el identificador de la tarea que implementa (`T-4.3`),
de modo que el historial de Git sea trazable contra la especificación.

---

## Stack técnico

| Ámbito | Tecnología |
|---|---|
| Backend | Python 3.13 · Django 5.1 · Django REST Framework 3.17 |
| Base de datos | PostgreSQL 18 |
| Autenticación | JWT (`djangorestframework-simplejwt`) con revocación inmediata |
| Frontend | Vue 3 · Vite · Pinia · Vue Router · PrimeVue 4 |
| Documentación de la API | drf-spectacular (OpenAPI) |
| Documentos | xhtml2pdf (informe de servicio, garantía y reporte en PDF) · openpyxl (reporte en Excel) |
| Códigos de barras | JsBarcode (EAN-13 y Code128 en SVG, en el navegador) |
| Pruebas | pytest + pytest-django (backend) · Vitest (frontend) |

Frontend y backend son **aplicaciones separadas** que se comunican
exclusivamente por la API REST. El frontend nunca accede a la base de
datos directamente.

---

## Estructura del repositorio

```
proyecto_grado_definitivo/
├── specs/            # Especificación, plan técnico y tareas
├── docs/             # Avance de la v1.4 y evidencia de concurrencia
├── backend/
│   ├── config/       # Ajustes, URLs
│   ├── core/         # Permisos, errores, paginación (compartido)
│   ├── usuarios/     # Cuentas, roles, autenticación
│   ├── catalogo/     # Categorías y productos
│   ├── configuracion/# Umbral global de existencias bajas
│   ├── ventas/       # Registro y anulación de ventas
│   ├── servicios/    # Solicitudes de servicio técnico
│   ├── inventario/   # Libro de movimientos de stock y ajuste (v1.4)
│   ├── clientes/     # Registro de contacto de clientes, sin cuenta (v1.4)
│   └── panel/        # Indicadores y reportes por rango (sin modelos propios)
└── frontend/
    └── src/          # api, stores, composables, router, views
```

Cada app del backend sigue la misma disposición: `models.py`,
`serializers.py`, `services.py`, `views.py`, `urls.py`, `tests/`.

> **Dónde vive cada cosa.** Las reglas de negocio están en
> `services.py`, nunca en las vistas. Una vista recibe, delega y
> responde. Las reglas que la base puede garantizar por sí sola están
> además declaradas como restricciones (`CheckConstraint`), porque una
> regla que solo vive en Python es una costumbre, no una garantía.

---

## Puesta en marcha

### Requisitos previos

- Python 3.12 o superior
- Node.js 20 o superior
- PostgreSQL 16 o superior, corriendo localmente

### 1. Base de datos

```sql
CREATE ROLE pcsolution LOGIN PASSWORD 'una-contraseña' CREATEDB;
CREATE DATABASE pcsolution OWNER pcsolution ENCODING 'UTF8';
```

`CREATEDB` no es opcional: pytest crea y destruye `test_pcsolution` en
cada ejecución, y sin ese permiso la prueba de concurrencia no puede
correr.

Alternativa con Docker, si se prefiere no instalar PostgreSQL:

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash)
# source .venv/bin/activate        # Linux / macOS

pip install -r requirements/dev.txt

cp .env.example .env               # y completar los valores
python manage.py migrate
python manage.py createsuperuser   # crea el primer administrador
python manage.py runserver
```

La API queda en `http://localhost:8000/api/v1/` y su documentación
interactiva en `http://localhost:8000/api/docs`.

> **El primer administrador.** El sistema recién instalado está vacío, y
> solo un administrador puede crear cuentas. `createsuperuser` resuelve
> ese arranque asignando el rol de administrador automáticamente; es un
> comando de consola que se ejecuta una sola vez al preparar el equipo.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

La aplicación queda en `http://localhost:5173`.

---

## Pruebas

```bash
cd backend  && pytest        # 1064 pruebas (2026-10-09)
cd frontend && npm run test  #  217 pruebas
```

La suite completa corre en pocos segundos: `conftest.py` sustituye
PBKDF2 por MD5 **solo durante las pruebas**, porque la lentitud
deliberada del hash real dominaba el tiempo total. La configuración de
producción sigue usando PBKDF2, y hay una prueba que lo verifica.

### Las pruebas que más importan

| Prueba | Qué demuestra |
|---|---|
| `ventas/tests/test_concurrencia.py` | Que ventas y ajustes simultáneos nunca dejan el stock en negativo (**RNF-08**) y que el libro de movimientos cuadra **con su cadena de resultantes**, no solo con la suma (**RNF-24**). Resultados con y sin el bloqueo en `docs/evidencia_concurrencia.md`. |
| `conftest.py` (guardián del libro) | Tras **cada** prueba con base de datos, la suma de movimientos de cada producto es su stock (**RN-MOV-03**). |
| `core/tests/test_matriz_permisos.py` | Cada uno de los 52 endpoints × cada rol, contra la matriz de `spec.md` §4.4. Falla si se publica un endpoint sin declarar quién puede usarlo. |
| `core/tests/test_trazabilidad.py` | Que cada uno de los 97 RF y 29 RNF de `spec.md` está citado en el código o las pruebas. |
| `panel/tests/test_coherencia_reportes.py` | Que el reporte en JSON, PDF y Excel tiene **las mismas cifras**, que el carnet no aparece en ninguno, y que un año de datos se reporta en menos de 5 s (**RN-REP-07**, **RNF-28**). |
| `core/tests/test_cobertura_reglas.py` | Que cada regla con prueba obligatoria (`plan.md` §9) conserva la suya. |
| `usuarios/tests/test_invalidacion_inmediata.py` | Que bloquear una cuenta la expulsa al instante, por las cuatro vías posibles. |

---

## Guion de la demostración

El sistema **no trae datos precargados** (decisión PT-04): todo se
registra a mano. Eso obliga a un orden concreto, porque el panel no
muestra nada hasta que existan ventas y servicios del día.

**Antes de empezar:** levantar backend y frontend, y tener creado el
primer administrador con `createsuperuser`.

| # | Paso | Con qué cuenta | Qué se ve |
|---|---|---|---|
| 1 | Iniciar sesión | administrador | El menú completo: panel, catálogo, ventas, servicios, categorías, usuarios, configuración |
| 2 | Crear dos cuentas: un Encargado de Ventas y uno de Servicios | administrador | Cada rol con su etiqueta |
| 3 | Intentar bloquearse a uno mismo | administrador | El botón aparece desactivado (**RN-USU-03**) |
| 4 | Crear 2–3 categorías y 4–5 productos, uno con stock 1 | administrador | El producto escaso se marca en ámbar (**RF-53**) |
| 5 | Cerrar sesión y entrar como Encargado de Ventas | ventas | Su menú **no** tiene usuarios, categorías ni panel |
| 6 | Registrar una venta de dos productos | ventas | Total en vivo; al confirmar, el stock baja |
| 7 | Intentar vender más unidades de las que hay | ventas | Error que dice qué falta y cuánto hay, y que **nada se descontó** (**RN-VEN-02**) |
| 8 | Abrir el detalle de la venta | ventas | Nombres y precios congelados (**RN-VEN-04**) |
| 9 | Entrar como Encargado de Servicios | servicios | Registrar una solicitud de reparación (en taller: no pide dirección) |
| 10 | Registrar otra de videovigilancia | servicios | Ahora **sí** pide dirección (**RN-SER-04**) |
| 11 | Iniciar la atención y tratar de finalizar | servicios | Se rechaza: falta cotizar, y dice que el administrador debe hacerlo (**RN-SER-13**) |
| 12 | Volver como administrador y cotizar | administrador | Monto y nombre del técnico |
| 13 | Volver como Encargado de Servicios y finalizar | servicios | El historial muestra a las **dos** personas |
| 14 | Abrir el panel | administrador | Ingresos del día **desglosados** por ventas y servicios (**RN-IND-05**) |
| 15 | Anular la venta del paso 6 | administrador | El stock vuelve y la venta sale del panel (**RN-VEN-01**) |

**Lo nuevo de la v1.4**, a continuación de lo anterior:

| # | Paso | Con qué cuenta | Qué se ve |
|---|---|---|---|
| 16 | Abrir el detalle de un producto | administrador | Su código EAN-13, el código de barras y el historial: alta, venta y anulación (**RF-71**, **RF-83**) |
| 17 | «Ajustar existencias» a lo contado, con motivo | administrador | La revisión «de X a Y», y el ajuste en el historial (**CU-CAT-07**) |
| 18 | Editar un producto: poner 12 meses de garantía y un código de fábrica | administrador | El código de fábrica repetido o con forma de interno se rechaza junto al campo (**RN-CAT-11**) |
| 19 | Imprimir la etiqueta y escanearla con el teléfono | administrador | El teléfono lee el mismo código (**RNF-27**) |
| 20 | Registrar un cliente | ventas | El carnet solo se ve en su detalle, no en la lista (**RN-CLI-06**) |
| 21 | Vender a ese cliente tecleando códigos en el campo «Código» | ventas | Cada Intro agrega el producto y el campo queda listo (**RF-74**) |
| 22 | Al confirmar, «Emitir garantía» | ventas | El PDF con el vencimiento de cada línea y la leyenda de no fiscal (**RF-76**) |
| 23 | Cambiar el nombre del cliente y reabrir la venta | ventas | La venta conserva los datos originales (**RN-CLI-05**) |
| 24 | Abrir «Movimientos» y «Reportes», exportar a PDF y Excel | administrador | Las mismas cifras en pantalla, PDF y Excel (**RN-REP-07**) |

**Para enseñar lo más defendible del proyecto**, la prueba de
concurrencia:

```bash
cd backend
pytest ventas/tests/test_concurrencia.py -v
```

Y para mostrar que no pasa por casualidad: quitar `select_for_update()`
de `ventas/services.py` y volver a correrla. Aparecen violaciones de la
restricción `producto_stock_no_negativo`, con el detalle de la fila que
intentó quedar en `-1`.

---

## Alcance de esta entrega

Este proyecto está preparado para ejecutarse en **entorno de
desarrollo**, que es lo requerido para la defensa (decisión PT-01).

Para un despliegue real en la empresa harían falta, al menos:

- `DEBUG = False` y `ALLOWED_HOSTS` explícito
- Servidor WSGI (Gunicorn o similar) detrás de un servidor web
- HTTPS con `SECURE_SSL_REDIRECT` y cookies `Secure`
- Recolección y servido de archivos estáticos y de `media/`
- Copias de seguridad programadas de la base de datos

Nada de esto está implementado ni configurado.
