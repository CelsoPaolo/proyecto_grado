# Plan Técnico — Sistema ERP PC-Solution

- **Proyecto:** Sistema ERP interno para PC-Solution (Sucre, Bolivia)
- **Documento:** Etapa 2 de Spec-Driven Development — Plan técnico
- **Versión:** 1.5
- **Fecha:** 2026-10-10
- **Estado:** **Aprobado** el 2026-10-08 — la v1.3 diseñó las cinco
  funcionalidades de `spec.md` v1.4, y la v1.4 de este plan las deja
  **implementadas** (bloques 8 a 13), con las precisiones de §11.4.
  Queda pendiente la importación del catálogo anterior (§11.3), que se
  aplica con aprobación expresa. Siguen vigentes PT-01 a PT-05 (sección 13)
- **Deriva de:** `spec.md` v1.4.1

### Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-09-22 | Versión inicial para revisión. |
| 1.1 | 2026-09-22 | Se resuelven los puntos pendientes PT-01 a PT-04. Alcance limitado a entorno de desarrollo (PT-01); **invalidación inmediata de sesiones** al bloquear una cuenta, con corrección de un error técnico de la v1.0 (PT-02); PrimeVue confirmado (PT-03); sin carga de datos de ejemplo, salvo el arranque del primer administrador (PT-04). |
| 1.2 | 2026-09-30 | Se añaden §7.6 (paleta e identidad visual: cromo oscuro sobre área clara, morado como color de marca y los estados semánticos conservando sus colores) y §7.7 (pantalla de Inicio por rol, decorativa, que deja de duplicar la barra lateral). Decisiones de presentación posteriores a las primeras sesiones de uso; ninguna altera un comportamiento y por eso no generan RF nuevos. Se añade además §7.8 y el endpoint `GET /solicitudes/{id}/pdf` en §4.4, que implementan RF-67 y RF-68 de `spec.md` v1.3. |
| 1.3 | 2026-10-08 | **Diseño de las cinco funcionalidades de `spec.md` v1.4.** Dos apps nuevas, `inventario` (movimientos de stock) y `clientes`; `panel` pasa a servir también los reportes por rango, y el panel diario se reescribe como el reporte de un día para que ambos no puedan divergir (RN-REP-08). Modelo de datos en §3.5; endpoints nuevos en §4.4; el libro de movimientos dentro del patrón de concurrencia en §6.5; lector de códigos, garantía y reportes en §7.9 a §7.11. Dependencias nuevas: `openpyxl` (backend) y `JsBarcode` (frontend), ambas sin componentes nativos. **Hallazgo que condiciona el diseño:** hoy las existencias se editan con el `PATCH` genérico del producto, **sin bloquear la fila**; con un libro de movimientos eso deja de ser aceptable y el ajuste pasa a un servicio propio con `select_for_update()` (§6.5). **De paso se corrigen cinco restos** de versiones anteriores: PostgreSQL 16 en §2.1, «asignación» en §2.3, una restricción de §3.3 que no existe en el modelo, y el ejemplo de `finalizar` y la nota sobre `iniciar` de §4.4, ambos anteriores a la v1.2. **Aprobado con las decisiones PA-06 a PA-08** de `spec.md` §12: se diseña el **código de fábrica** opcional (§3.5, §4.4, §7.9) y «servicios por estado» incluye las canceladas. **Revisado el 2026-10-09:** editar un producto con `stock` en la petición responde 400 en lugar de ignorarlo (§4.4). **Revisado otra vez el 2026-10-09 (T-9.2):** el reverso del paso 2 de la migración del código ya no borra los códigos; volver a aplicarlo cambiaría el código de productos ya etiquetados (§3.5, RN-CAT-08). |
| 1.4 | 2026-10-09 | **La v1.4 de `spec.md` queda implementada.** §11.4 recoge lo que la implementación precisó sin cambiar el alcance: el filtro inválido de movimientos responde 400, la cola del lector de códigos, el punto de extensión de las condiciones de la garantía, la búsqueda del carnet solo exacta, el `ANALYZE` tras cargas masivas y el join de «más vendidos». Ninguna precisión cambia un requerimiento. |
| 1.5 | 2026-10-10 | Tres ajustes de interfaz de `spec.md` v1.4.1. **Se retira la pantalla de Inicio** (§7.4 y §7.7, marcadas como retiradas, no borradas): cada rol entra a su espacio de trabajo (§7.12). Los nombres que abren un detalle en las listas dejan de verse como enlaces (§7.13). La cabecera y el menú lateral quedan fijos al desplazarse (§7.5). |

> Este documento traduce la especificación funcional a **decisiones
> técnicas concretas**: arquitectura, modelo de datos, contrato de la API,
> estrategia de seguridad y de concurrencia, y organización del proyecto.
> No introduce funcionalidad nueva: todo lo que aquí se diseña existe para
> satisfacer un requerimiento de `spec.md`, y cada decisión relevante se
> justifica. La descomposición en tareas ejecutables corresponde a la
> etapa 3 (`tasks.md`).

---

## 1. Decisiones tecnológicas

### 1.1 Cuadro resumen

| Ámbito | Decisión | Versión objetivo |
|---|---|---|
| Lenguaje backend | Python | 3.13 |
| Framework backend | Django | 5.1 LTS |
| API | Django REST Framework | 3.15 |
| Base de datos | PostgreSQL | 18 |
| Autenticación | JWT vía `djangorestframework-simplejwt` | 5.3 |
| Framework frontend | Vue.js (Composition API, `<script setup>`) | 3.5 |
| Empaquetador | Vite | 8 |
| Estado global | Pinia | 4 |
| Enrutamiento | Vue Router | 4 |
| Cliente HTTP | Axios | 1.7 |
| Componentes UI | PrimeVue (tema Aura) | 4 |
| Gráficos del panel | Chart.js (vía `PrimeVue Chart`) | 4 |
| Documentos PDF | `xhtml2pdf` (informe de servicio, garantía, reportes) | 0.2 |
| Hojas de cálculo | `openpyxl` *(v1.3)* — exportación de reportes a `.xlsx` | 3.1 |
| Códigos de barras | `JsBarcode` *(v1.3)* — EAN-13 en SVG, en el navegador | 3.11 |
| Pruebas backend | pytest + pytest-django + factory-boy | — |
| Pruebas frontend | Vitest + Vue Test Utils | — |
| Control de versiones | Git (repositorio propio) | — |

> **Versiones reales instaladas, registradas el 2026-09-24 (T-0.3, T-0.8).**
> El equipo tiene Python 3.13 y PostgreSQL 18; el andamiaje de Vite
> instaló Vite 8, Pinia 4 y Vitest 5, versiones mayores más recientes que
> las anotadas en la v1.1 de este plan. La tabla queda actualizada a lo
> realmente instalado. Ninguna decisión de arquitectura cambia: las
> versiones se fijaron como referencia, no como restricción, y todas son
> las estables vigentes de las mismas herramientas elegidas.

### 1.2 Justificación de las decisiones abiertas

#### Base de datos: PostgreSQL

Es la opción recomendada, y en este proyecto no es solo una convención
del ecosistema Django: **RNF-08 la exige**. El descuento seguro de
existencias bajo concurrencia se resuelve con bloqueo de filas
(`SELECT ... FOR UPDATE`) dentro de una transacción, y con restricciones
`CHECK` a nivel de tabla como última línea de defensa. SQLite no ofrece
bloqueo por fila y serializa la escritura a nivel de archivo, lo que
impide **demostrar** el escenario de concurrencia que la especificación
pide garantizar —y que este proyecto de grado debe poder evidenciar con
una prueba automatizada—. Además PostgreSQL aporta el tipo `NUMERIC`
exacto, imprescindible para importes monetarios (RN-VEN-05, RN-SER-13).

> SQLite queda descartado incluso para desarrollo: usar un motor en
> desarrollo y otro en producción ocultaría precisamente los defectos de
> concurrencia que RNF-08 obliga a controlar.

#### Autenticación: JWT con SimpleJWT

Se elige `djangorestframework-simplejwt` sobre el `TokenAuthentication`
básico de DRF por dos razones concretas:

1. **Caducidad incorporada.** El token básico de DRF no expira nunca; un
   token filtrado es válido de forma indefinida. SimpleJWT emite un
   *access token* de vida corta (30 minutos) y un *refresh token* de vida
   media (8 horas, la jornada laboral), lo que acota el daño ante robo
   de token.
2. **Cierre de sesión real.** Con la app `token_blacklist` activada y
   rotación de refresh, el cierre de sesión invalida efectivamente el
   refresh token (CU-AUT-02).

> **Corrección respecto de la v1.0 de este documento.** La v1.0 afirmaba
> que un *access token* seguiría siendo válido hasta 30 minutos después
> de bloquear una cuenta, y que la invalidación inmediata costaría «una
> consulta extra por petición». **Ambas afirmaciones son incorrectas.**
> `JWTAuthentication.get_user()` de SimpleJWT **ya carga el usuario desde
> la base de datos en cada petición** y rechaza el acceso si
> `is_active` es falso. Es decir: la consulta por petición ya se paga
> —no es un coste añadido— y el bloqueo de cuenta **ya es inmediato** por
> ese camino. Lo que la v1.0 describía como una decisión a tomar era, en
> parte, comportamiento por defecto. Lo que sí faltaba son las otras tres
> vías por las que una sesión podía sobrevivir al bloqueo, que la v1.1
> cierra a continuación.

### 1.3 Invalidación inmediata de sesiones (PT-02)

**Decisión: una cuenta bloqueada pierde el acceso al instante, por todas
las vías.** RN-ACC-05 dice que «sus sesiones activas dejan de tener
efecto», sin matices, y esta es su implementación literal.

Hay cuatro vías por las que una sesión podría sobrevivir al bloqueo. Se
cierran las cuatro:

| # | Vía | Estado por defecto | Medida |
|---|---|---|---|
| 1 | *Access token* vigente | **Ya cerrada** por SimpleJWT | Ninguna. `get_user()` comprueba `is_active` en cada petición. |
| 2 | *Refresh token* vigente | **Abierta** | `TokenRefreshSerializer` propio que carga el usuario y rechaza si está bloqueado. |
| 3 | Refresh no caducado tras desbloquear | **Abierta** | Al bloquear, se añaden a la lista negra **todos** los refresh vigentes de esa cuenta. |
| 4 | Cambio de rol o de contraseña a mitad de sesión | **Abierta** | Autorización leída siempre del usuario de base, nunca del token; `CHECK_REVOKE_TOKEN` para la contraseña. |

#### Vía 1 — El *access token*: ya resuelta, sin coste añadido

`JWTAuthentication.get_user()` hace, en cada petición autenticada:

```python
user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
if not user.is_active:
    raise AuthenticationFailed(_("User is inactive"), code="user_inactive")
```

Es una búsqueda por clave primaria, indexada, sobre una tabla de unas
pocas decenas de filas: irrelevante frente a las consultas de catálogo o
de historial. **No hay que escribir nada ni configurar nada**, y no se
paga ninguna consulta que no se estuviera pagando ya.

> Conviene tenerlo presente al justificar el proyecto: este sistema **no
> usa JWT de forma apátrida (*stateless*)**. Cada petición toca la base
> de datos para resolver el usuario. Se renuncia a la ventaja teórica de
> escalabilidad del JWT puro a cambio de revocación inmediata, y para un
> ERP interno de una sola sucursal ese intercambio es claramente el
> correcto.

#### Vía 2 — El *refresh token*

Es el hueco real del comportamiento por defecto: el serializer de
refresco de SimpleJWT valida la **firma y la caducidad** del token, pero
no carga al usuario ni comprueba su estado. Una cuenta bloqueada podría
seguir renovando su *access token* indefinidamente mientras su refresh
siguiera vigente.

```python
# usuarios/serializers.py
class TokenRefreshSeguroSerializer(TokenRefreshSerializer):
    """Rechaza el refresco si la cuenta fue bloqueada o eliminada (RN-ACC-05)."""

    def validate(self, attrs):
        # El usuario se comprueba ANTES de delegar en super(), y el
        # token se lee con UntypedToken, no con RefreshToken.
        token = UntypedToken(attrs["refresh"])
        usuario = Usuario.objects.filter(pk=token[api_settings.USER_ID_CLAIM]).first()
        if usuario is None or not usuario.is_active:
            raise CuentaBloqueada()          # → 403 CUENTA_BLOQUEADA
        return super().validate(attrs)
```

> **Dos detalles de orden descubiertos al implementar (T-1.4,
> 2026-09-24), que el esbozo de la v1.1 tenía al revés:**
>
> 1. **La comprobación va antes de `super()`, no después.** Con
>    `ROTATE_REFRESH_TOKENS` y `BLACKLIST_AFTER_ROTATION`, `super()`
>    pone en la lista negra el token recibido; releerlo después falla
>    **siempre**, incluso para una cuenta activa.
> 2. **Se lee con `UntypedToken`, no con `RefreshToken`.**
>    `RefreshToken` consulta la lista negra al construirse, así que la
>    vía 3 se adelantaría siempre a la vía 2 y el titular recibiría un
>    401 genérico en lugar de saber que su cuenta fue inhabilitada. Más
>    importante: las dos vías deben ser **independientes**, y esta tiene
>    que seguir cerrando el paso aunque la lista negra no se hubiera
>    actualizado —por ejemplo si la cuenta se desactivara desde el panel
>    de administración de Django—.

#### Vía 3 — Lista negra al bloquear

Bloquear una cuenta añade a la lista negra **todos** sus refresh tokens
pendientes, en la misma transacción que el bloqueo:

```python
# usuarios/services.py
@transaction.atomic
def bloquear_usuario(*, usuario, ejecutor):
    _validar_no_es_uno_mismo(usuario, ejecutor)            # RN-USU-03
    _validar_queda_un_administrador(usuario, bloqueando=True)  # RN-USU-04
    usuario.is_active = False
    usuario.save(update_fields=["is_active"])
    _invalidar_sesiones(usuario)                           # RN-ACC-05

def _invalidar_sesiones(usuario):
    for token in OutstandingToken.objects.filter(user=usuario):
        BlacklistedToken.objects.get_or_create(token=token)
```

Sin este paso, desbloquear una cuenta más tarde **resucitaría** las
sesiones antiguas que siguieran dentro de su ventana de 8 horas. Que
esté en la misma transacción importa: si el bloqueo se guarda y la
invalidación falla, la cuenta quedaría bloqueada con sesiones vivas.

#### Vía 4 — El rol nunca se lee del token

El *access token* incluye el rol **solo como dato informativo para la
interfaz**. Ninguna clase de permiso lo consulta: todas leen
`request.user.rol`, que procede de la fila cargada en la vía 1. Así, un
cambio de rol (CU-USU-02) surte efecto en la petición siguiente, sin
necesidad de que el usuario vuelva a iniciar sesión.

Para el cambio de contraseña se activa `CHECK_REVOKE_TOKEN = True`, que
invalida los access tokens emitidos antes del cambio comparando un
resumen de la contraseña —sin consultas adicionales, sobre el usuario ya
cargado—. Es lo que hace que restablecer la contraseña de una cuenta
comprometida (RF-42) expulse de verdad a quien la estuviera usando.

#### Configuración resultante

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=8),    # jornada laboral
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
    "CHECK_REVOKE_TOKEN": True,                      # cambio de contraseña
    "UPDATE_LAST_LOGIN": True,
}
```

Los 30 minutos del *access token* se conservan **aunque ya no sean la
ventana de bloqueo**: siguen acotando el daño de un token robado, que es
un riesgo distinto y que la revocación por `is_active` no cubre.

#### Cómo se verifica

Tres pruebas automatizadas, que son el criterio de aceptación ejecutable
de RN-ACC-05:

1. Usuario autenticado → el administrador lo bloquea → su **siguiente
   petición** con el mismo access token responde 401. Sin esperas.
2. Usuario bloqueado intenta `POST /auth/refresh` con un refresh válido →
   403 `CUENTA_BLOQUEADA`.
3. Bloquear y desbloquear → los refresh anteriores al bloqueo siguen
   rechazados; hay que iniciar sesión de nuevo.

#### Dónde se guarda el token en el frontend

En memoria (store de Pinia) más `localStorage` únicamente para el
*refresh token*, de modo que la sesión sobreviva a un refresco de página.
Es un sistema interno, sin exposición a internet pública. Se documenta
que la alternativa más segura (cookie `HttpOnly` + `SameSite`) exige que
frontend y backend compartan dominio, lo que complica el despliegue
separado que pide RNF-20.

#### Frontend: Vue 3 + Vite + Pinia + Vue Router

- **Vue 3 con Composition API y `<script setup>`** es hoy la versión
  estable y la recomendada por el equipo de Vue; la Options API queda
  descartada por coherencia y porque la lógica reutilizable (permisos,
  llamadas a la API, formularios) se expresa mejor en *composables*.
- **Vite** es la herramienta de construcción oficial del ecosistema Vue,
  sustituye a Vue CLI (en mantenimiento) y ofrece arranque en desarrollo
  casi instantáneo.
- **Pinia** es el gestor de estado oficial, sustituto de Vuex. Aquí
  sostiene tres estados verdaderamente globales: sesión del usuario, su
  rol y permisos derivados, y las notificaciones de la interfaz. El resto
  del estado vive en cada componente: un *store* global para todo sería
  complejidad sin beneficio en un sistema de este tamaño.
- **Vue Router** con *navigation guards* aplica RF-06 en la interfaz —
  ocultando y bloqueando rutas según el rol—, siempre recordando que eso
  es usabilidad, **no** seguridad: la autorización real vive en el
  servidor (RNF-02, RN-ACC-04).
- **PrimeVue 4** aporta `DataTable` con paginación, orden y filtros
  (cubre RNF-18 y los tres historiales), diálogos de confirmación
  (RNF-14), mensajes de validación junto al campo (RNF-15) y una rejilla
  adaptable (RNF-12), sin tener que construir esos componentes a mano.

---

## 2. Arquitectura del sistema

### 2.1 Vista general

Dos aplicaciones independientes que se comunican **solo** por HTTP/JSON
(RNF-20). El frontend es una SPA que se sirve como archivos estáticos y
nunca conoce la base de datos.

```
┌──────────────────────────────┐      ┌──────────────────────────────┐
│   NAVEGADOR (personal PCS)   │      │      SERVIDOR DE APLICACIÓN   │
│                              │      │                              │
│  SPA Vue 3 + Vite            │      │  Django 5 + DRF              │
│  ├─ Vue Router (guards/rol)  │      │  ├─ URLs  /api/v1/…          │
│  ├─ Pinia (sesión, rol)      │ JSON │  ├─ Permissions (por rol)    │
│  ├─ Axios + interceptores    │◄────►│  ├─ Serializers (validación) │
│  └─ Vistas y componentes     │ HTTPS│  ├─ Services (reglas negocio)│
│                              │      │  └─ Models (ORM)             │
└──────────────────────────────┘      └───────────────┬──────────────┘
                                                      │
                                              ┌───────▼────────┐
                                              │  PostgreSQL 18 │
                                              │  + CHECK       │
                                              │  + FOR UPDATE  │
                                              └────────────────┘
