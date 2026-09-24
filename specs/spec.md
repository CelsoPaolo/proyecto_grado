# Especificación Funcional — Sistema ERP PC-Solution

- **Proyecto:** Sistema ERP interno para PC-Solution (Sucre, Bolivia)
- **Documento:** Etapa 1 de Spec-Driven Development — Especificación funcional
- **Versión:** 1.1
- **Fecha:** 2026-09-22
- **Estado:** **Aprobada** — incorpora las decisiones PA-01 a PA-05
  (ver sección 11)

### Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-09-22 | Versión inicial para revisión. |
| 1.1 | 2026-09-22 | Se resuelven las preguntas abiertas PA-01 a PA-05. Cambios principales: umbral global de existencias bajas configurable (PA-01); anulación de ventas sin plazo (PA-02); monto cobrado por servicio e indicador de ingresos por servicios (PA-03); visibilidad compartida de las solicitudes entre el personal de servicios (PA-04); técnico asignado distinto del usuario registrador (PA-05). |

> **Nota sobre la numeración:** los identificadores (RF-, RN-, RNF-, CU-,
> SUP-) son estables entre versiones. Los requerimientos añadidos en la
> versión 1.1 toman números nuevos y se ubican en la tabla temática que
> les corresponde, por lo que las tablas no siempre son correlativas.

> Este documento es la **fuente de verdad funcional** del sistema. Describe
> *qué* debe hacer el sistema y *bajo qué reglas*, nunca *cómo* se
> implementa. Las decisiones técnicas (arquitectura, modelo físico de
> datos, endpoints, librerías, estructura de carpetas) corresponden a la
> etapa 2 (`plan.md`). Si una necesidad cambia, se edita primero este
> documento y luego se ajusta el código.

---

## 1. Propósito y contexto

PC-Solution es una empresa de Sucre, Bolivia, dedicada a la venta de
equipos y componentes informáticos y a la prestación de servicios técnicos
(mantenimiento, reparación, instalación de redes y videovigilancia).

Actualmente el registro de ventas, del inventario y de las solicitudes de
servicio se lleva de forma manual y dispersa, lo que dificulta conocer las
existencias reales, dar seguimiento a los servicios en curso y obtener
información consolidada para la toma de decisiones.

El propósito del sistema es **centralizar la operación interna de la
empresa** en una única aplicación: catálogo e inventario, registro de
ventas, seguimiento de servicios técnicos, gestión de las cuentas del
personal y un panel de indicadores para la administración.

---

## 2. Alcance

### 2.1 Dentro del alcance

El sistema es de **uso exclusivamente interno**. Solo el personal de
PC-Solution accede a él, siempre mediante una cuenta creada por el
Administrador. Comprende cinco módulos funcionales:

1. Catálogo e inventario (categorías y productos).
2. Registro de ventas.
3. Solicitudes de servicio técnico.
4. Gestión de usuarios y roles.
5. Panel de indicadores.

### 2.2 Fuera del alcance

Queda explícitamente **excluido** de este sistema:

- Portal de clientes, registro público o autoservicio: los clientes de la
  empresa **nunca** inician sesión en el sistema.
- Carrito de compras, checkout, pagos en línea o pasarelas de pago.
- Facturación tributaria o emisión de documentos fiscales.
- Contabilidad, nómina, cuentas por cobrar o pagar.
- Gestión de proveedores y órdenes de compra.
- Comercio electrónico o catálogo público en internet.
- Notificaciones automáticas al cliente (correo, SMS, WhatsApp).
- Aplicación móvil nativa.

### 2.3 Nota sobre los datos del cliente

Los clientes de la empresa se registran únicamente como **datos de
contacto** (nombre y teléfono) **dentro** de una venta o de una solicitud
de servicio. Este registro **no** crea una cuenta de usuario, no otorga
ningún acceso al sistema y no constituye un módulo de gestión de clientes.

---

## 3. Glosario

| Término | Definición |
|---|---|
| **Usuario** | Persona del personal de PC-Solution con una cuenta en el sistema. |
| **Rol** | Conjunto de permisos asignado a un usuario: Administrador, Encargado de Ventas o Encargado de Servicios. |
| **Cuenta bloqueada** | Cuenta que existe en el sistema pero cuyo titular no puede iniciar sesión. |
| **Categoría** | Agrupación de productos del catálogo (p. ej. laptops, periféricos, redes). |
| **Producto** | Artículo del catálogo con nombre, descripción, precio, existencias e imagen. |
| **Existencias (stock)** | Cantidad disponible de un producto para la venta. |
| **Venta** | Registro de una transacción de venta con uno o más productos, sus cantidades y el contacto del cliente. |
| **Detalle de venta** | Línea de una venta: producto, cantidad, y nombre y precio unitario **congelados** al momento de la confirmación. |
| **Anulación** | Invalidación de una venta registrada por error, que devuelve las existencias al inventario. |
| **Solicitud de servicio** | Registro de un trabajo técnico pedido por un cliente, con su contacto, descripción del problema y seguimiento de estado. |
| **Usuario registrador** | Usuario que dio de alta la solicitud de servicio. Queda fijo y no cambia nunca. |
| **Técnico asignado** | Usuario responsable de atender la solicitud. Puede ser distinto del registrador y puede reasignarse mientras la solicitud siga abierta. |
| **Monto cobrado** | Importe cobrado al cliente por un servicio técnico, registrado al finalizarlo. |
| **Servicio en taller** | Servicio atendido en las instalaciones de PC-Solution (mantenimiento, reparación). No requiere dirección. |
| **Servicio a domicilio** | Servicio atendido en el lugar del cliente (instalación de redes, videovigilancia). Requiere dirección. |
| **Observaciones del trabajo** | Descripción de lo realizado, obligatoria para poder finalizar un servicio. |
| **Existencias bajas** | Producto cuya cantidad disponible es menor o igual al umbral de alerta. |
| **Umbral de existencias bajas** | Único número, global para todo el catálogo, configurable por el Administrador, a partir del cual un producto se considera con existencias bajas. |

---

## 4. Actores del sistema

Todos los actores son **personal interno** de PC-Solution. No existe
ningún actor externo que interactúe con el sistema.

### 4.1 Administrador

Responsable de la gestión integral del sistema.

