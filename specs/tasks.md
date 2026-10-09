# Desglose de Tareas — Sistema ERP PC-Solution

- **Proyecto:** Sistema ERP interno para PC-Solution (Sucre, Bolivia)
- **Documento:** Etapa 3 de Spec-Driven Development — Desglose de tareas
- **Versión:** 1.1
- **Fecha:** 2026-10-08
- **Estado:** Bloques 0 a 7 **aprobados y completados** (v1.0). Bloques 8
  a 13 **aprobados el 2026-10-08**, pendientes de implementar (v1.1).
- **Deriva de:** `spec.md` v1.4 y `plan.md` v1.3

### Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-09-22 | Bloques 0 a 7, 73 tareas, derivadas de `spec.md` v1.1 y `plan.md` v1.1. El bloque 5 se reformuló el 2026-09-29 tras la v1.2 de la especificación. Todas completadas. |
| 1.1 | 2026-10-08 | **Bloques 8 a 13, 40 tareas**, para las cinco funcionalidades de `spec.md` v1.4 y sus decisiones PA-06 a PA-08 (T-9.7 es la del código de fábrica). Se corrige además la cabecera, que seguía diciendo «borrador pendiente de aprobación», y un resto de la v1.1 en T-6.1 («sin asignar» por «sin cotizar»). |

> Cada tarea es **atómica** (una unidad de trabajo con un resultado
> verificable), está **ordenada por dependencia** (nunca depende de una
> posterior) y declara **qué requerimiento de `spec.md` satisface** y
> **cómo se comprueba que está terminada**. Una tarea sin criterio de
> hecho comprobable no es una tarea: es una intención.
>
> Un *commit* por tarea, citando su identificador
> (`feat(ventas): T-4.3 registrar venta con descuento atómico de stock`),
> de modo que el historial de Git sea trazable contra la especificación.

---

## Cómo leer este documento

| Columna | Significado |
|---|---|
| **ID** | `T-<bloque>.<n>`. Estable: no se renumera aunque se inserten tareas. |
| **Cubre** | Requerimientos de `spec.md` que la tarea satisface. |
| **Depende de** | Tareas que deben estar terminadas antes de empezar esta. |
| **Hecho cuando** | Criterio verificable. Si no se puede comprobar, la tarea no está terminada. |

**Convenio de estado:** `[ ]` pendiente · `[~]` en curso · `[x]` hecha.

### Resumen de bloques

| Bloque | Contenido | Tareas | Dependencia |
|---|---|---|---|
| 0 | Andamiaje del proyecto | T-0.1 a T-0.9 ✅ | — |
| 1 | Autenticación y usuarios | T-1.1 a T-1.14 ✅ | Bloque 0 |
| 2 | Catálogo e inventario | T-2.1 a T-2.10 ✅ | Bloque 1 |
| 3 | Configuración (umbral global) | T-3.1 a T-3.4 ✅ | Bloque 2 |
| 4 | Ventas | T-4.1 a T-4.12 ✅ | Bloques 2, 3 |
| 5 | Servicios técnicos | T-5.1 a T-5.14 ✅ | Bloque 1 |
| 6 | Panel de indicadores | T-6.1 a T-6.5 ✅ | Bloques 4, 5 |
| 7 | Cierre y documentación | T-7.1 a T-7.5 ✅ | Todos |
| **8** | **Movimientos de stock** *(v1.4)* | T-8.1 a T-8.8 | Bloque 7 |
| **9** | **Código de producto** *(v1.4)* | T-9.1 a T-9.7 | Bloque 8 |
| **10** | **Garantía** *(v1.4)* | T-10.1 a T-10.7 | Bloque 9 |
| **11** | **Clientes** *(v1.4)* | T-11.1 a T-11.7 | Bloque 10 |
| **12** | **Reportes** *(v1.4)* | T-12.1 a T-12.8 | Bloque 11 |
| **13** | **Cierre de la v1.4** | T-13.1 a T-13.3 | Todos |

**Total: 113 tareas — 73 completadas (bloques 0 a 7), 40 pendientes
(bloques 8 a 13).** Los bloques 4 y 5 son independientes entre sí y
podrían abordarse en cualquier orden; se propone ventas primero por ser
el de lógica más delicada.

> **Los bloques 8 a 12 no son independientes**, aunque las cinco
> funcionalidades lo parezcan: cuatro de ellas tocan `registrar_venta()`.
> El orden (`plan.md` §11.2) hace que cada bloque añada **un solo**
> cambio a ese servicio, con su prueba, antes de que llegue el
> siguiente.

**Además, 4 tareas operativas** (`T-OP.1` a `T-OP.4`): la importación
única del catálogo del proyecto anterior (`plan.md` §11.3). No son
funcionalidad del sistema y no cuentan en el total de tareas; están al
final del documento.

---

## Bloque 0 — Andamiaje del proyecto

> **Este bloque no es opcional ni «preparación».** Contiene la decisión
> más difícil de revertir de todo el proyecto (T-0.4) y el entorno que
> hace demostrable RNF-08 (T-0.3).

### [x] T-0.1 — Repositorio Git e higiene inicial
- **Cubre:** RNF-21
- **Depende de:** —
- **Trabajo:** `git init` en la raíz; `.gitignore` para Python, Node,
  `.env`, `media/`, `__pycache__`, `node_modules`, `.venv`; primer commit
  con `specs/` ya dentro.
- **Hecho cuando:** `git log` muestra el commit inicial y `git status`
  está limpio con un `.env` de prueba presente en el disco.

### [x] T-0.2 — Esqueleto de carpetas y README
- **Cubre:** RNF-20, RNF-22
- **Depende de:** T-0.1
- **Trabajo:** Estructura `backend/`, `frontend/`, `specs/` según
  `plan.md` §8. README con: qué es el proyecto, cómo levantar cada parte,
  y la nota de PT-01 sobre qué haría falta para un despliegue real.
- **Hecho cuando:** un lector que no conoce el proyecto puede levantarlo
  siguiendo solo el README.

### [x] T-0.3 — PostgreSQL en desarrollo
- **Cubre:** RNF-08 (habilita su demostración)
- **Depende de:** T-0.2
- **Trabajo:** Base de datos y rol propios del proyecto sobre la
  **instalación nativa de PostgreSQL 18** del equipo, con credenciales
  desde `.env`. Se versiona además un `docker-compose.yml` equivalente
  como alternativa documentada, para reproducir el entorno en otra
  máquina.
- **Hecho cuando:** el rol y la base existen y se puede conectar con
  `psql` usando las credenciales del `.env`.
- > **Desviación respecto del plan v1.1, registrada el 2026-09-24.** El
  > plan proponía Docker como vía principal y la instalación nativa como
  > alternativa. En el equipo del autor ocurre lo contrario: PostgreSQL
  > 18 ya está instalado y corriendo como servicio, mientras que el
  > comando `docker` no está disponible en el PATH. Se invierte el orden
  > de preferencia. Nada más del plan cambia: lo que RNF-08 exige es
  > PostgreSQL real, no una forma concreta de instalarlo.

### [x] T-0.4 — Proyecto Django con modelo `Usuario` propio ⚠️
- **Cubre:** RN-ACC-02, RN-USU-05
- **Depende de:** T-0.3
- **Trabajo:** `django-admin startproject config backend/`; app `usuarios`
  con `Usuario(AbstractUser)` y campo `rol` (choices `ADMINISTRADOR`,
  `VENTAS`, `SERVICIOS`); `AUTH_USER_MODEL = "usuarios.Usuario"`.
- **Hecho cuando:** `python manage.py migrate` corre **por primera vez**
  con el modelo propio ya definido, y `auth_user` **no** existe en la base.
- > ⚠️ **Tarea de no retorno.** Cambiar `AUTH_USER_MODEL` después de
  > migrar obliga a reconstruir la base desde cero. Es el riesgo número
  > uno de `plan.md` §12. Antes de pasar a T-0.5: verificar en `psql`
  > que la tabla de usuarios es `usuarios_usuario`.

### [x] T-0.5 — Configuración por entornos y secretos
- **Cubre:** RNF-05, PT-01
- **Depende de:** T-0.4
- **Trabajo:** `config/settings/` dividido en `base.py` y `dev.py`;
  `django-environ`; `.env.example` versionado y `.env` ignorado; zona
  horaria `America/La_Paz`, idioma `es`.
- **Hecho cuando:** el proyecto arranca sin ningún secreto escrito en el
  código, y `.env` no aparece en `git status`.

### [x] T-0.6 — DRF con permisos cerrados por defecto
- **Cubre:** RNF-01
- **Depende de:** T-0.5
- **Trabajo:** Instalar DRF; `DEFAULT_PERMISSION_CLASSES =
  ["rest_framework.permissions.IsAuthenticated"]`; paginación por defecto
  de 20 con máximo 100; `DEFAULT_AUTHENTICATION_CLASSES` con
  `JWTAuthentication`.
- **Hecho cuando:** un endpoint de prueba **sin** permisos declarados
  responde 401 sin token. Olvidar declarar permisos cierra el endpoint,
  no lo abre.

### [x] T-0.7 — Manejador de errores y formato uniforme
- **Cubre:** RNF-06, RNF-15
- **Depende de:** T-0.6
- **Trabajo:** `core/exceptions.py` con el manejador propio y las
  excepciones de negocio del catálogo de `plan.md` §4.3; formato
  `{codigo, detalle, errores}`.
- **Hecho cuando:** un error de validación y un 403 devuelven ambos la
  misma forma de JSON, verificado con una prueba.

### [x] T-0.8 — Proyecto Vue con Vite, Pinia, Router y PrimeVue
- **Cubre:** RNF-12, RNF-13, PT-03
- **Depende de:** T-0.2
- **Trabajo:** `npm create vite@latest` (plantilla Vue); instalar Vue
  Router, Pinia, Axios, PrimeVue 4 con tema Aura; locale en español;
  estructura de `src/` según `plan.md` §7.1.
- **Hecho cuando:** `npm run dev` sirve una página con un componente de
  PrimeVue renderizado, adaptable a ancho de tableta.

### [x] T-0.9 — Entorno de pruebas de ambos lados
- **Cubre:** RNF-23
- **Depende de:** T-0.6, T-0.8
- **Trabajo:** `pytest`, `pytest-django`, `factory-boy` en backend con
  `pytest.ini`; `vitest` y Vue Test Utils en frontend; una prueba trivial
  en cada lado.
- **Hecho cuando:** `pytest` y `npm run test` pasan en verde.

---

## Bloque 1 — Autenticación y usuarios

> Es la base de todo lo demás: sin roles no se puede autorizar ningún
> otro módulo. Se implementa completo, backend y frontend, antes de
> tocar el siguiente bloque.

### [x] T-1.1 — Modelo `Usuario` completo y arranque del administrador
- **Cubre:** RN-ACC-02, RN-USU-06, §11.1 del plan
- **Depende de:** T-0.4
- **Trabajo:** Completar el modelo (`nombre_completo`, `rol`,
  `is_active` como bloqueo); `UNIQUE` en `username`; `createsuperuser`
  adaptado para asignar `rol = ADMINISTRADOR` automáticamente.
- **Hecho cuando:** `createsuperuser` crea una cuenta que pasa las
  clases de permiso de administrador; el sistema recién instalado es
  accesible.