```

### 2.2 Capas del backend y dónde vive cada cosa

La regla que se sigue en todo el proyecto: **las reglas de negocio no se
escriben en las vistas**. Una vista de DRF recibe, delega y responde.

| Capa | Responsabilidad | Ejemplo |
|---|---|---|
| **Model** | Estructura de datos e invariantes que la base puede garantizar por sí sola. | `CheckConstraint(stock >= 0)` |
| **Serializer** | Validación de forma del dato de entrada y forma del dato de salida. | «la cantidad es un entero > 0» |
| **Service** (`services.py` por app) | Reglas de negocio con transacción: todo lo que combina varias tablas o requiere atomicidad. | `registrar_venta()`, `finalizar_solicitud()` |
| **Permission** | Autorización por rol y por objeto. | `EsAdministrador`, `PuedeAnularVenta` |
| **ViewSet / APIView** | Traducir HTTP ↔ servicio. Sin lógica de negocio. | `VentaViewSet.create` |

> **Por qué una capa de servicios.** RN-VEN-02 (todo o nada), RNF-08
> (concurrencia) y RNF-09 (atomicidad) no son validaciones de campo: son
> operaciones que tocan varias tablas dentro de una transacción. Si eso
> vive en el serializer o en la vista, se vuelve imposible de probar de
> forma aislada y se duplica en cuanto haya un segundo punto de entrada
> (por ejemplo, el panel de administración de Django).

### 2.3 Aplicaciones Django

| App | Responsabilidad | Modelos |
|---|---|---|
| `usuarios` | Cuentas, roles, autenticación. | `Usuario` |
| `catalogo` | Categorías, productos, existencias. | `Categoria`, `Producto` |
| `ventas` | Registro y anulación de ventas. | `Venta`, `DetalleVenta` |
| `servicios` | Solicitudes, estados, cotización, cierre. | `SolicitudServicio`, `EventoSolicitud` |
| `configuracion` | Parámetros del sistema (umbral global). | `ConfiguracionSistema` |
| `inventario` *(v1.3)* | Libro de movimientos de stock y ajuste manual de existencias. | `MovimientoStock` |
| `clientes` *(v1.3)* | Registro de datos de contacto de clientes. | `Cliente` |
| `panel` | Indicadores del día **y reportes por rango** *(v1.3)*, con sus exportaciones. Solo lectura, sin modelos propios. | — |

> **Por qué `inventario` es una app aparte y no parte de `catalogo`.**
> `MovimientoStock` necesita una clave foránea a `Venta`, y `ventas` ya
> depende de `catalogo` (`DetalleVenta.producto`). Poner el movimiento en
> `catalogo` crearía una dependencia circular entre las dos apps, también
> en sus migraciones. En `inventario`, que depende de las dos, el grafo
> queda en una sola dirección: `catalogo` ← `ventas` ← `inventario`. Los
> servicios de `catalogo` y `ventas` llaman a `inventario.services`; los
> modelos de `inventario` no importan servicios de nadie.
| `core` | Piezas compartidas: permisos, manejador de errores, paginación, mixins. | — |

---

## 3. Modelo de datos

### 3.1 Diagrama entidad-relación

```
┌────────────────────┐
│ Usuario            │
│────────────────────│
│ id                 │
│ username       UQ  │◄──────────────┐
│ password (hash)    │               │ registrada_por
│ nombre_completo    │◄──────┐       │ cotizada_por
│ rol  (ADM/VEN/SER) │       │       │ cerrada_por
│ is_active (bloqueo)│       │       │ (PROTECT)
│ date_joined        │       │       │
└────────────────────┘       │       │
                             │       │
        ┌────────────────────┘       └───────────────────┐
        │ usuario / anulada_por (PROTECT)                │
        │                                                │
┌───────▼────────────┐                    ┌──────────────▼──────────────┐
│ Venta              │                    │ SolicitudServicio           │
│────────────────────│                    │─────────────────────────────│
│ id                 │                    │ id                          │
│ cliente_nombre     │                    │ cliente_nombre              │
│ cliente_telefono   │                    │ cliente_telefono            │
│ usuario        FK  │                    │ tipo  (MANT/REP/RED/VID)    │
│ fecha_hora         │                    │ modalidad (TALLER|DOMICILIO)│
│ estado (CONF/ANUL) │                    │ direccion         ''        │
│ total     NUMERIC  │                    │ descripcion                 │
│ motivo_anulacion   │                    │ estado (REG/ATE/FIN/CAN)    │
│ anulada_por    FK  │                    │ registrada_por    FK        │
│ fecha_anulacion    │                    │ tecnico     TEXTO LIBRE ★   │
└─────────┬──────────┘                    │ monto_cobrado     NULL      │
          │ 1                             │ cotizada_por      FK NULL   │
          │                               │ fecha_cotizacion  NULL      │
          │ N  (CASCADE)                  │ observaciones     ''        │
┌─────────▼──────────┐                    │ motivo_cancelacion''        │
│ DetalleVenta       │                    │ cerrada_por       FK NULL   │
│────────────────────│                    │ fecha_registro              │
│ id                 │                    │ fecha_inicio_atencion NULL  │
│ venta          FK  │                    │ fecha_cierre          NULL  │
│ producto  FK PROT  │──────┐             └──────────────┬──────────────┘
│ producto_nombre ❄  │      │                            │ 1
│ precio_unitario ❄  │      │                            │
│ cantidad           │      │                            │ N (CASCADE)
│ subtotal        ❄  │      │             ┌──────────────▼──────────────┐
└────────────────────┘      │             │ EventoSolicitud             │
                            │             │─────────────────────────────│
      ❄ = dato congelado    │             │ id                          │
        (RN-VEN-04)         │             │ solicitud          FK       │
                            │             │ tipo_evento                 │
      ★ = texto libre, NO   │             │ estado_anterior / nuevo     │
        es una cuenta       │             │ usuario            FK       │
        (RN-SER-09)         │             │ fecha_hora                  │
                            │             │ nota                        │
┌────────────────────┐      │             └─────────────────────────────┘
│ Producto           │◄─────┘
│────────────────────│                    ┌──────────────────────┐
│ id                 │                    │ ConfiguracionSistema │
│ nombre         UQ  │                    │──────────────────────│
│ descripcion        │                    │ id (singleton = 1)   │
│ precio   NUMERIC>0 │                    │ umbral_stock_bajo    │
│ stock       >= 0   │                    │ actualizado_por  FK  │
│ categoria  FK PROT │                    │ actualizado_en       │
│ imagen       NULL  │                    └──────────────────────┘
│ activo (soft del.) │
└─────────┬──────────┘
          │ N
          │ (PROTECT)
┌─────────▼──────────┐
│ Categoria          │
│────────────────────│
│ id                 │
│ nombre         UQ  │
│ descripcion        │
└────────────────────┘
```

### 3.2 Decisiones de modelado y su justificación

#### `Usuario` como modelo propio desde la primera migración

Se define `usuarios.Usuario(AbstractUser)` con `AUTH_USER_MODEL` apuntando
a él **antes de ejecutar la primera migración**. Cambiar el modelo de
usuario una vez creadas las tablas es una de las migraciones más
dolorosas de Django, y aquí hace falta sí o sí: el campo `rol` es central
(RN-ACC-02) y todas las tablas apuntan a este modelo.

- `rol`: `CharField` con `choices` (`ADMINISTRADOR`, `VENTAS`,
  `SERVICIOS`). **Un solo rol por usuario** (RN-ACC-02), por lo que no se
  usan los `Group` ni los `Permission` de Django: serían un mecanismo
  mucho más general del que el sistema necesita, y harían más difícil
  garantizar RN-USU-04 («nunca cero administradores activos»).
- **El bloqueo reutiliza `is_active`** en lugar de añadir un campo nuevo.
  Es exactamente su semántica en Django, y así SimpleJWT lo respeta de
  serie (RN-ACC-05) sin código adicional.
- **Las cuentas no se borran** (RN-USU-05); todas las claves foráneas que
  apuntan a `Usuario` usan `on_delete=PROTECT`, de modo que la base
  impide físicamente perder la autoría de una venta o un servicio.

#### El congelado de precios se implementa con columnas propias

`DetalleVenta` guarda `producto_nombre`, `precio_unitario` y `subtotal`
como **columnas propias**, copiadas en el momento de confirmar la venta.
No se calculan nunca a partir de `Producto` al leer.

Es la traducción directa de RN-VEN-04, y el motivo por el que
`DetalleVenta.producto` es una FK meramente informativa: si mañana el
producto cambia de precio o se retira del catálogo, la venta histórica
sigue diciendo lo que costó **ese día**. El `subtotal` también se
almacena (no se recalcula al vuelo) para que el total de la venta sea
reproducible aun si se modificara la forma de calcularlo.

#### Borrado suave de productos

`Producto.activo` implementa CU-CAT-04: el Administrador «elimina» un
producto y este deja de ofrecerse en ventas nuevas, pero la fila
permanece. Combinado con `on_delete=PROTECT`, esto resuelve además el
flujo alternativo de CU-VEN-03 de la forma más limpia posible: **las
existencias de una venta anulada siempre pueden devolverse**, porque el
producto nunca desaparece de la base. El caso «no pudo reponerse» que la
especificación contempla como posible deja de ocurrir por construcción.

#### `modalidad` derivada del tipo de servicio

`modalidad` (TALLER / DOMICILIO) no la elige el usuario: la determina el
sistema a partir de `tipo`, según RN-SER-01. Se almacena como columna,
en vez de calcularse, para que una eventual reclasificación futura de un
tipo de servicio no altere el significado de las solicitudes históricas —
el mismo principio que el congelado de precios. `direccion` es
obligatoria si y solo si `modalidad == DOMICILIO` (RN-SER-04), validado
en el serializer y reforzado con un `CheckConstraint`.

#### Un solo responsable con identidad; el técnico es texto

*(Revisado en spec.md v1.2.)* `registrada_por` es la única clave foránea
a `Usuario` en la solicitud: no nula e inmutable (RN-SER-11). El
**técnico** es un `CharField` opcional, una anotación del Administrador
(RN-SER-09), no una relación. No hay que validar que esa persona tenga
cuenta, ni reasignar cuando se bloquea, ni impedir autoasignaciones:
los tres problemas desaparecen al no ser una entidad.

`monto_cobrado` admite `NULL` porque una solicitud nace sin cotizar y
eso es un estado operativo legítimo que el panel debe poder contar
(RF-49, RF-60).

#### `EventoSolicitud`: el historial como tabla de primera clase

*(Reescrito tras la revisión de PA-04 en spec.md v1.2.)* El esbozo
anterior justificaba esta tabla diciendo que el módulo era un espacio
compartido donde cualquier encargado podía tocar cualquier solicitud
abierta. **Eso dejó de ser cierto:** desde la v1.2 cada solicitud la ven
solo quien la registró y el Administrador (RN-SER-15), igual que en
ventas.

El historial no pierde importancia por ello; la gana por otro motivo.
Sobre una misma solicitud actúan **dos personas distintas**: el
Administrador la cotiza y anota al técnico (RF-56), y el registrador la
inicia y la cierra. Ninguno de los dos ve la traza completa del otro en
los campos del registro, porque cada campo guarda solo el último valor.
El historial es lo que permite saber quién hizo qué y cuándo, incluso con
la visibilidad restringida.

Por eso es una tabla propia, de **solo inserción** (nunca se actualiza ni
se borra), que registra con el mismo formato los cuatro tipos de evento:
cambio de estado, cotización, anotación de técnico y cierre (RF-35,
RF-59). El técnico se **anota**, no se asigna: es texto libre y no una
relación (RN-SER-09).

#### `ConfiguracionSistema` como fila única

PA-01 decidió un umbral **global**. Se modela como una tabla de una sola
fila (`pk=1`, garantizada por un `CheckConstraint`) en lugar de una
variable de entorno o una constante, porque RF-52 exige que el
Administrador pueda **modificarlo desde la interfaz** sin redesplegar, y
porque RN-CAT-07 pide registrar quién lo cambió y cuándo.

### 3.3 Restricciones a nivel de base de datos

Se declaran en la base, no solo en Python, porque son los invariantes que
deben cumplirse pase lo que pase (RNF-08, RNF-11):

| Tabla | Restricción | Regla que protege |
|---|---|---|
| `producto` | `CHECK (stock >= 0)` | RN-CAT-02, **RNF-08** |
| `producto` | `CHECK (precio > 0)` | RN-CAT-01 |
| `producto` | `UNIQUE (nombre)` | RN-CAT-03 |
| `categoria` | `UNIQUE (nombre)` | RN-CAT-03 |
| `usuario` | `UNIQUE (username)` | RN-USU-06 |
| `detalle_venta` | `CHECK (cantidad > 0)` | RN-VEN-01 |
| `detalle_venta` | `CHECK (precio_unitario > 0)` | RN-VEN-05 |
| `venta` | `CHECK (total >= 0)` | RN-VEN-05 |
| `solicitud` | `CHECK (modalidad='DOMICILIO' → direccion <> '')` | RN-SER-04 |
| `solicitud` | `CHECK (estado='FINALIZADA' → monto_cobrado IS NOT NULL AND observaciones <> '')` | RN-SER-03, RN-SER-13 |
| `solicitud` | `CHECK (monto_cobrado IS NULL OR monto_cobrado >= 0)` | RN-SER-13 |
| `solicitud` | `CHECK (estado='CANCELADA' → motivo_cancelacion <> '' AND fecha_cierre IS NOT NULL)` | RN-SER-07 |
| `configuracion` | `CHECK (id = 1 AND umbral_stock_bajo >= 0)` | RN-CAT-07 |
| `producto` *(v1.3)* | `UNIQUE (codigo)`, `NOT NULL` | RN-CAT-08 |
| `producto` *(v1.3)* | `UNIQUE (codigo_fabrica) WHERE codigo_fabrica <> ''` — único **parcial** | RN-CAT-11 |
| `producto` *(v1.3)* | `CHECK (codigo_fabrica !~ '^20[0-9]{11}$')` — fuera del espacio interno | RN-CAT-11 |
| `producto` *(v1.3)* | `CHECK (meses_garantia >= 0)` | RN-CAT-09 |
| `detalle_venta` *(v1.3)* | `CHECK (meses_garantia >= 0)` | RN-VEN-12 |
| `movimiento_stock` *(v1.3)* | `CHECK (stock_resultante >= 0)` | RN-CAT-02, RN-MOV-03 |
| `movimiento_stock` *(v1.3)* | `CHECK (tipo IN ('VENTA','ANULACION') ⇔ venta IS NOT NULL)` | RN-MOV-02 |
| `movimiento_stock` *(v1.3)* | `CHECK (tipo='VENTA' → cantidad < 0)`, `CHECK (tipo='ANULACION' → cantidad > 0)` | RN-MOV-02 |
| `movimiento_stock` *(v1.3)* | `CHECK (tipo='AJUSTE' → cantidad <> 0 AND motivo <> '')` | RN-MOV-05 |
| `movimiento_stock` *(v1.3)* | `CHECK (tipo IN ('SALDO_INICIAL','ALTA') → cantidad >= 0)` | RN-MOV-02 |
| `movimiento_stock` *(v1.3)* | `CHECK (usuario IS NULL ⇔ tipo='SALDO_INICIAL')` | RN-MOV-02 |
| `cliente` *(v1.3)* | `UNIQUE (carnet) WHERE carnet <> ''` — único **parcial** | RN-CLI-02 |
| `cliente` *(v1.3)* | `CHECK (nombre <> '' AND telefono <> '')` | RN-CLI-01 |

> **Corrección en la v1.3.** La v1.2 listaba aquí
> `CHECK (estado='CANCELADA' → monto_cobrado IS NULL)` bajo RN-SER-14.
> **Esa restricción nunca existió en el modelo, y no debía existir:**
> RN-SER-14 dice que una solicitud cancelada no cuenta como ingreso
> *aunque se hubiera cotizado antes*, lo que presupone que una cancelada
> **puede** tener monto. La exclusión se resuelve en la consulta del
> panel, no en la tabla. La fila se sustituye por la restricción que sí
> existe, la del motivo de cancelación.

> `CHECK (stock >= 0)` es deliberadamente redundante con la validación
> del servicio de ventas. Es la garantía final de RNF-08: aunque un error
> de programación futuro saltara la validación, la base **rechaza** la
> operación en vez de dejar el inventario en negativo.

### 3.4 Índices

| Tabla | Índice | Motivo |
|---|---|---|
| `venta` | `(usuario, fecha_hora DESC)` | Historial propio del encargado (RF-21). |
| `venta` | `(fecha_hora DESC)`, `(estado)` | Filtros e indicador del día (RF-22, RF-48). |
| `detalle_venta` | `(venta)` | Carga del detalle y devolución de stock. |
| `solicitud` | `(estado)`, `(registrada_por, fecha_registro DESC)`, `(fecha_registro DESC)` | Visibilidad por registrador (RN-SER-15) y filtros de RF-37, RF-60 e indicador RF-49. |
| `solicitud` | `(estado, fecha_cierre)` | Ingresos por servicios del día (RN-IND-04). |
| `producto` | `(categoria)`, `(activo)`, `(stock)` | Catálogo filtrado y existencias bajas (RF-13, RF-50). |
| `evento_solicitud` | `(solicitud, fecha_hora)` | Historial ordenado de una solicitud. |
| `producto` *(v1.3)* | `(codigo)` y `(codigo_fabrica)` — los crean sus `UNIQUE` | Búsqueda por código y lector (RF-70, RF-74). |
| `movimiento_stock` *(v1.3)* | `(producto, fecha_hora DESC)`, `(tipo)`, `(fecha_hora DESC)` | Historial de un producto y filtros de RF-82. |
| `movimiento_stock` *(v1.3)* | `(venta)` | Movimientos de una venta al anularla o auditarla. |
| `cliente` *(v1.3)* | `(nombre)`, `(telefono)`, `(activo)` | Búsqueda de RF-86. El carnet ya tiene su índice único. |
| `venta` *(v1.3)* | `(cliente)` | Ventas de un cliente registrado. |
| `detalle_venta` *(v1.3)* | `(producto)` | Productos más vendidos del reporte (RN-REP-04). |

### 3.5 Modelo de datos de la v1.4 *(v1.3 de este plan)*

El diagrama de §3.1 describe el modelo hasta la v1.3 de la
especificación. Este es el fragmento que cambia; las entidades que no
aparecen quedan como estaban.

```
┌──────────────────────┐        ┌──────────────────────────────┐
│ Producto             │        │ MovimientoStock   (inventario)│
│──────────────────────│        │──────────────────────────────│
│ …campos de §3.1…     │◄───────│ producto        FK PROTECT   │
│ codigo   13 UQ  ★    │  1   N │ tipo  SALDO_INICIAL|ALTA|    │
│ codigo_fabrica ''    │        │       VENTA|ANULACION|AJUSTE │
│      UQ parcial      │        │                              │
│ meses_garantia >=0   │        │                              │
└──────────────────────┘        │ cantidad        con signo    │
                                │ stock_resultante  >= 0       │