- Gestiona el catálogo completo: categorías y productos.
- Consulta **todas** las ventas de la empresa y puede anularlas.
- Consulta **todas** las solicitudes de servicio y puede gestionarlas.
- Crea, edita, bloquea y desbloquea cuentas de usuario, y asigna roles.
- Asigna y reasigna el técnico responsable de cualquier solicitud abierta.
- Configura el umbral global de existencias bajas.
- Accede al panel de indicadores.
- Puede realizar, además, **todo lo que hacen los otros dos roles**
  (registrar ventas y registrar/atender servicios).

### 4.2 Encargado de Ventas

Responsable de la atención comercial.

- Consulta el catálogo y las existencias disponibles.
- Registra ventas, incluyendo nombre y teléfono de contacto del cliente.
- Consulta **su propio** historial de ventas.
- Anula una venta **propia** registrada por error, sin límite de plazo.
- No gestiona el catálogo, ni usuarios, ni servicios técnicos, ni accede
  al panel de indicadores.

### 4.3 Encargado de Servicios

Responsable de la atención técnica.

- Registra solicitudes de servicio técnico (mantenimiento, reparación,
  instalación de redes, videovigilancia) con el contacto del cliente y la
  descripción del problema.
- Consulta **todas** las solicitudes del área, no solo las que él
  registró, de modo que pueda continuar el trabajo de un compañero.
- Asigna o reasigna el técnico responsable de una solicitud abierta,
  pudiendo asignársela a sí mismo.
- Actualiza el estado de **cualquier** solicitud abierta conforme avanza
  la atención.
- Registra observaciones del trabajo realizado y el monto cobrado, y
  finaliza el servicio.
- No gestiona el catálogo, ni usuarios, ni ventas, ni accede al panel de
  indicadores.

> **Contraste deliberado con ventas:** la información de servicios es
> **compartida** dentro del área (cualquier encargado puede retomar una
> solicitud), mientras que el historial de ventas sigue siendo **privado
> por usuario** (cada encargado ve y anula solo lo suyo). Esta asimetría
> es intencional: un servicio es un trabajo en curso que puede cambiar de
> manos, una venta es un hecho consumado imputable a quien la registró.

### 4.4 Matriz de permisos

| Funcionalidad | Administrador | Enc. de Ventas | Enc. de Servicios |
|---|:--:|:--:|:--:|
| Iniciar sesión / cerrar sesión | ✔ | ✔ | ✔ |
| Cambiar la propia contraseña | ✔ | ✔ | ✔ |
| Gestionar categorías (crear/editar/eliminar) | ✔ | ✘ | ✘ |
| Gestionar productos (crear/editar/eliminar) | ✔ | ✘ | ✘ |
| Configurar el umbral global de existencias bajas | ✔ | ✘ | ✘ |
| Consultar catálogo y existencias | ✔ | ✔ | ✘ |
| Registrar una venta | ✔ | ✔ | ✘ |
| Consultar las ventas propias | ✔ | ✔ | ✘ |
| Consultar **todas** las ventas | ✔ | ✘ | ✘ |
| Anular una venta propia | ✔ | ✔ | ✘ |
| Anular **cualquier** venta | ✔ | ✘ | ✘ |
| Registrar una solicitud de servicio | ✔ | ✘ | ✔ |
| Consultar **todas** las solicitudes de servicio | ✔ | ✘ | ✔ |
| Asignar / reasignar el técnico de una solicitud abierta | ✔ | ✘ | ✔ |
| Actualizar el estado de **cualquier** solicitud abierta | ✔ | ✘ | ✔ |
| Registrar observaciones y monto, y finalizar un servicio | ✔ | ✘ | ✔ |
| Cancelar una solicitud abierta | ✔ | ✘ | ✔ |
| Gestionar cuentas de usuario y roles | ✔ | ✘ | ✘ |
| Ver el panel de indicadores | ✔ | ✘ | ✘ |

---

## 5. Casos de uso

Notación: **CU-\<módulo\>-\<n\>**. Cada caso de uso indica actor,
precondición, flujo principal, flujos alternativos y postcondición.

### 5.1 Autenticación y cuenta propia

#### CU-AUT-01 — Iniciar sesión
- **Actor:** cualquier usuario con cuenta activa.
- **Precondición:** la cuenta existe y no está bloqueada.
- **Flujo principal:** el usuario ingresa sus credenciales; el sistema las
  verifica y le da acceso a las funcionalidades correspondientes a su rol.
- **Alternativos:**
  - Credenciales inválidas → el sistema rechaza el acceso con un mensaje
    genérico, sin revelar si el usuario existe o si la contraseña es la
    incorrecta.
  - Cuenta bloqueada → el sistema rechaza el acceso e informa que la
    cuenta está inhabilitada.
- **Postcondición:** el usuario queda autenticado y su sesión identificada.

#### CU-AUT-02 — Cerrar sesión
- **Actor:** usuario autenticado.
- **Flujo principal:** el usuario cierra su sesión; el sistema invalida su
  acceso y lo devuelve a la pantalla de ingreso.
- **Postcondición:** las credenciales de sesión dejan de ser válidas.

#### CU-AUT-03 — Cambiar la propia contraseña
- **Actor:** usuario autenticado.
- **Flujo principal:** el usuario indica su contraseña actual y la nueva;
  el sistema verifica la actual, valida que la nueva cumpla la política
  mínima y la reemplaza.
- **Alternativos:** contraseña actual incorrecta o nueva contraseña que no
  cumple la política → se rechaza el cambio.
- **Postcondición:** la contraseña queda actualizada y cifrada.

### 5.2 Catálogo e inventario

#### CU-CAT-01 — Gestionar categorías
- **Actor:** Administrador.
- **Flujo principal:** crea, edita o elimina una categoría (nombre y
  descripción).
- **Alternativos:**
  - Nombre duplicado → se rechaza.
  - Eliminación de una categoría con productos asociados → se rechaza e
    informa que primero debe reasignar o eliminar esos productos.
- **Postcondición:** el catálogo de categorías queda actualizado.

#### CU-CAT-02 — Registrar un producto
- **Actor:** Administrador.
- **Precondición:** existe al menos una categoría.
- **Flujo principal:** registra nombre, descripción, precio, existencias
  iniciales, categoría e imagen del producto.
- **Alternativos:** datos inválidos (precio negativo, existencias
  negativas, nombre duplicado, imagen de formato o tamaño no permitido) →
  se rechaza indicando el error.