### [x] T-1.2 — Clases de permiso por rol
- **Cubre:** RNF-02, RN-ACC-04, matriz 4.4
- **Depende de:** T-1.1
- **Trabajo:** `core/permissions.py` con `EsAdministrador`,
  `PuedeVender`, `PuedeAtenderServicios`, `EsDuenoDeLaVentaOAdmin`. El
  rol se lee **siempre** de `request.user.rol`, nunca del token
  (`plan.md` §1.3, vía 4).
- **Hecho cuando:** pruebas unitarias cubren cada clase con los tres
  roles, y una prueba verifica que un rol manipulado en el token no
  concede acceso.

### [x] T-1.3 — Inicio de sesión (JWT)
- **Cubre:** RF-01, RF-02, RF-03
- **Depende de:** T-1.2, T-0.7
- **Trabajo:** SimpleJWT con la configuración de `plan.md` §1.3;
  `POST /auth/login` devolviendo `access`, `refresh` y datos del usuario.
- **Hecho cuando:** credenciales válidas → 200; inválidas → 401 con el
  **mismo** mensaje exista o no el usuario (RNF-06); cuenta bloqueada →
  403 `CUENTA_BLOQUEADA`.

### [x] T-1.4 — Invalidación inmediata de sesiones
- **Cubre:** **RN-ACC-05**, RNF-07
- **Depende de:** T-1.3
- **Trabajo:** Las cuatro vías de `plan.md` §1.3:
  `TokenRefreshSeguroSerializer`; lista negra de todos los refresh al
  bloquear, en la misma transacción; `CHECK_REVOKE_TOKEN = True`;
  verificar que ninguna clase de permiso lea el rol del token.
- **Hecho cuando:** pasan las **tres** pruebas de `plan.md` §1.3:
  1. bloquear → la petición siguiente con el mismo access da 401;
  2. refresh de cuenta bloqueada → 403;
  3. bloquear y desbloquear → los refresh anteriores siguen rechazados.

### [x] T-1.5 — Cierre de sesión y cambio de contraseña propia
- **Cubre:** RF-04, RF-05, RNF-03, RNF-04
- **Depende de:** T-1.4
- **Trabajo:** `POST /auth/logout` (lista negra del refresh);
  `GET /auth/me`; `POST /auth/me/password` verificando la anterior;
  validadores de contraseña activos.
- **Hecho cuando:** tras cerrar sesión el refresh ya no sirve; cambiar la
  contraseña invalida los access tokens previos (`CHECK_REVOKE_TOKEN`).

### [x] T-1.6 — Servicio de usuarios con las protecciones de administrador
- **Cubre:** **RN-USU-02, RN-USU-03, RN-USU-04**, RF-44, RF-45, RF-46
- **Depende de:** T-1.1
- **Trabajo:** `usuarios/services.py`: crear, editar, cambiar rol,
  bloquear, desbloquear, restablecer contraseña. La comprobación de
  «queda al menos un administrador activo» se hace **dentro de la
  transacción y con `select_for_update()`** sobre las cuentas de
  administrador activas (`plan.md` §5.2).
- **Hecho cuando:** pruebas rechazan autocambio de rol, autobloqueo y
  dejar cero administradores; **y** una prueba concurrente verifica que
  dos administradores bloqueándose a la vez no pueden dejar el sistema
  sin acceso.

### [x] T-1.7 — API de usuarios
- **Cubre:** RF-39 a RF-43, RF-47
- **Depende de:** T-1.6, T-1.2
- **Trabajo:** Endpoints de `plan.md` §4.4 (usuarios). Sin `DELETE`
  (RN-USU-05). `password` siempre `write_only`.
- **Hecho cuando:** pruebas de integración cubren cada endpoint; ninguna
  respuesta contiene el campo `password`; `DELETE` responde 405.

### [x] T-1.8 — Matriz de permisos automatizada
- **Cubre:** RNF-02, matriz 4.4 de `spec.md`
- **Depende de:** T-1.7
- **Trabajo:** Prueba parametrizada que recorre cada endpoint existente ×
  cada rol y compara el resultado contra la matriz de `spec.md` §4.4.
  Se amplía en cada bloque posterior al añadir endpoints.
- **Hecho cuando:** la prueba pasa y **falla** si se cambia a mano un
  permiso de cualquier vista.

### [x] T-1.9 — Cliente HTTP y store de sesión (frontend)
- **Cubre:** RF-06, RNF-15
- **Depende de:** T-0.8, T-1.5
- **Trabajo:** `api/http.js` con los tres interceptores de `plan.md`
  §7.2, incluida la cola de peticiones durante el refresco;
  `stores/auth.js` con sesión, rol y permisos derivados;
  `composables/useErroresApi.js`.
- **Hecho cuando:** un 401 dispara **un solo** refresco aunque haya
  varias peticiones en vuelo; si el refresco falla, se cierra la sesión y
  se redirige al inicio.

### [x] T-1.10 — Rutas y guards por rol
- **Cubre:** RF-06
- **Depende de:** T-1.9
- **Trabajo:** `router/index.js` con `meta.roles`; guard global; menú
  lateral construido **a partir de la misma definición** de rutas, para
  que lo visible y lo navegable no puedan divergir.
- **Hecho cuando:** pruebas de Vitest verifican la redirección por rol, y
  el menú de cada rol coincide con la matriz de `spec.md` §4.4.

### [x] T-1.11 — Pantalla de inicio de sesión
- **Cubre:** RF-01, RF-02, RF-03, RNF-13, RNF-15
- **Depende de:** T-1.10
- **Trabajo:** Formulario con validación, estado de carga y mensajes
  diferenciados para credenciales inválidas y cuenta bloqueada.
- **Hecho cuando:** se puede iniciar sesión con los tres roles y cada uno
  aterriza en la pantalla que le corresponde.

### [x] T-1.12 — Pantalla de cambio de contraseña propia
- **Cubre:** RF-05
- **Depende de:** T-1.11
- **Hecho cuando:** el cambio funciona y, al invalidarse la sesión, la
  aplicación lleva de vuelta al inicio de sesión sin quedarse colgada.

### [x] T-1.13 — Pantallas de gestión de usuarios
- **Cubre:** RF-39 a RF-47
- **Depende de:** T-1.11, T-1.7
- **Trabajo:** Lista con búsqueda y filtro por rol; formulario de alta y
  edición; acciones de bloquear, desbloquear y restablecer contraseña,
  con diálogo de confirmación (RNF-14).
- **Hecho cuando:** el intento de autobloqueo o de dejar cero
  administradores muestra el mensaje del servidor; la interfaz **no**
  duplica la regla, la respeta.

### [x] T-1.14 — Revisión del bloque 1
- **Depende de:** T-1.1 a T-1.13
- **Hecho cuando:** un administrador crea cuentas de los otros dos roles
  y cada una inicia sesión y ve solo lo suyo; bloquear a un usuario
  conectado lo expulsa en su siguiente acción, comprobado en el navegador.

---

## Bloque 2 — Catálogo e inventario

### [x] T-2.1 — Modelos `Categoria` y `Producto` con restricciones
- **Cubre:** RN-CAT-01 a RN-CAT-06, RF-14
- **Depende de:** T-1.1
- **Trabajo:** Modelos con `CheckConstraint` de `plan.md` §3.3
  (`stock >= 0`, `precio > 0`), `UNIQUE` en nombres, `categoria` con
  `on_delete=PROTECT`, campo `activo` para el borrado suave, `imagen`
  opcional. Índices de `plan.md` §3.4.
- **Hecho cuando:** una prueba intenta insertar stock negativo **saltando
  la validación de Django** y la base lo rechaza.

### [x] T-2.2 — API de categorías
- **Cubre:** RF-07, RF-08
- **Depende de:** T-2.1, T-1.2
- **Hecho cuando:** eliminar una categoría con productos responde 409
  `CATEGORIA_CON_PRODUCTOS`; sin productos, elimina correctamente.

### [x] T-2.3 — API de productos
- **Cubre:** RF-09, RF-10, RF-12, RF-14
- **Depende de:** T-2.2
- **Trabajo:** CRUD con `multipart` para la imagen; validación de tipo y
  tamaño máximo (2 MB) con verificación real vía Pillow.
- **Hecho cuando:** un archivo que no es imagen es rechazado aunque tenga
  extensión `.jpg`.

### [x] T-2.4 — Borrado suave de productos
- **Cubre:** RF-11, CU-CAT-04
- **Depende de:** T-2.3
- **Trabajo:** `DELETE` marca `activo = false`; los listados de venta
  excluyen inactivos; el detalle histórico sigue accesible.
- **Hecho cuando:** un producto «eliminado» desaparece del selector de
  ventas pero sigue visible en las ventas anteriores que lo incluyen.

### [x] T-2.5 — Búsqueda y filtros del catálogo
- **Cubre:** RF-13, RNF-18
- **Depende de:** T-2.3
- **Hecho cuando:** `?buscar=`, `?categoria=` y `?activo=` funcionan
  combinados y la respuesta viene paginada.

### [x] T-2.6 — Cliente de API del catálogo (frontend)
- **Cubre:** RF-12
- **Depende de:** T-2.5, T-1.9

### [x] T-2.7 — Lista de productos
- **Cubre:** RF-12, RF-13, RNF-12, RNF-18
- **Depende de:** T-2.6
- **Trabajo:** `DataTable` de PrimeVue con paginación de servidor,
  búsqueda y filtro por categoría; columna de existencias.
- **Hecho cuando:** un Encargado de Ventas la ve en modo consulta, sin
  botones de edición; un Administrador ve las acciones completas.

### [x] T-2.8 — Formulario de producto con imagen
- **Cubre:** RF-09, RF-10, RNF-15
- **Depende de:** T-2.7
- **Hecho cuando:** los errores de validación del servidor aparecen junto
  al campo que los origina; la vista previa de la imagen funciona.

### [x] T-2.9 — Pantalla de categorías
- **Cubre:** RF-07, RF-08, RNF-14
- **Depende de:** T-2.7

### [x] T-2.10 — Revisión del bloque 2
- **Depende de:** T-2.1 a T-2.9
- **Hecho cuando:** el Administrador gestiona el catálogo completo; el
  Encargado de Ventas lo consulta pero no lo modifica, ni por interfaz ni
  llamando a la API directamente.

---

## Bloque 3 — Configuración (umbral global)

> Bloque pequeño, colocado aquí porque el catálogo (T-3.4) y el panel
> (bloque 6) lo necesitan para marcar las existencias bajas.

### [x] T-3.1 — Modelo `ConfiguracionSistema` de fila única
- **Cubre:** RN-CAT-07
- **Depende de:** T-2.1
- **Trabajo:** Tabla con `CheckConstraint (id = 1)` y
  `umbral_stock_bajo >= 0`; migración de datos que crea la fila con un
  valor inicial de 5; `actualizado_por` y `actualizado_en`.
- **Hecho cuando:** intentar crear una segunda fila falla en la base; la
  fila existe tras migrar en una base vacía.

### [x] T-3.2 — API de configuración
- **Cubre:** RF-52
- **Depende de:** T-3.1, T-1.2
- **Hecho cuando:** solo el Administrador puede leer y modificar;
  un valor negativo se rechaza; se registra quién lo cambió.

### [x] T-3.3 — Pantalla de configuración
- **Cubre:** RF-52
- **Depende de:** T-3.2, T-2.6

### [x] T-3.4 — Marca de existencias bajas en el catálogo
- **Cubre:** RF-53
- **Depende de:** T-3.2, T-2.7
- **Trabajo:** Cada producto serializado incluye `stock_bajo`, calculado
  en el servidor contra el umbral vigente; filtro `?stock_bajo=true`;
  distintivo visual en la tabla.