┌──────────────────────┐        │ usuario   FK NULL ◆ PROTECT  │
│ DetalleVenta         │        │ venta     FK NULL ◆ PROTECT ─┼──┐
│──────────────────────│        │ fecha_hora                   │  │
│ …campos de §3.1…     │        │ motivo          ''           │  │
│ meses_garantia ❄     │        └──────────────────────────────┘  │
└──────────────────────┘                                          │
                                ┌──────────────────────────────┐  │
┌──────────────────────┐        │ Venta                        │◄─┘
│ Cliente   (clientes) │        │──────────────────────────────│
│──────────────────────│ 1    N │ …campos de §3.1…             │
│ nombre               │◄───────│ cliente  FK NULL  PROTECT    │
│ telefono             │        │ cliente_nombre    ❄ (sigue)  │
│ direccion      ''    │        │ cliente_telefono  ❄ (sigue)  │
│ carnet ''  UQ parcial│        └──────────────────────────────┘
│ activo               │
│ creado_por      FK   │   ★ = asignado por el sistema, inmutable
│ creado_en            │   ❄ = dato congelado al confirmar
│ actualizado_por FK   │   ◆ = nulidad acotada por CHECK (§3.3)
│ actualizado_en       │
└──────────────────────┘
```

#### El código de producto: secuencia propia, prefijo interno y dígito de control

```
  2 0 │ 0 0 0 0 0 0 0 1 4 7 │ 0      ← producto n.º 147
  ────┼─────────────────────┼───
  GS1 │ secuencia, 10 dígitos│ control

  control: 2·1 + 0·3 + … + 1·3 + 4·1 + 7·3 = 30  →  (10 − 30 mód 10) mód 10 = 0
```

- **Prefijo `20`.** GS1 reserva los prefijos 20 a 29 para **circulación
  restringida**: códigos que un comercio asigna para uso interno. Ningún
  fabricante puede tener un código que empiece por 20, así que el código
  interno **nunca colisiona** con el de una caja real (RN-CAT-08). Es
  también lo que permite tener los dos códigos a la vez (PA-07): el
  interno vive en el espacio `20…`, y el de fábrica, por RN-CAT-11, no
  puede entrar en él.
- **Secuencia PostgreSQL dedicada** (`producto_codigo_seq`), no la clave
  primaria. Así el código se conoce **antes** de insertar la fila —sin
  el guardar-y-luego-actualizar que exigiría derivarlo de `pk`—, y su
  generación queda desacoplada de la tabla. Una secuencia de PostgreSQL
  **nunca devuelve dos veces el mismo número**, ni aunque la transacción
  que lo pidió se revierta: eso es literalmente «no reutilizable».
- **Dígito de control EAN-13**, calculado al generar: suma ponderada 1-3
  de los 12 primeros dígitos, complemento a 10. Sin él, un lector
  estándar rechaza el código impreso (RNF-27). Una función pura,
  `calcular_digito_control()`, con pruebas contra códigos EAN-13 reales.
- **Inmutable por tres vías.** El serializer lo declara `read_only`; el
  servicio de edición no lo toca; y una prueba verifica que un `PATCH`
  que lo incluye no lo cambia. No se añade un *trigger*: el mismo
  criterio que con `EventoSolicitud`, protección en el código y prueba
  que la vigila.

**Migración en tres pasos**, porque `NOT NULL UNIQUE` no puede añadirse
de golpe a una tabla con filas:

1. Crear la secuencia y añadir `codigo` como **nulo**.
2. **Asignar** un código a cada producto existente, recorriéndolos por
   `id` ascendente para que el orden sea reproducible.
3. Imponer `NOT NULL` y `UNIQUE`.

Cada paso tiene su reverso (RNF-29). El paso 3 quita `NOT NULL` y
`UNIQUE`, y el 1 elimina la columna y la secuencia. El paso 2 **no
borra los códigos al revertirse**, y al aplicarse solo asigna los que
faltan *(revisado el 2026-10-09, T-9.2)*.

La primera versión decía que el reverso del paso 2 dejaba `codigo` en
nulo. Pero al volver a aplicarlo, cada producto recibiría un código
**distinto** del que ya tenía, y las etiquetas impresas dejarían de
corresponder: eso contradice RN-CAT-08, porque el código no cambia
nunca.

Revertir los tres pasos sigue devolviendo la tabla a su estado
anterior, porque el paso 1 elimina la columna entera. Se prueba con
más de 160 productos sintéticos, aunque la base de desarrollo tiene
hoy siete.

#### El código de fábrica: opcional, editable y fuera del espacio interno *(PA-07)*

- **`CharField` en blanco, no `NULL`**, con `UNIQUE` **parcial**
  `WHERE codigo_fabrica <> ''`: la misma solución que el carnet del
  cliente, por el mismo motivo —muchos productos sin código, y los que
  lo tienen, distintos—.
- **Sin validar el formato de fábrica.** Puede ser EAN-13, UPC-A de 12
  dígitos, EAN-8 o un Code128 alfanumérico; validar uno solo dejaría
  fuera mercadería real. Solo se normaliza —sin espacios, en
  mayúsculas— y se limita a 50 caracteres.
- **Lo único que se prohíbe es la forma del código interno:**
  `CHECK (codigo_fabrica !~ '^20[0-9]{11}$')`, reforzado en el
  serializer con un mensaje claro. Es lo que garantiza que una lectura
  identifique a un solo producto: el filtro `?codigo=` busca en los dos
  campos, y sin esta restricción el código de fábrica de un producto
  podría coincidir con el interno de otro.
- **No se congela en la venta**, igual que el interno: la garantía lista
  el código **interno**, que es el que no cambia nunca.
- **Migración trivial**: un campo nuevo con valor por defecto vacío, sin
  datos que transformar. Reversible eliminando la columna.

#### Los meses de garantía se congelan; el código no hace falta

`DetalleVenta.meses_garantia` se copia del producto al confirmar, por
el mismo motivo que el precio (RN-VEN-12). Las líneas anteriores a la
v1.4 se rellenan con **cero**, no con los meses actuales del producto:
asignarles una garantía hoy sería inventar un dato que no existía
cuando se vendió.

El **código** del producto, en cambio, **no** se congela en el detalle.
Congelar sirve para que un dato que *puede* cambiar no altere el pasado;
el código no cambia nunca (RN-CAT-08), así que leerlo a través de
`DetalleVenta.producto` siempre da el mismo valor. Copiarlo sería una
columna redundante que además podría desincronizarse.

#### `MovimientoStock`: libro de solo inserción

- **`cantidad` con signo** y **`stock_resultante`**, no solo uno de los
  dos. Con la cantidad se reconstruye el saldo; con el resultante se
  audita sin sumar todo el historial. Tener los dos permite verificar el
  invariante de RN-MOV-03 en una prueba: `SUM(cantidad) = stock` y
  `último.stock_resultante = stock`.
- **`usuario` nulo solo para `SALDO_INICIAL`**, y un `CHECK` lo
  garantiza en la base. El saldo inicial lo crea la migración, no una
  persona; cualquier otro movimiento sin autor sería un agujero en
  RNF-07.
- **`venta` obligatoria exactamente para `VENTA` y `ANULACION`**, también
  con `CHECK`. La relación usa `PROTECT`, que por RN-VEN-06 nunca llega a
  activarse: las ventas no se borran.
- **Inmutable** como `EventoSolicitud`: `save()` rechaza actualizar una
  fila existente, `delete()` y el `delete()` del *queryset* lanzan
  excepción, y no existe ningún endpoint de escritura. Una prueba lo
  vigila (RNF-25).
- **Saldo inicial por migración de datos**: una fila por producto con su
  stock actual —también los que tienen cero, para que **todo** producto
  tenga un movimiento de origen—. Reversible: el reverso borra solo las
  filas `SALDO_INICIAL`, las únicas que creó.

#### `Cliente`: carnet único parcial y normalizado

- **`carnet` como cadena vacía, no `NULL`**, con un `UNIQUE` **parcial**
  `WHERE carnet <> ''`. Así dos clientes sin carnet no chocan y dos con
  el mismo sí (RN-CLI-02). Se sigue la convención de Django de no usar
  `NULL` en campos de texto.
- **Se normaliza antes de guardar**: sin espacios y en mayúsculas. Un
  carnet boliviano puede llevar complemento o extensión
  (`1234567-1A`, `1234567 LP`); sin normalizar, `1234567-1a` y
  `1234567-1A` serían dos clientes distintos para la base.
- **Auditoría**: `creado_por`, `actualizado_por` y sus fechas, con
  `PROTECT` hacia `Usuario`. RNF-07 no nombraba a los clientes porque no
  existían, pero su espíritu —toda modificación tiene autor— aplica.
- **`Venta.cliente` con `PROTECT`**, que nunca se activa porque los
  clientes no se borran (RN-CLI-03). Es la misma garantía física que
  protege la autoría de las ventas.
- **El carnet no sale de su app.** Ningún serializer fuera de
  `clientes` lo declara: ni el de la venta, ni el de la garantía, ni el
  de los reportes. La minimización de RNF-26 queda en la forma de los
  datos, no en la disciplina de quien escriba la próxima vista.

---

## 4. Diseño de la API REST

### 4.1 Convenciones generales

- **Base:** `/api/v1/`. El versionado en la URL permite evolucionar el
  contrato sin romper el frontend desplegado.
- **Formato:** JSON en ambos sentidos. `Content-Type: application/json`,
  salvo la carga de imagen de producto, que usa `multipart/form-data`.
- **Nombres de campo:** `snake_case`, igual que en el modelo, para no
  introducir una capa de traducción que solo aportaría errores.
- **Fechas:** ISO-8601 con zona horaria (`America/La_Paz`).
- **Importes:** cadena decimal (`"1250.00"`), nunca número de coma
  flotante, para no perder precisión en el trayecto.
- **Paginación:** `?page=`, `?page_size=` (por defecto 20, máximo 100),
  respuesta con `count`, `next`, `previous`, `results` (RNF-18).
- **Autenticación:** cabecera `Authorization: Bearer <access_token>` en
  toda petición salvo el propio inicio de sesión (RNF-01).

### 4.2 Códigos de estado

| Código | Uso |
|---|---|
| 200 | Consulta o actualización correcta. |
| 201 | Recurso creado (venta, solicitud, producto, usuario). |
| 204 | Operación sin contenido de respuesta. |
| 400 | Error de validación o de regla de negocio. |
| 401 | Sin autenticar, token ausente, inválido o expirado. |
| 403 | Autenticado pero sin permiso para esa operación (rol u objeto). |
| 404 | Recurso inexistente. |
| 409 | Conflicto de estado: transición inválida, venta ya anulada. |
| 422 | Existencias insuficientes al confirmar una venta. |

> Se distingue **401 vs 403** de forma estricta porque el frontend actúa
> distinto: 401 dispara el refresco de token o el cierre de sesión; 403
> muestra un mensaje de permiso insuficiente. Y se reserva **422** para
> el caso de stock porque es el único error que el frontend debe mostrar
> de forma enriquecida (qué producto falta y cuánto hay), no como un
> mensaje de validación cualquiera.

### 4.3 Formato uniforme de error

Un manejador de excepciones propio (`core/exceptions.py`) normaliza
**toda** respuesta de error a la misma forma, de modo que el frontend
tenga un único camino de tratamiento:

```json
{
  "codigo": "STOCK_INSUFICIENTE",
  "detalle": "No hay existencias suficientes para confirmar la venta.",
  "errores": {
    "items": [
      {"producto_id": 12, "nombre": "Teclado mecánico",
       "solicitado": 5, "disponible": 2}
    ]
  }
}
```

Para errores de validación de campo, `errores` es el diccionario de DRF
(`{"precio": ["El precio debe ser mayor que cero."]}`), que el frontend
mapea directamente al campo correspondiente del formulario (RNF-15).

Catálogo de códigos previsto: `CREDENCIALES_INVALIDAS`,
`CUENTA_BLOQUEADA`, `PERMISO_INSUFICIENTE`, `VALIDACION`,
`STOCK_INSUFICIENTE`, `VENTA_YA_ANULADA`, `TRANSICION_INVALIDA`,
`TECNICO_REQUERIDO`, `OBSERVACIONES_REQUERIDAS`, `MONTO_REQUERIDO`,
`SOLICITUD_CERRADA`, `ULTIMO_ADMINISTRADOR`, `AUTOMODIFICACION_PROHIBIDA`,
`CATEGORIA_CON_PRODUCTOS`, `ERROR_AL_GENERAR_PDF`.

Nuevos en la v1.3: `AJUSTE_SIN_DIFERENCIA` (409, la cantidad real ya es
la registrada), `GARANTIA_NO_DISPONIBLE` (409, venta anulada o sin
líneas con garantía), `CLIENTE_INACTIVO` (409), `CARNET_DUPLICADO` (409)
y `RANGO_INVALIDO` (400, `desde` posterior a `hasta`). Un código de
fábrica repetido o con forma de código interno es un error de
validación de campo (400 `VALIDACION` sobre `codigo_fabrica`), para que
el formulario lo muestre junto al campo (RNF-15).

> **RNF-06:** los mensajes son deliberadamente genéricos donde deben
> serlo. `CREDENCIALES_INVALIDAS` se devuelve tanto si el usuario no
> existe como si la contraseña es incorrecta (CU-AUT-01), y nunca expone
> trazas ni detalles internos.

### 4.4 Endpoints

Leyenda de roles: **A** = Administrador, **V** = Encargado de Ventas,
**S** = Encargado de Servicios.

#### Autenticación (`/api/v1/auth/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| POST | `/auth/login` | público | Devuelve `access`, `refresh` y los datos del usuario con su rol. | RF-01, RF-02, RF-03 |
| POST | `/auth/refresh` | autenticado | Renueva el `access` y rota el `refresh`. Verifica que la cuenta siga activa; 403 si fue bloqueada (§1.3, vía 2). | RN-ACC-05 |
| POST | `/auth/logout` | autenticado | Invalida el `refresh` recibido. | RF-04 |
| GET | `/auth/me` | autenticado | Usuario actual, su rol y sus permisos efectivos. | RF-06 |
| POST | `/auth/me/password` | autenticado | Cambia la contraseña propia verificando la anterior. | RF-05 |