- **Postcondición:** el producto queda disponible en el catálogo.

#### CU-CAT-03 — Editar un producto
- **Actor:** Administrador.
- **Flujo principal:** modifica cualquiera de los datos del producto,
  incluidas las existencias (ajuste de inventario).
- **Postcondición:** el producto queda actualizado. Las ventas ya
  confirmadas **no** se ven afectadas (ver RN-VEN-04).

#### CU-CAT-04 — Eliminar un producto
- **Actor:** Administrador.
- **Flujo principal:** el Administrador retira un producto del catálogo;
  el sistema lo deja de ofrecer para nuevas ventas.
- **Alternativos:** el producto aparece en ventas históricas → el sistema
  conserva intacto el historial (RN-VEN-04) y retira el producto solo de
  la oferta vigente.
- **Postcondición:** el producto ya no puede seleccionarse en una venta
  nueva; el historial permanece legible.

#### CU-CAT-05 — Consultar el catálogo y las existencias
- **Actor:** Administrador, Encargado de Ventas.
- **Flujo principal:** consulta la lista de productos con su categoría,
  precio e existencias disponibles, con búsqueda por nombre y filtro por
  categoría.
- **Postcondición:** ninguna (consulta).

#### CU-CAT-06 — Configurar el umbral de existencias bajas
- **Actor:** Administrador.
- **Flujo principal:** el Administrador consulta el umbral vigente y lo
  modifica por un número entero no negativo; el sistema lo aplica de
  inmediato a **todo** el catálogo.
- **Alternativos:** valor negativo o no entero → se rechaza.
- **Postcondición:** el nuevo umbral rige el indicador de existencias
  bajas y las alertas del catálogo.

### 5.3 Registro de ventas

#### CU-VEN-01 — Registrar una venta
- **Actor:** Encargado de Ventas, Administrador.
- **Precondición:** existen productos con existencias disponibles.
- **Flujo principal:**
  1. El usuario registra el nombre y teléfono de contacto del cliente.
  2. Agrega uno o más productos indicando la cantidad de cada uno.
  3. El sistema calcula el subtotal por línea y el total de la venta.
  4. Al confirmar, el sistema valida que haya existencias suficientes de
     cada producto, descuenta el inventario, congela nombre y precio
     unitario de cada producto en el detalle, y registra la venta a nombre
     del usuario que la realizó con su fecha y hora.
- **Alternativos:**
  - Existencias insuficientes de algún producto → la venta **no** se
    confirma; ningún producto se descuenta y el sistema indica cuáles
    faltan y cuánto hay disponible.
  - Venta sin productos o con cantidad cero o negativa → se rechaza.
  - Datos de contacto del cliente incompletos → se rechaza.
- **Postcondición:** la venta queda registrada en estado *Confirmada* y el
  inventario refleja el descuento.

#### CU-VEN-02 — Consultar el historial de ventas
- **Actor:** Encargado de Ventas (solo las propias), Administrador (todas).
- **Flujo principal:** consulta la lista de ventas con fecha, cliente,
  total, estado y responsable, con filtro por rango de fechas y estado, y
  puede abrir el detalle de cada una.
- **Postcondición:** ninguna (consulta).

#### CU-VEN-03 — Anular una venta
- **Actor:** Encargado de Ventas (solo las propias), Administrador
  (cualquiera).
- **Precondición:** la venta está en estado *Confirmada*. No existe
  límite de plazo para anularla.
- **Flujo principal:** el usuario solicita la anulación indicando el
  motivo; el sistema pide confirmación, devuelve las existencias de cada
  producto del detalle al inventario y marca la venta como *Anulada*,
  registrando quién la anuló, cuándo y por qué.
- **Alternativos:**
  - La venta ya está anulada → se rechaza.
  - Un producto del detalle fue eliminado del catálogo → las existencias
    de los productos aún vigentes se devuelven igualmente y el sistema
    informa cuáles no pudieron reponerse.
- **Postcondición:** la venta queda *Anulada*, no se elimina, y el
  inventario refleja la devolución.

### 5.4 Servicios técnicos

#### CU-SER-01 — Registrar una solicitud de servicio
- **Actor:** Encargado de Servicios, Administrador.
- **Flujo principal:**
  1. El usuario selecciona el tipo de servicio: mantenimiento, reparación,
     instalación de redes o videovigilancia.
  2. Registra nombre y teléfono de contacto del cliente y la descripción
     del problema o del trabajo solicitado.
  3. Si el tipo de servicio se atiende **a domicilio** (instalación de
     redes, videovigilancia), el sistema exige además la dirección. Si se
     atiende **en taller** (mantenimiento, reparación), la dirección no se
     solicita.
  4. Opcionalmente indica ya el **técnico asignado**; si no lo hace, la
     solicitud queda sin asignar a la espera de CU-SER-06.
  5. El sistema registra la solicitud en estado *Registrada*, con fecha,
     hora y el **usuario registrador**.
- **Alternativos:**
  - Datos obligatorios faltantes (incluida la dirección cuando
    corresponde) → se rechaza el registro.
  - Técnico indicado que no es una cuenta activa con rol habilitado para
    atender servicios → se rechaza (RN-SER-10).
- **Postcondición:** la solicitud queda registrada y visible para todo el
  personal de servicios.

#### CU-SER-02 — Actualizar el estado de una solicitud
- **Actor:** Encargado de Servicios (cualquier solicitud abierta),
  Administrador (cualquiera).
- **Precondición:** la solicitud no está en un estado terminal.
- **Flujo principal:** el usuario avanza la solicitud al siguiente estado
  válido (ver RN-SER-02); el sistema registra el cambio con su fecha, hora
  y autor en el historial.
- **Alternativos:**
  - Transición no permitida → se rechaza.
  - Paso a *En atención* sin técnico asignado → se rechaza, y el sistema
    ofrece asignar uno (RN-SER-11).
- **Postcondición:** la solicitud refleja el nuevo estado y su historial
  de cambios.

#### CU-SER-03 — Registrar observaciones, monto cobrado y finalizar
- **Actor:** Encargado de Servicios (cualquier solicitud abierta),
  Administrador (cualquiera).
- **Precondición:** la solicitud está en estado *En atención* y tiene
  técnico asignado.