- **Hecho cuando:** cambiar el umbral cambia de inmediato qué productos
  aparecen marcados, **sin tocar el frontend**: la regla vive en el
  servidor.

---

## Bloque 4 — Ventas

> El bloque técnicamente más delicado. El orden interno es deliberado:
> **el servicio y su prueba de concurrencia van antes que la API**, para
> no construir encima de un descuento de stock no verificado.

### [x] T-4.1 — Modelos `Venta` y `DetalleVenta`
- **Cubre:** RN-VEN-01, RN-VEN-04, RN-VEN-05, RN-VEN-09, RNF-11
- **Depende de:** T-2.1
- **Trabajo:** Campos congelados `producto_nombre`, `precio_unitario` y
  `subtotal` como columnas propias; `usuario` y `producto` con
  `on_delete=PROTECT`; restricciones y campos de anulación de
  `plan.md` §3.3; índices de §3.4.
- **Hecho cuando:** el esquema impide cantidad ≤ 0 y precio ≤ 0 a nivel
  de base.

### [x] T-4.2 — Excepciones de negocio de ventas
- **Cubre:** RNF-06
- **Depende de:** T-4.1, T-0.7
- **Trabajo:** `StockInsuficiente` (422, con el detalle por producto),
  `VentaYaAnulada` (409).

### [x] T-4.3 — Servicio `registrar_venta()` ⚠️
- **Cubre:** **RN-VEN-02, RN-VEN-03, RN-VEN-04**, RNF-08, RNF-09
- **Depende de:** T-4.2
- **Trabajo:** El patrón de tres capas de `plan.md` §6.3:
  `transaction.atomic()`, `select_for_update()` **en orden ascendente de
  `pk`**, validación con las filas ya bloqueadas, descuento con `F()` y
  congelado de nombre y precio en cada línea. El precio lo toma el
  servidor del catálogo, **nunca** del cliente.
- **Hecho cuando:**
  - venta válida → stock descontado, detalle congelado, total correcto;
  - un solo producto sin stock → `StockInsuficiente` y **ningún**
    producto descontado (RN-VEN-02);
  - cambiar el precio del producto después no altera la venta guardada
    (RN-VEN-04).

### [x] T-4.4 — Prueba de concurrencia de existencias ⚠️
- **Cubre:** **RNF-08**
- **Depende de:** T-4.3
- **Trabajo:** `TransactionTestCase` (no `TestCase`) contra PostgreSQL
  real: N hilos venden el mismo producto con stock limitado.
- **Hecho cuando:** las ventas confirmadas son exactamente el stock
  disponible, el stock final es exactamente `0` —nunca negativo— y las
  peticiones sobrantes reciben 422.
- > ⚠️ **Es el criterio de aceptación ejecutable de RNF-08** y una de las
  > evidencias más defendibles del proyecto de grado. No se continúa al
  > resto del bloque hasta que esta prueba pase de forma estable en
  > varias ejecuciones seguidas.

### [x] T-4.5 — Servicio `anular_venta()`
- **Cubre:** RN-VEN-07, RN-VEN-08, RN-VEN-11, RNF-10
- **Depende de:** T-4.4
- **Trabajo:** Mismo patrón en sentido inverso: bloqueo ordenado,
  devolución con `F()`, motivo obligatorio, registro de quién y cuándo.
  Sin límite de plazo (PA-02).
- **Hecho cuando:** el stock vuelve exactamente al valor previo; anular
  dos veces da 409; una venta con fecha antigua se anula sin problema.

### [x] T-4.6 — API de ventas
- **Cubre:** RF-15 a RF-20, RF-23, RF-24, RF-54
- **Depende de:** T-4.5, T-1.2
- **Trabajo:** `POST /ventas`, `GET /ventas/{id}`,
  `POST /ventas/{id}/anular`. **Sin** `PUT`, `PATCH` ni `DELETE`: su
  ausencia implementa RN-VEN-06 y RF-26.
- **Hecho cuando:** `PATCH` y `DELETE` sobre una venta responden 405; el
  422 de stock trae el detalle por producto del formato de §4.3.

### [x] T-4.7 — Historial de ventas filtrado por rol
- **Cubre:** RF-21, RF-22, RF-27, RN-VEN-09
- **Depende de:** T-4.6
- **Trabajo:** `get_queryset()` restringe al usuario autenticado si su rol
  es VENTAS; el Administrador ve todo. Filtros de fecha y estado.
- **Hecho cuando:** un Encargado de Ventas **no** recibe las ventas de
  otro ni en la lista ni pidiendo su id directamente, y no puede
  anularlas (403/404).

### [x] T-4.8 — Cliente de API de ventas (frontend)
- **Depende de:** T-4.6, T-1.9

### [x] T-4.9 — Pantalla de registro de venta
- **Cubre:** RF-15, RF-16, RF-17, RNF-16
- **Depende de:** T-4.8, T-2.7
- **Trabajo:** Datos de contacto del cliente, buscador de productos,
  lista temporal en el estado del componente, subtotales y total en vivo,
  confirmación.
- **Hecho cuando:** el 422 de stock muestra con claridad qué producto
  falta y cuánto hay disponible.
- > **Nota:** la lista temporal **no** es un carrito de comercio
  > electrónico: no se persiste ni existe fuera de la pantalla
  > (`spec.md` §2.2, `plan.md` §7.4).

### [x] T-4.10 — Historial y detalle de venta
- **Cubre:** RF-21, RF-22, RF-23, RNF-18
- **Depende de:** T-4.9
- **Hecho cuando:** el detalle muestra los datos congelados; un producto
  posteriormente modificado o retirado aparece tal como estaba el día de
  la venta.

### [x] T-4.11 — Anulación desde la interfaz
- **Cubre:** RF-24, RF-25, RNF-14
- **Depende de:** T-4.10
- **Hecho cuando:** el diálogo exige motivo, y tras anular el stock del
  catálogo refleja la devolución sin recargar la aplicación.

### [x] T-4.12 — Revisión del bloque 4
- **Depende de:** T-4.1 a T-4.11
- **Hecho cuando:** ciclo completo comprobado en el navegador: registrar
  venta → ver el descuento en el catálogo → anular → ver la devolución.

---

## Bloque 5 — Servicios técnicos

> Independiente del bloque 4: depende solo de usuarios. Incorpora las
> decisiones PA-03 (monto cobrado), PA-04 (visibilidad compartida) y
> PA-05 (técnico asignado).

> **Reformulado el 2026-09-29** tras la revisión de PA-03, PA-04 y
> PA-05 en `spec.md` v1.2. El bloque se simplifica: desaparecen la
> asignación de técnico como entidad y la visibilidad compartida, y
> aparece la cotización por parte del Administrador. Los criterios de
> cada tarea siguen derivando de la especificación, no al revés.

### [x] T-5.1 — Modelo `SolicitudServicio`
- **Cubre:** RN-SER-01, RN-SER-04, RN-SER-05, RN-SER-09, RN-SER-11, RF-55
- **Depende de:** T-1.1
- **Trabajo:** `tipo` con choices; `modalidad` **derivada del tipo por el
  sistema**, no elegida por el usuario, y almacenada como columna;
  `registrada_por` como **única** FK a `Usuario`, no nula e inmutable;
  `tecnico` como `CharField` opcional (anotación, no relación);
  `monto_cobrado` decimal nulo hasta que se cotice; restricciones de
  `plan.md` §3.3 e índices de §3.4.
- **Hecho cuando:** la base rechaza una solicitud a domicilio sin
  dirección y un monto negativo, y el técnico no tiene ninguna relación
  con la tabla de usuarios.

### [x] T-5.2 — Modelo `EventoSolicitud` (historial)
- **Cubre:** RN-SER-06, RF-35, RF-59
- **Depende de:** T-5.1
- **Trabajo:** Tabla de **solo inserción** que registra con el mismo
  formato los tipos de evento del módulo: cambio de estado, cotización,
  anotación de técnico y cierre.
- **Hecho cuando:** existe una prueba de que el historial no se
  actualiza ni se borra desde ningún punto del código.
- > Aunque cada usuario solo vea lo suyo, sobre una misma solicitud
  > actúan dos personas distintas —el Administrador cotiza, el
  > registrador cierra—, así que el historial sigue siendo lo que
  > permite saber quién hizo qué.

### [x] T-5.3 — Máquina de estados
- **Cubre:** **RN-SER-02**, RF-31
- **Depende de:** T-5.2
- **Trabajo:** Transiciones válidas declaradas en un solo lugar, con sus
  dos guardas: observaciones **y monto ya cotizado** para finalizar,
  motivo para cancelar. Pasar a *En atención* no tiene guarda. Estados
  terminales sin salida.
- **Hecho cuando:** una prueba parametrizada recorre **todas** las
  combinaciones de estado origen × destino y solo permite las del
  diagrama de `spec.md` RN-SER-02.

### [x] T-5.4 — Servicio de registro de solicitud
- **Cubre:** RF-28, RF-29, RF-30, RN-SER-04
- **Depende de:** T-5.3
- **Hecho cuando:** mantenimiento y reparación no piden dirección; redes
  y videovigilancia la exigen; toda solicitud nace *Registrada*, sin
  cotizar y con su registrador.

### [x] T-5.5 — Servicio de cotización (solo Administrador)
- **Cubre:** **RN-SER-09, RN-SER-10, RN-SER-12, RN-SER-13, RN-SER-16,
  RN-SER-17**, RF-56, RF-58, RF-59, RF-62
- **Depende de:** T-5.4
- **Trabajo:** Fijar el monto y anotar el técnico; ambos solo mientras
  la solicitud siga abierta; el monto puede reajustarse; cada cambio al
  historial con autor y momento.
- **Hecho cuando:** monto negativo → 400; monto cero → aceptado;
  cotizar una solicitud terminal → 409; el monto puede corregirse
  mientras esté abierta.

### [x] T-5.6 — Servicios de inicio, finalización y cancelación
- **Cubre:** **RN-SER-03, RN-SER-07, RN-SER-13, RN-SER-14, RN-SER-16**,
  RF-32, RF-33, RF-34, RF-61, RF-63
- **Depende de:** T-5.5
- **Trabajo:** `iniciar()` sin guardas; `finalizar()` exige
  observaciones **y** monto ya cotizado, fija fecha de cierre y autor;
  `cancelar()` exige motivo.
- **Hecho cuando:**
  - finalizar sin observaciones → 400;
  - finalizar sin monto cotizado → 409, indicando que debe cotizarse;
  - finalizar con monto `0` → 200 (servicio en garantía o de cortesía);
  - una solicitud finalizada no admite edición de nada.

### [x] T-5.7 — API de solicitudes con visibilidad por usuario ⚠️
- **Cubre:** **RN-SER-15**, RF-36, RF-38, RF-57, RF-64
- **Depende de:** T-5.6, T-1.2
- **Trabajo:** Endpoints de `plan.md` §4.4, cada transición con nombre
  propio. `get_queryset()` filtra por `registrada_por` cuando el rol no
  es Administrador, **igual que en ventas**. La cotización exige
  `EsAdministrador`.
- **Hecho cuando:** un Encargado de Servicios no ve ni puede tocar una
  solicitud que no registró, ni pidiendo su id directamente; y no puede
  cotizar ninguna, ni siquiera las suyas.