<details>
<summary><code>POST /auth/login</code> — petición y respuesta</summary>

```jsonc
// → petición
{ "username": "jperez", "password": "••••••••" }

// ← 200
{
  "access": "eyJhbGciOi…",
  "refresh": "eyJhbGciOi…",
  "usuario": {
    "id": 4, "username": "jperez", "nombre_completo": "Juan Pérez",
    "rol": "VENTAS", "rol_display": "Encargado de Ventas"
  }
}

// ← 401  (usuario inexistente O contraseña incorrecta: mismo mensaje)
{ "codigo": "CREDENCIALES_INVALIDAS",
  "detalle": "Usuario o contraseña incorrectos." }

// ← 403  (cuenta bloqueada)
{ "codigo": "CUENTA_BLOQUEADA",
  "detalle": "Esta cuenta está inhabilitada. Consulte al administrador." }
```
</details>

#### Catálogo (`/api/v1/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/categorias` | A, V | Lista de categorías. | RF-12 |
| POST | `/categorias` | A | Crea una categoría. | RF-07 |
| PATCH | `/categorias/{id}` | A | Edita una categoría. | RF-07 |
| DELETE | `/categorias/{id}` | A | Elimina; 409 si tiene productos. | RF-07, RF-08 |
| GET | `/productos` | A, V | Lista paginada. Filtros `?categoria=`, `?buscar=`, `?stock_bajo=true`, `?activo=`, **`?codigo=`** *(v1.3, coincidencia exacta con `codigo` **o** `codigo_fabrica`)*. | RF-12, RF-13, RF-53, RF-70 |
| POST | `/productos` | A | Crea (`multipart` si lleva imagen). Asigna el código y registra el movimiento de alta. **`codigo` en la petición se ignora**; `codigo_fabrica` es opcional. | RF-09, RF-14, RF-69, RF-72, RF-81, RF-97 |
| GET | `/productos/{id}` | A, V | Detalle, con `codigo`, `codigo_fabrica` y `meses_garantia`. | RF-12, RF-71 |
| PATCH | `/productos/{id}` | A | Edita los datos descriptivos, incluido `codigo_fabrica`. **Si la petición trae `stock`, responde 400** con el error en ese campo y no aplica nada; `codigo` se ignora *(v1.3, revisado el 2026-10-09)*. | RF-10, RF-97 |
| DELETE | `/productos/{id}` | A | Borrado suave (`activo = false`). | RF-11 |
| POST | `/productos/{id}/ajustar-existencias` *(v1.3)* | **solo A** | `{ "cantidad_real": 12, "motivo": "Recuento físico" }`. Bloquea la fila, calcula la diferencia y registra el movimiento (§6.5). | RF-73, RF-81 |
| GET | `/productos/{id}/movimientos` *(v1.3)* | **solo A** | Historial de movimientos del producto, paginado, del más reciente al más antiguo. | RF-83 |

Cada producto listado incluye `stock_bajo: true|false`, calculado contra
el umbral global vigente, para que el frontend no tenga que conocer la
regla (RF-53).

> **Editar con `stock` se rechaza, no se ignora** *(revisado el
> 2026-10-09)*. La primera versión de este plan decía lo contrario
> —ignorarlo, para no romper a un cliente antiguo que siguiera
> enviándolo—, y T-8.3 se implementó así. Al usarlo apareció el
> problema: el formulario de producto **enviaba las existencias al
> editar**, de modo que quien cambiaba ese número y guardaba recibía un
> 200 y el cambio no se aplicaba, sin ningún aviso. Un error explícito
> («las existencias se corrigen con Ajustar existencias») es mejor que
> un éxito falso.
>
> Dos consecuencias:
>
> - **`stock` sigue siendo de solo lectura al editar**, así que su valor
>   nunca se aplica; el rechazo se añade además, en `validate()`,
>   mirando la petición original.
> - **El formulario deja de enviar las existencias al editar** y las
>   muestra sin poder cambiarlas. Sin eso, el 400 haría fallar **toda**
>   edición hecha desde la interfaz. La acción «Ajustar existencias» que
>   las sustituye llega en T-8.7.

#### Inventario (`/api/v1/movimientos-stock`) *(v1.3)*

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/movimientos-stock` | **solo A** | Lista paginada. Filtros `?producto=`, `?tipo=`, `?desde=`, `?hasta=`. | RF-82 |

Sin `POST`, `PUT`, `PATCH` ni `DELETE`: los movimientos solo los crean
los servicios de venta, anulación, alta y ajuste. La ausencia de verbos
de escritura es, igual que en las ventas, la implementación de RNF-25.

#### Configuración (`/api/v1/configuracion/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/configuracion` | A | Umbral vigente, quién lo cambió y cuándo. | RF-52 |
| PATCH | `/configuracion` | A | Modifica el umbral global. | RF-52, RN-CAT-07 |

#### Ventas (`/api/v1/ventas/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/ventas` | A (todas), V (propias) | Lista paginada. Filtros `?desde=`, `?hasta=`, `?estado=`. | RF-21, RF-22 |
| POST | `/ventas` | A, V | Registra y confirma la venta de forma atómica. Admite **`cliente_id`** opcional *(v1.3)*. | RF-15 a RF-20, RF-75, RF-79, RF-80, RF-81 |
| GET | `/ventas/{id}` | A, V (propia) | Detalle con líneas congeladas, incluidos sus meses de garantía, y `tiene_garantia`. | RF-23 |
| POST | `/ventas/{id}/anular` | A (cualquiera), V (propia) | Anula devolviendo existencias y registrando los movimientos. | RF-24, RF-25, RF-27, RF-54, RF-81 |
| GET | `/ventas/{id}/garantia` *(v1.3)* | A (cualquiera), V (propia) | PDF de la garantía. 409 si está anulada o no tiene líneas con garantía. Sin permiso propio: hereda el del detalle. | RF-76, RF-78 |

**`cliente_id` en `POST /ventas`.** Si llega, el servidor carga el
cliente, comprueba que esté **activo** y **copia** su nombre y teléfono
en la venta, ignorando los que viniera en `cliente_nombre` y
`cliente_telefono`: es la misma razón por la que el cliente no envía
precios (RN-VEN-10). Si no llega, la venta es de un cliente ocasional y
se usan los dos campos de texto, como hasta ahora. Un cliente inactivo
responde 409 `CLIENTE_INACTIVO`.

**La garantía hereda la visibilidad de la venta** por el mismo mecanismo
que el informe de servicio: `get_object()` pasa por `get_queryset()`, y
una venta ajena da 404 sin una segunda regla de autorización que
mantener (RN-VEN-16). Los dos rechazos de negocio —anulada, sin líneas
con garantía— son 409 `GARANTIA_NO_DISPONIBLE` con el motivo en
`detalle`.

No existen `PUT`, `PATCH` ni `DELETE` sobre una venta: **la ausencia de
esos verbos es la implementación de RN-VEN-06 y RF-26**. La anulación es
una acción con nombre propio, no un borrado.

<details>
<summary><code>POST /ventas</code> — petición y respuestas</summary>

```jsonc
// → petición
{
  "cliente_nombre": "María Gutiérrez",
  "cliente_telefono": "70012345",
  "items": [
    { "producto_id": 12, "cantidad": 2 },
    { "producto_id": 7,  "cantidad": 1 }
  ]
}

// ← 201
{
  "id": 138,
  "fecha_hora": "2026-09-22T15:42:11-04:00",
  "cliente_nombre": "María Gutiérrez",
  "cliente_telefono": "70012345",
  "estado": "CONFIRMADA",
  "total": "1450.00",
  "usuario": { "id": 4, "nombre_completo": "Juan Pérez" },
  "items": [
    { "producto_id": 12, "producto_nombre": "Teclado mecánico",
      "precio_unitario": "350.00", "cantidad": 2, "subtotal": "700.00" },
    { "producto_id": 7,  "producto_nombre": "Monitor 24\"",
      "precio_unitario": "750.00", "cantidad": 1, "subtotal": "750.00" }
  ]
}

// ← 422  (ningún producto fue descontado: RN-VEN-02)
{
  "codigo": "STOCK_INSUFICIENTE",
  "detalle": "No hay existencias suficientes para confirmar la venta.",
  "errores": { "items": [
    { "producto_id": 12, "nombre": "Teclado mecánico",
      "solicitado": 2, "disponible": 1 }
  ]}
}
```

El cliente **no envía precios**: los toma el servidor del catálogo en el
momento de confirmar (RN-VEN-04). Enviar el precio desde el frontend
permitiría alterarlo desde el navegador.
</details>

#### Servicios (`/api/v1/solicitudes/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/solicitudes` | A (todas), S (propias) | Lista paginada. Filtros `?estado=`, `?tipo=`, `?desde=`, `?hasta=`, `?sin_cotizar=true`. | RF-36, RF-37, RF-60 |
| POST | `/solicitudes` | A, S | Registra la solicitud. Sin monto ni técnico: son del Administrador. | RF-28, RF-29, RF-30, RF-55 |
| GET | `/solicitudes/{id}` | A (todas), S (propias) | Detalle con historial completo. | RF-38, RF-64 |
| POST | `/solicitudes/{id}/cotizar` | **solo A** | Fija el monto y anota el técnico. Única acción del módulo con permiso más estrecho. | RF-56, RF-57, RF-58, RF-59 |
| POST | `/solicitudes/{id}/iniciar` | A, S | Pasa a *En atención*. Sin guardas: el trabajo empieza antes de cotizar. | RF-31 |
| POST | `/solicitudes/{id}/finalizar` | A, S | Cierra con observaciones; 409 si no hay monto cotizado. | RF-32, RF-33, RF-61 |
| POST | `/solicitudes/{id}/cancelar` | A, S | Cancela con motivo. | RF-34 |
| GET | `/solicitudes/{id}/pdf` | A (todas), S (propias) | Informe para el cliente, `application/pdf`. Disponible en cualquier estado. Sin permiso propio: hereda el del detalle. | RF-67 |

> **Por qué el informe no lleva permiso propio.** Usa `get_object()`,
> que pasa por el mismo `get_queryset()` que el detalle. Así la
> visibilidad del PDF **no puede** desalinearse de la de la solicitud:
> quien recibe 404 al abrirla recibe 404 al pedir su informe. Una
> segunda regla de autorización, escrita aparte, sería una regla que
> algún día se quedaría atrás —y el informe lleva el nombre y el
> teléfono de un cliente.

Cada transición es un endpoint con nombre propio en lugar de un
`PATCH {"estado": "..."}`. Así la máquina de estados de RN-SER-02 vive en
el contrato de la API: `finalizar` exige observaciones y un monto **ya
cotizado**, e `iniciar` no exige nada, cosa que un `PATCH` genérico no
expresa. *(Corregido en la v1.3 de este plan: decía que `iniciar` podía
exigir técnico, lo que dejó de ser cierto con la v1.2 de la
especificación.)*

<details>
<summary><code>POST /solicitudes/{id}/finalizar</code> — petición y respuestas</summary>

*(Corregido en la v1.3 de este plan. El ejemplo anterior enviaba el monto
al finalizar, que era el comportamiento de la v1.1: desde la v1.2 el
monto lo fija antes el Administrador con `cotizar`, y `finalizar` solo
recibe las observaciones.)*

```jsonc
// → petición
{ "observaciones": "Se reemplazó la fuente de poder y se limpió el equipo." }

// ← 200
{
  "id": 91, "estado": "FINALIZADA",
  "fecha_cierre": "2026-09-22T17:10:03-04:00",
  "monto_cobrado": "250.00",          // el que fijó el Administrador al cotizar
  "cerrada_por": { "id": 6, "nombre_completo": "Ana Rojas" }
}