- **Flujo principal:** el usuario registra las **observaciones del
  trabajo realizado** y el **monto cobrado** al cliente, y finaliza el
  servicio; el sistema lo marca como *Finalizado* con su fecha y hora de
  cierre y con el autor del cierre.
- **Alternativos:**
  - Intento de finalizar sin observaciones registradas → se rechaza
    (RN-SER-03).
  - Intento de finalizar sin monto cobrado → se rechaza (RN-SER-13). Un
    servicio sin cargo se registra con monto cero, no dejándolo vacío.
  - Monto negativo → se rechaza.
- **Postcondición:** la solicitud queda *Finalizada*, ya no admite
  cambios de estado, y su monto pasa a contar en los ingresos por
  servicios del panel de indicadores.

#### CU-SER-04 — Cancelar una solicitud
- **Actor:** Encargado de Servicios (cualquier solicitud abierta),
  Administrador (cualquiera).
- **Precondición:** la solicitud no está *Finalizada* ni *Cancelada*.
- **Flujo principal:** el usuario cancela la solicitud indicando el
  motivo; el sistema la marca como *Cancelada* registrando autor y fecha.
- **Postcondición:** la solicitud queda cerrada sin atención y sin monto
  cobrado; no cuenta como ingreso (RN-SER-14).

#### CU-SER-05 — Consultar las solicitudes de servicio
- **Actor:** Encargado de Servicios (todas), Administrador (todas).
- **Flujo principal:** consulta la lista de solicitudes con cliente, tipo,
  estado, fecha, usuario registrador y técnico asignado; filtra por
  estado, tipo, rango de fechas y técnico asignado —incluido un filtro
  rápido «asignadas a mí» y otro de «sin asignar»— y abre el detalle de
  cada una con su historial de cambios.
- **Postcondición:** ninguna (consulta).

#### CU-SER-06 — Asignar o reasignar el técnico responsable
- **Actor:** Encargado de Servicios, Administrador.
- **Precondición:** la solicitud no está en un estado terminal.
- **Flujo principal:** el usuario selecciona al técnico responsable entre
  las cuentas activas habilitadas para atender servicios —pudiendo
  elegirse a sí mismo para retomar el trabajo de un compañero— y confirma
  la asignación; el sistema registra el cambio en el historial con el
  técnico anterior, el nuevo, el autor y el momento.
- **Alternativos:**
  - Solicitud ya *Finalizada* o *Cancelada* → se rechaza (RN-SER-12).
  - Cuenta elegida bloqueada o sin rol habilitado → se rechaza
    (RN-SER-10).
- **Postcondición:** la solicitud queda a cargo del nuevo técnico y el
  cambio es trazable.

### 5.5 Gestión de usuarios

#### CU-USU-01 — Crear una cuenta de usuario
- **Actor:** Administrador.
- **Flujo principal:** registra los datos del empleado (nombre,
  identificador de acceso, contraseña inicial) y le asigna exactamente un
  rol; la cuenta queda activa.
- **Alternativos:** identificador ya existente o contraseña que no cumple
  la política mínima → se rechaza.
- **Postcondición:** el empleado puede iniciar sesión con los permisos de
  su rol.

#### CU-USU-02 — Editar una cuenta y cambiar su rol
- **Actor:** Administrador.
- **Flujo principal:** modifica los datos de la cuenta y/o le asigna otro
  rol.
- **Alternativos:**
  - Intento de cambiar el **propio** rol → se rechaza (RN-USU-02).
  - El cambio dejaría al sistema sin ningún Administrador activo → se
    rechaza (RN-USU-04).
- **Postcondición:** la cuenta queda actualizada y los permisos efectivos
  se aplican desde ese momento.

#### CU-USU-03 — Bloquear o desbloquear una cuenta
- **Actor:** Administrador.
- **Flujo principal:** bloquea una cuenta para impedir su acceso, o la
  desbloquea para restituirlo.
- **Alternativos:**
  - Intento de bloquearse a **sí mismo** → se rechaza (RN-USU-03).
  - El bloqueo dejaría al sistema sin ningún Administrador activo → se
    rechaza (RN-USU-04).
- **Postcondición:** el acceso de la cuenta queda impedido o restituido.
  El historial de ventas y servicios de esa cuenta se conserva intacto.

#### CU-USU-04 — Restablecer la contraseña de un usuario
- **Actor:** Administrador.
- **Flujo principal:** asigna una nueva contraseña a la cuenta de otro
  usuario, que este podrá cambiar después.
- **Postcondición:** la contraseña anterior deja de ser válida.

#### CU-USU-05 — Consultar las cuentas del personal
- **Actor:** Administrador.
- **Flujo principal:** consulta la lista de cuentas con su rol y estado
  (activa o bloqueada), con búsqueda por nombre y filtro por rol.
- **Postcondición:** ninguna (consulta).

### 5.6 Panel de indicadores

#### CU-PAN-01 — Consultar el panel de indicadores
- **Actor:** Administrador.
- **Flujo principal:** el sistema muestra un resumen visual con, al menos:
  - **Ventas del día:** cantidad de ventas confirmadas e importe total
    acumulado de la jornada.
  - **Ingresos por servicios del día:** cantidad de servicios finalizados
    en la jornada y suma de sus montos cobrados.
  - **Ingreso total del día:** suma de ambos orígenes, mostrando de forma
    diferenciada cuánto proviene de ventas y cuánto de servicios.
  - **Servicios pendientes:** cantidad de solicitudes en estado
    *Registrada* o *En atención*, desglosando cuántas están **sin técnico
    asignado**.
  - **Productos con existencias bajas:** lista de productos cuya
    existencia está en el umbral global de alerta o por debajo.
- **Postcondición:** ninguna (consulta).

---

## 6. Reglas de negocio

### 6.1 Acceso y roles

- **RN-ACC-01** — Ninguna funcionalidad del sistema, salvo el propio
  inicio de sesión, es accesible sin autenticación.
- **RN-ACC-02** — Cada usuario tiene **exactamente un** rol.
- **RN-ACC-03** — El Administrador hereda todas las capacidades del
  Encargado de Ventas y del Encargado de Servicios.
- **RN-ACC-04** — El control de acceso por rol se verifica en el servidor
  en **cada** operación; ocultar una opción en la interfaz nunca se
  considera control de acceso.
