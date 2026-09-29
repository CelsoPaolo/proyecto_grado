# Desglose de Tareas — Sistema ERP PC-Solution

- **Proyecto:** Sistema ERP interno para PC-Solution (Sucre, Bolivia)
- **Documento:** Etapa 3 de Spec-Driven Development — Desglose de tareas
- **Versión:** 1.0 (borrador para revisión)
- **Fecha:** 2026-09-22
- **Estado:** Pendiente de aprobación
- **Deriva de:** `spec.md` v1.1 y `plan.md` v1.1

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

**Total: 73 tareas — todas completadas.** Los bloques 4 y 5 son independientes entre sí y
podrían abordarse en cualquier orden; se propone ventas primero por ser
el de lógica más delicada.

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
  registro—, pendientes con desglose de «sin asignar», y productos bajo
  el umbral global.
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