// ← 409   la solicitud aún no está cotizada (RN-SER-13)
{ "codigo": "MONTO_REQUERIDO",
  "detalle": "No se puede finalizar un servicio sin monto. El administrador
              debe cotizarlo primero." }

// ← 409   la solicitud no está En atención
{ "codigo": "TRANSICION_INVALIDA",
  "detalle": "La solicitud no puede pasar a ese estado." }
```
</details>

#### Usuarios (`/api/v1/usuarios/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/usuarios` | A | Lista con rol y estado. `?buscar=`, `?rol=`, `?activo=`. | RF-43 |
| POST | `/usuarios` | A | Crea una cuenta con su rol. | RF-39, RF-47 |
| GET | `/usuarios/{id}` | A | Detalle. | RF-43 |
| PATCH | `/usuarios/{id}` | A | Edita datos y/o rol. | RF-40, RF-44, RF-46 |
| POST | `/usuarios/{id}/bloquear` | A | Bloquea la cuenta. | RF-41, RF-45, RF-46 |
| POST | `/usuarios/{id}/desbloquear` | A | Restituye el acceso. | RF-41 |
| POST | `/usuarios/{id}/restablecer-password` | A | Asigna una contraseña nueva. | RF-42 |

No hay `DELETE`: RN-USU-05 lo prohíbe, y su ausencia en el contrato lo
hace explícito.

#### Panel (`/api/v1/panel/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/panel/resumen` | A | Todos los indicadores del día en una sola respuesta. | RF-48 a RF-51, RF-65, RF-66 |

<details>
<summary><code>GET /panel/resumen</code> — respuesta</summary>

```jsonc
{
  "fecha": "2026-09-22",
  "ventas_dia":     { "cantidad": 12, "importe": "8450.00" },
  "servicios_dia":  { "cantidad": 5,  "importe": "1300.00" },
  "ingreso_total":  { "importe": "9750.00",
                      "de_ventas": "8450.00", "de_servicios": "1300.00" },
  "servicios_pendientes": { "total": 9, "sin_cotizar": 3,
                            "registradas": 4, "en_atencion": 5 },
  "stock_bajo": {
    "umbral": 5,
    "cantidad": 3,
    "productos": [
      { "id": 12, "nombre": "Teclado mecánico", "stock": 1 },
      { "id": 30, "nombre": "Cable HDMI 2m",    "stock": 4 }
    ]
  }
}
```

`ingreso_total` **siempre** viaja desglosado por origen: RN-IND-05 exige
que nunca se presente un total que impida distinguir ventas de servicios,
y la forma más segura de garantizarlo es que la API no ofrezca la cifra
agregada por separado.
</details>

> **Desde la v1.3 este endpoint es un caso particular de `/reportes`.**
> Por dentro, `panel/resumen` calcula sus cifras de ventas, servicios e
> ingreso con la misma función que el reporte, para el rango
> `[hoy, hoy]`. La respuesta conserva exactamente su forma —ninguna
> prueba ni pantalla existente cambia—, pero ya no hay dos consultas que
> puedan dar números distintos para el mismo día (RN-REP-08).

#### Reportes (`/api/v1/reportes`) *(v1.3)*

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/reportes?desde=&hasta=` | **solo A** | Reporte del rango en JSON. 400 si falta una fecha o si `desde > hasta`. | RF-90 a RF-94 |
| GET | `/reportes/pdf?desde=&hasta=` | **solo A** | El mismo reporte, en PDF con membrete. | RF-95 |
| GET | `/reportes/xlsx?desde=&hasta=` | **solo A** | El mismo reporte, en Excel. | RF-96 |

Los atajos —hoy, esta semana, este mes— **los resuelve el frontend** en
fechas concretas antes de llamar: el servidor solo conoce rangos. Así hay
una única forma de pedir un reporte, y un atajo no es más que una forma
cómoda de rellenar dos fechas.

<details>
<summary><code>GET /reportes?desde=2026-10-01&hasta=2026-10-07</code> — respuesta</summary>

```jsonc
{
  "desde": "2026-10-01", "hasta": "2026-10-07",
  "ventas":    { "cantidad": 41, "importe": "28450.00" },
  "servicios": { "cantidad": 9,  "importe": "2150.00" },
  "ingreso_total": { "importe": "30600.00",
                     "de_ventas": "28450.00", "de_servicios": "2150.00" },
  "productos_mas_vendidos": [
    { "producto_id": 12, "codigo": "2000000000121", "nombre": "Teclado mecánico",
      "unidades": 14, "importe": "4900.00" }
  ],
  "ventas_por_usuario": [
    { "usuario_id": 4, "nombre_completo": "Juan Pérez",
      "cantidad": 29, "importe": "19800.00" }
  ],
  "servicios_por_estado": { "REGISTRADA": 3, "EN_ATENCION": 2,
                            "FINALIZADA": 9, "CANCELADA": 1 }
}
```

**`servicios_por_estado` incluye las canceladas** (PA-08) y solo trae
recuentos, nunca importes: las canceladas aparecen para que se vea
cuántas se perdieron, sin riesgo de que alguien las sume a un ingreso.
Los cuatro estados viajan **siempre**, aunque alguno valga cero, para que
la pantalla, el PDF y el Excel muestren las mismas filas.

**`productos_mas_vendidos` muestra el nombre actual del producto**, no el
congelado. Es un agregado de muchas ventas en las que el nombre pudo
cambiar; lo que identifica a la fila es el producto, y el código —que no
cambia nunca— lo deja sin ambigüedad.
</details>

**Una sola función calcula el reporte, y las tres salidas la usan.** La
vista JSON, el PDF y el Excel llaman a `panel.reportes.calcular(desde,
hasta)` y solo difieren en cómo **presentan** el resultado. No hay
consultas propias en los exportadores: es lo que hace que RN-REP-07 se
cumpla por construcción y no por cuidado.

#### Clientes (`/api/v1/clientes`) *(v1.3)*

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/clientes` | A, V | Lista paginada **sin carnet**. `?buscar=` (nombre o teléfono que contienen el texto, o carnet exacto), `?activo=`. | RF-86, RF-89 |
| POST | `/clientes` | A, V | Registra un cliente. 409 `CARNET_DUPLICADO` si el carnet ya existe. | RF-84, RF-88 |
| GET | `/clientes/{id}` | A, V | Detalle **con carnet**. Es la única respuesta de toda la API que lo incluye. | RF-89 |
| PATCH | `/clientes/{id}` | A, V | Edita sus datos. | RF-85 |
| POST | `/clientes/{id}/desactivar` | **solo A** | Desactiva. | RF-87 |
| POST | `/clientes/{id}/reactivar` | **solo A** | Reactiva. | RF-87 |

No hay `DELETE`, por RN-CLI-03, igual que en usuarios.

**Dos serializers, no uno con campos condicionales.**
`ClienteResumenSerializer` —lista y selector de la venta— no declara el
carnet; `ClienteDetalleSerializer` sí. Un único serializer que lo quitara
«según la acción» dependería de que cada vista nueva recordara
quitarlo; con dos, olvidarse es imposible (RNF-26).

**La búsqueda por carnet es exacta, la de nombre y teléfono no.** Buscar
por fragmentos de carnet permitiría enumerar los números registrados
probando prefijos; con coincidencia exacta, solo encuentra a un cliente
quien ya conoce su número.

---

## 5. Seguridad y autorización

### 5.1 Autorización en el servidor

Toda vista declara explícitamente sus permisos. La configuración global
de DRF fija `IsAuthenticated` por defecto (RNF-01), de modo que **olvidar
declarar un permiso deja el endpoint cerrado, no abierto**.

Clases en `core/permissions.py`:

| Clase | Concede acceso a | Usada en |
|---|---|---|
| `EsAdministrador` | Solo rol ADMINISTRADOR. | Catálogo (escritura), usuarios, configuración, panel. |
| `PuedeVender` | ADMINISTRADOR o VENTAS. | Ventas, lectura del catálogo. |
| `PuedeAtenderServicios` | ADMINISTRADOR o SERVICIOS. | Solicitudes. |
| `EsDuenoDeLaVentaOAdmin` | Nivel de objeto: autor de la venta, o admin. | `GET/anular` de una venta (RF-27), y su garantía *(v1.3)*. |
| `PuedeGestionarClientes` *(v1.3)* | ADMINISTRADOR o VENTAS. | Clientes, salvo desactivar y reactivar, que usan `EsAdministrador`. |

**Los clientes no se filtran por usuario.** A diferencia de
`VentaViewSet`, `ClienteViewSet.get_queryset()` **no** restringe por
quién registró al cliente: el directorio es común para el Administrador
y el Encargado de Ventas (`spec.md` §4.4). Que el Encargado de Ventas vea
a un cliente no le da acceso a las ventas que otros le hicieron, porque
esas siguen pasando por el filtro de `VentaViewSet`.

**Filtrado de consultas por rol.** No basta con permitir o denegar el
endpoint: `VentaViewSet.get_queryset()` y
`SolicitudViewSet.get_queryset()` restringen la lista al usuario
autenticado cuando su rol no es Administrador. Un encargado nunca
recibe, ni siquiera paginadas, las filas de otro.

> *(La v1.1 de este plan describía aquí una asimetría entre ambos
> módulos: servicios compartido, ventas privado. La revisión de PA-04
> en `spec.md` v1.2 la elimino: los dos se comportan igual, y el código
> resulta más simple por partida doble.)*

### 5.2 Las protecciones de la cuenta de administrador

RN-USU-02, RN-USU-03 y RN-USU-04 se implementan en
`usuarios/services.py`, **no** en el serializer, porque RN-USU-04 exige
consultar el estado global del sistema:

```python
def _validar_queda_un_administrador(usuario, *, nuevo_rol=None, bloqueando=False):
    """Rechaza toda operación que dejaría el sistema sin administradores activos."""
```

La comprobación se hace dentro de la misma transacción que el cambio y
con `select_for_update()` sobre las cuentas de administrador activas. Sin
ese bloqueo, dos administradores que se bloquean mutuamente **a la vez**
podrían pasar ambos la validación y dejar el sistema sin acceso: es el
mismo problema de concurrencia que el del stock, con una consecuencia
peor, porque nadie podría repararlo desde la interfaz.

### 5.3 Contraseñas

- Hash con el `PBKDF2` por defecto de Django (RNF-03). Se documenta
  Argon2 como alternativa preferible si se instala `argon2-cffi`.
- Validadores activos (RNF-04): longitud mínima de 8, no puede ser
  demasiado común, no puede ser solo numérica, no puede parecerse al
  nombre de usuario.
- El campo `password` **nunca** aparece en ninguna respuesta de la API:
  los serializers lo declaran `write_only`.

### 5.4 Otras medidas

| Medida | Configuración |
|---|---|
| CORS | `django-cors-headers` con lista blanca explícita del origen del frontend. Nunca `CORS_ALLOW_ALL_ORIGINS`. |
| Secretos | `django-environ`; `SECRET_KEY`, credenciales de base y `DEBUG` salen de variables de entorno. El `.env` **no** se versiona. |
| Producción | **Fuera de alcance (PT-01).** El sistema se ejecuta en entorno de desarrollo. Se documenta en el `README` lo que haría falta para un despliegue real (`DEBUG=False`, `ALLOWED_HOSTS` explícito, `SECURE_SSL_REDIRECT`, cookies `Secure`, servidor WSGI, archivos estáticos), sin implementarlo. |
| Subida de imágenes | Validación de extensión y tamaño máximo (2 MB) en el serializer; `Pillow` verifica que el archivo sea realmente una imagen. |
| Limitación de intentos | `throttling` de DRF sobre `/auth/login` (`5/min` por IP) para frenar el ensayo de contraseñas. |

---

## 6. Concurrencia e integridad (RNF-08 a RNF-10)

Este es el punto técnicamente más delicado del sistema y el que exige una
decisión explícita.

### 6.1 El problema

Dos encargados venden el último teclado en el mismo instante. Sin
protección, ambas peticiones leen `stock = 1`, ambas validan que alcanza,
y ambas descuentan: el inventario queda en `-1` y se vendió dos veces la
misma unidad.

### 6.2 Por qué `F()` por sí solo no basta

Un `update(stock=F('stock') - cantidad)` es atómico a nivel de sentencia
y evita la condición de carrera del *read-modify-write*, pero **no valida
nada**: llevaría el stock a negativo sin protestar. Es necesario, pero
insuficiente.

### 6.3 Solución adoptada: tres capas

```python
# ventas/services.py
@transaction.atomic
def registrar_venta(*, usuario, cliente_nombre, cliente_telefono, items):
    # 1) Bloqueo de filas SIEMPRE en orden de pk ascendente → sin interbloqueos
    ids = sorted({item["producto_id"] for item in items})
    productos = {
        p.id: p
        for p in Producto.objects.select_for_update().filter(id__in=ids, activo=True)
    }

    # 2) Validación con las filas ya bloqueadas: nadie puede cambiarlas
    faltantes = [...]
    if faltantes:
        raise StockInsuficiente(faltantes)      # → 422, nada se ha escrito

    # 3) Descuento con F() + congelado de precios en el detalle
    ...
```

1. **`select_for_update()` con orden determinista por clave primaria.**
   Bloquea las filas de producto hasta el final de la transacción; una
   segunda venta simultánea espera y, al pasar, lee el stock ya
   actualizado. Ordenar siempre por `pk` ascendente evita el interbloqueo
   clásico de dos transacciones que toman los mismos productos en orden
   inverso.
2. **`transaction.atomic()`** garantiza RNF-09: o se guardan la venta, sus
   líneas y el descuento completos, o no queda nada. La excepción
   `StockInsuficiente` revierte todo, lo que implementa literalmente el
   «todo o nada» de RN-VEN-02.
3. **`CHECK (stock >= 0)` en la base** como red de seguridad final: si un
   cambio futuro rompiera la validación, la base rechaza la operación en
   lugar de corromper el inventario.

La anulación (`anular_venta`) aplica exactamente el mismo patrón en
sentido inverso, cumpliendo RNF-10.

### 6.4 Cómo se demuestra

RNF-08 no se da por buena porque el código «parezca» correcto. Se prueba
con un test que lanza **N hilos concurrentes** vendiendo el mismo
producto con stock limitado contra PostgreSQL real
(`TransactionTestCase`, no `TestCase`, porque este último envuelve cada
prueba en una transacción y enmascararía el bloqueo). Se verifica que:

- el número de ventas confirmadas es exactamente el stock disponible,
- el stock final es exactamente `0`, nunca negativo,
- las peticiones sobrantes reciben `422`.

Este test es el **criterio de aceptación ejecutable de RNF-08** y una de
las evidencias más defendibles del proyecto de grado.

### 6.5 El libro de movimientos dentro del mismo patrón *(v1.3)*

RNF-24 no pide un mecanismo nuevo: pide que el movimiento **viaje dentro**
del que ya existe. Las tres capas de §6.3 se mantienen y el movimiento se
escribe en el paso 3, con la fila todavía bloqueada:

```python
# ventas/services.py — paso 3 de registrar_venta(), ampliado
for pid in ids:                                   # mismo orden ascendente de pk
    producto = productos[pid]                     # fila bloqueada en el paso 1
    cantidad = cantidades[pid]
    Producto.objects.filter(pk=pid).update(stock=F("stock") - cantidad)
    registrar_movimiento(                         # inventario/services.py
        producto=producto,
        tipo=TipoMovimiento.VENTA,
        cantidad=-cantidad,
        stock_resultante=producto.stock - cantidad,   # ← exacto: ver abajo
        usuario=usuario,
        venta=venta,
    )
```

**Por qué `stock_resultante` puede calcularse en Python.** Normalmente
leer el stock, restarle algo y escribirlo es exactamente la carrera de
§6.1. Aquí no lo es, porque `producto.stock` se leyó **con la fila ya
bloqueada** por `select_for_update()`: ninguna otra transacción puede
modificarla hasta que esta termine. El valor leído es el vigente, y lo
seguirá siendo hasta el `COMMIT`. El `F()` se conserva igualmente para la
escritura —es la forma idiomática y no cuesta nada—, pero la cifra del
movimiento es exacta sin necesidad de releer la fila.

**Qué garantiza `transaction.atomic()` aquí.** Si `registrar_movimiento`
falla —por ejemplo, por un `CHECK` de §3.3—, la excepción revierte
también el descuento de stock y la venta. Y si el descuento falla, el
movimiento nunca llega a escribirse. No existe un estado intermedio
observable: es RN-MOV-01 implementada por la transacción, no por una
comprobación posterior.

#### El ajuste manual deja de ser un `PATCH`

Hoy las existencias se cambian con el `PATCH` genérico del producto. Eso
**escribe un valor absoluto leído antes, sin bloquear la fila**. Sin
libro de movimientos era tolerable: el Administrador fija «quedan 15» y
quedan 15. **Con libro de movimientos deja de serlo**, porque el
movimiento necesita la diferencia, y la diferencia calculada contra un
valor viejo omite cualquier venta ocurrida en medio:

```
  t0  Admin abre el formulario: stock = 10
  t1  Se vende 1 unidad           stock = 9   movimiento −1
  t2  Admin guarda «12» con PATCH stock = 12  movimiento +2  (12 − 10)
                                  ─────────
                                  suma de movimientos = 10 + (−1) + 2 = 11 ≠ 12
```

El libro queda descuadrado y nadie hizo nada mal. Por eso el ajuste pasa
a `inventario.services.ajustar_existencias()`:

```python
@transaction.atomic
def ajustar_existencias(*, producto_id, cantidad_real, motivo, usuario):
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    diferencia = cantidad_real - producto.stock    # contra el valor bloqueado
    if diferencia == 0:
        raise AjusteSinDiferencia()                # RN-MOV-05
    Producto.objects.filter(pk=producto_id).update(stock=cantidad_real)
    registrar_movimiento(producto=producto, tipo=TipoMovimiento.AJUSTE,
                         cantidad=diferencia, stock_resultante=cantidad_real,
                         usuario=usuario, motivo=motivo)
```

Con la fila bloqueada, la venta de `t1` espera a que termine el ajuste o
el ajuste espera a que termine la venta. En los dos órdenes el libro
cuadra. La interfaz sigue mostrando la diferencia antes de confirmar
(CU-CAT-07), pero es **orientativa**: la que se registra es la que
calcula el servidor con la fila bloqueada.

#### Cómo se demuestra

La prueba de §6.4 se **amplía**, no se sustituye. Además de lo que ya
verifica, comprueba que:

- el número de movimientos `VENTA` es exactamente el número de ventas
  confirmadas, y las peticiones rechazadas con 422 **no dejaron ningún
  movimiento**;
- `SUM(cantidad)` de los movimientos del producto es igual a su stock
  final, y el `stock_resultante` del último movimiento también;
- los `stock_resultante` de los movimientos `VENTA`, ordenados por
  fecha, forman una secuencia **estrictamente decreciente sin huecos**:
  si dos ventas hubieran leído el mismo stock, aparecería un valor
  repetido.

Y una prueba nueva lanza **ajustes y ventas concurrentes** sobre el mismo
producto, verificando que el libro cuadra al final en cualquier
intercalado.

El invariante del libro —`SUM(cantidad) = stock` para **todo**
producto— se convierte además en una **prueba guardián** que recorre la
base de pruebas tras cada escenario, del mismo tipo que la matriz de
permisos: si algún camino futuro cambia el stock sin pasar por
`registrar_movimiento`, falla.

---

## 7. Diseño del frontend

### 7.1 Estructura

```
frontend/src/
├── main.js
├── App.vue
├── router/index.js          # rutas + guards por rol (RF-06)
├── stores/
│   ├── auth.js              # sesión, rol, permisos derivados
│   └── ui.js                # notificaciones, estado de carga
├── api/
│   ├── http.js              # instancia Axios + interceptores
│   ├── auth.js  catalogo.js  ventas.js  servicios.js
│   ├── usuarios.js  panel.js  configuracion.js
├── composables/
│   ├── usePermisos.js       # ¿puede el usuario actual hacer X?
│   ├── useListadoPaginado.js
│   └── useErroresApi.js     # mapea `errores` de la API a campos
├── components/              # reutilizables: tablas, formularios, diálogos
├── views/
│   ├── auth/  catalogo/  ventas/  servicios/  usuarios/  panel/
└── assets/
```

### 7.2 Comunicación con la API

Una única instancia de Axios (`api/http.js`) concentra tres
comportamientos, de modo que ninguna vista se ocupe de ellos:

1. **Interceptor de petición:** añade `Authorization: Bearer …` desde el
   store de sesión.
2. **Interceptor de respuesta 401:** intenta **una sola vez** renovar el
   token con el `refresh`; si falla, cierra la sesión y redirige al
   inicio. Las peticiones que llegaron durante la renovación se encolan y
   se reintentan al terminar, para no disparar varios refrescos a la vez.
3. **Interceptor de error general:** normaliza el cuerpo de error al
   formato de §4.3 y muestra un aviso para los errores no ligados a un
   campo (403, 409, 5xx).

### 7.3 Rutas y control de acceso en la interfaz

`router/index.js` declara en cada ruta los roles admitidos
(`meta: { roles: ['ADMINISTRADOR', 'VENTAS'] }`) y un *guard* global
redirige al usuario sin permiso. El menú lateral se construye a partir
de la misma definición, de modo que **lo que se muestra y lo que se
permite navegar nunca puedan divergir**.

> Se repite aquí lo que dice RN-ACC-04: esto es **usabilidad**. Un
> usuario que escriba la URL a mano igual recibirá 403 del servidor. La
> seguridad está en el backend; el router solo evita mostrar puertas que
> no se pueden abrir.

### 7.4 Pantallas previstas

| Módulo | Vistas |
|---|---|
| Autenticación | Inicio de sesión; cambio de contraseña propia. |
| ~~Inicio~~ | ~~Pantalla de entrada por rol: saludo, rol, fecha e ilustración. Sin datos y sin navegación (ver §7.7).~~ **Retirada el 2026-10-10 (v1.5 de este plan):** cada rol entra directamente a su espacio de trabajo (§7.12). |
| Catálogo | Lista de productos con búsqueda, filtro y marca de stock bajo; formulario de producto; gestión de categorías. |
| Ventas | Registro de venta (buscador de productos, carrito interno de la pantalla, total en vivo); historial con filtros; detalle con líneas congeladas; diálogo de anulación con motivo. |
| Servicios | Lista con filtros de estado y tipo, más un acceso rápido a «pendientes de cotizar» que solo ve el Administrador (RF-60); formulario de registro con dirección condicional al tipo, sin monto ni técnico; detalle con línea de tiempo del historial; diálogos de cotizar (monto y técnico, solo Administrador), finalizar (observaciones) y cancelar (motivo), más la acción directa de iniciar. Botón de descarga del informe en PDF (RF-67). |
| Usuarios | Lista con rol y estado; formulario de alta y edición; acciones de bloqueo y restablecimiento de contraseña. |
| Panel | Tarjetas de indicadores, desglose de ingresos y tabla de productos con stock bajo, cada una enlazando a su módulo (RF-51). |
| Configuración | Umbral global de existencias bajas. |
| Catálogo *(v1.3)* | Columna de código en la lista y búsqueda por código. Detalle de producto con su código de barras, botón de imprimir etiqueta y —solo Administrador— historial de movimientos y diálogo «Ajustar existencias» (cantidad real, motivo, diferencia orientativa y confirmación). El formulario de edición deja de ofrecer las existencias e incorpora los meses de garantía. |
| Inventario *(v1.3)* | Pantalla de movimientos de stock, solo Administrador: filtros por producto, tipo y rango de fechas, tabla paginada. |
| Ventas *(v1.3)* | En el registro: selector de cliente (buscar, nuevo en un diálogo, u ocasional) y campo de código que acepta el lector. Tras confirmar, y en el detalle de la venta, botón «Garantía» si la venta tiene alguna línea con garantía. |
| Clientes *(v1.3)* | Lista paginada con búsqueda y filtro de activos, sin carnet; formulario de alta y edición; detalle con carnet; desactivar y reactivar con confirmación, solo Administrador. |
| Reportes *(v1.3)* | Selector de rango con atajos; tarjetas de ventas, servicios e ingreso desglosado; tablas de productos más vendidos, ventas por usuario y servicios por estado; botones de exportar a PDF y a Excel. |

> **Nota sobre el «carrito» de la pantalla de ventas:** es una lista
> temporal en el estado del componente mientras se arma la venta. No es
> un carrito de comercio electrónico, no se persiste y no existe fuera
> de esa pantalla. `spec.md` §2.2 excluye el carrito de compras y esto no
> lo contradice.

### 7.5 Interfaz adaptable (RNF-12)

Se usa la rejilla adaptable de PrimeVue con tres puntos de corte
(escritorio, portátil, tableta). Las tablas de datos cambian a
presentación apilada en pantallas estrechas. No se diseña para teléfono
móvil: `spec.md` §2.2 excluye la aplicación móvil y el personal trabaja
en mostrador.


**Cabecera y menú fijos** *(v1.5, 2026-10-10)*. Al desplazarse, la
cabecera y el menú lateral quedan en su sitio y solo se mueve el
contenido. Se hace con `position: sticky`, no con un contenedor de
scroll propio: la página sigue desplazándose con normalidad, y así la
impresión, los PDF y la etiqueta no cambian (además, `@media print` las
devuelve al flujo normal). La cabecera tiene una altura fija
(`--pcs-alto-cabecera`) y el menú se pega justo debajo, con el alto de
la ventana y **su propio scroll** si no cabe. Su `z-index` (100) queda
por debajo de los diálogos, menús y desplegables de PrimeVue (1000 y
1100), que siguen encima de todo. En tableta, la barra de menú
horizontal también queda fija bajo la cabecera.
### 7.6 Paleta e identidad visual

Decidido el 30/09/2026, después de las primeras sesiones de uso: la
paleta verde y blanca de arranque no representaba a la empresa. Se
sustituye por **cromo oscuro sobre área de trabajo clara**.

No se le asigna un RF. Un cambio de paleta no altera ningún
comportamiento del sistema: ninguna regla de negocio, ningún permiso y
ningún dato dependen de él. Se registra aquí, que es donde viven las
decisiones de presentación.

**Dónde vive.** Dos archivos y nada más:

| Archivo | Qué define |
|---|---|
| `frontend/src/main.js` | `definePreset(Aura, …)` con las rampas `primary` y `surface`. Es el sitio único. |
| `frontend/src/assets/main.css` | Fondo del `body` y los tokens propios `--pcs-cromo-*` y `--pcs-degradado-*` |

Los `var(--token, #hex)` repartidos por los componentes son respaldos
inertes —el token siempre resuelve—, pero se actualizaron igualmente
para que no asome el verde anterior durante la carga inicial.

**Rampas.** `primary`: violeta `#f5f3ff` … `#2e1065`, con
`primary.color = {primary.600}` (`#7c3aed`). `surface`: grises fríos
`#ffffff` … `#09090b`.

**El color sigue siendo información, no decoración.** Los estados
semánticos —éxito, aviso, peligro, información— **conservan sus colores
propios** y no pasan a morado. Las existencias bajas en ámbar, una
venta anulada en rojo o una solicitud sin cotizar resaltada son señales
que el personal lee de un vistazo; teñirlas del color de la marca las
borraría. El morado queda para identidad, navegación, botones primarios
y estados de interacción (`#6d28d9` al pasar el ratón, anillo de foco
`#a78bfa`).

**Contrastes verificados (RNF-14, WCAG AA).**

| Combinación | Ratio | |
|---|---|---|
| Texto `#18181b` sobre blanco | 17,4:1 | ✅ |
| Texto atenuado `#71717a` sobre blanco | 4,8:1 | ✅ |
| Botón y menú activo `#7c3aed` + blanco | 5,3:1 | ✅ |
| Barra lateral `#09090b` + texto `#f4f4f5` | 18,1:1 | ✅ |
| Barra lateral + opción inactiva `#a1a1aa` | 7,4:1 | ✅ |
| `#8b5cf6` sobre blanco | 3,9:1 | ⚠️ no se usa como color de texto |

Verificado en navegador con los tres puntos de corte de §7.5 (1440,
1024 y 768 px).

### 7.7 Pantalla de Inicio por rol *(retirada el 2026-10-10)*

> **Retirada en la v1.5 de este plan** (`spec.md` v1.4.1). Al usar el
> sistema, la pantalla se percibió como un paso de más: nadie trabajaba
> en ella. Cada rol entra ahora directamente a su espacio de trabajo
> (§7.12). Se conserva el texto como registro de la decisión de
> entonces; nada de lo que sigue está ya en el código.

Decidido el 30/09/2026, junto con la paleta. Tampoco lleva RF, y por
el mismo motivo: no muestra ningún dato ni cambia ningún
comportamiento. Es presentación.

**El problema.** La versión de arranque construía sus tarjetas de
acceso con `menuPara()`, la misma función que levanta la barra
lateral, de modo que eran los mismos enlaces dos veces. Y como el
número de tarjetas depende de los módulos del rol, al Encargado de
Servicios —que tiene uno solo— le quedaba una tarjeta suelta en una
pantalla en blanco.

**La decisión: identidad, no resumen.** Se evaluó sustituir las
tarjetas por un resumen con cifras reales por rol. Se descartó: exigía
un endpoint nuevo y dejaba una segunda vista de los mismos números que
ya da el panel, que habría que mantener sincronizada. La pantalla
queda **puramente decorativa**: saluda, nombra el rol, da la fecha y
explica en una frase de qué se ocupa.

Lo que se pierde está asumido: quien quiera saber qué tiene pendiente
entra a su módulo, que es donde la lista está completa y al día.

| Rol | Icono | Degradado |
|---|---|---|
| Administrador | `pi-shield` | `--pcs-degradado-admin` |
| Encargado de Ventas | `pi-shopping-cart` | `--pcs-degradado-ventas` |
| Encargado de Servicios | `pi-wrench` | `--pcs-degradado-servicios` |

La identidad de los tres vive en un único objeto plano,
`config/identidadRol.js`, porque el encabezado y la ilustración
necesitan los mismos valores y duplicarlos garantizaba que acabaran
divergiendo.

**La ilustración** es un SVG en línea —sin dependencias ni archivos de
imagen nuevos—, dibujado con los tokens del tema. El motivo son trazos
de circuito, los mismos del logo, para que la pantalla hable el
lenguaje visual de la marca en lugar de traer un dibujo genérico.

**Accesibilidad.** El SVG y el icono del encabezado son decoración:
llevan `aria-hidden` y el SVG no lleva `<title>`, porque anunciarlos
solo alargaría el recorrido de un lector de pantalla sin informar de
nada que la frase de al lado no diga ya. El saludo sigue siendo un
`<h1>` real: la estructura del documento no depende de la decoración.

**Queda cubierto por prueba** que el Inicio no contiene ningún
elemento pulsable. Es lo que impide que la duplicación del menú
vuelva a colarse más adelante.

### 7.12 Espacio de trabajo por rol *(v1.5, 2026-10-10)*

Sustituye a la pantalla de Inicio (§7.7, retirada). Cada rol tiene un
**espacio de trabajo**, la pantalla en la que pasa la jornada:

| Rol | Espacio de trabajo | Ruta |
|---|---|---|
| Administrador | Panel de indicadores | `panel` |
| Encargado de Ventas | Registrar venta | `venta-nueva` |
| Encargado de Servicios | Lista de servicios | `servicios` |

- **Un solo lugar lo decide**: `espacioDeTrabajo(rol)` en
  `router/index.js`, junto a las rutas. Lo usan el destino tras iniciar
  sesión, la ruta `/`, el logo de la cabecera, la redirección de quien
  ya tiene sesión y abre el login, y el botón de «Sin permiso».
- **Sin bucles ni pantalla en blanco.** Si el login trae un destino
  (`?redirigir=`) que el rol no puede abrir, se ignora y se va al
  espacio de trabajo. «Sin permiso» se abre para cualquier sesión, de
  modo que un rol inesperado no rebota entre dos redirecciones.
- **Es navegación, no seguridad** (RN-ACC-04): el servidor sigue
  respondiendo 403 a lo que el rol no puede hacer.

### 7.13 Nombres que abren un detalle *(v1.5, 2026-10-10)*

En las listas, el nombre que abre un detalle se lee como el resto del
texto de la tabla, no como un enlace del navegador (morado y
subrayado). Una clase común, `.enlace-de-tabla` en `main.css`: hereda el
color, sin subrayado —también visitado—, con cursor de mano, y con el
**indicador de foco de teclado** conservado y marcado. Se aplica al
producto en el Catálogo, al cliente en Clientes y al producto en la
tabla de Movimientos, que eran los únicos nombres con enlace en una
lista. Los accesos del Panel no son nombres y tienen su propio estilo.

### 7.8 Informe en PDF (RF-67, RF-68)

**Se genera en el servidor.** Se evaluó generarlo en el navegador con
jsPDF y se descartó por dos razones, la segunda de más peso:

1. La plantilla queda en un solo sitio y en HTML, en vez de maquetada
   a mano dentro de JavaScript.
2. **La fecha de generación y el nombre de quien genera el informe los
   pone el servidor**, que ya sabe quién está autenticado. Generado en
   el cliente, ese pie sería un dato que el propio cliente escribe.

`html2pdf.js` quedó descartado de entrada: produce una captura de
pantalla, no texto. Un PDF de imagen no se puede buscar, ni copiar, ni
leer con un lector de pantalla. Hay una prueba que extrae el texto del
PDF generado para dejarlo comprobado y no solo dicho.

**Librería: `xhtml2pdf`.** Python puro, se instala con `pip` sin
dependencias nativas. Se descartó WeasyPrint: en Windows exige GTK
instalado aparte, y el entorno de desarrollo de este proyecto es
Windows.

La plantilla se escribe con tablas y estilos en línea a propósito:
`xhtml2pdf` no implementa *flexbox* ni *grid*.

**Dónde se guarda (RF-68).** Una página web no puede elegir la carpeta
por su cuenta; eso lo decide el navegador. Lo que sí puede es **abrir
el cuadro de guardado nativo** con `showSaveFilePicker()`, y entonces
es el usuario quien elige Descargas, Documentos o donde prefiera, con
el nombre ya propuesto (`informe-servicio-12.pdf`). En los navegadores
que no lo implementan —Firefox, Safari— se descarga a la carpeta
predeterminada; de ahí el «cuando el navegador lo permita» del
requerimiento. Vive en `composables/useDescarga.js`, reutilizable el
día que haya un comprobante de venta.

Cerrar el cuadro de guardado **no** se trata como error: es una
decisión del usuario y no produce ningún mensaje.

**Un detalle del cliente HTTP.** La descarga pide
`responseType: 'blob'`, y axios aplica ese tipo también al cuerpo de
los errores. Sin desempaquetarlo, un 404 llegaría como blob,
`cuerpo.codigo` sería `undefined` y el mensaje se degradaría a un
«Ocurrió un error inesperado». Se desempaqueta en el interceptor de
`api/http.js`, antes de normalizar, porque leer un blob es asíncrono y
hacerlo dentro de `normalizarError()` obligaría a volver asíncrona una
función que usan todas las vistas.

### 7.9 Lector de código de barras y etiquetas *(v1.3)*

**El lector no necesita código especial.** Un lector en modo teclado
(SUP-07) escribe los trece dígitos y pulsa Intro, exactamente como lo
haría una persona. Por eso la pantalla de venta tiene un **campo de
código** normal que, al recibir Intro:

1. si el campo no está vacío, consulta
   `GET /productos?codigo=…&activo=true`, que busca en el código interno
   y en el de fábrica. *No* se exige que sean 13 dígitos: un código de
   fábrica puede ser un UPC de 12, un EAN-8 o un código alfanumérico
   (PA-07);
2. si hay coincidencia con existencias, agrega el producto —o suma una
   unidad— y **vacía el campo, que conserva el foco**, listo para la
   siguiente lectura;
3. si no, muestra el aviso junto al campo y selecciona el texto, para
   que la lectura siguiente lo sustituya.

Se descartó escuchar las teclas en toda la página para «detectar» al
lector por la velocidad de escritura: es frágil —depende del modelo de
lector y de la carga del equipo— y captura teclas destinadas a otros
campos. Un campo con foco es predecible y funciona igual con el teclado.

**El código de barras se dibuja en el navegador** con `JsBarcode`, en
formato EAN-13 y como **SVG**. Un SVG imprime nítido a cualquier tamaño,
que es lo que un lector necesita para leer la etiqueta impresa. Se
descartó generarlo en el servidor: `reportlab` sabe dibujarlo, pero
exportarlo a imagen exige `renderPM`, que en Windows depende de
bibliotecas nativas —el mismo motivo por el que se descartó WeasyPrint
en §7.8—.

**La etiqueta se imprime con la impresión del navegador** y una hoja de
estilos `@media print` que oculta todo salvo la etiqueta: código de
barras, cifras y nombre. No hace falta generar un PDF para algo que se
imprime y se pega.

### 7.10 Garantía en PDF: misma plantilla, mismo mecanismo *(v1.3)*

La garantía **no** trae una segunda forma de generar documentos:

- **Plantilla base común.** El membrete, la línea morada y el pie de
  página del informe de servicio pasan a
  `core/templates/pdf/base.html`. El informe de servicio, la garantía y
  el reporte la extienden con `{% extends %}` y solo rellenan su cuerpo.
  El informe de servicio queda **idéntico** —sus pruebas no cambian—,
  pero ya no es dueño de un membrete que ahora comparten tres
  documentos.
- **Mismo generador.** `core/pdf.py` (`render_a_pdf`,
  `imagen_incrustada`) se usa tal cual.
- **Misma descarga.** En el frontend, `useDescarga.js` —con su cuadro de
  guardado nativo y su manejo de la cancelación— sirve la garantía y los
  reportes sin cambios. El comentario de §7.8 que lo anticipaba («
  reutilizable el día que haya un comprobante de venta») se cumple aquí.

**La fecha de vencimiento se calcula en el servidor**, con una función
pura `sumar_meses(fecha, meses)` que aplica RN-VEN-13 —el día inexistente
pasa al último del mes— usando solo `calendar` de la biblioteca estándar.
No se añade `python-dateutil` para una operación de cinco líneas con sus
pruebas propias.

### 7.11 Exportación de reportes *(v1.3)*

- **PDF**: la plantilla base de §7.10 con las mismas secciones que la
  pantalla, en tablas.
- **Excel**: `openpyxl`, Python puro como `xhtml2pdf`. Una **hoja por
  sección** —resumen, productos, usuarios, servicios—, con los importes
  como **números con formato monetario**, no como texto: así el
  Administrador puede sumarlos o graficarlos en Excel sin convertir
  nada.
- **Nombre del archivo** con el rango:
  `reporte-2026-10-01_2026-10-07.xlsx`, propuesto en el cuadro de
  guardado.

Las tres salidas consumen el mismo resultado de
`panel.reportes.calcular()` (§4.4): no hay una consulta por formato.

---

## 8. Estructura del repositorio

Un **único repositorio Git** con las dos aplicaciones (RNF-21), lo que
mantiene sincronizados los cambios de la API y de su consumidor, y
permite que `specs/` viva junto al código que describe.

```
proyecto_grado_definitivo/
├── .git/
├── .gitignore
├── README.md
├── docker-compose.yml           # PostgreSQL para desarrollo
├── specs/
│   ├── spec.md                  # etapa 1 ✓
│   ├── plan.md                  # etapa 2 (este documento)
│   └── tasks.md                 # etapa 3
├── backend/
│   ├── manage.py
│   ├── requirements/
│   │   ├── base.txt  dev.txt     # sin prod.txt (PT-01)
│   ├── .env.example
│   ├── config/                  # settings/, urls.py, wsgi.py
│   │   └── settings/  base.py  dev.py
│   ├── core/                    # permissions, exceptions, pagination, mixins
│   ├── usuarios/                # models, serializers, services, views, tests
│   ├── catalogo/
│   ├── ventas/
│   ├── servicios/
│   ├── configuracion/
│   ├── inventario/              # movimientos de stock (v1.3)
│   ├── clientes/                # registro de clientes (v1.3)
│   ├── panel/                   # indicadores del día y reportes (v1.3)
│   └── media/                   # imágenes de producto (no versionado)
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── .env.example
    └── src/                     # según §7.1
```

Cada app Django sigue la misma disposición interna:
`models.py`, `serializers.py`, `services.py`, `permissions.py`,
`views.py`, `urls.py`, `admin.py`, `tests/`.

### 8.1 Convenciones de Git

- Rama principal `main`; una rama por módulo (`feat/usuarios`,
  `feat/catalogo`…), fusionada al completarse.
- Mensajes de *commit* en formato convencional (`feat:`, `fix:`,
  `test:`, `docs:`, `refactor:`), en español.
- Un *commit* por tarea de `tasks.md`, citando su identificador. Así el
  historial de Git queda trazable contra la especificación, algo
  directamente defendible en la presentación del proyecto de grado.

---

## 9. Estrategia de pruebas (RNF-23)

| Nivel | Herramienta | Qué cubre |
|---|---|---|
| Unitarias de servicio | pytest + pytest-django | Cada regla de negocio de `spec.md` §6, en aislamiento. |
| Integración de API | DRF `APIClient` | Códigos de estado, formato de error, filtrado por rol. |
| Permisos | Matriz automatizada | Cada endpoint × cada rol, comparado contra la matriz 4.4 de `spec.md`. |
| Concurrencia | `TransactionTestCase` + hilos | RNF-08 (§6.4). |
| Frontend | Vitest + Vue Test Utils | Composables de permisos, mapeo de errores a campos, guards del router. |

**Reglas con prueba obligatoria** (fallar una de estas prueba equivale a
incumplir la especificación):

| Regla | Prueba |
|---|---|
| RN-VEN-02 | Venta con un producto sin stock → 422 y **ningún** producto descontado. |
| RN-VEN-04 | Cambiar el precio de un producto tras la venta → el detalle histórico no cambia. |
| RN-VEN-07 | Anular → el stock vuelve exactamente al valor previo. |
| RN-VEN-11 | Anular una venta con fecha antigua → permitido. |
| RN-SER-03 | Finalizar sin observaciones → 400. |
| RN-SER-09 | El técnico es texto libre: aceptar un nombre que no es cuenta del sistema. |
| RN-SER-13 | Finalizar sin monto cotizado → 409; con monto `0` → 200. |
| RN-SER-15 | Un encargado de servicios pide la solicitud de otro → 404. |
| RF-57 | Un encargado de servicios intenta cotizar, incluso la suya → 403. |
| RN-VEN-09 / RF-27 | Un encargado de ventas intenta ver o anular la venta de otro → 403/404. |
| RN-USU-02/03/04 | Autocambio de rol, autobloqueo y último administrador → rechazados. |
| RN-IND-05 | El ingreso total nunca se devuelve sin su desglose por origen. |
| RN-ACC-05 | Las tres pruebas de invalidación inmediata de §1.3. |
| RNF-08 | Prueba de concurrencia de §6.4, **ampliada en §6.5** con los movimientos. |
| RN-CAT-08 *(v1.3)* | Un `PATCH` con otro `codigo` no lo cambia; el código generado es EAN-13 válido; tras retirar un producto, el siguiente creado recibe un código distinto. |
| RN-CAT-10 *(v1.3)* | Un `PATCH` que incluye `stock` → 400 con el error en ese campo; no cambia las existencias, no crea movimiento y no aplica los demás campos de la petición. |
| RN-CAT-11 *(v1.3)* | Código de fábrica repetido → 400; con forma de código interno → 400, también saltando la validación de Django; dos productos sin código de fábrica → aceptados; `?codigo=` encuentra un producto por cualquiera de sus dos códigos. |
| RN-VEN-12 *(v1.3)* | Cambiar los meses de garantía del producto tras la venta → la línea y la garantía emitida no cambian. |
| RN-VEN-13 *(v1.3)* | Venta del 31 de enero con 1 mes → vence el 28 de febrero; en año bisiesto, el 29. |
| RN-VEN-14 *(v1.3)* | Garantía de venta anulada → 409; de venta sin líneas con garantía → 409; la garantía lista solo las líneas con meses > 0. |
| RN-VEN-16 *(v1.3)* | Un Encargado de Ventas pide la garantía de la venta de otro → 404. |
| RN-MOV-01 *(v1.3)* | Venta rechazada por stock → **ningún** movimiento; un fallo forzado al registrar el movimiento → el stock y la venta se revierten. |
| RN-MOV-03 *(v1.3)* | Prueba guardián del invariante `SUM(cantidad) = stock` para todo producto. |
| RN-MOV-04 *(v1.3)* | Actualizar o borrar un movimiento desde el ORM lanza excepción; la API no expone ningún verbo de escritura. |
| RN-MOV-05 *(v1.3)* | Ajuste sin motivo → 400; sin diferencia → 409; ajuste y venta concurrentes → el libro cuadra. |
| RN-CLI-04 *(v1.3)* | Registrar un cliente no crea ningún `Usuario`. |
| RN-CLI-05 *(v1.3)* | Editar el nombre y el teléfono de un cliente, y desactivarlo → sus ventas anteriores conservan los datos originales. |
| RN-CLI-06 *(v1.3)* | El carnet **no** aparece en la lista de clientes, el detalle de venta, la garantía, el reporte JSON, el PDF ni el Excel. |
| RN-REP-07 *(v1.3)* | Para el mismo rango, las cifras del JSON, del PDF y del Excel son idénticas. |
| RN-REP-08 *(v1.3)* | El reporte de hoy y `panel/resumen` devuelven las mismas cifras. |
| RNF-29 *(v1.3)* | Las migraciones de datos —códigos y saldos iniciales— se aplican y se revierten sobre una base con productos sin perder datos. |

---

## 10. Trazabilidad: de la especificación al código

Resumen de dónde se implementa cada grupo de requerimientos. La
trazabilidad fina, requerimiento por requerimiento, se completa en
`tasks.md`.

| Requerimientos | Backend | Frontend |
|---|---|---|
| RF-01 a RF-06 | `usuarios` + SimpleJWT | `stores/auth.js`, `views/auth/`, guards |
| RF-07 a RF-14, RF-53 | `catalogo` | `views/catalogo/` |
| RF-52 | `configuracion` | `views/configuracion/` |
| RF-15 a RF-27, RF-54 | `ventas/services.py` | `views/ventas/` |
| RF-28 a RF-38, RF-55 a RF-64 | `servicios/services.py` | `views/servicios/` |
| RF-39 a RF-47 | `usuarios/services.py` | `views/usuarios/` |
| RF-48 a RF-51, RF-65, RF-66 | `panel/views.py` | `views/panel/` |
| RF-69 a RF-72, RF-97 *(v1.3)* | `catalogo` (códigos, secuencia, garantía) | `views/catalogo/` + `JsBarcode` |
| RF-73, RF-81 a RF-83 *(v1.3)* | `inventario/services.py` | `views/catalogo/`, `views/inventario/` |
| RF-74 a RF-80 *(v1.3)* | `ventas/services.py`, plantilla de garantía | `views/ventas/` |
| RF-84 a RF-89 *(v1.3)* | `clientes` | `views/clientes/`, selector en `views/ventas/` |
| RF-90 a RF-96 *(v1.3)* | `panel/reportes.py`, exportadores | `views/reportes/` |
| RNF-24, RNF-25 *(v1.3)* | `inventario`, §6.5 | — |
| RNF-26 *(v1.3)* | serializers de `clientes` | — |
| RNF-27 *(v1.3)* | — | campo de código de la venta, `JsBarcode` |
| RNF-28, RNF-29 *(v1.3)* | índices, migraciones reversibles | — |
| RNF-01 a RNF-07 | `core/permissions.py`, `core/exceptions.py`, settings | interceptores Axios |
| RNF-08 a RNF-11 | `services.py` + constraints | — |
| RNF-12 a RNF-16 | — | PrimeVue, `useErroresApi` |
| RNF-17 a RNF-19 | índices, paginación, `select_related` | tablas paginadas |
| RNF-20 a RNF-23 | estructura, Git, pruebas | — |

---

## 11. Orden de implementación propuesto

Derivado de las dependencias reales entre módulos. Se detalla en
`tasks.md`; aquí queda la secuencia y su porqué.

| # | Módulo | Por qué en esta posición |
|---|---|---|
| 0 | Andamiaje | Proyectos Django y Vue, PostgreSQL, Git, CI mínima. **`Usuario` propio antes de la primera migración.** |
| 1 | Autenticación y usuarios | Base de todo lo demás: sin roles no hay forma de autorizar ningún otro módulo (indicado explícitamente en el prompt inicial). Incluye el **arranque del primer administrador** (§11.1). |
| 2 | Catálogo e inventario | Las ventas dependen de que existan productos con existencias. |
| 3 | Configuración (umbral) | Pequeño, y el catálogo y el panel ya lo necesitan para marcar stock bajo. |
| 4 | Ventas | El módulo con la lógica más delicada; se aborda con los cimientos ya probados. |
| 5 | Servicios técnicos | Independiente de ventas; depende solo de usuarios. |
| 6 | Panel de indicadores | Agrega datos de todos los anteriores: va último por necesidad. |

### 11.2 Orden de la v1.4 *(v1.3 de este plan)*

| # | Bloque | Por qué en esta posición |
|---|---|---|
| 8 | **Movimientos de stock** | Va **primero** porque reescribe todos los caminos que cambian existencias: venta, anulación, alta y ajuste. Si se dejara para después, cada bloque posterior que tocara `registrar_venta()` —garantía y clientes lo tocan— habría que revisarlo de nuevo. Y es el de mayor riesgo técnico: conviene abordarlo con el resto del sistema quieto. |
| 9 | **Código de producto** | Independiente del resto, pero la garantía y los reportes **muestran** el código: tiene que existir antes. |
| 10 | **Garantía** | Necesita el código (lo lista) y toca `registrar_venta()`, que ya incluye los movimientos. |
| 11 | **Clientes** | Vuelve a tocar `registrar_venta()`. Se hace después de la garantía para que cada bloque añada **un solo** cambio a ese servicio, probado antes del siguiente. |
| 12 | **Reportes** | Agrega datos de todos los anteriores —usa el código en los más vendidos—, igual que el panel en la v1.0: va último por necesidad. |
| 13 | **Cierre de la v1.4** | Matriz de permisos, guardianes, usabilidad y coherencia final. |

**El guardián de trazabilidad marca el avance.** Desde que se aprueba
`spec.md` v1.4, `test_trazabilidad.py` falla para los 35 requerimientos
nuevos que el código todavía no cita. **No se silencia**: cada bloque
apaga los suyos al implementarlos, y el bloque 13 termina con el
guardián en verde. Es la forma más directa de ver, en cualquier momento,
cuánto de la v1.4 falta.

### 11.1 El arranque del primer administrador

PT-04 descarta la carga de datos de ejemplo, pero queda un problema que
**no** es dato de ejemplo sino un requisito de arranque, y conviene
resolverlo explícitamente:

> RN-USU-01 dice que solo el Administrador crea cuentas. Si no existe
> ninguna cuenta, **nadie puede crear la primera**: el sistema recién
> instalado es inaccesible.

Se resuelve con el `createsuperuser` de Django, adaptado para que asigne
`rol = ADMINISTRADOR` automáticamente —un superusuario sin rol podría
autenticarse pero no pasaría ninguna clase de permiso—. Es un comando de
consola, ejecutado una sola vez al preparar el equipo, fuera del flujo de
la aplicación: no vulnera RN-USU-01, del mismo modo que tener la llave
del local no es una función del ERP.

No se carga nada más: ni productos, ni categorías, ni ventas, ni
servicios de prueba. Todo se registra a mano durante la demostración,
conforme a PT-04.

> **Consecuencia práctica para la defensa.** Sin datos precargados, la
> demostración empieza con el sistema vacío, y varias pantallas solo
> tienen sentido con datos dentro: el panel de indicadores necesita
> ventas y servicios del día, y el aviso de existencias bajas necesita un
> producto por debajo del umbral. El orden de la demostración deja de ser
> libre y pasa a ser: crear usuarios → categorías y productos → una
> venta → un servicio completo hasta finalizarlo → **y solo entonces** el
> panel. Vale la pena ensayarlo cronometrado; si al probarlo resulta
> demasiado largo, siempre se puede reconsiderar PT-04.

### 11.3 Importación del catálogo anterior: operación de una sola vez *(PT-05)*

**Qué es y qué no es.** Un **comando de gestión de Django** que se
ejecuta una vez para cargar el catálogo del intento anterior en Laravel.
**No es una funcionalidad del sistema**: no tiene pantalla, ni caso de
uso, ni requerimiento propio, igual que el `createsuperuser` adaptado de
§11.1. Por eso vive aquí y en las tareas operativas de `tasks.md`, y no
en `spec.md`.

**Origen de los datos.** 153 productos en 14 categorías, de la base
MariaDB `pcsolution` del proyecto Laravel. El seeder de ese proyecto
declara que **los productos y las categorías son reales, pero los
precios son referenciales** y las existencias inventadas. De ahí dos
decisiones (PT-05):

- **Se importa con existencias 0.** Las existencias reales se cargan
  después con el **ajuste por recuento** (CU-CAT-07), una vez contado el
  inventario físico. Importar las existencias del seeder llenaría el
  libro de movimientos de altas ficticias, y el libro existe justamente
  para que cada unidad tenga una explicación verdadera.
- **Los precios se importan tal cual**, y el informe lo advierte para
  que el Administrador los revise. Un precio referencial se corrige con
  la edición normal; una existencia inventada en el libro no se borra.

**Se lee de CSV, nunca de la base.** El comando lee `productos.csv` y
`categorias.csv`, exportados de una copia de la base antigua. No
necesita un controlador de MariaDB ni que ningún servidor esté en
marcha, y no puede escribir en la base de origen porque no la conoce.

**Pasa por el servicio de alta**, no por el ORM directamente. Así cada
producto importado nace exactamente igual que uno creado a mano: con su
código EAN-13 interno (RN-CAT-08), su movimiento `ALTA` con cantidad 0 y
como autor el Administrador que ejecuta el comando (`--usuario`), y 0
meses de garantía. Por eso se ejecuta **después del bloque 9**: antes no
existirían ni el código ni el movimiento de alta.

**Qué se importa y qué no:**

| Columna antigua | Destino | |
|---|---|---|
| `nombre` | `nombre` | Recortado; es problemático si queda vacío, pasa de 150 caracteres o se repite —dentro del CSV o con un producto ya existente—. |
| `descripcion` | `descripcion` | Tal cual. |
| `precio` | `precio` | Tal cual; es problemático si no es positivo. |
| `categoria_id` → nombre | `categoria` | Por nombre, sin distinguir mayúsculas ni tildes; se crea si no existe. Es problemática si no existe en `categorias.csv` o su nombre pasa de 100 caracteres. |
| `imagen` | `imagen` | Se copia el archivo desde el proyecto antiguo, con la misma validación que una subida (Pillow, 2 MB). Si falta o no es válido, el producto se importa **sin imagen** y el informe lo lista (RN-CAT-06 la hace opcional). |
| `stock` | — | **No**: existencias 0 (PT-05). |
| `marca` | — | **No**: los nombres ya la incluyen. |
| `slug`, `destacado`, fechas | — | Propias de la tienda online; sin equivalente aquí. |

**Tablas que no se importan nunca:** `pedidos`, `detalle_pedidos` y
`mensajes_contacto` —restos de la tienda online que `spec.md` §2.2
excluye—, ni `users`, `solicitudes_servicio` o las tablas internas de
Laravel.

**Dos modos y una huella.**

1. **`--informe`** (por defecto): no escribe nada. Produce el informe con
   los productos que se importarían; **cuántos y cuáles tienen nombre o
   categoría problemáticos**, y por qué; **cuáles tienen la imagen
   faltante** o inválida; y las categorías que se crearían, las que
   coinciden con una existente y las **parecidas** a una existente
   —«Redes» frente a «Redes y Conectividad»—, para decidir si se fusionan
   con `--mapa-categorias`. Termina con una **huella**: un resumen
   criptográfico del conjunto exacto que se importaría.
2. **`--aplicar --huella <huella>`**: recalcula el plan y **solo importa
   si la huella coincide** con la del informe aprobado. Si algo cambió
   entre el informe y la ejecución —un producto creado a mano, un CSV
   tocado—, la huella no coincide y no se importa nada. Así lo que se
   ejecuta es exactamente lo que se aprobó.

Los productos problemáticos **no se importan** y quedan listados para
corregirlos a mano. La importación del resto es **todo o nada**: una
sola transacción. Ejecutarla dos veces no duplica nada, porque la
segunda vez todos los nombres ya existen.

**Productos que difieren entre la base antigua y el seeder** *(añadido
el 2026-10-09)*. La exportación se validó contra el seeder de Laravel:
coinciden 149 de 153 productos; los otros **4** se editaron a mano en
la aplicación Laravel, en agosto, después de sembrarlos. Están en
`diferencias_con_seeder.csv`, junto a los otros dos CSV, y **el informe
los marca**:

| Id | Producto | Campo | Base antigua | Seeder | Se importaría |
|---:|---|---|---:|---:|---:|
| 28 | Adaptador Bluetooth 5.1 USB | stock | 0 | 25 | 0 |
| 88 | Parlante Bluetooth JBL Go 4 | stock | 15 | 16 | 0 |
| 98 | Audífonos Gamer Turtle Beach Stealth 600 | **precio** | **580,00** | **680,00** | **580,00** |
| 98 | ″ | stock | 2 | 0 | 0 |
| 138 | Consola Nintendo Switch Estándar | stock | 1 | 5 | 0 |

**Por defecto se importa la versión de la base antigua**, porque es la
última decisión tomada a mano: el seeder es el estado inicial y la base
refleja lo que alguien cambió después. Pero solo importa en un caso:

- **Las existencias dan igual.** Se importan siempre en 0 (PT-05), así
  que cuatro de las cinco diferencias no llegan al sistema.
- **El precio del Turtle Beach sí importa**: 580 frente a 680. Se usa
  580, y el informe lo señala para **confirmarlo con la empresa**:
  ambos son precios referenciales de un catálogo de demostración, así
  que «la última edición» no garantiza que sea el precio real.

El comando lee `diferencias_con_seeder.csv` con la opción
`--diferencias` y solo lo usa para marcar filas en el informe: no
cambia qué se importa.

#### Fusión de categorías renombrando las existentes *(decidido al revisar el informe, 2026-10-09)*

El informe señaló tres categorías del catálogo antiguo parecidas a otras
ya creadas en el sistema: «Cables y Adaptadores» y «cables», «Cámaras y
Videovigilancia» y «Videovigilancia», «Redes y Conectividad» y «Redes».
**Se fusionan quedándose con el nombre del catálogo antiguo:** la
categoría existente **se renombra** y los productos importados entran en
ella. Sus productos actuales la conservan.

- **Se hace dentro de la importación**, con `--fusionar-categorias`
  (CSV `existente,nombre_final`), y no editando a mano antes: así el
  renombrado está en el informe, entra en la **huella** y se aplica en
  la **misma transacción**. Antes de aprobar no se escribe nada.
- **No rompe nada**: en este sistema la categoría se referencia siempre
  por su **id** —producto, filtros de la API y rutas de la interfaz— y no
  tiene *slug*. El nombre solo se muestra, leído en vivo. Renombrar
  conserva el id.
- **El nombre final no puede chocar** con otra categoría existente: el
  `UNIQUE` sin distinguir mayúsculas lo impediría, y el plan lo rechaza
  antes.

**Precio por confirmar.** El producto 98 (Turtle Beach Stealth 600) se
importa a 580,00 —base antigua— y el informe lo lista aparte como
**«precio por confirmar con la empresa»**.

#### Carga de las existencias contadas *(opcional, añadido el 2026-10-09)*

Con 153 productos importados en 0, ajustarlos uno a uno desde el diálogo
de «Ajustar existencias» (T-8.7) sería poco práctico. El comando acepta
por eso, **opcionalmente**, un CSV con las existencias contadas, y las
carga en la **misma ejecución** que la importación. Sigue siendo una
operación de una sola vez: sin pantalla y sin caso de uso nuevo.

**Pasa por el servicio de ajuste, no fija el stock al dar de alta.**
Sería más corto que el alta naciera ya con lo contado —un movimiento por
producto en vez de dos—, pero el libro perdería una distinción que vale
la pena: un `ALTA` de 0 seguido de un `AJUSTE` con el motivo **«Carga
inicial»** deja dos hechos separados —cuándo entró el producto en el
catálogo, y cuándo y quién contó sus unidades—. Así cada producto
importado queda con un libro `ALTA 0 → AJUSTE +N`, que cuadra, y la
carga inicial es auditable igual que cualquier ajuste posterior
(RN-MOV-05).

**Una planilla que genera el propio comando.** Los productos todavía no
tienen código cuando se cuentan, y escribir nombres a mano invita a
errores. Con `--planilla-recuento <archivo>`, el comando escribe un CSV
con `id_antiguo`, `nombre` y `categoria` ya rellenos y la columna
`existencias_contadas` vacía, más una fila de cabecera con la fecha del
recuento a completar. El personal la rellena al contar y se devuelve con
`--existencias <archivo>`.

| Situación de una fila | Qué hace el comando |
|---|---|
| Entero positivo | Ajuste «Carga inicial» por esa cantidad, con el autor de `--usuario`. |
| Cero | Ningún ajuste —no hay diferencia con el 0 importado— y el informe la cuenta como «contado en cero». |
| Vacía | Ningún ajuste; el producto queda en 0 y el informe la lista como **no contado**. |
| Negativa, decimal o texto | Fila problemática: no se carga y el informe la lista. El producto se importa igual, en 0. |
| `id_antiguo` que no existe, o producto excluido por problemático | Se lista y se ignora. |
| `nombre` que no coincide con el de su `id_antiguo` | Fila problemática: indica una planilla equivocada o desordenada. |

**Dentro de la misma huella y la misma transacción.** La huella del
informe incluye el contenido del CSV de existencias, de modo que
cambiar una sola cifra después de aprobar el informe invalida la
ejecución. Importación y carga son **todo o nada**: si un ajuste falla,
no queda ni el producto ni su ajuste.

**El recuento tiene que hacerse el día del cambio.** Mientras no se pase
al sistema nuevo, la tienda sigue vendiendo con el antiguo: si se cuenta
el lunes y se importa el jueves, las existencias ya no serán las reales.
El comando no puede impedirlo, pero el informe muestra la **fecha del
recuento** de la planilla junto a la fecha de ejecución, para que la
diferencia se vea antes de aprobar.

**Si el recuento no está listo al importar**, la importación se hace sin
`--existencias` y los productos quedan en 0, y las existencias se cargan
después con el modo `--solo-existencias` (decidido el 2026-10-09, tras
importar sin recuento; T-OP.5).

#### Carga posterior del recuento: `--solo-existencias` *(T-OP.5, 2026-10-09)*

Un segundo modo del mismo comando para cargar el recuento en productos
**ya importados**. Mismas reglas que la carga dentro de la importación,
con tres diferencias que impone el hecho de que los productos ya existen.

- **`--planilla-importados <archivo>`** escribe la planilla de los
  productos del CSV antiguo **que ya están en el sistema**, con las
  columnas `id_antiguo,nombre,categoria,existencias_contadas,meses_garantia`
  y la fila inicial `fecha_del_recuento,`.
- **`--solo-existencias <planilla>`** informa, y con `--aplicar --huella
  --usuario` aplica. Cada fila se casa con su producto por `id_antiguo`
  (el nombre de esa fila en `productos.csv`) **y** por el nombre escrito
  en la planilla, que deben coincidir. Las filas sin producto en el
  sistema, con nombre equivocado o con cifras inválidas no se cargan y
  se listan.
- **No duplica.** Un producto que ya tiene un `AJUSTE` con el motivo
  «Carga inicial» **se salta** y se lista como «ya cargado». Ejecutar el
  modo dos veces no crea ningún movimiento la segunda.
- **Ajuste contra las existencias actuales.** El ajuste deja el producto
  en lo contado, calculando la diferencia contra el valor vigente, igual
  que CU-CAT-07. Si coincide con lo contado no hay ajuste («sin
  diferencia»). Y como **la huella incluye las existencias actuales** de
  cada producto, una venta entre el informe y la aplicación invalida la
  huella: se aplica exactamente lo aprobado.
- **Meses de garantía, opcional.** Si la columna `meses_garantia` trae un
  entero no negativo distinto del actual, se fija en el producto en la
  misma transacción. Es una edición del producto, no un movimiento; solo
  afecta a las ventas futuras (RN-CAT-09, RN-VEN-12). Vacía, no se toca.
  Entra en la huella.
- **Todo o nada**, en una transacción, y `ANALYZE` al terminar.

**Lectura de la base antigua: solo sobre una copia.** Al preparar este
plan se leyó la base antigua y hubo un incidente: `my.ini` de XAMPP fija
con ruta absoluta los archivos de sistema de InnoDB, y una instancia
arrancada «sobre la copia» usó los originales. Se revirtió restaurando
los tres archivos afectados desde la copia, verificado byte a byte, y
sin que ninguna tabla cambiara. Desde entonces no se arranca ningún
servidor de base de datos sobre archivos fuera del proyecto; los datos
antiguos se leen de los CSV exportados.

### 11.4 Lo que la implementación precisó *(v1.4 de este plan, 2026-10-09)*

Ninguna de estas precisiones cambia un requerimiento de `spec.md` v1.4.
Son decisiones en las que el plan no entraba, y quedan aquí para que el
plan describa el sistema tal como quedó. El detalle, con la tarea y el
porqué, está en `docs/avance_v1.4.md`.

| Tema | Precisión | Tarea |
|---|---|---|
| Movimientos | Un filtro inválido en `/movimientos-stock` (producto, tipo o fecha) responde **400** en lugar de ignorarse: en una auditoría, una lista sin filtrar parecería válida. Las fechas se filtran por día en hora de Bolivia. | T-8.6 |
| Ajuste | Responde **201** con el movimiento creado. La interfaz confirma en dos pasos dentro del diálogo y avisa si el servidor registró otra diferencia porque se vendió mientras tanto. | T-8.6, T-8.7 |
| Código interno | Se asigna en `Producto.save()` al insertar, no en el servicio de alta, para que lo reciba todo producto. El reverso del paso 2 de su migración no borra códigos (§3.5). | T-9.1, T-9.2 |
| Lector de códigos (§7.9) | El campo se vacía **en el mismo Intro** y las lecturas se procesan **en cola**, en orden: un lector envía la siguiente antes de que responda la anterior. Una lectura que excedería las existencias avisa en lugar de sumar. Un `?codigo=` vacío devuelve una lista vacía. | T-9.3, T-9.5 |
| Envío multipart | Las cadenas vacías viajan: sin eso, no se podía vaciar un campo de texto al subir a la vez una imagen nueva. | T-9.7 |
| Garantía (§7.10) | Las condiciones de garantía de la empresa, que la spec no define, tienen un **punto de extensión único**: `CONDICIONES_DE_GARANTIA` en `ventas/garantia.py`. Vacío, la sección no aparece. | T-10.7 |
| Clientes | Sin `?activo=`, la lista incluye a los inactivos (el Administrador los reactiva desde ahí); el selector de la venta pide `activo=true`. El carnet se busca **solo por coincidencia exacta**. El mensaje de carnet duplicado no dice de quién es. Un `cliente_id` inexistente en la venta responde 400 junto al campo. | T-11.2 a T-11.4 |
| Reportes | `calcular(desde, hasta, con_detalles=True)`: el panel diario pide `con_detalles=False`. «Más vendidos» se consulta con un **join** a la venta y no con `venta__in=<subconsulta>`: con estadísticas viejas, PostgreSQL ejecutó la subconsulta como bucle anidado (213 s por petición con un año de datos). Tras una carga masiva, y en la prueba de RNF-28, se ejecuta `ANALYZE`. | T-12.3, T-12.7 |
| Documentación de la API | Una prueba genera el esquema OpenAPI con `--fail-on-warn`; las enumeraciones `tipo` de la solicitud y del movimiento tienen nombre propio. | T-13.3 |
| Importación (§11.3) | Las imágenes se leen de la carpeta que indique `--imagenes` (base de las rutas de la columna `imagen`), **sin ninguna ruta por defecto** hacia fuera del proyecto. El mapa de categorías es un CSV `origen,destino`. La planilla de recuento empieza con la fila `fecha_del_recuento,<fecha>` y sigue con `id_antiguo,nombre,categoria,existencias_contadas`. `--salida` guarda el informe en un archivo. La huella son los 16 primeros caracteres del SHA-256 del conjunto a importar, incluido el contenido de cada imagen. Tras aplicar se ejecuta `ANALYZE`. | T-OP.2 |

---

## 12. Riesgos técnicos y cómo se mitigan

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Cambiar el modelo `Usuario` después de migrar | Muy alto: reconstrucción de la base | Definirlo en la tarea 0, antes de la primera migración. |
| La prueba de concurrencia no reproduce la carrera | RNF-08 queda sin evidencia | `TransactionTestCase` contra PostgreSQL real, nunca SQLite ni `TestCase`. |
| Interbloqueo entre dos ventas simultáneas | Peticiones colgadas | Bloquear siempre en orden ascendente de `pk`. |
| Importes con `float` | Céntimos perdidos en los totales | `DecimalField` en Django, `NUMERIC` en PostgreSQL, cadena decimal en el JSON. |
| Desfase entre el `spec.md` y el código | Se pierde el sentido de SDD | Un *commit* por tarea citando su id; todo cambio funcional se edita primero en `specs/`. |
| Lógica de negocio filtrándose a las vistas | Reglas no probables ni reutilizables | Capa `services.py` obligatoria; las vistas no abren transacciones. |
| Token válido tras bloquear la cuenta | Acceso indebido tras el bloqueo | Cerradas las cuatro vías de §1.3; verificado con tres pruebas automatizadas. |
| Suponer que SimpleJWT se comporta como JWT apátrida | Decisiones de diseño sobre premisas falsas (le ocurrió a la v1.0 de este plan) | Lo verificado se cita con el código real del framework; lo no verificado se marca como supuesto. |
| Un camino que cambia el stock sin dejar movimiento *(v1.3)* | El libro deja de cuadrar y pierde su valor de auditoría | Toda escritura de `stock` pasa por `inventario.services`; prueba guardián del invariante `SUM(cantidad) = stock` (§6.5). |
| Migración de datos que falla a mitad *(v1.3)* | Productos sin código o sin saldo inicial | Migraciones en pasos atómicos y reversibles; probadas en ambos sentidos sobre una base con productos (RNF-29). |
| Lector configurado distinto de lo supuesto *(v1.3)* | La venta no reconoce los códigos leídos | El campo de código funciona igual a mano; se verifica con un lector real antes de cerrar el bloque 9. Si el lector no envía Intro, se configura —es un ajuste de fábrica estándar—. |
| El carnet se filtra por una vista nueva *(v1.3)* | Exposición de un dato personal | Dos serializers distintos; prueba que busca el carnet en cada salida de la API, en el PDF y en el Excel (RN-CLI-06). |
| Etiquetas que el lector no lee *(v1.3)* | El flujo por código no sirve en la práctica | Dígito de control probado contra EAN-13 reales; etiqueta en SVG; verificación con lector real (RNF-27). |

---

## 13. Decisiones resueltas

Los cuatro puntos pendientes de la versión 1.0 fueron resueltos el
2026-09-22 y ya están incorporados al documento.

| # | Punto | Decisión | Se refleja en |
|---|---|---|---|
| **PT-01** | Despliegue | **Solo entorno de desarrollo** en el equipo del autor, para la defensa. Sin configuración de servidor real. | §5.4, §8 (sin `prod.py` ni `prod.txt`), README |
| **PT-02** | Invalidación de sesiones | **Inmediata** al bloquear una cuenta, por las cuatro vías. | §1.2 (corrección), **§1.3 completa**, §9, §12 |
| **PT-03** | Biblioteca de componentes | **PrimeVue 4** confirmada. | §1.1, §1.2, §7 |
| **PT-04** | Datos de ejemplo | **No se cargan.** Todo se registra a mano en la demostración. Se mantiene solo el arranque del primer administrador, que no es dato de ejemplo sino requisito de acceso. | §11.1 |
| **PT-05** *(2026-10-09)* | Catálogo del proyecto anterior | **Se importa una vez** con un comando de gestión, después del bloque 9, pasando por el servicio de alta: **existencias 0**, sin marca, con imágenes, precios a revisar. Las existencias reales se cargan por ajuste de recuento. No contradice PT-04: son los productos reales de la empresa, no datos inventados para la demostración; lo inventado —las existencias— es justo lo que no se importa. | §11.3, tareas operativas de `tasks.md` |

### Qué cambió de fondo con PT-02

La decisión no encareció el sistema: lo que la v1.0 presentaba como el
coste a pagar —una consulta por petición— resultó ser comportamiento que
SimpleJWT ya tenía. Lo que sí aportó fue cerrar tres agujeros reales que
la v1.0 no había identificado (refresh de cuenta bloqueada, resurrección
de sesiones al desbloquear, y rol leído del token), ninguno de los cuales
se habría resuelto acortando la vida del access token.

El efecto secundario que conviene tener presente al defender el proyecto:
**este sistema usa JWT de forma deliberadamente no apátrida**. Si en la
defensa se pregunta «¿por qué JWT si igual consultas la base en cada
petición?», la respuesta no es un descuido sino la decisión de §1.3: se
cambia escalabilidad teórica —irrelevante en una sola sucursal— por
revocación inmediata, que RN-ACC-05 exige.