- **RN-ACC-05** — Una cuenta bloqueada no puede iniciar sesión, y sus
  sesiones activas dejan de tener efecto.

### 6.2 Usuarios

- **RN-USU-01** — Ningún rol se autoasigna: solo el Administrador crea
  cuentas y asigna o cambia roles.
- **RN-USU-02** — Ningún usuario puede cambiar su **propio** rol.
- **RN-USU-03** — Ningún usuario puede bloquearse a **sí mismo**.
- **RN-USU-04** — El sistema nunca debe quedar sin **al menos un
  Administrador activo**: se rechaza cualquier cambio de rol o bloqueo que
  dejara cero administradores activos.
- **RN-USU-05** — Las cuentas no se eliminan; se bloquean, de modo que el
  historial de ventas y servicios conserve siempre a su responsable.
- **RN-USU-06** — El identificador de acceso es único en todo el sistema.

### 6.3 Catálogo e inventario

- **RN-CAT-01** — El precio de un producto es mayor que cero.
- **RN-CAT-02** — Las existencias de un producto nunca son negativas.
- **RN-CAT-03** — El nombre de una categoría es único; el nombre de un
  producto es único dentro del catálogo.
- **RN-CAT-04** — Una categoría con productos asociados no puede
  eliminarse.
- **RN-CAT-05** — Un producto sin existencias sigue visible en el catálogo
  pero no puede agregarse a una venta.
- **RN-CAT-06** — La imagen del producto es opcional; si no se carga, el
  sistema muestra una imagen genérica.
- **RN-CAT-07** — El umbral de existencias bajas es **un único valor
  global** para todo el catálogo, entero y no negativo, configurable solo
  por el Administrador. No se define por producto ni por categoría. Su
  modificación surte efecto inmediato y no altera ningún dato histórico.

### 6.4 Ventas

- **RN-VEN-01** — Una venta tiene al menos una línea de detalle, y cada
  línea tiene cantidad mayor que cero.
- **RN-VEN-02** — Una venta solo se confirma si **todos** sus productos
  tienen existencias suficientes: la confirmación es **todo o nada**,
  nunca parcial.
- **RN-VEN-03** — Al confirmar la venta, el sistema descuenta del
  inventario la cantidad vendida de cada producto.
- **RN-VEN-04** — El nombre y el precio unitario del producto se
  **congelan** en el detalle al confirmar la venta. Modificar o eliminar
  el producto después **no** altera ninguna venta histórica.
- **RN-VEN-05** — El total de la venta es la suma de los subtotales de sus
  líneas, y cada subtotal es el precio congelado por la cantidad.
- **RN-VEN-06** — Una venta confirmada **no se edita ni se elimina**; el
  único cambio posible es su anulación.
- **RN-VEN-07** — La anulación devuelve al inventario las existencias de
  cada producto del detalle y exige un motivo.
- **RN-VEN-08** — Una venta anulada no puede anularse otra vez, ni cuenta
  en los indicadores de ventas del día.
- **RN-VEN-09** — Toda venta queda asociada al usuario que la registró y a
  su fecha y hora, dato que no cambia nunca.
- **RN-VEN-10** — El nombre y el teléfono de contacto del cliente son
  obligatorios en toda venta, y son un dato de la venta: no crean cuenta
  ni acceso alguno.
- **RN-VEN-11** — La anulación **no tiene límite de plazo**: una venta
  confirmada puede anularse en cualquier momento posterior, sin importar
  cuánto tiempo haya pasado desde su registro. La trazabilidad de quién
  anuló, cuándo y por qué (RN-VEN-07) es el control que sustituye a
  cualquier restricción temporal.

### 6.5 Servicios técnicos

- **RN-SER-01** — Los tipos de servicio son: **mantenimiento**,
  **reparación**, **instalación de redes** y **videovigilancia**.
  Mantenimiento y reparación se atienden **en taller**; instalación de
  redes y videovigilancia se atienden **a domicilio**.
- **RN-SER-02** — Los estados de una solicitud y sus transiciones válidas
  son:

  ```
                 [1]              [2]
  Registrada ──────────► En atención ──────────► Finalizada
       │                      │
       └──────────────────────┴──────────────► Cancelada
                                 [3]

  [1] exige técnico asignado ............................. RN-SER-11
  [2] exige observaciones del trabajo y monto cobrado .... RN-SER-03, RN-SER-13
  [3] exige motivo de cancelación ........................ RN-SER-07
  ```

  *Finalizada* y *Cancelada* son estados terminales: no admiten
  transiciones posteriores. No se permite retroceder de estado.

- **RN-SER-03** — Una solicitud **no puede finalizarse** sin observaciones
  del trabajo realizado previamente registradas.
- **RN-SER-04** — La dirección es **obligatoria** para los servicios a
  domicilio y **no se solicita** para los servicios en taller.
- **RN-SER-05** — El nombre y el teléfono de contacto del cliente y la
  descripción del problema son obligatorios en toda solicitud.
- **RN-SER-06** — Toda solicitud queda asociada al usuario que la registró
  y a su fecha y hora; cada cambio de estado registra su autor y momento.
- **RN-SER-07** — La cancelación exige un motivo.
- **RN-SER-08** — Las solicitudes no se eliminan; se cancelan.

#### Técnico asignado (PA-05)

- **RN-SER-09** — Una solicitud distingue dos responsables:
  el **usuario registrador**, que queda fijo desde el alta y **nunca
  cambia**, y el **técnico asignado**, que puede estar vacío al inicio y
  puede cambiar mientras la solicitud siga abierta. Los indicadores de
  productividad y la trazabilidad usan ambos datos, nunca los confunden.
- **RN-SER-10** — Solo puede ser técnico asignado una cuenta **activa**
  con rol **Encargado de Servicios** o **Administrador**. Si la cuenta
  del técnico asignado se bloquea después, la solicitud conserva el dato
  histórico y el sistema la señala como pendiente de reasignación.
- **RN-SER-11** — Una solicitud **no puede pasar a *En atención*** sin un
  técnico asignado. Es la contrapartida de RN-SER-03: así como no se
  cierra un trabajo sin decir qué se hizo, no se empieza sin decir quién
  lo hace.
- **RN-SER-12** — La asignación y la reasignación solo son posibles
  mientras la solicitud no esté en un estado terminal. Cada cambio queda
  en el historial con técnico anterior, técnico nuevo, autor y momento.