### [x] T-5.8 — Filtros de solicitudes
- **Cubre:** RF-37, RF-60
- **Depende de:** T-5.7
- **Trabajo:** `?estado=`, `?tipo=`, `?desde=`, `?hasta=` y
  `?sin_cotizar=true` para el Administrador.
- **Hecho cuando:** los filtros funcionan combinados y el de
  «pendientes de cotizar» devuelve solo las abiertas sin monto.

### [x] T-5.9 — Ampliación de la matriz de permisos
- **Cubre:** RNF-02
- **Depende de:** T-5.7, T-1.8
- **Hecho cuando:** T-1.8 incluye los endpoints de servicios y refleja
  que el rol VENTAS no accede a ninguno y que solo el Administrador
  cotiza.

### [x] T-5.10 — Cliente de API de servicios (frontend)
- **Depende de:** T-5.8, T-1.9

### [x] T-5.11 — Lista de solicitudes
- **Cubre:** RF-36, RF-37, RF-60, RNF-18
- **Depende de:** T-5.10
- **Trabajo:** Tabla con filtros; columnas de estado, tipo, técnico
  anotado y monto; distintivo para las pendientes de cotizar.
- **Hecho cuando:** el Administrador distingue de un vistazo cuáles
  esperan su cotización.

### [x] T-5.12 — Formulario de registro con dirección condicional
- **Cubre:** RF-28, RF-29, RNF-15
- **Depende de:** T-5.11
- **Hecho cuando:** el campo de dirección aparece y se vuelve
  obligatorio solo al elegir redes o videovigilancia, y la regla la
  sigue imponiendo el servidor aunque se manipule el formulario.

### [x] T-5.13 — Detalle con historial y acciones
- **Cubre:** RF-32 a RF-35, RF-38, RF-56, RF-61, RNF-14
- **Depende de:** T-5.12
- **Trabajo:** Línea de tiempo del historial; diálogos de iniciar,
  cotizar (solo Administrador), finalizar y cancelar; las acciones no
  disponibles se ocultan según el estado y el rol.
- **Hecho cuando:** al Encargado de Servicios no se le ofrece cotizar, y
  si intenta finalizar sin monto el sistema le explica que el
  Administrador debe cotizarla primero.

### [x] T-5.14 — Revisión del bloque 5
- **Depende de:** T-5.1 a T-5.13
- **Hecho cuando:** ciclo completo comprobado con **dos** usuarios: un
  Encargado de Servicios registra e inicia, el Administrador cotiza, el
  registrador finaliza, y el historial muestra la cadena completa con
  ambos autores. Un segundo Encargado de Servicios no ve esa solicitud.

---

## Bloque 6 — Panel de indicadores

### [x] T-6.1 — Consultas agregadas de los indicadores
- **Cubre:** RN-IND-01 a RN-IND-05
- **Depende de:** T-4.7, T-5.8, T-3.2
- **Trabajo:** Agregados del día: ventas confirmadas (excluyendo
  anuladas), servicios **finalizados en la fecha de cierre** —no de
  registro—, pendientes con desglose de «sin cotizar», y productos bajo
  el umbral global. *(Corregido en v1.1: decía «sin asignar», resto de
  la v1.1 de la especificación.)*
- **Hecho cuando:** pruebas con datos límite verifican que una venta
  anulada no suma, que un servicio cancelado no suma, y que un servicio
  registrado ayer y cerrado hoy cuenta **hoy**.

### [x] T-6.2 — API del panel
- **Cubre:** RF-48 a RF-50, RF-65, RF-66
- **Depende de:** T-6.1, T-1.2
- **Trabajo:** `GET /panel/resumen` con la forma de `plan.md` §4.4.
  `ingreso_total` viaja **siempre** desglosado por origen.
- **Hecho cuando:** solo el Administrador accede (403 para los otros dos
  roles); la respuesta nunca ofrece un total agregado sin su desglose
  (RN-IND-05).

### [x] T-6.3 — Pantalla del panel
- **Cubre:** RF-48 a RF-51, RF-65, RF-66, RNF-12
- **Depende de:** T-6.2
- **Trabajo:** Tarjetas de indicadores, desglose de ingresos por origen,
  tabla de productos con existencias bajas.
- **Hecho cuando:** cada indicador enlaza a su módulo (RF-51) y la
  disposición se mantiene legible en ancho de tableta.

### [x] T-6.4 — Rendimiento de los indicadores
- **Cubre:** RNF-17
- **Depende de:** T-6.3
- **Trabajo:** Revisar las consultas con `django-debug-toolbar`;
  `select_related` y `annotate` donde corresponda; confirmar que los
  índices de `plan.md` §3.4 se usan.
- **Hecho cuando:** el panel responde por debajo de 3 segundos con un
  volumen de datos realista, y no hay consultas N+1.

### [x] T-6.5 — Revisión del bloque 6
- **Depende de:** T-6.1 a T-6.4
- **Hecho cuando:** registrar una venta y finalizar un servicio se
  reflejan en el panel al recargarlo, con los importes correctos y
  separados por origen.

---

## Bloque 7 — Cierre y documentación

### [x] T-7.1 — Cobertura de las reglas obligatorias
- **Cubre:** RNF-23
- **Depende de:** bloques 1 a 6
- **Trabajo:** Verificar que **todas** las reglas de la tabla «reglas con
  prueba obligatoria» de `plan.md` §9 tienen su prueba y pasan.
- **Hecho cuando:** la suite completa está en verde y ninguna regla de
  esa tabla queda sin cubrir.

### [x] T-7.2 — Revisión de la matriz de permisos completa
- **Cubre:** RNF-02
- **Depende de:** T-7.1
- **Hecho cuando:** T-1.8, ya con todos los endpoints, coincide celda por
  celda con la matriz de `spec.md` §4.4.

### [x] T-7.3 — Verificación de usabilidad
- **Cubre:** RNF-12 a RNF-16
- **Depende de:** T-7.1
- **Hecho cuando:** recorrido manual en ancho de escritorio, portátil y
  tableta; toda acción destructiva pide confirmación; todo error de
  validación aparece junto a su campo; la interfaz está íntegramente en
  español.

### [x] T-7.4 — Documentación final
- **Cubre:** RNF-22
- **Depende de:** T-7.1
- **Trabajo:** README con instalación y puesta en marcha; documentación
  de la API (`drf-spectacular`); nota de PT-01 sobre el despliegue real;
  **guion de la demostración** derivado de `plan.md` §11.1, con el orden
  obligatorio: usuarios → catálogo → venta → servicio completo → panel.
- **Hecho cuando:** otra persona levanta el proyecto y ejecuta la
  demostración completa siguiendo solo la documentación.

### [x] T-7.5 — Verificación de coherencia con la especificación
- **Cubre:** RNF-22
- **Depende de:** T-7.1 a T-7.4
- **Trabajo:** Recorrer `spec.md` requerimiento por requerimiento contra
  lo construido. Toda diferencia se resuelve **editando primero
  `specs/`** y ajustando después el código, nunca al revés.
- **Hecho cuando:** los 66 RF y los 23 RNF están verificados, y `spec.md`
  describe el sistema tal como quedó.

---

# Versión 1.4 — cinco funcionalidades nuevas

> Los bloques 8 a 13 derivan de `spec.md` v1.4 y `plan.md` v1.3. Las
> reglas del método no cambian: un *commit* por tarea citando su
> identificador; la especificación manda; una tarea no está hecha hasta
> que su criterio se comprueba.
>
> **Al cerrar cada bloque se ejecuta la suite completa** —backend y
> frontend— y se muestra el resultado antes de abrir el siguiente.
>
> **Estado de partida: el guardián de trazabilidad en rojo.** Desde que
> se aprueba `spec.md` v1.4, `test_trazabilidad.py` falla para los 35
> requerimientos nuevos (RF-69 a RF-97, RNF-24 a RNF-29), porque ningún
> código los cita todavía. **No se silencia.** Cada bloque apaga los
> suyos, y el bloque 13 termina con el guardián en verde.

---

## Bloque 8 — Movimientos de stock

> **Va primero** porque reescribe todos los caminos que cambian
> existencias (`plan.md` §11.2). Es el bloque de mayor riesgo técnico de
> la v1.4: igual que en el bloque 4, **el servicio y su prueba de
> concurrencia van antes que la API**.

### [x] T-8.1 — App `inventario` y modelo `MovimientoStock` ⚠️
- **Cubre:** RN-MOV-02, RN-MOV-03, RN-MOV-04, RNF-25
- **Depende de:** T-7.5
- **Trabajo:** App `inventario`; modelo con `tipo` (`SALDO_INICIAL`,
  `ALTA`, `VENTA`, `ANULACION`, `AJUSTE`), `cantidad` con signo,
  `stock_resultante`, `usuario` y `venta` con nulidad acotada, `motivo`
  y `fecha_hora`; todos los `CHECK` y los índices de `plan.md` §3.3 y
  §3.4. `save()` rechaza actualizar una fila existente; `delete()` y el
  `delete()` del *queryset* lanzan excepción. Se actualiza además la
  cifra de control de `test_trazabilidad.py` a 97 RF y 29 RNF: la
  especificación aprobada ya los declara.
- **Hecho cuando:** pruebas que **saltan la validación de Django**
  verifican que la base rechaza: un movimiento `VENTA` sin venta, un
  `AJUSTE` sin motivo o con cantidad cero, un `stock_resultante`
  negativo y un movimiento sin autor que no sea `SALDO_INICIAL`. Otra
  prueba verifica que actualizar o borrar un movimiento lanza excepción.

### [x] T-8.2 — `registrar_movimiento()` dentro de la venta y la anulación ⚠️
- **Cubre:** **RN-MOV-01**, RNF-09, RNF-10, RNF-24, RF-81
- **Depende de:** T-8.1
- **Trabajo:** `inventario/services.py` con `registrar_movimiento()`.
  `registrar_venta()` y `anular_venta()` lo llaman **dentro** de su
  transacción, con la fila todavía bloqueada, calculando
  `stock_resultante` a partir del valor leído bajo bloqueo (`plan.md`
  §6.5). Un movimiento por producto, no por línea.
- **Hecho cuando:**
  - una venta de dos productos deja dos movimientos `VENTA` con la venta
    de referencia y el resultante correcto;
  - una venta rechazada por stock **no deja ningún movimiento**;
  - un fallo **forzado** en `registrar_movimiento()` revierte también el
    descuento de stock y la venta;
  - una anulación deja un movimiento `ANULACION` por producto.

### [x] T-8.3 — Alta con movimiento y ajuste con bloqueo
- **Cubre:** RN-CAT-10, RN-MOV-05, RF-73, RF-81, CU-CAT-02, CU-CAT-07
- **Depende de:** T-8.2
- **Trabajo:** Crear un producto registra su movimiento `ALTA`, aunque
  sea con cero existencias. `inventario.services.ajustar_existencias()`
  con `select_for_update()`, motivo obligatorio y diferencia calculada
  contra el valor bloqueado. En el serializer de producto, `stock` pasa a
  `read_only` en la edición: solo se fija al crear.
- **Hecho cuando:** ajuste sin motivo → 400; ajuste sin diferencia →
  409 `AJUSTE_SIN_DIFERENCIA`; un `PATCH` con `stock` → 400 sin cambiar
  nada ni crear movimiento; un ajuste registra la diferencia con signo y
  el resultante.
