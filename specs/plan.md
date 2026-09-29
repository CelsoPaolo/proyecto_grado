# Plan Técnico — Sistema ERP PC-Solution

- **Proyecto:** Sistema ERP interno para PC-Solution (Sucre, Bolivia)
- **Documento:** Etapa 2 de Spec-Driven Development — Plan técnico
- **Versión:** 1.1
- **Fecha:** 2026-09-22
- **Estado:** **Aprobado** — incorpora las decisiones PT-01 a PT-04
  (ver sección 13)
- **Deriva de:** `spec.md` v1.1

### Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-09-22 | Versión inicial para revisión. |
| 1.1 | 2026-09-22 | Se resuelven los puntos pendientes PT-01 a PT-04. Alcance limitado a entorno de desarrollo (PT-01); **invalidación inmediata de sesiones** al bloquear una cuenta, con corrección de un error técnico de la v1.0 (PT-02); PrimeVue confirmado (PT-03); sin carga de datos de ejemplo, salvo el arranque del primer administrador (PT-04). |

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
                                              │  PostgreSQL 16 │
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
| `servicios` | Solicitudes, estados, asignación, cierre. | `SolicitudServicio`, `EventoSolicitud` |
| `configuracion` | Parámetros del sistema (umbral global). | `ConfiguracionSistema` |
| `panel` | Indicadores agregados. Solo lectura, sin modelos propios. | — |
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
│ nombre_completo    │◄──────┐       │ tecnico_asignado
│ rol  (ADM/VEN/SER) │       │       │ (PROTECT)
│ is_active (bloqueo)│       │       │
│ date_joined        │       │       │
└────────────────────┘       │       │
                             │       │
        ┌────────────────────┘       └──────────────────┐
        │ usuario / anulada_por (PROTECT)               │
        │                                                │
┌───────▼────────────┐                    ┌──────────────▼──────────────┐
│ Venta              │                    │ SolicitudServicio           │
│────────────────────│                    │─────────────────────────────│
│ id                 │                    │ id                          │
│ cliente_nombre     │                    │ cliente_nombre              │
│ cliente_telefono   │                    │ cliente_telefono            │
│ usuario        FK  │                    │ tipo  (MANT/REP/RED/VID)    │
│ fecha_hora         │                    │ modalidad (TALLER|DOMICILIO)│
│ estado (CONF/ANUL) │                    │ direccion         NULL      │
│ total     NUMERIC  │                    │ descripcion                 │
│ motivo_anulacion   │                    │ estado (REG/ATE/FIN/CAN)    │
│ anulada_por    FK  │                    │ registrada_por    FK        │
│ fecha_anulacion    │                    │ tecnico_asignado  FK NULL   │
└─────────┬──────────┘                    │ observaciones     ''        │
          │ 1                             │ monto_cobrado     NULL      │
          │                               │ motivo_cancelacion''        │
          │ N  (CASCADE)                  │ fecha_registro              │
┌─────────▼──────────┐                    │ fecha_inicio_atencion NULL  │
│ DetalleVenta       │                    │ fecha_cierre          NULL  │
│────────────────────│                    │ cerrada_por       FK NULL   │
│ id                 │                    └──────────────┬──────────────┘
│ venta          FK  │                                   │ 1
│ producto  FK PROT  │──────┐                            │
│ producto_nombre ❄  │      │                            │ N (CASCADE)
│ precio_unitario ❄  │      │             ┌──────────────▼──────────────┐
│ cantidad           │      │             │ EventoSolicitud             │
│ subtotal        ❄  │      │             │─────────────────────────────│
└────────────────────┘      │             │ id                          │
                            │             │ solicitud          FK       │
      ❄ = dato congelado    │             │ tipo_evento                 │
        (RN-VEN-04)         │             │ estado_anterior / nuevo     │
                            │             │ tecnico_anterior / nuevo FK │
┌────────────────────┐      │             │ usuario            FK       │
│ Producto           │◄─────┘             │ fecha_hora                  │
│────────────────────│                    │ nota                        │
│ id                 │                    └─────────────────────────────┘
│ nombre         UQ  │
│ descripcion        │      ┌──────────────────────┐
│ precio   NUMERIC>0 │      │ ConfiguracionSistema │
│ stock       >= 0   │      │──────────────────────│
│ categoria  FK PROT │      │ id (singleton = 1)   │
│ imagen       NULL  │      │ umbral_stock_bajo    │
│ activo (soft del.) │      │ actualizado_por  FK  │
└─────────┬──────────┘      │ actualizado_en       │
          │ N               └──────────────────────┘
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