- **RN-SER-15** — La información de servicios es **compartida** dentro
  del área: todo Encargado de Servicios puede consultar y actuar sobre
  cualquier solicitud abierta, esté o no asignada a él. Esto contrasta
  deliberadamente con las ventas, cuyo historial es privado por usuario
  (RN-VEN-09), y es lo que permite continuar el trabajo de un compañero.

#### Monto cobrado (PA-03)

- **RN-SER-13** — Para finalizar una solicitud es obligatorio registrar,
  además de las observaciones, el **monto cobrado** al cliente. El monto
  es un número no negativo: un servicio en garantía o de cortesía se
  registra con monto **cero**, nunca se deja vacío.
- **RN-SER-14** — Una solicitud *Cancelada* no registra monto y **no
  cuenta** como ingreso. Solo los servicios *Finalizados* aportan a los
  indicadores de ingresos.
- **RN-SER-16** — El monto cobrado se registra una sola vez, en el acto
  de finalizar, y forma parte del cierre **inmutable** de la solicitud:
  una vez finalizada, ni el monto ni las observaciones se editan. Un
  cierre equivocado se corrige registrando una nueva solicitud, del mismo
  modo que una venta errónea se corrige anulándola.

### 6.6 Indicadores

- **RN-IND-01** — «Ventas del día» considera únicamente las ventas
  confirmadas de la fecha actual; las anuladas quedan excluidas.
- **RN-IND-02** — «Servicios pendientes» considera las solicitudes en
  estado *Registrada* o *En atención*, sin límite de fecha, y desglosa
  cuántas de ellas no tienen técnico asignado.
- **RN-IND-03** — «Productos con existencias bajas» considera los
  productos cuya existencia es menor o igual al **umbral global**
  vigente (RN-CAT-07).
- **RN-IND-04** — «Ingresos por servicios del día» es la suma de los
  montos cobrados de las solicitudes **finalizadas en la fecha actual**;
  las canceladas y las aún abiertas quedan excluidas. Una solicitud
  aporta al indicador por su **fecha de cierre**, no por su fecha de
  registro.
- **RN-IND-05** — «Ingreso total del día» es la suma de las ventas
  confirmadas del día (RN-IND-01) y de los ingresos por servicios del día
  (RN-IND-04), y siempre se presenta desglosado por origen: el sistema
  nunca muestra un total que impida distinguir cuánto vino de ventas y
  cuánto de servicios.

---

## 7. Requerimientos funcionales

### 7.1 Autenticación y cuenta propia

| ID | Requerimiento |
|---|---|
| RF-01 | El sistema debe permitir a un usuario registrado iniciar sesión con sus credenciales. |
| RF-02 | El sistema debe rechazar el acceso de credenciales inválidas con un mensaje genérico que no revele si el usuario existe. |
| RF-03 | El sistema debe impedir el inicio de sesión de cuentas bloqueadas. |
| RF-04 | El sistema debe permitir al usuario cerrar su sesión. |
| RF-05 | El sistema debe permitir a cada usuario cambiar su propia contraseña verificando la anterior. |
| RF-06 | El sistema debe mostrar a cada usuario únicamente las opciones correspondientes a su rol. |

### 7.2 Catálogo e inventario

| ID | Requerimiento |
|---|---|
| RF-07 | El sistema debe permitir al Administrador crear, editar y eliminar categorías. |
| RF-08 | El sistema debe impedir eliminar una categoría con productos asociados. |
| RF-09 | El sistema debe permitir al Administrador registrar productos con nombre, descripción, precio, existencias, categoría e imagen. |
| RF-10 | El sistema debe permitir al Administrador editar cualquier dato de un producto, incluidas sus existencias. |
| RF-11 | El sistema debe permitir al Administrador retirar un producto del catálogo conservando intacto el historial de ventas que lo incluya. |
| RF-12 | El sistema debe permitir al Administrador y al Encargado de Ventas consultar el catálogo con las existencias disponibles. |
| RF-13 | El sistema debe permitir buscar productos por nombre y filtrarlos por categoría. |
| RF-14 | El sistema debe validar que el precio sea mayor que cero y las existencias no negativas. |
| RF-52 | El sistema debe permitir al Administrador consultar y modificar el umbral global de existencias bajas, como un único valor entero no negativo aplicable a todo el catálogo. |
| RF-53 | El sistema debe señalar visualmente, en el catálogo, los productos cuya existencia esté en el umbral global o por debajo. |

### 7.3 Ventas

| ID | Requerimiento |
|---|---|
| RF-15 | El sistema debe permitir registrar una venta con nombre y teléfono de contacto del cliente y una o más líneas de producto con su cantidad. |
| RF-16 | El sistema debe calcular y mostrar el subtotal de cada línea y el total de la venta antes de confirmarla. |
| RF-17 | El sistema debe validar, antes de confirmar, que todos los productos tengan existencias suficientes, e indicar cuáles faltan y su disponibilidad. |
| RF-18 | El sistema debe descontar las existencias de todos los productos al confirmar la venta, de forma completa o no realizarla en absoluto. |
| RF-19 | El sistema debe congelar el nombre y el precio unitario de cada producto en el detalle de la venta al confirmarla. |
| RF-20 | El sistema debe registrar en cada venta el usuario responsable y la fecha y hora de la operación. |
| RF-21 | El sistema debe permitir al Encargado de Ventas consultar su propio historial de ventas y al Administrador consultar todas. |
| RF-22 | El sistema debe permitir filtrar el historial de ventas por rango de fechas y por estado. |
| RF-23 | El sistema debe permitir consultar el detalle completo de una venta. |
| RF-24 | El sistema debe permitir anular una venta confirmada indicando el motivo, previa confirmación del usuario. |
| RF-25 | El sistema debe devolver al inventario las existencias de los productos al anular una venta. |
| RF-26 | El sistema debe impedir editar o eliminar una venta confirmada. |
| RF-27 | El sistema debe impedir que un Encargado de Ventas anule una venta registrada por otro usuario. |
| RF-54 | El sistema debe permitir anular una venta confirmada sin imponer ningún límite de plazo desde su registro. |

### 7.4 Servicios técnicos