- > **Revisada el 2026-10-09**, después de hecha: se implementó
  > ignorando el `stock` del `PATCH`, como decía entonces el plan, y se
  > cambió a rechazarlo con 400, porque el formulario de producto lo
  > enviaba al editar y el cambio se perdía sin aviso (`plan.md` §4.4).
  > El formulario deja de enviarlo en la misma corrección; la acción
  > «Ajustar existencias» que lo sustituye sigue siendo T-8.7.

### [x] T-8.4 — Migración de saldos iniciales
- **Cubre:** RNF-29, RN-MOV-02
- **Depende de:** T-8.1
- **Trabajo:** Migración de datos que crea un movimiento
  `SALDO_INICIAL`, sin autor, por **cada** producto existente que **aún
  no tenga punto de partida en el libro** —también los de cero—. Su
  cantidad es el stock menos lo que ya sumen sus movimientos, para que
  el libro cuadre aunque el producto se hubiera vendido después de
  T-8.2. Reverso que borra solo las filas `SALDO_INICIAL`.
  **Idempotente**: aplicarla, revertirla y volver a aplicarla, o ejecutar
  su función dos veces, no duplica ningún movimiento. Un producto que ya
  tiene su `ALTA` (creado después de T-8.3) no recibe saldo inicial.
- **Hecho cuando:** una prueba de migración, sobre una base con **más de
  160 productos** con stock variado, verifica que tras aplicar cada
  producto tiene exactamente un saldo inicial igual a su stock y el libro
  cuadra; que al revertir no queda ninguno y los productos no cambiaron;
  y que aplicarla dos veces deja exactamente los mismos movimientos.

### [x] T-8.5 — Concurrencia ampliada y guardián del libro ⚠️
- **Cubre:** **RNF-08**, **RNF-24**, RN-MOV-03
- **Depende de:** T-8.2, T-8.3
- **Trabajo:** Ampliar la prueba de T-4.4 con las comprobaciones del
  libro de `plan.md` §6.5. Prueba nueva de **ajustes y ventas
  concurrentes** sobre el mismo producto. Prueba guardián que verifica
  `SUM(cantidad) = stock` para todo producto tocado por cada prueba.
- **Hecho cuando:** con N hilos vendiendo el mismo producto, los
  movimientos `VENTA` son exactamente las ventas confirmadas, sus
  resultantes forman una secuencia decreciente sin repeticiones, y el
  libro cuadra; con ajustes y ventas intercalados, el libro cuadra en
  cualquier orden. **Estable en cinco ejecuciones seguidas.**
- > ⚠️ Igual que T-4.4: **no se continúa al resto del bloque** hasta que
  > esta prueba pase de forma estable. Además se verifica que **falla**
  > si se quita el `select_for_update()` del ajuste.
- **Resultado (2026-10-09):** estable en cinco ejecuciones seguidas. Sin el
  `select_for_update()` del ajuste falla 5/5. Hallazgo: en parte de esos
  fallos la suma SÍ cuadraba y solo fallaba el último resultante, así que
  `inventario/verificacion.py` comprueba también la cadena de resultantes,
  no solo la suma. El guardián vive en `conftest.py` como *fixture*
  automática; las pruebas que descuadran el libro a propósito llevan la
  marca `libro_libre`.

### [x] T-8.6 — API de movimientos y de ajuste
- **Cubre:** RF-73, RF-82, RF-83, RN-MOV-06, RNF-18
- **Depende de:** T-8.5
- **Trabajo:** `GET /movimientos-stock` con filtros, `GET
  /productos/{id}/movimientos` y `POST /productos/{id}/ajustar-existencias`,
  todos solo Administrador. Sin verbos de escritura sobre los
  movimientos. Ampliar la matriz de T-1.8.
- **Hecho cuando:** el Encargado de Ventas recibe 403 en los tres;
  `POST`, `PATCH` y `DELETE` sobre `/movimientos-stock` responden 405;
  los filtros funcionan combinados y la respuesta viene paginada.
- **Resultado (2026-10-09):** el ajuste responde 201 con el movimiento
  creado; 400 junto al campo si la entrada no vale; 409 si no hay
  diferencia. Decisión de implementación: un filtro inválido en
  `/movimientos-stock` (producto, tipo o fecha) responde **400** en lugar
  de ignorarse, porque en una auditoría una lista sin filtrar parecería
  una respuesta válida. Las fechas se filtran por el día en hora de
  Bolivia, no en UTC.

### [x] T-8.7 — Pantallas de movimientos y ajuste
- **Cubre:** RF-73, RF-82, RF-83, RNF-14, RNF-15
- **Depende de:** T-8.6
- **Trabajo:** Pantalla de movimientos con filtros; historial en el
  detalle del producto; diálogo «Ajustar existencias» con cantidad real,
  motivo, diferencia orientativa y confirmación. El formulario de
  edición de producto deja de ofrecer las existencias.
- **Hecho cuando:** un ajuste desde la interfaz aparece en el historial
  del producto con su motivo; el Encargado de Ventas no ve ni el menú ni
  las acciones.
- **Resultado (2026-10-09):** construido y con pruebas de Vitest (16).
  - El ajuste se confirma en dos pasos dentro del mismo diálogo: primero
    se revisa «de X a Y (±N)» con el motivo, y luego se confirma.
  - Si el servidor registra otra diferencia, porque se vendió mientras
    tanto, se avisa.
  - Historial en el detalle del producto (ruta nueva `/catalogo/:id`) y
    pantalla `/movimientos`.
  - El Encargado de Ventas ni ve las acciones ni pide el historial.
  - **Comprobación visual pendiente** (ver `docs/avance_v1.4.md`).

### [x] T-8.8 — Revisión del bloque 8
- **Depende de:** T-8.1 a T-8.7
- **Hecho cuando:** ciclo comprobado en el navegador —crear producto →
  vender → anular → ajustar— y el historial muestra los cuatro
  movimientos con el libro cuadrado. **Suite completa en verde** salvo el
  guardián de trazabilidad para los requerimientos de bloques
  posteriores; resultado mostrado.
- **Resultado (2026-10-09):** el ciclo crear → vender → anular → ajustar
  se probó **por la API**, con las mismas peticiones que hace la interfaz
  (`inventario/tests/test_ciclo_bloque8.py`).
  - El historial muestra los cuatro movimientos, con su autor y en
    orden, y el libro cuadra.
  - Si la anulación deja de escribir su movimiento, la prueba falla.
  - `makemigrations --check`: sin cambios pendientes.
  - Suites: B 755 pasan y 28 fallan, todas de trazabilidad de bloques
    posteriores; F 153 pasan.
  - **La comprobación en el navegador queda para revisión humana.**

---

## Bloque 9 — Código de producto

### [x] T-9.1 — Generación del código EAN-13
- **Cubre:** **RN-CAT-08**, RF-69
- **Depende de:** T-8.8
- **Trabajo:** Secuencia PostgreSQL `producto_codigo_seq`; función pura
  `calcular_digito_control()`; `generar_codigo()` con prefijo `20`,
  secuencia de 10 dígitos y control (`plan.md` §3.5). El producto nuevo
  recibe su código al crearse; el serializer lo declara `read_only`.
- **Hecho cuando:** el dígito de control coincide con EAN-13 reales
  conocidos; un `POST` con `codigo` lo ignora; un `PATCH` con otro
  `codigo` no lo cambia; retirar un producto y crear otro da un código
  distinto.
- **Resultado (2026-10-09):** `catalogo/codigos.py` contiene las
  funciones puras y la secuencia `producto_codigo_seq`.
  - El código se asigna en `Producto.save()` al insertar, así que lo
    reciben también las fábricas de prueba y la importación.
  - La migración `0002` es el paso 1 de 3 (secuencia y columna nula) y
    se prueba en los dos sentidos.
  - Mutaciones detectadas:
    - si el código se regenera en cada guardado, fallan 2 pruebas;
    - si se calcula como `COUNT + 1` en lugar de usar la secuencia, falla
      la prueba de la transacción revertida.

### [x] T-9.2 — Migración: código para todos los productos existentes
- **Cubre:** RNF-29, RN-CAT-08
- **Depende de:** T-9.1
- **Trabajo:** Las tres migraciones de `plan.md` §3.5: columna nula →
  asignación por `id` ascendente → `NOT NULL` y `UNIQUE`. Cada una con su
  reverso.
- **Hecho cuando:** sobre una base con más de 160 productos, todos
  quedan con un código EAN-13 válido y distinto, y revertir las tres
  migraciones devuelve la tabla a su estado anterior sin pérdida.
- **Resultado (2026-10-09):** migraciones `0003` (asignación por `id`
  ascendente, idempotente) y `0004` (`NOT NULL` y `UNIQUE`).
  - Probado con 165 productos: códigos válidos, distintos y en orden; el
    resto de los datos no cambia; revertir los tres pasos devuelve la
    tabla idéntica.
  - **Cambio en el plan (§3.5):** el reverso del paso 2 no borra los
    códigos, porque reaplicarlo cambiaría el código de productos ya
    etiquetados (RN-CAT-08). Una prueba lo vigila.
  - Aplicado a la base de desarrollo: sus 7 productos tienen ya códigos
    de `2000000000015` a `2000000000077`.

### [x] T-9.3 — Búsqueda por código
- **Cubre:** RF-70
- **Depende de:** T-9.2
- **Trabajo:** Filtro `?codigo=` de coincidencia exacta en
  `GET /productos`; el código en las respuestas de lista y detalle.
- **Hecho cuando:** un código exacto devuelve un único producto; uno
  incompleto o inexistente devuelve una lista vacía sin error.
- **Resultado (2026-10-09):** `?codigo=` busca por coincidencia exacta,
  quitando los espacios de alrededor.
  - Un código vacío no devuelve el catálogo entero, sino una lista vacía.
  - Un código incompleto, con el dígito de control equivocado o
    inexistente da una lista vacía, sin error.
  - Mutaciones detectadas: la búsqueda parcial (`contains`) y la que
    ignora el código vacío.
  - La búsqueda por código de fábrica llega con T-9.7.

### [x] T-9.7 — Código de fábrica opcional *(PA-07)*
> Insertada al aprobar la v1.4. Conserva el número siguiente al último
> del bloque porque los identificadores no se renumeran; se ejecuta en
> esta posición, antes de T-9.4, porque T-9.5 la necesita.
- **Cubre:** **RN-CAT-11**, RF-97, RF-70, RF-74
- **Depende de:** T-9.3
- **Trabajo:** `Producto.codigo_fabrica` con `UNIQUE` parcial y el
  `CHECK` que lo saca del espacio interno (`plan.md` §3.5);
  normalización; el campo en el serializer y el formulario de producto;
  `?codigo=` busca también en él.
- **Hecho cuando:** código de fábrica repetido → 400 junto al campo; con
  forma de código interno → 400, y la base lo rechaza también saltando
  la validación de Django; dos productos sin código de fábrica →
  aceptados; `?codigo=` encuentra el producto por cualquiera de sus dos
  códigos; la migración se aplica y se revierte.