PA-04 convirtió el módulo de servicios en un espacio compartido: cualquier
encargado puede tocar cualquier solicitud abierta. Como señala la sección
11 de `spec.md`, eso hace del historial el control principal de
responsabilidad del módulo, no un accesorio. Por eso es una tabla propia,
de solo inserción (nunca se actualiza ni se borra), que registra con el
mismo formato los tres tipos de evento: cambio de estado, asignación de
técnico y cierre (RF-35, RF-59).

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
| `solicitud` | `CHECK (estado='CANCELADA' → monto_cobrado IS NULL)` | RN-SER-14 |
| `configuracion` | `CHECK (id = 1 AND umbral_stock_bajo >= 0)` | RN-CAT-07 |

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
| `solicitud` | `(estado)`, `(tecnico_asignado)`, `(fecha_registro DESC)` | Filtros de RF-37, RF-60 e indicador RF-49. |
| `solicitud` | `(estado, fecha_cierre)` | Ingresos por servicios del día (RN-IND-04). |
| `producto` | `(categoria)`, `(activo)`, `(stock)` | Catálogo filtrado y existencias bajas (RF-13, RF-50). |
| `evento_solicitud` | `(solicitud, fecha_hora)` | Historial ordenado de una solicitud. |

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
`CATEGORIA_CON_PRODUCTOS`.

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
| GET | `/productos` | A, V | Lista paginada. Filtros `?categoria=`, `?buscar=`, `?stock_bajo=true`, `?activo=`. | RF-12, RF-13, RF-53 |
| POST | `/productos` | A | Crea (`multipart` si lleva imagen). | RF-09, RF-14 |
| GET | `/productos/{id}` | A, V | Detalle. | RF-12 |
| PATCH | `/productos/{id}` | A | Edita, incluido ajuste de existencias. | RF-10 |
| DELETE | `/productos/{id}` | A | Borrado suave (`activo = false`). | RF-11 |

Cada producto listado incluye `stock_bajo: true|false`, calculado contra
el umbral global vigente, para que el frontend no tenga que conocer la
regla (RF-53).

#### Configuración (`/api/v1/configuracion/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/configuracion` | A | Umbral vigente, quién lo cambió y cuándo. | RF-52 |
| PATCH | `/configuracion` | A | Modifica el umbral global. | RF-52, RN-CAT-07 |

#### Ventas (`/api/v1/ventas/`)

| Método | Ruta | Roles | Descripción | Cubre |
|---|---|---|---|---|
| GET | `/ventas` | A (todas), V (propias) | Lista paginada. Filtros `?desde=`, `?hasta=`, `?estado=`. | RF-21, RF-22 |
| POST | `/ventas` | A, V | Registra y confirma la venta de forma atómica. | RF-15 a RF-20 |
| GET | `/ventas/{id}` | A, V (propia) | Detalle con líneas congeladas. | RF-23 |
| POST | `/ventas/{id}/anular` | A (cualquiera), V (propia) | Anula devolviendo existencias. | RF-24, RF-25, RF-27, RF-54 |

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

Cada transición es un endpoint con nombre propio en lugar de un
`PATCH {"estado": "..."}`. Así la máquina de estados de RN-SER-02 vive en
el contrato de la API: `finalizar` puede exigir observaciones y monto, e
`iniciar` puede exigir técnico, cosa que un `PATCH` genérico no expresa.

<details>
<summary><code>POST /solicitudes/{id}/finalizar</code> — petición y respuestas</summary>

```jsonc
// → petición
{
  "observaciones": "Se reemplazó la fuente de poder y se limpió el equipo.",
  "monto_cobrado": "250.00"
}

// ← 200
{
  "id": 91, "estado": "FINALIZADA",
  "fecha_cierre": "2026-09-22T17:10:03-04:00",
  "monto_cobrado": "250.00",
  "cerrada_por": { "id": 6, "nombre_completo": "Ana Rojas" }
}

// ← 400   monto ausente (un servicio sin cargo se envía como "0.00")
{ "codigo": "MONTO_REQUERIDO",
  "detalle": "Debe registrar el monto cobrado para finalizar el servicio.
              Si el servicio no tuvo costo, registre 0." }

// ← 409   la solicitud no está En atención
{ "codigo": "TRANSICION_INVALIDA",
  "detalle": "Solo puede finalizarse una solicitud en atención." }
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
| `EsDuenoDeLaVentaOAdmin` | Nivel de objeto: autor de la venta, o admin. | `GET/anular` de una venta (RF-27). |

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
| Catálogo | Lista de productos con búsqueda, filtro y marca de stock bajo; formulario de producto; gestión de categorías. |
| Ventas | Registro de venta (buscador de productos, carrito interno de la pantalla, total en vivo); historial con filtros; detalle con líneas congeladas; diálogo de anulación con motivo. |
| Servicios | Lista con filtros y accesos rápidos «asignadas a mí» / «sin asignar»; formulario de registro con dirección condicional al tipo; detalle con línea de tiempo del historial; diálogos de asignar, iniciar, finalizar (observaciones + monto) y cancelar. |
| Usuarios | Lista con rol y estado; formulario de alta y edición; acciones de bloqueo y restablecimiento de contraseña. |
| Panel | Tarjetas de indicadores, desglose de ingresos y tabla de productos con stock bajo, cada una enlazando a su módulo (RF-51). |
| Configuración | Umbral global de existencias bajas. |

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
│   ├── panel/
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
| RN-SER-11 | Iniciar sin técnico asignado → 409. |
| RN-SER-13 | Finalizar sin monto → 400; con monto `0` → 200. |
| RN-SER-15 | Un encargado de servicios actúa sobre la solicitud de otro → permitido. |
| RN-VEN-09 / RF-27 | Un encargado de ventas intenta ver o anular la venta de otro → 403/404. |
| RN-USU-02/03/04 | Autocambio de rol, autobloqueo y último administrador → rechazados. |
| RN-ACC-05 | Las tres pruebas de invalidación inmediata de §1.3. |
| RNF-08 | Prueba de concurrencia de §6.4. |

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