| ID | Requerimiento |
|---|---|
| RF-28 | El sistema debe permitir registrar una solicitud de servicio indicando tipo, contacto del cliente y descripción del problema. |
| RF-29 | El sistema debe exigir la dirección solo cuando el tipo de servicio se atiende a domicilio. |
| RF-30 | El sistema debe registrar toda solicitud nueva en estado *Registrada*, con su usuario registrador y fecha y hora. |
| RF-31 | El sistema debe permitir avanzar el estado de una solicitud únicamente por transiciones válidas. |
| RF-32 | El sistema debe permitir registrar observaciones del trabajo realizado en una solicitud. |
| RF-33 | El sistema debe impedir finalizar una solicitud que no tenga observaciones registradas. |
| RF-34 | El sistema debe permitir cancelar una solicitud no terminal indicando el motivo. |
| RF-35 | El sistema debe registrar el autor y el momento de cada cambio de estado de una solicitud. |
| RF-36 | El sistema debe permitir al Encargado de Servicios y al Administrador consultar **todas** las solicitudes de servicio, con independencia de quién las registró o tenga asignadas. |
| RF-37 | El sistema debe permitir filtrar las solicitudes por estado, tipo y rango de fechas. |
| RF-38 | El sistema debe permitir consultar el detalle de una solicitud con su historial de cambios. |
| RF-55 | El sistema debe registrar en cada solicitud el usuario registrador y el técnico asignado como dos datos distintos, permitiendo que el segundo esté vacío al inicio. |
| RF-56 | El sistema debe permitir asignar y reasignar el técnico responsable de una solicitud no terminal, incluida la autoasignación. |
| RF-57 | El sistema debe ofrecer como técnico asignable únicamente las cuentas activas con rol Encargado de Servicios o Administrador. |
| RF-58 | El sistema debe impedir que una solicitud pase a *En atención* sin un técnico asignado. |
| RF-59 | El sistema debe registrar en el historial cada asignación y reasignación, con técnico anterior, técnico nuevo, autor y momento. |
| RF-60 | El sistema debe permitir filtrar las solicitudes por técnico asignado, incluyendo los filtros rápidos «asignadas a mí» y «sin asignar». |
| RF-61 | El sistema debe exigir el registro del monto cobrado, junto con las observaciones, como condición para finalizar una solicitud. |
| RF-62 | El sistema debe aceptar un monto cobrado de cero y rechazar montos negativos. |
| RF-63 | El sistema debe impedir la edición del monto cobrado y de las observaciones una vez finalizada la solicitud. |
| RF-64 | El sistema debe señalar las solicitudes abiertas cuyo técnico asignado corresponda a una cuenta bloqueada, como pendientes de reasignación. |

### 7.5 Gestión de usuarios

| ID | Requerimiento |
|---|---|
| RF-39 | El sistema debe permitir al Administrador crear cuentas de usuario asignándoles un rol. |
| RF-40 | El sistema debe permitir al Administrador editar los datos de una cuenta y cambiar su rol. |
| RF-41 | El sistema debe permitir al Administrador bloquear y desbloquear cuentas. |
| RF-42 | El sistema debe permitir al Administrador restablecer la contraseña de cualquier cuenta. |
| RF-43 | El sistema debe permitir al Administrador consultar las cuentas con su rol y estado, con búsqueda por nombre y filtro por rol. |
| RF-44 | El sistema debe impedir que un usuario cambie su propio rol. |
| RF-45 | El sistema debe impedir que un usuario bloquee su propia cuenta. |
| RF-46 | El sistema debe impedir cualquier operación que deje al sistema sin al menos un Administrador activo. |
| RF-47 | El sistema debe impedir el registro de dos cuentas con el mismo identificador de acceso. |

### 7.6 Panel de indicadores

| ID | Requerimiento |
|---|---|
| RF-48 | El sistema debe mostrar al Administrador la cantidad y el importe total de las ventas confirmadas del día. |
| RF-49 | El sistema debe mostrar al Administrador la cantidad de solicitudes de servicio pendientes, desglosando cuántas no tienen técnico asignado. |
| RF-50 | El sistema debe mostrar al Administrador la lista de productos con existencias bajas según el umbral global vigente. |
| RF-51 | El sistema debe presentar los indicadores de forma visual y permitir acceder desde ellos al módulo correspondiente. |
| RF-65 | El sistema debe mostrar al Administrador la cantidad de servicios finalizados en el día y la suma de sus montos cobrados. |
| RF-66 | El sistema debe mostrar al Administrador el ingreso total del día, diferenciando siempre el importe proveniente de ventas del proveniente de servicios. |

---

## 8. Requerimientos no funcionales

### 8.1 Seguridad

| ID | Requerimiento |
|---|---|
| RNF-01 | Ninguna funcionalidad, dato u operación es accesible sin autenticación. |
| RNF-02 | El control de acceso por rol se verifica en el servidor en cada operación, no solo en la interfaz. |
| RNF-03 | Las contraseñas se almacenan cifradas mediante un algoritmo de hash resistente; nunca en texto plano ni de forma reversible. |
| RNF-04 | Las contraseñas deben cumplir una política mínima de longitud y complejidad. |
| RNF-05 | El sistema valida todos los datos de entrada en el servidor, independientemente de la validación de la interfaz. |
| RNF-06 | Los mensajes de error no revelan información interna del sistema ni la existencia de cuentas. |
| RNF-07 | Las operaciones que modifican ventas, servicios, inventario o cuentas quedan asociadas a su autor y momento, de forma no alterable. |

### 8.2 Integridad y concurrencia

| ID | Requerimiento |
|---|---|
| RNF-08 | El descuento de existencias es seguro ante concurrencia: dos ventas simultáneas del mismo producto **nunca** pueden dejar el stock en negativo ni vender la misma unidad dos veces. |
| RNF-09 | El registro de una venta es atómico: o se guardan la venta, su detalle y el descuento de inventario completos, o no se guarda nada. |
| RNF-10 | La anulación de una venta es igualmente atómica respecto de la devolución de existencias. |
| RNF-11 | El historial de ventas y servicios es inmutable en sus datos congelados, incluso si los productos o las cuentas cambian después. |

### 8.3 Usabilidad