- **Resultado (2026-10-09):** `codigo_fabrica` con `UNIQUE` parcial y el
  `CHECK` contra la forma interna, ambos probados en SQL crudo.
  - Se normaliza quitando los espacios y pasando a mayúsculas.
  - `?codigo=` busca en los dos campos. El código vacío devuelve
    `none()`, porque si no traería todos los productos sin código de
    fábrica.
  - Campo en el formulario de producto. Migración `0005` probada en los
    dos sentidos y aplicada a la base de desarrollo.
  - **De paso se corrige un defecto anterior:** con imagen, el envío
    multipart omitía las cadenas vacías, así que no se podía vaciar la
    descripción ni quitar el código de fábrica al subir una imagen
    nueva.
  - Se desactiva el validador de unicidad que DRF genera para el campo,
    porque compara el valor sin normalizar.

### [x] T-9.4 — Código de barras y etiqueta
- **Cubre:** RF-71, RNF-27, CU-CAT-09
- **Depende de:** T-9.3
- **Trabajo:** `JsBarcode` en EAN-13 y SVG en el detalle del producto;
  columna de código en la lista; botón de imprimir etiqueta con
  `@media print` (`plan.md` §7.9).
- **Hecho cuando:** la etiqueta impresa, escaneada con la **cámara de un
  teléfono con una aplicación lectora**, devuelve exactamente el código
  del producto. *(Decidido al aprobar la v1.4: no se dispone de un
  lector físico. La aplicación lee el EAN-13 con las mismas reglas que
  un lector, incluido el dígito de control, así que valida lo que esta
  tarea necesita validar.)*
- **Resultado (2026-10-09):** construido. `CodigoBarras.vue` usa
  JsBarcode 3.11.6 (versión fija) para dibujar un SVG.
  - Dibuja en EAN-13 si el código lo es (el interno siempre) y en
    Code128 si no.
  - En el detalle se ven los dos códigos y la etiqueta con barras,
    cifras y nombre. «Imprimir etiqueta» usa `window.print()` con una
    hoja `@media print` que oculta todo lo demás.
  - En la lista hay columna de código y un filtro de código exacto.
  - En las pruebas se simula solo la medición de texto del `<canvas>`,
    que jsdom no tiene.
  - **Pendiente de verificación humana:** escanear la etiqueta impresa
    con la cámara del teléfono.

### [x] T-9.5 — Entrada por código en el registro de venta
- **Cubre:** RF-74, **RN-VEN-17**, RNF-16, RNF-27
- **Depende de:** T-9.7
- **Trabajo:** Campo de código en la pantalla de venta que, al recibir
  Intro, agrega el producto o suma una unidad, vacía el campo y conserva
  el foco (`plan.md` §7.9).
- **Hecho cuando:** pruebas de Vitest verifican: código interno exacto →
  se agrega; código de fábrica exacto → se agrega; mismo código otra vez
  → suma uno; un código de fábrica de 12 dígitos o alfanumérico también
  se consulta; código inexistente, retirado o sin stock → aviso y nada
  se agrega; tras cada lectura el foco sigue en el campo.
- **Resultado (2026-10-09):** construido, con 14 pruebas de Vitest que
  simulan un lector, es decir, teclear el código y pulsar Intro.
  - El campo se vacía en el mismo Intro y las lecturas se procesan en
    cola. Así ninguna se pierde ni se pega a la anterior, y la venta
    queda en el orden en que se leyó.
  - No suma más unidades que las existencias.
  - Un código rechazado vuelve al campo seleccionado.
  - Mutaciones detectadas:
    - sin cola, se pierde el orden;
    - si el campo se vacía al responder, la segunda lectura se pega a
      la primera;
    - sin el control de existencias, se agrega un producto agotado.
  - **Verificación con lector o teléfono pendiente** (revisión humana).

### [x] T-9.6 — Revisión del bloque 9
- **Depende de:** T-9.1 a T-9.5, T-9.7
- **Hecho cuando:** una venta completa se arma solo con lecturas de
  código —internos y de fábrica—, comprobado en el navegador. Suite
  completa ejecutada y resultado mostrado.
- **Resultado (2026-10-09):** una venta armada solo con lecturas, por la
  API (`catalogo/tests/test_ciclo_bloque9.py`).
  - Mezcla códigos internos, de fábrica EAN-13 y Code128 (este último en
    minúsculas), y lecturas repetidas.
  - Un producto retirado y un código incompleto no entran.
  - Ninguna lectura identifica a más de un producto, y la venta contiene
    exactamente lo leído.
  - Todos los RF y RNF del bloque 9 están citados.
    `makemigrations --check`: sin cambios.
  - Suites: B 827 pasan y 22 fallan, todas de trazabilidad de bloques
    10 a 13; F 182 pasan.
  - **Comprobación en el navegador con lecturas reales pendiente**
    (revisión humana).

---

## Bloque 10 — Garantía

### [x] T-10.1 — Meses de garantía en producto y en el detalle
- **Cubre:** RN-CAT-09, RN-VEN-12, RF-72, RF-75, RNF-29
- **Depende de:** T-9.6
- **Trabajo:** `Producto.meses_garantia` y `DetalleVenta.meses_garantia`
  con `CHECK (>= 0)`; migración que deja las líneas existentes en **cero**
  (`plan.md` §3.5); el campo en el serializer y el formulario de
  producto.
- **Hecho cuando:** un valor negativo lo rechaza la base; tras migrar,
  todas las líneas anteriores tienen cero meses.
- **Resultado (2026-10-09):** `meses_garantia` en el producto y en la
  línea de venta, con un `CHECK (>= 0)` en cada una, comprobado en SQL
  crudo.
  - Probado con modelos históricos: las líneas anteriores quedan en cero
    aunque su producto tenga garantía.
  - Las dos migraciones se revierten sin perder datos.
  - El campo está en el serializer y en el formulario, sin tope superior
    porque la spec no lo fija.
  - Aplicado a la base de desarrollo.

### [x] T-10.2 — Congelado de la garantía en la venta
- **Cubre:** **RN-VEN-12**, RF-75
- **Depende de:** T-10.1
- **Trabajo:** `registrar_venta()` copia los meses de garantía junto con
  el nombre y el precio.
- **Hecho cuando:** cambiar los meses del producto después de la venta
  no altera la línea guardada.
- **Resultado (2026-10-09):** `registrar_venta()` copia `meses_garantia`
  en cada línea.
  - Si después se quitan, se reducen o se amplían los meses del
    producto, la línea no cambia.
  - Si la línea se graba siempre con cero, fallan las 4 pruebas nuevas.

### [x] T-10.3 — Cálculo del vencimiento
- **Cubre:** **RN-VEN-13**
- **Depende de:** T-10.1
- **Trabajo:** Función pura `sumar_meses(fecha, meses)` con la
  biblioteca estándar (`plan.md` §7.10).
- **Hecho cuando:** prueba parametrizada: 31 de enero + 1 → 28 de
  febrero; en año bisiesto → 29; 30 de noviembre + 3 → 28 de febrero;
  15 de marzo + 12 → 15 de marzo del año siguiente; cero meses → la
  misma fecha.
- **Resultado (2026-10-09):** `ventas/garantia.py` contiene
  `sumar_meses`, `fecha_local` y `vencimiento`, solo con `calendar` de
  la biblioteca estándar.
  - 10 casos parametrizados: los 5 de la tarea y 5 bordes más, entre
    ellos 29/02 + 12 meses y cruces de año.
  - Además, una venta de las 22:00 en La Paz cuenta como del día local,
    no del día en UTC.
  - Mutaciones detectadas: quitar el recorte al último día del mes, y
    calcular la fecha en UTC.

### [x] T-10.4 — Plantilla base de documentos PDF
- **Cubre:** RF-76 (habilita), RF-67
- **Depende de:** T-10.1
- **Trabajo:** Extraer el membrete, la línea morada y el pie del informe
  de servicio a `core/templates/pdf/base.html`; el informe de servicio
  pasa a extenderla.
- **Hecho cuando:** **todas** las pruebas del informe de servicio pasan
  sin cambios —incluida la que rechaza restos de sintaxis de plantilla—
  y el PDF resultante tiene los mismos colores en su flujo.
- **Resultado (2026-10-09):** `core/templates/pdf/base.html` con los
  bloques `estilos`, `titulo`, `numero`, `contenido` y `leyenda`. El
  informe de servicio la extiende.
  - Las 15 pruebas de `servicios/tests/test_pdf.py` pasan **sin
    cambios**.
  - Prueba nueva en `core/tests/test_plantilla_pdf.py`: los operadores
    de color del flujo coinciden con los registrados antes de la
    extracción. Si se quita la línea morada, solo fallan estas pruebas,
    no las del informe.
  - Comprobado una vez: el texto del PDF es idéntico con la plantilla
    antigua y con la nueva, en 3 casos.

### [x] T-10.5 — Endpoint de la garantía
- **Cubre:** RF-76, RF-78, **RN-VEN-14, RN-VEN-15, RN-VEN-16**
- **Depende de:** T-10.2, T-10.3, T-10.4
- **Trabajo:** `GET /ventas/{id}/garantia` con `get_object()`; plantilla
  que extiende la base y lista solo las líneas con garantía; leyenda de
  no fiscal; sin carnet.
- **Hecho cuando:** el texto extraído del PDF contiene el cliente, el
  código y el vencimiento de cada línea con garantía y la leyenda; **no**
  contiene las líneas sin garantía ni restos de plantilla; venta anulada
  → 409; sin líneas con garantía → 409; venta ajena para un Encargado de
  Ventas → 404.
- **Resultado (2026-10-09):** `GET /ventas/{id}/garantia` con
  `get_object()`.
  - La plantilla `ventas/garantia.html` extiende la base y lista solo
    las líneas con meses mayores que cero, con el código y el
    vencimiento calculado en hora de Bolivia.
  - Lleva la leyenda de no fiscal en el cuerpo y en el pie.
  - Errores 409 con código propio (`GARANTIA_DE_VENTA_ANULADA`,
    `VENTA_SIN_GARANTIA`); una venta ajena da 404. La ruta está en la
    matriz de permisos.
  - 15 pruebas sobre el texto real del PDF.
  - Mutaciones detectadas: listar también las líneas sin garantía, y
    usar los meses actuales del producto en lugar de los congelados.

### [x] T-10.6 — Garantía en la interfaz
- **Cubre:** RF-77
- **Depende de:** T-10.5
- **Trabajo:** Campo de meses de garantía en el formulario de producto;
  tras confirmar una venta con garantía, oferta de emitirla; botón en el
  detalle de la venta; descarga con `useDescarga.js`.
- **Hecho cuando:** el botón solo aparece en ventas confirmadas con
  alguna línea con garantía, y el PDF se descarga con el cuadro de
  guardado.
- **Resultado (2026-10-09):** botón «Garantía» en el detalle de venta,
  solo si la venta está confirmada y tiene alguna línea con garantía.
  - Al llegar desde la confirmación (`?recien=1`) se ofrece emitirla.
  - La descarga usa `useDescarga.js`, y el detalle muestra la columna
    de garantía.
  - El campo de meses en el formulario se hizo en T-10.1.
  - Se actualizó la prueba de navegación de T-4.9, que ahora incluye
    `query: { recien: '1' }`.
  - **Pendiente de revisión humana:** abrir el PDF descargado.

### [x] T-10.7 — Revisión del bloque 10
- **Depende de:** T-10.1 a T-10.6
- **Hecho cuando:** vender un producto con garantía, emitir la garantía,
  cambiar los meses del producto y volver a emitirla da el mismo
  vencimiento; abrir el PDF lo confirma visualmente. Suite completa
  ejecutada y resultado mostrado.
- **Resultado (2026-10-09):** el ciclo vender → emitir → cambiar los
  meses → volver a emitir da el mismo vencimiento; lo prueba
  `test_garantia_pdf.py` sobre el texto del PDF.
  - **Punto de extensión** para las condiciones de la garantía: la
    constante `CONDICIONES_DE_GARANTIA` de `ventas/garantia.py`, el único
    sitio donde pegar el texto. Si está vacía, la sección no aparece.
    Hay pruebas de los dos casos.
  - Todos los requisitos del bloque 10 están citados.
    `makemigrations --check`: sin cambios.
  - Suites: B 878 pasan y 17 fallan, todas de trazabilidad de bloques
    11 a 13; F 190 pasan.
  - **Abrir el PDF queda para revisión humana.**

---

## Bloque 11 — Clientes

### [ ] T-11.1 — App `clientes` y modelo `Cliente`
- **Cubre:** RN-CLI-01, **RN-CLI-02**, RN-CLI-03, RNF-07
- **Depende de:** T-10.7
- **Trabajo:** Modelo con `UNIQUE` parcial sobre el carnet, `CHECK` de
  nombre y teléfono, `activo` y auditoría (`plan.md` §3.5). Normalización
  del carnet antes de guardar.
- **Hecho cuando:** dos clientes con el mismo carnet los rechaza la base,
  aunque uno esté inactivo; dos sin carnet se aceptan; `1234567-1a` y
  `1234567-1A` se consideran el mismo carnet.

### [ ] T-11.2 — Servicio de clientes
- **Cubre:** RF-84, RF-85, RF-87, RN-CLI-03, **RN-CLI-04**
- **Depende de:** T-11.1
- **Trabajo:** Crear, editar, desactivar y reactivar, registrando autor y
  fecha.
- **Hecho cuando:** registrar un cliente no crea ningún `Usuario`; un
  cliente desactivado no se elimina y puede reactivarse.

### [ ] T-11.3 — API de clientes
- **Cubre:** RF-84 a RF-89, **RN-CLI-06**, RN-CLI-07, RNF-26
- **Depende de:** T-11.2
- **Trabajo:** Endpoints de `plan.md` §4.4; `ClienteResumenSerializer`
  sin carnet y `ClienteDetalleSerializer` con carnet; búsqueda exacta
  por carnet y parcial por nombre y teléfono; permisos; matriz de T-1.8.
- **Hecho cuando:** la lista no contiene la clave `carnet` en ninguna
  fila; el Encargado de Ventas recibe 403 al desactivar; el Encargado de
  Servicios recibe 403 en todos; `DELETE` responde 405.

### [ ] T-11.4 — Cliente en la venta ⚠️
- **Cubre:** **RN-VEN-10**, **RN-CLI-05**, RF-79, RF-80
- **Depende de:** T-11.3
- **Trabajo:** `Venta.cliente` nulo con `PROTECT`; `registrar_venta()`
  acepta `cliente_id`, comprueba que esté activo y **copia** su nombre y
  teléfono. Sin `cliente_id`, cliente ocasional como hasta ahora.
- **Hecho cuando:**
  - con `cliente_id`, la venta guarda los datos del cliente aunque la
    petición traiga otros;
  - **editar el nombre y el teléfono del cliente, y desactivarlo, no
    altera las ventas anteriores**;
  - cliente inactivo → 409 `CLIENTE_INACTIVO` y ningún stock descontado;
  - el detalle de la venta **no** contiene el carnet.

### [ ] T-11.5 — Pantallas de clientes
- **Cubre:** RF-84 a RF-89, RNF-14
- **Depende de:** T-11.3
- **Hecho cuando:** el carnet solo aparece en el detalle; desactivar y
  reactivar piden confirmación y solo los ve el Administrador.

### [ ] T-11.6 — Selector de cliente en el registro de venta
- **Cubre:** RF-79, RNF-16
- **Depende de:** T-11.4, T-11.5
- **Trabajo:** Tres opciones: buscar y elegir, registrar uno nuevo en un
  diálogo, o escribir un cliente ocasional.
- **Hecho cuando:** elegir un cliente rellena sus datos; registrar uno
  nuevo desde la venta lo deja elegido; el modo ocasional funciona como
  en la v1.3; los clientes inactivos no se ofrecen.

### [ ] T-11.7 — Revisión del bloque 11
- **Depende de:** T-11.1 a T-11.6
- **Hecho cuando:** venta a un cliente registrado → editar el cliente →
  la venta conserva los datos originales, comprobado en el navegador.
  Suite completa ejecutada y resultado mostrado.

---

## Bloque 12 — Reportes

### [ ] T-12.1 — Cálculo del reporte por rango
- **Cubre:** RN-REP-01, **RN-REP-02**, RN-REP-03, RF-91
- **Depende de:** T-11.7
- **Trabajo:** `panel/reportes.py` con `calcular(desde, hasta)`: ventas,
  servicios e ingreso desglosado, en hora de Bolivia y con los mismos
  criterios que el panel.
- **Hecho cuando:** pruebas con datos límite: una venta anulada no suma;
  un servicio cancelado no suma; un servicio registrado antes del rango y
  cerrado dentro **sí** suma; una venta a las 23:59 del último día cuenta
  y una a las 00:00 del día siguiente no.

### [ ] T-12.2 — El panel diario como reporte de un día
- **Cubre:** **RN-REP-08**
- **Depende de:** T-12.1
- **Trabajo:** `panel/resumen` calcula sus cifras de ventas, servicios e
  ingreso con `calcular(hoy, hoy)`, conservando la forma de su respuesta
  (`plan.md` §4.4).
- **Hecho cuando:** **todas** las pruebas del panel pasan sin cambios, y
  una prueba nueva verifica que el panel y el reporte de hoy coinciden.

### [ ] T-12.3 — Detalles del reporte
- **Cubre:** RN-REP-04, RN-REP-05, RN-REP-06, RF-92, RF-93, RF-94
- **Depende de:** T-12.1
- **Hecho cuando:** los productos más vendidos son diez como máximo, con
  el desempate por importe; las ventas por usuario suman el total de
  ventas; los servicios por estado **incluyen las canceladas** como fila
  propia, los cuatro estados aparecen aunque valgan cero, y ninguna
  cancelada suma a un importe (PA-08).

### [ ] T-12.4 — API del reporte
- **Cubre:** RF-90, RN-REP-10
- **Depende de:** T-12.3
- **Hecho cuando:** `desde > hasta` → 400 `RANGO_INVALIDO`; falta una
  fecha → 400; los otros dos roles reciben 403; matriz de T-1.8
  ampliada.

### [ ] T-12.5 — Exportación a PDF
- **Cubre:** RF-95
- **Depende de:** T-12.4, T-10.4
- **Hecho cuando:** el PDF extiende la plantilla base y su texto contiene
  todas las secciones del reporte, sin restos de plantilla.

### [ ] T-12.6 — Exportación a Excel
- **Cubre:** RF-96
- **Depende de:** T-12.4
- **Trabajo:** `openpyxl` como dependencia nueva; una hoja por sección;
  importes como números con formato monetario (`plan.md` §7.11).
- **Hecho cuando:** el archivo se abre con `openpyxl` en la prueba y los
  importes son celdas numéricas, no texto.

### [ ] T-12.7 — Coherencia de las tres salidas ⚠️
- **Cubre:** **RN-REP-07**, **RN-REP-09**, RNF-26, RNF-28
- **Depende de:** T-12.5, T-12.6
- **Trabajo:** Prueba que genera el JSON, el PDF y el Excel del mismo
  rango y compara sus cifras; prueba que busca el carnet de un cliente en
  las tres salidas; medición con un año de datos sintéticos.
- **Hecho cuando:** las cifras son idénticas en las tres; el carnet no
  aparece en ninguna; el reporte de un año y su exportación tardan menos
  de 5 segundos.

### [ ] T-12.8 — Pantalla de reportes
- **Cubre:** RF-90 a RF-96
- **Depende de:** T-12.7
- **Trabajo:** Selector de rango con atajos resueltos en el frontend;
  secciones del reporte; exportar con `useDescarga.js`.
- **Hecho cuando:** pruebas de Vitest verifican que «esta semana»
  empieza el lunes y «este mes» el día 1; las exportaciones se descargan;
  un rango sin actividad muestra ceros con aviso. Suite completa
  ejecutada y resultado mostrado.

---

## Bloque 13 — Cierre de la v1.4

### [ ] T-13.1 — Matriz de permisos y guardianes
- **Cubre:** RNF-02, RNF-22, RNF-23
- **Depende de:** bloques 8 a 12
- **Trabajo:** Comprobar que la matriz de T-1.8 coincide celda por celda
  con `spec.md` §4.4 v1.4; añadir a `test_cobertura_reglas.py` las
  reglas nuevas de `plan.md` §9.
- **Hecho cuando:** los tres guardianes —matriz, cobertura de reglas y
  trazabilidad— están en verde. **Es la primera vez desde la aprobación
  de la v1.4 que el de trazabilidad lo está.**

### [ ] T-13.2 — Usabilidad de lo nuevo
- **Cubre:** RNF-12 a RNF-16
- **Depende de:** T-13.1
- **Hecho cuando:** recorrido manual en los tres anchos de pantalla;
  toda acción nueva que modifica datos —ajustar, desactivar, reactivar—
  pide confirmación; toda la interfaz nueva está en español.

### [ ] T-13.3 — Coherencia y documentación
- **Cubre:** RNF-22
- **Depende de:** T-13.2
- **Trabajo:** Recorrer los 97 RF y 29 RNF contra lo construido;
  actualizar README, guion de la demostración y documentación de la API.
- **Hecho cuando:** `spec.md` describe el sistema tal como quedó, y toda
  diferencia encontrada se resolvió editando primero `specs/`.

---

## Tareas operativas — importación del catálogo anterior *(PT-05)*

> No son funcionalidad del sistema: no tienen pantalla, ni caso de uso,
> ni requerimiento (`plan.md` §11.3). Se rigen igual por el método —un
> *commit* por tarea que cambie código y un criterio comprobable—, pero
> **dos de ellas terminan en una aprobación del usuario**, no solo en
> una prueba.
>
> **Regla firme desde el 2026-10-09:** no se arranca ningún servidor de
> base de datos sobre archivos fuera del proyecto. Los datos antiguos se
> leen de los CSV exportados.