| ID | Requerimiento |
|---|---|
| RNF-12 | La interfaz es usable en distintos tamaños de pantalla (escritorio, portátil y tableta). |
| RNF-13 | La interfaz está íntegramente en español. |
| RNF-14 | Toda operación que modifica o elimina datos pide confirmación explícita e informa claramente su resultado. |
| RNF-15 | Los errores de validación se muestran junto al campo que los origina, con un mensaje comprensible para el usuario. |
| RNF-16 | Las tareas frecuentes (registrar una venta, registrar un servicio) se completan sin pasos innecesarios. |

### 8.4 Rendimiento y operación

| ID | Requerimiento |
|---|---|
| RNF-17 | Las consultas habituales (catálogo, historiales, panel) responden en menos de 3 segundos bajo carga normal de trabajo. |
| RNF-18 | Los listados extensos se presentan paginados. |
| RNF-19 | El sistema soporta el uso simultáneo de todo el personal de la empresa sin degradación perceptible. |

### 8.5 Mantenibilidad y trazabilidad del proyecto

| ID | Requerimiento |
|---|---|
| RNF-20 | El frontend y el backend son aplicaciones separadas que se comunican exclusivamente por la API; el frontend nunca accede a la base de datos directamente. |
| RNF-21 | El proyecto se versiona en un repositorio Git propio e independiente de cualquier otro proyecto. |
| RNF-22 | La especificación (`spec.md`), el plan técnico (`plan.md`) y el desglose de tareas (`tasks.md`) son documentos vivos: todo cambio funcional se refleja primero en ellos y luego en el código. |
| RNF-23 | Cada funcionalidad implementada cuenta con pruebas automatizadas que verifican sus reglas de negocio. |

---

## 9. Criterios de aceptación de la especificación

Esta etapa se considera aprobada cuando:

1. Los tres actores, sus permisos y sus límites reflejan la operación real
   de PC-Solution.
2. Los cinco módulos funcionales están cubiertos por casos de uso.
3. Las reglas de negocio críticas están explícitas y son verificables:
   congelado de precios (RN-VEN-04), confirmación todo-o-nada
   (RN-VEN-02), devolución de existencias en la anulación (RN-VEN-07),
   dirección condicional al tipo de servicio (RN-SER-04), observaciones
   obligatorias para finalizar (RN-SER-03) y las protecciones de la cuenta
   de Administrador (RN-USU-02 a RN-USU-04).
4. La separación entre usuario registrador y técnico asignado es explícita
   y trazable (RN-SER-09, RN-SER-12).
5. Los ingresos del panel distinguen siempre su origen (RN-IND-05).
6. El documento no contiene decisiones de implementación.

---

## 10. Supuestos

- **SUP-01** — *(Resuelto en v1.1 → RN-CAT-07.)* El umbral de «existencias
  bajas» es un único valor global configurable por el Administrador,
  igual para todos los productos.
- **SUP-02** — Una venta corresponde a un único cliente y se registra en
  un solo acto, sin apartados, reservas ni ventas parciales.
- **SUP-03** — Los precios se manejan en bolivianos (Bs) y no incluyen
  descuentos ni promociones.
- **SUP-04** — El sistema no registra la ubicación física del inventario
  (almacenes o sucursales): PC-Solution opera en un solo local.
- **SUP-05** — Un servicio técnico no consume productos del inventario; si
  el cliente compra repuestos, se registra como una venta aparte. El
  monto cobrado del servicio (RN-SER-13) cubre únicamente la mano de obra
  y el trabajo técnico.

---

## 11. Decisiones resueltas

Las cinco preguntas abiertas de la versión 1.0 fueron resueltas el
2026-09-22 y ya están incorporadas al cuerpo del documento.

| # | Pregunta | Decisión | Se refleja en |
|---|---|---|---|
| **PA-01** | ¿Umbral de existencias bajas global o por producto? | **Global**: un único número configurable para todo el catálogo. | RN-CAT-07, CU-CAT-06, RF-52, RF-53, RN-IND-03, SUP-01 |
| **PA-02** | ¿Plazo límite para anular una venta propia? | **Sin límite de plazo**; el control es la trazabilidad de la anulación. | RN-VEN-11, CU-VEN-03, RF-54 |
| **PA-03** | ¿El servicio técnico registra un monto cobrado? | **Sí**, obligatorio al finalizar junto con las observaciones, y alimenta los indicadores de ingresos. | RN-SER-13, RN-SER-14, RN-SER-16, CU-SER-03, RF-61 a RF-63, RN-IND-04, RN-IND-05, RF-65, RF-66 |
| **PA-04** | ¿El Encargado de Servicios ve solo lo suyo o todo el área? | **Todo el área**: visibilidad y actuación compartidas sobre cualquier solicitud abierta. | RN-SER-15, sección 4.3, matriz 4.4, CU-SER-02 a CU-SER-05, RF-36 |
| **PA-05** | ¿Técnico responsable distinto del registrador? | **Sí**: usuario registrador fijo + técnico asignado reasignable. | RN-SER-09 a RN-SER-12, CU-SER-06, RF-55 a RF-60, RF-64 |

### Consecuencias de PA-04 y PA-05 sobre el modelo de permisos

La combinación de ambas decisiones cambia el modelo de autorización del
módulo de servicios respecto de la versión 1.0:

1. **La autorización de servicios deja de ser por propiedad y pasa a ser
   por rol.** En la v1.0, un Encargado de Servicios solo podía actuar
   sobre lo que él había registrado. Ahora basta con tener el rol para
   consultar y actuar sobre cualquier solicitud abierta (RN-SER-15). El
   técnico asignado indica **de quién es el trabajo**, no **quién tiene
   permiso**: no es un mecanismo de control de acceso.
2. **Ventas y servicios quedan asimétricos, y es intencional.** Las
   ventas conservan la autorización por propiedad (RF-27): un Encargado
   de Ventas sigue viendo y anulando solo las suyas. Un servicio es
   trabajo en curso que cambia de manos; una venta es un hecho consumado
   imputable a quien la registró.
3. **La trazabilidad sustituye a la restricción.** Como cualquier
   encargado puede tocar cualquier solicitud, el historial de cambios
   (RF-35, RF-59) deja de ser un accesorio y pasa a ser el control
   principal de responsabilidad del módulo: sin él, no habría forma de
   saber quién hizo qué sobre una solicitud compartida.
4. **Aparece un estado operativo nuevo:** la solicitud *sin técnico
   asignado*, que el panel debe visibilizar (RF-49) porque representa
   trabajo que nadie ha tomado.