### [ ] T-OP.1 — Exportar el catálogo antiguo a CSV
- **Depende de:** —
- **Trabajo:** Exportar `productos` (todas las columnas, incluidas la
  marca y la ruta de imagen) y `categorias` a
  `Documents\backup_xampp_mariadb\catalogo_export\`, leyendo **solo de la
  copia** de la base, nunca de XAMPP.
- **Hecho cuando:** existen `productos.csv` (153 filas) y
  `categorias.csv` (14 filas), y los archivos de XAMPP no cambiaron.
- > **En espera de confirmación**: exportar exige arrancar un servidor
  > sobre la copia, que está fuera del proyecto, y la regla de arriba lo
  > prohíbe.

### [ ] T-OP.2 — Comando `importar_catalogo` con informe y huella
- **Depende de:** T-9.6 (código interno y de fábrica) y T-8.3 (servicio
  de alta con movimiento)
- **Trabajo:** Comando de gestión que lee los dos CSV y la carpeta de
  imágenes del proyecto antiguo, y crea cada producto **a través del
  servicio de alta**: existencias 0, garantía 0, sin marca. Modo
  `--informe` por defecto, que no escribe nada; modo `--aplicar --huella`;
  opciones `--mapa-categorias` y `--diferencias`, esta última para marcar
  en el informe las filas de `diferencias_con_seeder.csv`. Y,
  **opcionalmente**, la carga de existencias contadas: `--planilla-recuento`
  genera la planilla y `--existencias` la carga **a través del servicio de
  ajuste**, con el motivo «Carga inicial», en la misma transacción y
  dentro de la misma huella (`plan.md` §11.3).
- **Hecho cuando:** pruebas con CSV de muestra verifican que:
  - `--informe` no escribe nada en la base;
  - cada producto importado tiene código EAN-13, un único movimiento
    `ALTA` de cantidad 0 con el autor indicado, existencias 0 y 0 meses
    de garantía;
  - los problemáticos —nombre vacío, largo o repetido, categoría
    inexistente, precio no positivo— no se importan y aparecen en el
    informe con su motivo;
  - una imagen faltante deja el producto sin imagen y aparece en el
    informe;
  - una huella distinta de la del plan no importa nada;
  - un fallo a mitad no deja ningún producto importado;
  - ejecutarlo dos veces no duplica nada;
  - las filas de `--diferencias` aparecen marcadas en el informe con los
    dos valores y el que se importaría, sin cambiar qué se importa;
  - `--planilla-recuento` produce un CSV con un producto por fila, sin
    los problemáticos, y la columna de existencias vacía;
  - con `--existencias`, cada producto contado tiene un libro
    `ALTA 0 → AJUSTE +N` con el motivo «Carga inicial» y el autor de
    `--usuario`, y sus existencias son N; los contados en cero y los no
    contados quedan en 0 sin ajuste; las filas inválidas o con un nombre
    que no corresponde a su `id_antiguo` aparecen en el informe y no se
    cargan;
  - cambiar una cifra del CSV de existencias después del informe cambia
    la huella, y `--aplicar` con la huella vieja no hace nada;
  - un ajuste que falla revierte también la importación.

### [ ] T-OP.3 — Informe de importación y aprobación ⚠️
- **Depende de:** T-OP.1, T-OP.2
- **Trabajo:** Ejecutar `--informe` sobre los CSV reales y presentarlo:
  cuántos productos se importarían; **cuántos tienen nombre o categoría
  problemáticos, y cuáles**; **cuáles tienen la imagen faltante**; **los
  4 productos que difieren entre la base antigua y el seeder**, con el
  precio del Turtle Beach Stealth 600 señalado para confirmarlo con la
  empresa; qué categorías se crearían, cuáles coinciden y cuáles son
  parecidas a una existente; si se carga recuento, cuántos productos se
  cargan, cuántos contados en cero, cuáles quedan sin contar y qué filas
  son inválidas, junto con la **fecha del recuento**; y la huella.
- **Hecho cuando:** **el usuario aprueba el informe** y, si hace falta,
  el mapa de categorías. Sin aprobación explícita no se pasa a T-OP.4.

### [ ] T-OP.4 — Aplicar la importación
- **Depende de:** T-OP.3, con la aprobación del usuario
- **Trabajo:** `--aplicar --huella <la aprobada>`.
- **Hecho cuando:** el número de productos creados y de existencias
  cargadas coincide con el del informe; el libro de movimientos cuadra
  para todos los importados (`SUM(cantidad) = existencias`); una segunda
  ejecución no importa nada.
- > **El recuento**, fuera del sistema y **el día del cambio**: la
  > empresa cuenta su inventario físico sobre la planilla que genera el
  > comando y la entrega para cargarla en esta misma ejecución. Si no
  > está lista, se importa sin ella y las existencias se cargan después
  > con «Ajustar existencias» (CU-CAT-07), una a una.

---

## Trazabilidad inversa: requerimiento → tarea

Comprobación de que ningún requerimiento de `spec.md` quedó sin tarea.

| Requerimientos | Tareas |
|---|---|
| RF-01 a RF-06 | T-1.3, T-1.5, T-1.9, T-1.10, T-1.11 |
| RF-07, RF-08 | T-2.2, T-2.9 |
| RF-09, RF-10, RF-14 | T-2.3, T-2.8 |
| RF-11 | T-2.4 |
| RF-12, RF-13 | T-2.3, T-2.5, T-2.7 |
| RF-15 a RF-20 | T-4.3, T-4.6, T-4.9 |
| RF-21, RF-22 | T-4.7, T-4.10 |
| RF-23 | T-4.6, T-4.10 |
| RF-24, RF-25 | T-4.5, T-4.6, T-4.11 |
| RF-26 | T-4.6 (ausencia de verbos de escritura) |
| RF-27 | T-4.7 |
| RF-28 a RF-30 | T-5.4, T-5.12 |
| RF-31 | T-5.3 |
| RF-32, RF-33 | T-5.6, T-5.13 |
| RF-34 | T-5.6, T-5.13 |
| RF-35 | T-5.2, T-5.13 |
| RF-36 | T-5.7, T-5.11 |
| RF-37 | T-5.8, T-5.11 |
| RF-38 | T-5.7, T-5.13 |
| RF-39 a RF-43 | T-1.7, T-1.13 |
| RF-44 a RF-46 | T-1.6, T-1.13 |
| RF-47 | T-1.1, T-1.7 |
| RF-48 a RF-51 | T-6.1, T-6.2, T-6.3 |
| RF-52 | T-3.2, T-3.3 |
| RF-53 | T-3.4 |
| RF-54 | T-4.5, T-4.6 |
| RF-55 | T-5.1 |
| RF-56, RF-57, RF-59 | T-5.5, T-5.13 |
| RF-58 | T-5.6, T-5.13 |
| RF-60 | T-5.8, T-5.11 |
| RF-61 a RF-63 | T-5.6, T-5.13 |
| RF-64 | T-5.8 |
| RF-65, RF-66 | T-6.1, T-6.2, T-6.3 |
| RNF-01, RNF-02 | T-0.6, T-1.2, T-1.8, T-5.9, T-7.2 |
| RNF-03, RNF-04 | T-1.5 |
| RNF-05 | T-0.5 |
| RNF-06 | T-0.7, T-1.3, T-4.2 |
| RNF-07 | T-1.4, T-5.2 |
| RNF-08 | **T-4.3, T-4.4** |
| RNF-09, RNF-10 | T-4.3, T-4.5 |
| RNF-11 | T-4.1, T-5.2 |
| RNF-12 | T-0.8, T-2.7, T-6.3, T-7.3 |
| RNF-13 a RNF-16 | T-1.11, T-2.8, T-4.9, T-7.3 |
| RNF-17 | T-6.4 |
| RNF-18 | T-2.5, T-4.10, T-5.11 |
| RNF-19 | T-4.4, T-6.4 |
| RNF-20, RNF-21 | T-0.1, T-0.2 |
| RNF-22 | T-7.4, T-7.5 |
| RNF-23 | T-0.9, T-7.1 |
| RN-ACC-05 | T-1.4 |
| RN-USU-02 a RN-USU-04 | T-1.6 |
| RN-VEN-02, RN-VEN-04 | T-4.3 |
| RN-SER-02 | T-5.3 |
| RN-SER-15 | T-5.7 |
| RN-IND-01 a RN-IND-05 | T-6.1 |
| **v1.4** | |
| RF-69 | T-9.1, T-9.2 |
| RF-70 | T-9.3, T-9.7 |
| RF-97 | T-9.7 |
| RF-71 | T-9.4 |
| RF-72 | T-10.1, T-10.6 |
| RF-73 | T-8.3, T-8.6, T-8.7 |
| RF-74 | T-9.5 |
| RF-75 | T-10.1, T-10.2 |
| RF-76 | T-10.4, T-10.5 |
| RF-77 | T-10.6 |
| RF-78 | T-10.5 |
| RF-79, RF-80 | T-11.4, T-11.6 |
| RF-81 | T-8.2, T-8.3 |
| RF-82, RF-83 | T-8.6, T-8.7 |
| RF-84 a RF-89 | T-11.2, T-11.3, T-11.5 |
| RF-90 | T-12.4, T-12.8 |
| RF-91 | T-12.1 |
| RF-92 a RF-94 | T-12.3 |
| RF-95 | T-12.5 |
| RF-96 | T-12.6 |
| RNF-24 | **T-8.2, T-8.5** |
| RNF-25 | T-8.1, T-8.6 |
| RNF-26 | T-11.3, T-12.7 |
| RNF-27 | T-9.4, T-9.5 |
| RNF-28 | T-12.7 |
| RNF-29 | T-8.4, T-9.2, T-10.1 |
| RN-CAT-08 | T-9.1, T-9.2 |
| RN-CAT-09, RN-CAT-10 | T-10.1, T-8.3 |
| RN-CAT-11 | T-9.7 |
| RN-VEN-10 | **T-11.4** |
| RN-VEN-12 a RN-VEN-16 | T-10.2, T-10.3, T-10.5 |
| RN-VEN-17 | T-9.5 |
| RN-MOV-01 a RN-MOV-06 | T-8.1 a T-8.6 |
| RN-CLI-01 a RN-CLI-07 | T-11.1 a T-11.4 |
| RN-REP-01 a RN-REP-10 | T-12.1 a T-12.7 |

---

## Las cinco tareas críticas

Si algo se tuerce en el proyecto, casi con seguridad será una de estas:

| Tarea | Por qué es crítica |
|---|---|
| **T-0.4** | `AUTH_USER_MODEL` después de migrar obliga a reconstruir la base desde cero. Irreversible en la práctica. |
| **T-1.4** | Es la implementación completa de RN-ACC-05 y de la decisión PT-02. Tres de sus cuatro vías no vienen resueltas por defecto. |
| **T-1.6** | Un fallo aquí puede dejar el sistema **sin ningún administrador**, sin forma de repararlo desde la interfaz. |
| **T-4.3** | Concentra las reglas de negocio más delicadas: todo-o-nada, congelado de precios y descuento atómico. |
| **T-4.4** | Es la única evidencia de que RNF-08 se cumple de verdad. Sin ella, la garantía de concurrencia es una afirmación sin respaldo. |

### Las críticas de la v1.4

| Tarea | Por qué es crítica |
|---|---|
| **T-8.2** | Mete un segundo escrito dentro de la transacción más delicada del sistema. Un error aquí rompe la venta, no solo el libro. |
| **T-8.5** | Es la evidencia de RNF-24, igual que T-4.4 lo es de RNF-08. Sin ella, «el libro siempre cuadra» es una afirmación. |
| **T-9.2** | Migración de datos sobre la tabla de productos, que todas las ventas referencian. Tiene que poder deshacerse. |
| **T-11.4** | Es donde un cliente registrado podría alterar ventas pasadas si la copia de datos se hiciera mal. RN-CLI-05 se juega aquí. |
| **T-12.7** | Sin ella, la pantalla, el PDF y el Excel podrían dar cifras distintas para el mismo período sin que nadie lo note. |

---

## Antes de empezar a programar

Cuando apruebes este desglose, la implementación arranca por
**T-0.1** y avanza en orden, un *commit* por tarea. Dos recordatorios
del método:

1. **La especificación manda.** Si al implementar aparece algo que
   `spec.md` no contempla o contempla mal, se edita primero `specs/` y
   luego el código. Nunca al revés: en eso consiste que estos documentos
   estén vivos.
2. **Una tarea no está hecha hasta que su criterio se comprueba.**
   «Funciona en mi máquina» no es un criterio; una prueba que pasa, sí.
