# Especificación Funcional — Sistema ERP PC-Solution

- **Proyecto:** Sistema ERP interno para PC-Solution (Sucre, Bolivia)
- **Documento:** Etapa 1 de Spec-Driven Development — Especificación funcional
- **Versión:** 1.4
- **Fecha:** 2026-10-08
- **Estado:** **Aprobada** el 2026-10-08 — la v1.3 está implementada; la
  v1.4 está aprobada y pendiente de implementar. Incorpora las decisiones
  PA-01 a PA-08 (secciones 11 y 12)

### Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-09-22 | Versión inicial para revisión. |
| 1.1 | 2026-09-22 | Se resuelven las preguntas abiertas PA-01 a PA-05. Cambios principales: umbral global de existencias bajas configurable (PA-01); anulación de ventas sin plazo (PA-02); monto cobrado por servicio e indicador de ingresos por servicios (PA-03); visibilidad compartida de las solicitudes entre el personal de servicios (PA-04); técnico asignado distinto del usuario registrador (PA-05). |
| 1.2 | 2026-09-29 | **Se revisan PA-03, PA-04 y PA-05 antes de implementar el módulo de servicios.** El monto lo cotiza y registra el **Administrador** tras la revisión, no el técnico al finalizar (PA-03). Cada solicitud la ven **solo quien la registró y el Administrador**, no toda el área (PA-04). El técnico deja de ser una entidad asignable y pasa a ser **una anotación de texto libre** del Administrador (PA-05). Consecuencia notable: desaparece la asimetría entre ventas y servicios que la v1.1 declaraba intencional. |
| 1.3 | 2026-09-30 | **Se añade el informe en PDF de la solicitud de servicio (RF-67, RF-68).** Surge del uso real: el cliente deja su equipo y se va sin nada en la mano, y al recogerlo no hay forma de entregarle por escrito qué se le hizo. Es el único documento que sale del sistema hacia el cliente; §2.2 sigue excluyendo la facturación y el portal del cliente, y esto no lo contradice. |
| 1.4 | 2026-10-08 | **Cinco funcionalidades nuevas.** (1) **Código por producto** EAN-13 generado por el sistema e inmutable, con búsqueda por código y entrada por lector de código de barras en la venta. (2) **Garantía imprimible**: meses de garantía por producto, congelados en la venta, y PDF de garantía reutilizando el membrete del informe de servicio. (3) **Reportes por rango de fechas** con exportación a PDF y Excel. (4) **Historial de movimientos de stock**, inmutable y registrado en la misma transacción que el cambio de existencias; las existencias dejan de editarse con el resto del producto y pasan a ajustarse con motivo. (5) **Módulo de Clientes** como registro de datos de contacto: **cambia el alcance** de §2.1 y §2.3, pero los clientes siguen **sin cuenta, sin inicio de sesión y sin acceso**. Se revisan RN-VEN-10, CU-CAT-02, CU-CAT-03, CU-CAT-05, CU-VEN-01 y CU-VEN-03. **De paso se corrigen tres restos de la v1.1** que la revisión de la v1.2 no alcanzó: la definición de «Monto cobrado» del glosario, el desglose «sin técnico asignado» de CU-PAN-01, y la mención a un «técnico asignado» en el criterio 4 de §9. **Aprobada con tres decisiones** (§12): las solicitudes de servicio no usan Clientes hasta la v1.5 (PA-06); se añade un **código de fábrica** opcional por producto, reconocido por la búsqueda y por el lector junto al código interno (PA-07, RN-CAT-11, RF-97); y las solicitudes canceladas cuentan como fila informativa en «servicios por estado» (PA-08). **Revisada el 2026-10-09:** una edición de producto que incluya las existencias se **rechaza** con un error junto al campo, en lugar de ignorarse en silencio (CU-CAT-03, RN-CAT-10). |

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
empresa** en una única aplicación: catálogo e inventario con trazabilidad
de cada movimiento de existencias, registro de ventas con su garantía,
registro de clientes, seguimiento de servicios técnicos, gestión de las
cuentas del personal, y un panel de indicadores y reportes para la
administración.

---

## 2. Alcance

### 2.1 Dentro del alcance

El sistema es de **uso exclusivamente interno**. Solo el personal de
PC-Solution accede a él, siempre mediante una cuenta creada por el
Administrador. Comprende seis módulos funcionales:

1. Catálogo e inventario (categorías, productos con su código, y
   movimientos de existencias).
2. Registro de ventas, con su garantía.
3. Solicitudes de servicio técnico.
4. Gestión de usuarios y roles.
5. Panel de indicadores y reportes.
6. Clientes: registro de los datos de contacto de los clientes de la
   empresa *(v1.4, ver §2.3)*.

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

> **Precisión sobre el informe en PDF (v1.3, RF-67).** El informe de
> servicio que el personal imprime o descarga para entregar en mano al
> cliente **no** contradice ninguna de estas exclusiones. No es un
> documento fiscal, no se envía solo a ningún lado y no supone que el
> cliente entre al sistema: lo genera un usuario autenticado y se lo da
> al cliente igual que le daría un papel escrito a mano. Sigue siendo
> el personal quien lo entrega.

> **Precisiones de la v1.4.**
>
> - **La garantía en PDF (RF-76)** tampoco es un documento fiscal y lo
>   declara expresamente en su texto (RN-VEN-15). Sigue el mismo
>   principio que el informe de servicio: la genera el personal y la
>   entrega en mano.
> - **Los reportes (§5.8)** son **operativos, no contables**: resumen
>   ventas y servicios de un período para la administración. No son
>   libros contables, no calculan impuestos ni saldos, y no sustituyen
>   a la contabilidad, que sigue excluida.
> - **El módulo de Clientes (§2.3)** no contradice la exclusión del
>   portal de clientes: registra datos **sobre** los clientes, nunca
>   **para** ellos. Ningún cliente accede al sistema.

### 2.3 Nota sobre los datos del cliente

*(Reescrita en la v1.4.)*

Hasta la v1.3 el sistema no tenía un registro de clientes: su nombre y
teléfono solo existían **dentro** de cada venta o solicitud. Desde la
v1.4 existe un **módulo de Clientes**, con un alcance deliberadamente
estrecho:

- **Es un registro de datos de contacto**, que el personal mantiene para
  no tener que escribir de nuevo los datos de un cliente habitual.
- **Un cliente sigue sin tener cuenta**, sin inicio de sesión y sin
  ningún acceso al sistema (RN-CLI-04). Ser cliente no es ser usuario.
- **Registrar al cliente es opcional.** Una venta puede seguir
  haciéndose con un **cliente ocasional**, escribiendo su nombre y
  teléfono como hasta ahora.
- **La venta sigue guardando su propia copia** del nombre y el teléfono
  del cliente (RN-VEN-10). La referencia al cliente registrado es
  adicional: editar o desactivar un cliente después **no altera**
  ninguna venta ya hecha (RN-CLI-05).
- **Las solicitudes de servicio no cambian** en esta versión: siguen
  guardando el contacto del cliente como dato propio y el Encargado de
  Servicios no accede al módulo de Clientes. Integrarlos queda decidido
  para la v1.5 (PA-06).

---

## 3. Glosario

| Término | Definición |
|---|---|
| **Usuario** | Persona del personal de PC-Solution con una cuenta en el sistema. |
| **Rol** | Conjunto de permisos asignado a un usuario: Administrador, Encargado de Ventas o Encargado de Servicios. |
| **Cuenta bloqueada** | Cuenta que existe en el sistema pero cuyo titular no puede iniciar sesión. |
| **Categoría** | Agrupación de productos del catálogo (p. ej. laptops, periféricos, redes). |
| **Producto** | Artículo del catálogo con código, nombre, descripción, precio, existencias, meses de garantía e imagen. |
| **Código de producto** | Número de 13 dígitos en formato EAN-13 que el sistema asigna a cada producto al crearlo. Identifica al producto de forma única, no se edita y no se reutiliza nunca (RN-CAT-08). Puede imprimirse como código de barras y leerse con un lector. |
| **Código de fábrica** | Código de barras que trae impreso el producto o su caja de origen, registrado de forma **opcional**. El lector lo reconoce igual que el código interno, de modo que un producto que ya trae código no necesita etiqueta (RN-CAT-11). |
| **Existencias (stock)** | Cantidad disponible de un producto para la venta. |
| **Movimiento de stock** | Registro inmutable de un cambio en las existencias de un producto: cuánto cambió, con qué signo, en qué quedó, quién lo hizo, cuándo y por qué (RN-MOV-01). |
| **Ajuste de existencias** | Corrección manual de las existencias de un producto para que coincidan con lo contado físicamente. Exige un motivo y deja su movimiento (CU-CAT-07). |
| **Meses de garantía** | Duración de la garantía de un producto, en meses. Cero significa que el producto no tiene garantía. |
| **Garantía** | Documento en PDF que la empresa entrega al cliente con los productos de una venta que tienen garantía y la fecha en que vence cada una. **No es un documento fiscal.** |
| **Venta** | Registro de una transacción de venta con uno o más productos, sus cantidades y el contacto del cliente. |
| **Detalle de venta** | Línea de una venta: producto, cantidad, y nombre y precio unitario **congelados** al momento de la confirmación. |
| **Anulación** | Invalidación de una venta registrada por error, que devuelve las existencias al inventario. |
| **Solicitud de servicio** | Registro de un trabajo técnico pedido por un cliente, con su contacto, descripción del problema y seguimiento de estado. |
| **Usuario registrador** | Usuario que dio de alta la solicitud de servicio. Queda fijo y no cambia nunca. |
| **Técnico** | Nombre anotado en **texto libre** por el Administrador al cotizar la solicitud (RN-SER-09). No es una cuenta del sistema ni una relación con `Usuario`: es un dato informativo para el seguimiento, nunca un mecanismo de acceso. |
| **Monto cobrado** | Importe que se cobra al cliente por un servicio técnico. Lo **cotiza el Administrador** tras la revisión del trabajo (CU-SER-06), y tenerlo cotizado es **condición previa** para poder finalizar el servicio (RN-SER-13). *(Corregido en v1.4: decía «registrado al finalizarlo», que era la definición de la v1.1.)* |
| **Servicio en taller** | Servicio atendido en las instalaciones de PC-Solution (mantenimiento, reparación). No requiere dirección. |
| **Servicio a domicilio** | Servicio atendido en el lugar del cliente (instalación de redes, videovigilancia). Requiere dirección. |
| **Observaciones del trabajo** | Descripción de lo realizado, obligatoria para poder finalizar un servicio. |
| **Existencias bajas** | Producto cuya cantidad disponible es menor o igual al umbral de alerta. |
| **Umbral de existencias bajas** | Único número, global para todo el catálogo, configurable por el Administrador, a partir del cual un producto se considera con existencias bajas. |
| **Cliente** | Persona o entidad que compra a la empresa, registrada con sus datos de contacto en el módulo de Clientes. **No es un usuario**: no tiene cuenta, no inicia sesión y no accede al sistema (RN-CLI-04). |
| **Cliente ocasional** | Cliente de una venta cuyo nombre y teléfono se escriben en la propia venta sin registrarlo en el módulo de Clientes. |
| **Carnet** | Número del documento de identidad del cliente. Dato personal **opcional**, que solo se muestra en el detalle del cliente (RN-CLI-06). |
| **Reporte** | Resumen de ventas y servicios de un rango de fechas, para la administración. Es **operativo, no contable** (§2.2). |

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
- **Cotiza los servicios técnicos:** registra el monto a cobrar tras la
  revisión, y anota el nombre del técnico que los atiende.
- Configura el umbral global de existencias bajas.
- **Ajusta las existencias** de un producto con un motivo, y consulta el
  historial de movimientos de stock.
- Accede al panel de indicadores y a los **reportes por rango de
  fechas**, y los exporta a PDF y Excel.
- **Desactiva y reactiva clientes.**
- Puede realizar, además, **todo lo que hacen los otros dos roles**
  (registrar ventas, emitir garantías, registrar clientes y
  registrar/atender servicios).

### 4.2 Encargado de Ventas

Responsable de la atención comercial.

- Consulta el catálogo y las existencias disponibles, buscando por
  nombre o por código, y ve el código de barras de cada producto.
- Registra ventas, eligiendo un cliente registrado, registrando uno
  nuevo o escribiendo el nombre y teléfono de un cliente ocasional.
  Puede agregar productos con un lector de código de barras.
- Emite la **garantía** de sus propias ventas.
- **Consulta, registra y edita clientes.** No puede desactivarlos.
- Consulta **su propio** historial de ventas.
- Anula una venta **propia** registrada por error, sin límite de plazo.
- No gestiona el catálogo, ni ajusta existencias, ni ve los movimientos
  de stock, ni gestiona usuarios ni servicios técnicos, ni accede al
  panel ni a los reportes.

### 4.3 Encargado de Servicios

Responsable de la atención técnica.

- Registra solicitudes de servicio técnico (mantenimiento, reparación,
  instalación de redes, videovigilancia) con el contacto del cliente y la
  descripción del problema.
- Consulta **sus propias** solicitudes: las que él registró.
- Actualiza el estado de sus solicitudes conforme avanza la atención.
- Registra observaciones del trabajo realizado y finaliza el servicio.
- **No** fija el monto cobrado ni anota el técnico: ambas cosas son del
  Administrador (RN-SER-13, RN-SER-09).
- No gestiona el catálogo, ni usuarios, ni ventas, ni accede al panel de
  indicadores ni a los reportes.
- **No accede al módulo de Clientes** en esta versión. El contacto del
  cliente de una solicitud sigue escribiéndose en la propia solicitud
  (§2.3, PA-06).

> **Simetría con ventas.** Cada encargado ve y gestiona únicamente lo
> suyo, igual que en el historial de ventas. Las dos áreas siguen el
> mismo modelo de visibilidad: privado por usuario, con el Administrador
> viéndolo todo. *(La v1.1 planteaba lo contrario para servicios —un
> espacio compartido dentro del área— y la revisión de PA-04 lo
> descartó.)*

### 4.4 Matriz de permisos

| Funcionalidad | Administrador | Enc. de Ventas | Enc. de Servicios |
|---|:--:|:--:|:--:|
| Iniciar sesión / cerrar sesión | ✔ | ✔ | ✔ |
| Cambiar la propia contraseña | ✔ | ✔ | ✔ |
| Gestionar categorías (crear/editar/eliminar) | ✔ | ✘ | ✘ |
| Gestionar productos (crear/editar/eliminar) | ✔ | ✘ | ✘ |
| **Ajustar las existencias de un producto, con motivo** *(v1.4)* | ✔ | ✘ | ✘ |
| **Consultar los movimientos de stock** *(v1.4)* | ✔ | ✘ | ✘ |
| Configurar el umbral global de existencias bajas | ✔ | ✘ | ✘ |
| Consultar catálogo y existencias | ✔ | ✔ | ✘ |
| **Buscar productos por código; ver e imprimir su código de barras** *(v1.4)* | ✔ | ✔ | ✘ |
| Registrar una venta | ✔ | ✔ | ✘ |
| Consultar las ventas propias | ✔ | ✔ | ✘ |
| Consultar **todas** las ventas | ✔ | ✘ | ✘ |
| Anular una venta propia | ✔ | ✔ | ✘ |
| Anular **cualquier** venta | ✔ | ✘ | ✘ |
| **Emitir la garantía de una venta propia** *(v1.4)* | ✔ | ✔ | ✘ |
| **Emitir la garantía de cualquier venta** *(v1.4)* | ✔ | ✘ | ✘ |
| **Consultar, registrar y editar clientes** *(v1.4)* | ✔ | ✔ | ✘ |
| **Ver el carnet en el detalle de un cliente** *(v1.4)* | ✔ | ✔ | ✘ |
| **Desactivar o reactivar un cliente** *(v1.4)* | ✔ | ✘ | ✘ |
| Registrar una solicitud de servicio | ✔ | ✘ | ✔ |
| Consultar las solicitudes **propias** | ✔ | ✘ | ✔ |
| Consultar **todas** las solicitudes | ✔ | ✘ | ✘ |
| Actualizar el estado de una solicitud propia | ✔ | ✘ | ✔ |
| Registrar observaciones y finalizar un servicio propio | ✔ | ✘ | ✔ |
| Cancelar una solicitud propia | ✔ | ✘ | ✔ |
| **Cotizar: fijar el monto a cobrar** | ✔ | ✘ | ✘ |
| **Anotar el nombre del técnico** | ✔ | ✘ | ✘ |
| Gestionar cuentas de usuario y roles | ✔ | ✘ | ✘ |
| Ver el panel de indicadores | ✔ | ✘ | ✘ |
| **Consultar reportes por rango de fechas y exportarlos** *(v1.4)* | ✔ | ✘ | ✘ |

> **El directorio de clientes es común, las ventas no.** El Encargado de
> Ventas ve **todos** los clientes registrados —un cliente habitual lo
> atiende cualquiera del mostrador—, pero sigue viendo **solo sus
> propias ventas** (RN-VEN-09). Son dos cosas distintas: conocer a un
> cliente no da acceso a lo que otros le vendieron.

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
*(Revisado en v1.4: código automático, meses de garantía y movimiento de
alta.)*
- **Actor:** Administrador.
- **Precondición:** existe al menos una categoría.
- **Flujo principal:** registra nombre, descripción, precio, existencias
  iniciales, **meses de garantía**, categoría, imagen y, si lo tiene, el
  **código de fábrica** del producto. El sistema le **asigna
  automáticamente su código** interno (RN-CAT-08) y registra un
  **movimiento de alta** con las existencias iniciales (RN-MOV-01).
- **Alternativos:** datos inválidos (precio negativo, existencias
  negativas, meses de garantía negativos, nombre duplicado, imagen de
  formato o tamaño no permitido) → se rechaza indicando el error. Si el
  usuario intenta fijar el código interno, el valor se ignora: lo asigna
  siempre el sistema. Un código de fábrica que ya tiene otro producto, o
  que pertenece al espacio de los códigos internos, se rechaza
  (RN-CAT-11).
- **Postcondición:** el producto queda disponible en el catálogo con su
  código, y su historial de movimientos empieza con el alta.

#### CU-CAT-03 — Editar un producto
*(Revisado en v1.4: las existencias y el código ya no se editan aquí.)*
- **Actor:** Administrador.
- **Flujo principal:** modifica los datos descriptivos del producto
  —nombre, descripción, precio, meses de garantía, categoría, imagen y
  código de fábrica, que puede añadirse, corregirse o quitarse—.
- **Alternativos:** el formulario no ofrece las existencias ni el código
  interno.
  - Si la petición incluye las **existencias**, el sistema la
    **rechaza** con un error junto a ese campo, que indica que se
    corrigen con «Ajustar existencias» (RN-CAT-10). No se aplica ningún
    otro cambio de la misma petición. *(Revisado el 2026-10-09: antes se
    ignoraban en silencio, y una persona podía creer que el cambio se
    había guardado.)*
  - Si incluye el **código interno**, se ignora (RN-CAT-08).
  - Un código de fábrica inválido o repetido se rechaza (RN-CAT-11).

  Las existencias se corrigen con CU-CAT-07, que exige motivo y deja
  movimiento.
- **Postcondición:** el producto queda actualizado. Las ventas ya
  confirmadas **no** se ven afectadas (RN-VEN-04, RN-VEN-12): cambiar el
  precio o los meses de garantía solo rige para ventas futuras.

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
*(Revisado en v1.4: búsqueda por código.)*
- **Actor:** Administrador, Encargado de Ventas.
- **Flujo principal:** consulta la lista de productos con su código,
  categoría, precio y existencias disponibles, con búsqueda por nombre,
  **búsqueda por código exacto** —el interno o el de fábrica— y filtro
  por categoría.
- **Alternativos:** un código que no corresponde a ningún producto → la
  búsqueda no devuelve resultados, sin error.
- **Postcondición:** ninguna (consulta).

#### CU-CAT-06 — Configurar el umbral de existencias bajas
- **Actor:** Administrador.
- **Flujo principal:** el Administrador consulta el umbral vigente y lo
  modifica por un número entero no negativo; el sistema lo aplica de
  inmediato a **todo** el catálogo.
- **Alternativos:** valor negativo o no entero → se rechaza.
- **Postcondición:** el nuevo umbral rige el indicador de existencias
  bajas y las alertas del catálogo.

#### CU-CAT-07 — Ajustar las existencias de un producto *(v1.4)*
- **Actor:** Administrador.
- **Precondición:** el producto existe (activo o retirado).
- **Flujo principal:**
  1. El Administrador indica la **cantidad real contada** del producto y
     el **motivo** del ajuste (por ejemplo, «recuento físico», «unidad
     dañada», «error de carga»).
  2. El sistema muestra la diferencia respecto de las existencias
     registradas y pide confirmación (RNF-14).
  3. Al confirmar, el sistema calcula la diferencia contra las
     existencias **vigentes en ese instante** —no contra las que se
     mostraban al abrir el formulario—, actualiza las existencias y
     registra un **movimiento de ajuste** con la diferencia con signo, las
     existencias resultantes, el autor, la fecha y el motivo.
- **Alternativos:**
  - Sin motivo → se rechaza (RN-MOV-05).
  - Cantidad negativa o no entera → se rechaza.
  - La cantidad indicada es igual a las existencias vigentes → se
    rechaza indicando que no hay nada que ajustar.
- **Postcondición:** las existencias coinciden con lo contado y el
  historial de movimientos deja constancia de por qué cambiaron.

> **Por qué la diferencia se calcula al confirmar.** Si entre que el
> Administrador abre el formulario y lo confirma se vende una unidad,
> calcular la diferencia contra el valor que vio al abrirlo dejaría esa
> venta fuera del libro de movimientos: la suma de los movimientos ya no
> coincidiría con las existencias (RN-MOV-03).

#### CU-CAT-08 — Consultar los movimientos de stock *(v1.4)*
- **Actor:** Administrador.
- **Flujo principal:** consulta la lista de movimientos —producto, tipo,
  cantidad con signo, existencias resultantes, autor, fecha y hora,
  venta de referencia y motivo—, con filtro por producto, por tipo y por
  rango de fechas, paginada. Desde el detalle de un producto ve
  directamente el historial de ese producto.
- **Postcondición:** ninguna (consulta).

#### CU-CAT-09 — Ver e imprimir el código de barras de un producto *(v1.4)*
- **Actor:** Administrador, Encargado de Ventas.
- **Flujo principal:** en el detalle del producto, el usuario ve su
  código y su representación como código de barras, y puede imprimir
  una etiqueta con el código de barras, el código en cifras y el nombre
  del producto, para pegarla en el artículo o en el estante.
- **Postcondición:** ninguna (consulta).

### 5.3 Registro de ventas

#### CU-VEN-01 — Registrar una venta
*(Revisado en v1.4: cliente registrado, entrada por código, garantía
congelada y movimientos de stock.)*
- **Actor:** Encargado de Ventas, Administrador.
- **Precondición:** existen productos con existencias disponibles.
- **Flujo principal:**
  1. El usuario identifica al cliente de **una** de tres formas:
     - **busca y elige un cliente registrado** activo por nombre,
       teléfono o carnet; el sistema completa su nombre y teléfono;
     - **registra un cliente nuevo** en ese mismo momento (CU-CLI-01), que
       queda elegido;
     - o atiende a un **cliente ocasional**, escribiendo su nombre y
       teléfono sin registrarlo, como hasta la v1.3.
  2. Agrega uno o más productos buscándolos por nombre **o introduciendo
     su código** —el interno o el de fábrica—, por teclado o con un
     **lector de código de barras**. Un código que coincide exactamente
     con un producto disponible lo agrega con cantidad 1, o suma 1 si ya
     estaba en la venta (RN-VEN-17).
  3. Ajusta la cantidad de cada producto; el sistema calcula el subtotal
     por línea y el total de la venta.
  4. Al confirmar, el sistema valida que haya existencias suficientes de
     cada producto, descuenta el inventario, **congela** en el detalle el
     nombre, el precio unitario y los **meses de garantía** de cada
     producto, copia en la venta el nombre y teléfono del cliente,
     registra la referencia al cliente si se eligió uno, registra **un
     movimiento de stock por producto** y deja la venta a nombre del
     usuario que la realizó con su fecha y hora. Todo en una sola
     operación (RNF-09, RNF-24).
  5. Si alguna línea tiene garantía, el sistema ofrece emitirla en ese
     momento (CU-VEN-04).
- **Alternativos:**
  - Existencias insuficientes de algún producto → la venta **no** se
    confirma; ningún producto se descuenta, **no se registra ningún
    movimiento** y el sistema indica cuáles faltan y cuánto hay
    disponible.
  - Venta sin productos o con cantidad cero o negativa → se rechaza.
  - Datos de contacto del cliente incompletos → se rechaza.
  - Se elige un cliente que fue **desactivado** entre la búsqueda y la
    confirmación → se rechaza (RN-CLI-03).
  - El código introducido no corresponde a ningún producto → se avisa y
    no se agrega nada.
  - El código corresponde a un producto **retirado o sin existencias** →
    se avisa y no se agrega (RN-CAT-05).
- **Postcondición:** la venta queda registrada en estado *Confirmada*, el
  inventario refleja el descuento y cada producto vendido tiene su
  movimiento de venta.

#### CU-VEN-02 — Consultar el historial de ventas
- **Actor:** Encargado de Ventas (solo las propias), Administrador (todas).
- **Flujo principal:** consulta la lista de ventas con fecha, cliente,
  total, estado y responsable, con filtro por rango de fechas y estado, y
  puede abrir el detalle de cada una. Desde el detalle de una venta
  confirmada con garantía puede emitirla (CU-VEN-04).
- **Postcondición:** ninguna (consulta).

#### CU-VEN-03 — Anular una venta
- **Actor:** Encargado de Ventas (solo las propias), Administrador
  (cualquiera).
- **Precondición:** la venta está en estado *Confirmada*. No existe
  límite de plazo para anularla.
- **Flujo principal:** el usuario solicita la anulación indicando el
  motivo; el sistema pide confirmación, devuelve las existencias de cada
  producto del detalle al inventario, **registra un movimiento de
  anulación por producto** que referencia la venta, y marca la venta como
  *Anulada*, registrando quién la anuló, cuándo y por qué. Todo en una
  sola operación (RNF-10, RNF-24).
- **Alternativos:**
  - La venta ya está anulada → se rechaza.
  - Un producto del detalle fue eliminado del catálogo → las existencias
    de los productos aún vigentes se devuelven igualmente y el sistema
    informa cuáles no pudieron reponerse.
- **Postcondición:** la venta queda *Anulada*, no se elimina, el
  inventario refleja la devolución y cada producto devuelto tiene su
  movimiento. Una venta anulada **ya no puede emitir garantía**
  (RN-VEN-14).

#### CU-VEN-04 — Emitir la garantía de una venta *(v1.4)*
- **Actor:** Encargado de Ventas (solo las propias), Administrador
  (cualquiera).
- **Precondición:** la venta está *Confirmada* y tiene al menos una línea
  con meses de garantía mayor que cero.
- **Flujo principal:** al confirmar la venta, o desde su detalle, el
  usuario pide la garantía; el sistema genera un PDF con el membrete de
  la empresa que contiene:
  - los datos del cliente —nombre y teléfono—, **nunca el carnet**;
  - la fecha de la venta y su número;
  - **solo las líneas con garantía**: producto, código, cantidad, meses de
    garantía y **fecha de vencimiento** calculada (RN-VEN-13);
  - quién la generó y la fecha y hora de generación;
  - la leyenda de que **no es un documento fiscal** (RN-VEN-15).

  El usuario elige dónde guardarlo cuando el navegador lo permite, con
  el mismo mecanismo que el informe de servicio (RF-68).
- **Alternativos:**
  - La venta está anulada → se rechaza.
  - Ninguna línea de la venta tiene garantía → se rechaza indicándolo.
  - Un Encargado de Ventas pide la garantía de una venta ajena → el
    sistema responde como si no existiera (RN-VEN-16).
- **Postcondición:** ninguna sobre los datos. La garantía se calcula
  siempre a partir de la venta guardada, de modo que emitirla varias
  veces produce el mismo contenido salvo la fecha de generación.

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
  4. El sistema registra la solicitud en estado *Registrada*, con fecha,
     hora y el **usuario registrador**.
- **Alternativos:** datos obligatorios faltantes (incluida la dirección
  cuando corresponde) → se rechaza el registro.
- **Postcondición:** la solicitud queda registrada, visible para su
  registrador y para el Administrador.

#### CU-SER-02 — Actualizar el estado de una solicitud
- **Actor:** Encargado de Servicios (solo las propias), Administrador
  (cualquiera).
- **Precondición:** la solicitud no está en un estado terminal.
- **Flujo principal:** el usuario avanza la solicitud al siguiente estado
  válido (ver RN-SER-02); el sistema registra el cambio con su fecha, hora
  y autor en el historial.
- **Alternativos:** transición no permitida → se rechaza.
- **Postcondición:** la solicitud refleja el nuevo estado y su historial
  de cambios.

#### CU-SER-03 — Registrar observaciones y finalizar
- **Actor:** Encargado de Servicios (solo las propias), Administrador
  (cualquiera).
- **Precondición:** la solicitud está en estado *En atención* y ya tiene
  monto cotizado (CU-SER-06).
- **Flujo principal:** el usuario registra las **observaciones del
  trabajo realizado** y finaliza el servicio; el sistema lo marca como
  *Finalizado* con su fecha y hora de cierre y con el autor del cierre.
- **Alternativos:**
  - Intento de finalizar sin observaciones registradas → se rechaza
    (RN-SER-03).
  - Intento de finalizar sin monto cotizado → se rechaza (RN-SER-13); el
    sistema indica que el Administrador debe cotizarla primero.
- **Postcondición:** la solicitud queda *Finalizada*, ya no admite
  cambios de estado, y su monto pasa a contar en los ingresos por
  servicios del panel de indicadores.

#### CU-SER-04 — Cancelar una solicitud
- **Actor:** Encargado de Servicios (solo las propias), Administrador
  (cualquiera).
- **Precondición:** la solicitud no está *Finalizada* ni *Cancelada*.
- **Flujo principal:** el usuario cancela la solicitud indicando el
  motivo; el sistema la marca como *Cancelada* registrando autor y fecha.
- **Postcondición:** la solicitud queda cerrada sin atención; no cuenta
  como ingreso aunque estuviera cotizada (RN-SER-14).

#### CU-SER-05 — Consultar las solicitudes de servicio
- **Actor:** Encargado de Servicios (solo las propias), Administrador
  (todas).
- **Flujo principal:** consulta la lista de solicitudes con cliente, tipo,
  estado, fecha, usuario registrador, técnico anotado y monto cotizado;
  filtra por estado, tipo y rango de fechas —incluido un filtro rápido de
  «pendientes de cotizar» para el Administrador— y abre el detalle de
  cada una con su historial de cambios.
- **Postcondición:** ninguna (consulta).

#### CU-SER-06 — Cotizar un servicio y anotar el técnico
- **Actor:** **Administrador únicamente.**
- **Precondición:** la solicitud no está en un estado terminal.
- **Flujo principal:** tras la revisión del equipo o del trabajo, el
  Administrador registra en la solicitud el **monto a cobrar** y,
  opcionalmente, el **nombre del técnico** que la atiende; el sistema
  guarda ambos y deja constancia del cambio en el historial.
- **Alternativos:**
  - Monto negativo → se rechaza. Un servicio en garantía o de cortesía
    se cotiza en **cero**, nunca se deja vacío.
  - Solicitud ya *Finalizada* o *Cancelada* → se rechaza (RN-SER-12).
- **Postcondición:** la solicitud queda cotizada y puede finalizarse.

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
    *Registrada* o *En atención*, desglosando cuántas están **pendientes
    de cotizar** (RN-IND-02). *(Corregido en v1.4: decía «sin técnico
    asignado», resto de la v1.1; RN-IND-02 y RF-49 ya hablaban de las
    pendientes de cotizar, que es lo que el sistema muestra.)*
  - **Productos con existencias bajas:** lista de productos cuya
    existencia está en el umbral global de alerta o por debajo.
- **Postcondición:** ninguna (consulta).

> El panel diario **se conserva** en la v1.4. Los reportes de §5.8 no lo
> sustituyen: el panel responde «¿cómo va hoy?» de un vistazo, y el
> reporte responde «¿cómo fue este período?» con detalle. Sus cifras del
> día coinciden por construcción (RN-REP-08).

### 5.7 Clientes *(v1.4)*

#### CU-CLI-01 — Registrar un cliente
- **Actor:** Encargado de Ventas, Administrador.
- **Flujo principal:** desde el módulo de Clientes o desde el registro de
  una venta, el usuario registra el **nombre** y el **teléfono** del
  cliente y, opcionalmente, su **dirección** y su **carnet**; el sistema
  lo guarda como cliente activo, registrando quién lo creó y cuándo.
- **Alternativos:**
  - Falta el nombre o el teléfono → se rechaza.
  - El carnet ya pertenece a otro cliente, activo o no → se rechaza
    (RN-CLI-02).
- **Postcondición:** el cliente queda disponible para elegirlo en las
  ventas. **No** se crea ninguna cuenta ni acceso (RN-CLI-04).

#### CU-CLI-02 — Editar un cliente
- **Actor:** Encargado de Ventas, Administrador.
- **Flujo principal:** el usuario corrige el nombre, teléfono, dirección o
  carnet de un cliente; el sistema pide confirmación y registra quién lo
  modificó y cuándo.
- **Alternativos:** mismas validaciones que CU-CLI-01.
- **Postcondición:** el cliente queda actualizado. **Las ventas ya
  registradas conservan los datos que tenían** (RN-CLI-05): corregir un
  teléfono hoy no cambia lo que dice una venta de ayer.

#### CU-CLI-03 — Consultar y buscar clientes
- **Actor:** Encargado de Ventas, Administrador.
- **Flujo principal:** el usuario consulta la lista paginada de clientes,
  busca por nombre, teléfono o carnet, filtra por activos o inactivos, y
  abre el detalle de cada uno.
- **Alternativos:** la búsqueda puede hacerse por carnet, pero **la lista
  no muestra el carnet**: solo aparece en el detalle del cliente
  (RN-CLI-06).
- **Postcondición:** ninguna (consulta).

#### CU-CLI-04 — Desactivar o reactivar un cliente
- **Actor:** **Administrador únicamente.**
- **Flujo principal:** el Administrador desactiva un cliente, o reactiva
  uno inactivo; el sistema pide confirmación.
- **Postcondición:** un cliente inactivo **no puede elegirse en ventas
  nuevas**, pero no se elimina: sus datos y las ventas que lo referencian
  quedan intactos (RN-CLI-03).

### 5.8 Reportes *(v1.4)*

#### CU-REP-01 — Consultar un reporte por rango de fechas
- **Actor:** Administrador.
- **Flujo principal:**
  1. El Administrador elige un rango de fechas —desde y hasta— o uno de
     los atajos **hoy**, **esta semana** o **este mes** (RN-REP-01).
  2. El sistema muestra para ese rango:
     - ventas confirmadas: cantidad e importe;
     - servicios finalizados: cantidad e importe;
     - ingreso total, **siempre desglosado** por origen (RN-REP-03);
     - productos más vendidos (RN-REP-04);
     - ventas por usuario (RN-REP-05);
     - servicios por estado (RN-REP-06).
- **Alternativos:**
  - La fecha «desde» es posterior a «hasta» → se rechaza.
  - El rango no tiene movimientos → el reporte se muestra con ceros y
    un aviso de que no hubo actividad, no vacío ni con error.
- **Postcondición:** ninguna (consulta).

#### CU-REP-02 — Exportar un reporte
- **Actor:** Administrador.
- **Flujo principal:** desde un reporte ya consultado, el Administrador lo
  exporta a **PDF** —con el membrete de la empresa— o a **Excel
  (.xlsx)**; el sistema genera el archivo para el mismo rango y el
  usuario elige dónde guardarlo cuando el navegador lo permite.
- **Postcondición:** el archivo contiene **exactamente las mismas
  cifras** que la pantalla para ese rango (RN-REP-07), y ningún dato
  personal de clientes (RN-REP-09).

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
- **RN-CAT-08** *(v1.4)* — Cada producto tiene un **código** de 13
  dígitos en formato **EAN-13** válido, que el sistema le asigna
  automáticamente al crearlo. El código:
  - es **único** en todo el catálogo;
  - **no se edita nunca**, ni por el Administrador;
  - **no se reutiliza nunca**, aunque el producto se retire del catálogo:
    un código identifica siempre al mismo producto;
  - usa el **prefijo de circulación interna** de GS1 (20), reservado
    para uso dentro de un comercio, de modo que nunca puede coincidir
    con el código de fábrica de un producto real (RN-CAT-11).
- **RN-CAT-09** *(v1.4)* — Los **meses de garantía** de un producto son
  un entero mayor o igual que cero; **cero** significa que el producto no
  tiene garantía. Modificarlos afecta solo a las ventas futuras
  (RN-VEN-12).
- **RN-CAT-10** *(v1.4)* — Las existencias de un producto ya creado
  cambian **únicamente** por una venta, una anulación o un ajuste manual
  (CU-CAT-07). La edición general del producto no las modifica. Así,
  cada cambio de existencias tiene su movimiento (RN-MOV-01) y ninguno
  queda sin explicar. Una edición que **incluya** las existencias **se
  rechaza** indicando que se corrigen con el ajuste *(revisado el
  2026-10-09)*: ignorarlas en silencio haría creer que el cambio se
  aplicó.
- **RN-CAT-11** *(v1.4, PA-07)* — Un producto puede tener, además de su
  código interno, un **código de fábrica** opcional: el que trae impreso
  el producto o su caja. Ese código:
  - es **único** entre todos los productos, activos y retirados, si se
    informa; dos productos sin código de fábrica no entran en conflicto;
  - **puede editarse y quitarse**, a diferencia del interno, porque lo
    escribe una persona y puede equivocarse;
  - **no puede pertenecer al espacio de los códigos internos**: se
    rechaza un código de fábrica de 13 dígitos que empiece por 20. Así
    un código leído identifica siempre a un único producto, sin
    ambigüedad entre los dos tipos;
  - se guarda sin espacios y en mayúsculas, porque algunos códigos de
    fábrica son alfanuméricos.

  Consecuencia práctica: si dos productos distintos traen el mismo
  código de fábrica —el mismo modelo en dos colores, por ejemplo—, solo
  uno puede registrarlo; el otro se vende con su código interno y su
  etiqueta.

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
- **RN-VEN-10** *(revisada en v1.4)* — El nombre y el teléfono de
  contacto del cliente son obligatorios en toda venta, y **la venta
  guarda su propia copia** de ambos, que no cambia nunca (RNF-11).
  Además, la venta puede llevar una **referencia opcional** a un cliente
  registrado (§2.3):
  - si se elige un cliente registrado, el nombre y el teléfono los
    **copia el sistema** del registro del cliente en el momento de
    confirmar, igual que el precio se copia del catálogo (RN-VEN-04);
  - si no se elige ninguno, la venta es de un **cliente ocasional** y el
    nombre y el teléfono son los que escribe el usuario.

  En ningún caso el cliente obtiene cuenta ni acceso alguno (RN-CLI-04).
- **RN-VEN-11** — La anulación **no tiene límite de plazo**: una venta
  confirmada puede anularse en cualquier momento posterior, sin importar
  cuánto tiempo haya pasado desde su registro. La trazabilidad de quién
  anuló, cuándo y por qué (RN-VEN-07) es el control que sustituye a
  cualquier restricción temporal.

#### Garantía *(v1.4)*

- **RN-VEN-12** — Los **meses de garantía** de cada producto se
  **congelan** en el detalle de la venta al confirmarla, junto con el
  nombre y el precio (RN-VEN-04). Cambiar después los meses de garantía
  del producto **no altera** ninguna garantía ya emitida ni por emitir de
  una venta pasada. Las ventas registradas antes de la v1.4 quedan con
  cero meses: no se les atribuye una garantía que no se pactó.
- **RN-VEN-13** — La **fecha de vencimiento** de cada línea es la fecha
  de la venta —en hora de Bolivia— más sus meses de garantía, contados
  como meses de calendario. Si el día no existe en el mes resultante, se
  toma el último día de ese mes: una venta del 31 de enero con un mes de
  garantía vence el 28 de febrero (o el 29 en año bisiesto).
- **RN-VEN-14** — Solo se emite garantía de una venta **confirmada** que
  tenga **al menos una línea** con meses de garantía mayor que cero, y la
  garantía lista **únicamente** esas líneas. Una venta anulada no emite
  garantía.
- **RN-VEN-15** — La garantía **declara en su texto que no es un
  documento fiscal** (§2.2). Contiene el nombre y el teléfono del cliente
  tal como están en la venta, quién la generó y cuándo; **nunca el
  carnet** (RN-CLI-06).
- **RN-VEN-16** — La garantía de una venta la pueden emitir **las mismas
  personas que pueden ver esa venta**: el Encargado de Ventas, solo las
  propias; el Administrador, todas. Se verifica en el servidor
  (RN-ACC-04): pedir la garantía de una venta ajena responde como si la
  venta no existiera.

#### Entrada por código *(v1.4)*

- **RN-VEN-17** — En el registro de venta, un código introducido —a mano
  o con un lector— agrega el producto **solo si coincide exactamente**
  con el código interno **o con el código de fábrica** (RN-CAT-11) de un
  producto **activo y con existencias**. No hay
  coincidencias parciales: un código incompleto no agrega nada, porque
  un lector que lea mal no debe añadir un producto equivocado.

### 6.5 Servicios técnicos

- **RN-SER-01** — Los tipos de servicio son: **mantenimiento**,
  **reparación**, **instalación de redes** y **videovigilancia**.
  Mantenimiento y reparación se atienden **en taller**; instalación de
  redes y videovigilancia se atienden **a domicilio**.
- **RN-SER-02** — Los estados de una solicitud y sus transiciones válidas
  son:

  ```
                                  [1]
  Registrada ──────────► En atención ──────────► Finalizada
       │                      │
       └──────────────────────┴──────────────► Cancelada
                                 [2]

  [1] exige observaciones del trabajo Y monto ya cotizado
      por el Administrador ............... RN-SER-03, RN-SER-13
  [2] exige motivo de cancelación ........ RN-SER-07
  ```

  Pasar a *En atención* no tiene guarda: el trabajo puede empezar
  antes de que el Administrador lo cotice, que es justamente el orden
  que describe PA-03 (primero se revisa, después se cotiza).

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

#### Técnico anotado (PA-05, revisado en v1.2)

- **RN-SER-09** — El **técnico** es una **anotación de texto libre**, no
  una entidad del sistema: el Administrador escribe el nombre de quien
  atiende el trabajo. No hay asignación formal, ni relación con las
  cuentas de usuario, ni validación de que esa persona tenga cuenta. Es
  información para el seguimiento, **nunca un mecanismo de acceso**.
- **RN-SER-10** — Solo el **Administrador** anota o modifica el técnico.
  El campo es opcional: una solicitud puede atenderse sin que se
  registre quién lo hizo.
- **RN-SER-11** — El único responsable con identidad en el sistema es el
  **usuario registrador**, que queda fijo desde el alta y **nunca
  cambia**. La trazabilidad de quién hizo cada cambio la aporta el
  historial (RN-SER-06), no el campo del técnico.
- **RN-SER-12** — El monto y el técnico solo pueden fijarse mientras la
  solicitud no esté en un estado terminal. Cada cambio queda en el
  historial con su autor y momento.
- **RN-SER-15** — Cada solicitud la ven **únicamente quien la registró y
  el Administrador**. El modelo de visibilidad es el mismo que el de las
  ventas (RN-VEN-09): privado por usuario, con el Administrador viéndolo
  todo.

#### Monto cotizado (PA-03, revisado en v1.2)

- **RN-SER-13** — El **monto a cobrar lo fija el Administrador** tras la
  revisión del trabajo (CU-SER-06), no el técnico al cerrarlo. Una
  solicitud **no puede finalizarse sin monto cotizado**: sin esa
  condición, un servicio podría cerrarse sin importe y los ingresos del
  panel (RN-IND-04) dejarían de reflejar lo realmente cobrado.
- **RN-SER-14** — Una solicitud *Cancelada* **no cuenta** como ingreso,
  aunque se hubiera cotizado antes de cancelarla. Solo los servicios
  *Finalizados* aportan a los indicadores.
- **RN-SER-16** — El monto puede corregirse **mientras la solicitud siga
  abierta**: cotizar es una estimación tras la revisión y puede ajustarse
  si el trabajo resulta distinto. Una vez *Finalizada*, el cierre es
  **inmutable**: ni el monto, ni las observaciones, ni el técnico se
  editan. Un cierre equivocado se corrige registrando una nueva
  solicitud, del mismo modo que una venta errónea se corrige anulándola.
- **RN-SER-17** — El monto es un número **no negativo**. Un servicio en
  garantía o de cortesía se cotiza en **cero**, nunca se deja vacío: así
  «gratis» y «sin cotizar» no se confunden.

### 6.6 Indicadores

- **RN-IND-01** — «Ventas del día» considera únicamente las ventas
  confirmadas de la fecha actual; las anuladas quedan excluidas.
- **RN-IND-02** — «Servicios pendientes» considera las solicitudes en
  estado *Registrada* o *En atención*, sin límite de fecha, y desglosa
  cuántas de ellas están **pendientes de cotizar**, que son las que el
  Administrador tiene que atender para que puedan cerrarse.
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

### 6.7 Movimientos de stock *(v1.4)*

- **RN-MOV-01** — **Todo cambio** en las existencias de un producto
  genera **exactamente un movimiento** por producto afectado, dentro de
  la **misma operación atómica** que el cambio: si el cambio de
  existencias falla, no queda movimiento; si el movimiento no puede
  registrarse, las existencias no cambian (RNF-24).
- **RN-MOV-02** — Los tipos de movimiento son:

  | Tipo | Cuándo | Signo | Autor | Venta de referencia |
  |---|---|---|---|---|
  | **Saldo inicial** | Una sola vez por producto, al incorporar este historial a un sistema que ya tenía productos | + o 0 | ninguno (lo genera el sistema) | — |
  | **Alta** | Al crear un producto, con sus existencias iniciales | + o 0 | quien lo crea | — |
  | **Venta** | Al confirmar una venta | − | quien vende | **obligatoria** |
  | **Anulación** | Al anular una venta | + | quien anula | **obligatoria** |
  | **Ajuste manual** | Al corregir las existencias (CU-CAT-07) | + o − | el Administrador | — |

- **RN-MOV-03** — Cada movimiento registra la **cantidad con signo**
  —negativa si salen unidades, positiva si entran— y las **existencias
  resultantes** tras aplicarlo. Por construcción, la **suma** de las
  cantidades de todos los movimientos de un producto es **siempre igual
  a sus existencias vigentes**, y las existencias resultantes del último
  movimiento coinciden con ellas. Es el invariante que permite auditar
  el inventario.
- **RN-MOV-04** — Los movimientos son **inmutables**: no se editan ni se
  eliminan, ni siquiera por el Administrador. Un error se corrige con un
  nuevo movimiento —un ajuste—, nunca modificando el anterior, igual
  que una venta errónea se corrige anulándola (RN-VEN-06).
- **RN-MOV-05** — Un ajuste manual exige un **motivo**, una cantidad real
  entera y no negativa, y que esa cantidad **difiera** de las existencias
  vigentes. La diferencia se calcula contra las existencias **en el
  instante de confirmar** el ajuste (ver CU-CAT-07).
- **RN-MOV-06** — Los movimientos solo los consulta el **Administrador**.

### 6.8 Clientes *(v1.4)*

- **RN-CLI-01** — El **nombre** y el **teléfono** de un cliente son
  obligatorios; la **dirección** y el **carnet** son opcionales.
- **RN-CLI-02** — Si se informa el carnet, es **único** entre todos los
  clientes, activos e inactivos. Dos clientes sin carnet no entran en
  conflicto. El nombre y el teléfono **no** son únicos: dos personas
  pueden llamarse igual, y una familia puede compartir teléfono.
- **RN-CLI-03** — Los clientes **no se eliminan**: se desactivan, igual
  que las cuentas del personal (RN-USU-05). Un cliente inactivo no puede
  elegirse en ventas nuevas, pero conserva sus datos y las ventas que lo
  referencian siguen intactas. Puede reactivarse.
- **RN-CLI-04** — Un cliente **no es un usuario**: no tiene cuenta, no
  inicia sesión y no accede al sistema por ninguna vía. Registrarlo no
  le concede ningún acceso.
- **RN-CLI-05** — Editar o desactivar un cliente **no altera** ninguna
  venta ya registrada: cada venta conserva el nombre y el teléfono que
  tenía al confirmarse (RN-VEN-10, RNF-11).
- **RN-CLI-06** — El **carnet es un dato personal** y se trata con
  minimización: **solo se muestra en el detalle del cliente**. No aparece
  en la lista de clientes, ni en el detalle de una venta, ni en la
  garantía, ni en ningún reporte ni exportación (RNF-26). Sí puede
  usarse para **buscar** a un cliente.
- **RN-CLI-07** — Solo el **Administrador** desactiva o reactiva
  clientes. El Encargado de Ventas los consulta, registra y edita. El
  Encargado de Servicios no accede al módulo en esta versión (PA-06).

### 6.9 Reportes *(v1.4)*

- **RN-REP-01** — Un reporte cubre un **rango de fechas de calendario**
  en hora de Bolivia, **inclusivo en ambos extremos**, con «desde»
  anterior o igual a «hasta». Los atajos significan:
  - **hoy**: el día en curso;
  - **esta semana**: desde el **lunes** de la semana en curso hasta hoy;
  - **este mes**: desde el día 1 del mes en curso hasta hoy.
- **RN-REP-02** — Qué cuenta en un reporte, con los mismos criterios que
  los indicadores del panel:
  - **ventas**: las **confirmadas** cuya fecha de registro cae en el
    rango; las anuladas quedan excluidas aunque se hubieran registrado
    en el rango (RN-IND-01);
  - **servicios**: los **finalizados** cuya **fecha de cierre** cae en el
    rango, sumando su monto cobrado; los cancelados quedan excluidos
    (RN-IND-04, RN-SER-14).
- **RN-REP-03** — El ingreso total del rango se presenta **siempre
  desglosado** por origen, ventas y servicios. RN-IND-05 rige también
  para los reportes y sus exportaciones.
- **RN-REP-04** — **Productos más vendidos**: los **diez** productos con
  más unidades vendidas en las ventas confirmadas del rango, con sus
  unidades y su importe. A igualdad de unidades, ordena el mayor
  importe.
- **RN-REP-05** — **Ventas por usuario**: cantidad e importe de las
  ventas confirmadas del rango, agrupadas por el usuario que las
  registró.
- **RN-REP-06** — **Servicios por estado**: cantidad de solicitudes
  **registradas** en el rango, agrupadas por su estado actual,
  **incluidas las canceladas como fila informativa** (PA-08). Esta
  sección cuenta solicitudes, no importes: las canceladas aparecen para
  mostrar cuántas se perdieron en el período, y siguen sin sumar a
  ningún ingreso (RN-REP-02, RN-SER-14).
- **RN-REP-07** — Las exportaciones a PDF y a Excel de un rango
  contienen **exactamente las mismas cifras** que la pantalla para ese
  rango. No se calculan aparte.
- **RN-REP-08** — El reporte de **hoy** y el panel diario muestran
  **las mismas cifras** de ventas, servicios e ingreso total. El panel
  se conserva tal como está.
- **RN-REP-09** — Ningún reporte ni exportación incluye el **carnet** ni
  otros datos personales de clientes (RN-CLI-06). Los reportes son de
  operación, no de personas.
- **RN-REP-10** — Los reportes y sus exportaciones solo los consulta el
  **Administrador**.

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
| RF-10 | El sistema debe permitir al Administrador editar los datos descriptivos de un producto. *(Revisado en v1.4: decía «cualquier dato, incluidas sus existencias». Las existencias pasan a corregirse con RF-73 y el código no se edita nunca: RN-CAT-08, RN-CAT-10.)* |
| RF-11 | El sistema debe permitir al Administrador retirar un producto del catálogo conservando intacto el historial de ventas que lo incluya. |
| RF-12 | El sistema debe permitir al Administrador y al Encargado de Ventas consultar el catálogo con las existencias disponibles. |
| RF-13 | El sistema debe permitir buscar productos por nombre y filtrarlos por categoría. |
| RF-14 | El sistema debe validar que el precio sea mayor que cero y las existencias no negativas. |
| RF-52 | El sistema debe permitir al Administrador consultar y modificar el umbral global de existencias bajas, como un único valor entero no negativo aplicable a todo el catálogo. |
| RF-53 | El sistema debe señalar visualmente, en el catálogo, los productos cuya existencia esté en el umbral global o por debajo. |
| RF-69 | El sistema debe asignar automáticamente a cada producto, al crearlo, un código único de 13 dígitos en formato EAN-13, que no puede editarse ni reutilizarse aunque el producto se retire. |
| RF-70 | El sistema debe permitir buscar un producto por su código exacto en el catálogo, sea el código interno o el de fábrica. |
| RF-71 | El sistema debe mostrar el código del producto en su detalle, representarlo como código de barras y permitir imprimirlo como etiqueta. |
| RF-72 | El sistema debe permitir registrar en cada producto sus meses de garantía, como un entero no negativo en el que cero significa sin garantía. |
| RF-73 | El sistema debe permitir al Administrador ajustar las existencias de un producto indicando la cantidad real y un motivo obligatorio, calculando la diferencia contra las existencias vigentes al confirmar. |
| RF-97 | El sistema debe permitir al Administrador registrar, corregir y quitar el código de fábrica opcional de un producto, rechazando un código ya registrado en otro producto o perteneciente al espacio de los códigos internos. |

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
| RF-74 | El sistema debe agregar un producto a la venta en curso cuando se introduce un código —a mano o con un lector de código de barras— que coincide exactamente con el código interno o el de fábrica de un producto activo con existencias. |
| RF-75 | El sistema debe congelar los meses de garantía de cada producto en el detalle de la venta al confirmarla. |
| RF-76 | El sistema debe generar en PDF la garantía de una venta, con el membrete de la empresa, los datos del cliente, las líneas con garantía (producto, código, cantidad, meses y fecha de vencimiento), quién la generó, la fecha de generación y la leyenda de que no es un documento fiscal. |
| RF-77 | El sistema debe ofrecer la emisión de la garantía al confirmar una venta y desde el detalle de una venta del historial. |
| RF-78 | El sistema debe impedir emitir la garantía de una venta anulada o sin ninguna línea con garantía. |
| RF-79 | El sistema debe permitir, al registrar una venta, elegir un cliente registrado activo, registrar uno nuevo en ese momento o escribir el nombre y teléfono de un cliente ocasional. |
| RF-80 | El sistema debe guardar en cada venta su propia copia del nombre y el teléfono del cliente y, si se eligió un cliente registrado, una referencia a él. |

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
| RF-36 | El sistema debe permitir al Encargado de Servicios consultar **sus propias** solicitudes y al Administrador consultar todas. |
| RF-37 | El sistema debe permitir filtrar las solicitudes por estado, tipo y rango de fechas. |
| RF-38 | El sistema debe permitir consultar el detalle de una solicitud con su historial de cambios. |
| RF-55 | El sistema debe registrar en cada solicitud el usuario registrador, que queda fijo, y separadamente el nombre del técnico como anotación de texto libre. |
| RF-56 | El sistema debe permitir **solo al Administrador** fijar el monto a cobrar y anotar el técnico de una solicitud no terminal. |
| RF-57 | El sistema debe impedir que un Encargado de Servicios fije el monto o anote el técnico. |
| RF-58 | El sistema debe permitir cotizar una solicitud en cualquier momento antes de su cierre, y volver a ajustar el monto mientras siga abierta. |
| RF-59 | El sistema debe registrar en el historial cada cotización y cada anotación de técnico, con autor y momento. |
| RF-60 | El sistema debe permitir al Administrador filtrar las solicitudes pendientes de cotizar. |
| RF-61 | El sistema debe impedir finalizar una solicitud que no tenga monto cotizado, indicando que el Administrador debe cotizarla primero. |
| RF-62 | El sistema debe aceptar un monto de cero y rechazar montos negativos. |
| RF-63 | El sistema debe impedir la edición del monto, de las observaciones y del técnico una vez finalizada la solicitud. |
| RF-64 | El sistema debe impedir que un Encargado de Servicios acceda a una solicitud que no registró, ni siquiera solicitando su identificador directamente. |
| RF-67 | El sistema debe permitir descargar en PDF el informe de una solicitud de servicio, con el membrete de la empresa, la fecha de generación y quién lo generó. |
| RF-68 | El sistema debe ofrecer al usuario elegir la ubicación de guardado del informe cuando el navegador lo permita. |

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
| RF-49 | El sistema debe mostrar al Administrador la cantidad de solicitudes de servicio pendientes, desglosando cuántas están pendientes de cotizar. |
| RF-50 | El sistema debe mostrar al Administrador la lista de productos con existencias bajas según el umbral global vigente. |
| RF-51 | El sistema debe presentar los indicadores de forma visual y permitir acceder desde ellos al módulo correspondiente. |
| RF-65 | El sistema debe mostrar al Administrador la cantidad de servicios finalizados en el día y la suma de sus montos cobrados. |
| RF-66 | El sistema debe mostrar al Administrador el ingreso total del día, diferenciando siempre el importe proveniente de ventas del proveniente de servicios. |

### 7.7 Movimientos de stock *(v1.4)*

| ID | Requerimiento |
|---|---|
| RF-81 | El sistema debe registrar automáticamente un movimiento por cada cambio de existencias —alta, venta, anulación o ajuste manual—, con el producto, el tipo, la cantidad con signo, las existencias resultantes, el autor, la fecha y hora, la venta de referencia cuando corresponda y el motivo. |
| RF-82 | El sistema debe permitir al Administrador consultar los movimientos de stock filtrando por producto, tipo y rango de fechas, en una lista paginada. |
| RF-83 | El sistema debe mostrar al Administrador el historial de movimientos de un producto desde su detalle. |

### 7.8 Clientes *(v1.4)*

| ID | Requerimiento |
|---|---|
| RF-84 | El sistema debe permitir al Administrador y al Encargado de Ventas registrar clientes con nombre y teléfono obligatorios, y dirección y carnet opcionales. |
| RF-85 | El sistema debe permitir al Administrador y al Encargado de Ventas editar los datos de un cliente. |
| RF-86 | El sistema debe permitir buscar clientes por nombre, teléfono o carnet, en una lista paginada que pueda filtrarse por activos o inactivos. |
| RF-87 | El sistema debe permitir solo al Administrador desactivar y reactivar clientes, sin eliminarlos nunca. |
| RF-88 | El sistema debe impedir registrar dos clientes con el mismo carnet. |
| RF-89 | El sistema debe mostrar el carnet de un cliente únicamente en su detalle. |

### 7.9 Reportes *(v1.4)*

| ID | Requerimiento |
|---|---|
| RF-90 | El sistema debe ofrecer al Administrador una pantalla de reportes con un rango de fechas elegible y los atajos «hoy», «esta semana» y «este mes». |
| RF-91 | El sistema debe mostrar, para el rango, la cantidad e importe de las ventas confirmadas y de los servicios finalizados, y el ingreso total desglosado por origen. |
| RF-92 | El sistema debe mostrar los productos más vendidos del rango, con sus unidades e importe. |
| RF-93 | El sistema debe mostrar la cantidad e importe de las ventas del rango agrupadas por el usuario que las registró. |
| RF-94 | El sistema debe mostrar la cantidad de solicitudes de servicio del rango agrupadas por estado. |
| RF-95 | El sistema debe exportar el reporte de un rango a PDF con el membrete de la empresa. |
| RF-96 | El sistema debe exportar el reporte de un rango a Excel (.xlsx). |

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
| RNF-26 | *(v1.4)* Los datos personales de los clientes se tratan con minimización: el carnet solo es visible en el detalle del cliente y nunca se incluye en listados, detalles de venta, garantías, reportes ni exportaciones. |

### 8.2 Integridad y concurrencia

| ID | Requerimiento |
|---|---|
| RNF-08 | El descuento de existencias es seguro ante concurrencia: dos ventas simultáneas del mismo producto **nunca** pueden dejar el stock en negativo ni vender la misma unidad dos veces. |
| RNF-09 | El registro de una venta es atómico: o se guardan la venta, su detalle y el descuento de inventario completos, o no se guarda nada. |
| RNF-10 | La anulación de una venta es igualmente atómica respecto de la devolución de existencias. |
| RNF-11 | El historial de ventas y servicios es inmutable en sus datos congelados, incluso si los productos o las cuentas cambian después. |
| RNF-24 | *(v1.4)* El registro de cada movimiento de stock es atómico con el cambio de existencias que lo origina y respeta el mismo bloqueo de filas que RNF-08: ni dos operaciones simultáneas, ni un fallo a mitad de una operación, pueden dejar una existencia sin su movimiento o un movimiento sin su existencia. |
| RNF-25 | *(v1.4)* Los movimientos de stock son inmutables: ninguna vía del sistema permite editarlos ni eliminarlos. |

### 8.3 Usabilidad

| ID | Requerimiento |
|---|---|
| RNF-12 | La interfaz es usable en distintos tamaños de pantalla (escritorio, portátil y tableta). |
| RNF-13 | La interfaz está íntegramente en español. |
| RNF-14 | Toda operación que modifica o elimina datos pide confirmación explícita e informa claramente su resultado. |
| RNF-15 | Los errores de validación se muestran junto al campo que los origina, con un mensaje comprensible para el usuario. |
| RNF-16 | Las tareas frecuentes (registrar una venta, registrar un servicio) se completan sin pasos innecesarios. |
| RNF-27 | *(v1.4)* El registro de venta funciona con un lector de código de barras que opera como teclado, sin configuración ni pasos adicionales; los códigos de barras que imprime el sistema son EAN-13 válidos, legibles por lectores estándar. |

### 8.4 Rendimiento y operación

| ID | Requerimiento |
|---|---|
| RNF-17 | Las consultas habituales (catálogo, historiales, panel) responden en menos de 3 segundos bajo carga normal de trabajo. |
| RNF-18 | Los listados extensos se presentan paginados. |
| RNF-19 | El sistema soporta el uso simultáneo de todo el personal de la empresa sin degradación perceptible. |
| RNF-28 | *(v1.4)* Un reporte de un rango de hasta un año, y su exportación, se generan en menos de 5 segundos bajo carga normal de trabajo. |

### 8.5 Mantenibilidad y trazabilidad del proyecto

| ID | Requerimiento |
|---|---|
| RNF-20 | El frontend y el backend son aplicaciones separadas que se comunican exclusivamente por la API; el frontend nunca accede a la base de datos directamente. |
| RNF-21 | El proyecto se versiona en un repositorio Git propio e independiente de cualquier otro proyecto. |
| RNF-22 | La especificación (`spec.md`), el plan técnico (`plan.md`) y el desglose de tareas (`tasks.md`) son documentos vivos: todo cambio funcional se refleja primero en ellos y luego en el código. |
| RNF-23 | Cada funcionalidad implementada cuenta con pruebas automatizadas que verifican sus reglas de negocio. |
| RNF-29 | *(v1.4)* Toda migración de la base de datos es reversible, y las que transforman datos existentes —asignación de códigos, saldos iniciales de stock— no pierden ni alteran ningún dato previo. |

---

## 9. Criterios de aceptación de la especificación

Esta etapa se considera aprobada cuando:

1. Los tres actores, sus permisos y sus límites reflejan la operación real
   de PC-Solution.
2. Los seis módulos funcionales están cubiertos por casos de uso.
3. Las reglas de negocio críticas están explícitas y son verificables:
   congelado de precios (RN-VEN-04), confirmación todo-o-nada
   (RN-VEN-02), devolución de existencias en la anulación (RN-VEN-07),
   dirección condicional al tipo de servicio (RN-SER-04), observaciones
   obligatorias para finalizar (RN-SER-03) y las protecciones de la cuenta
   de Administrador (RN-USU-02 a RN-USU-04).
4. La separación entre usuario registrador y técnico anotado es explícita
   y trazable (RN-SER-09, RN-SER-12). *(Corregido en v1.4: decía
   «técnico asignado».)*
5. Los ingresos del panel y de los reportes distinguen siempre su origen
   (RN-IND-05, RN-REP-03).
6. El documento no contiene decisiones de implementación.
7. *(v1.4)* Las nuevas reglas críticas también son verificables: código
   inmutable y no reutilizable (RN-CAT-08), congelado de la garantía
   (RN-VEN-12), movimiento atómico con el cambio de existencias y libro
   cuadrado (RN-MOV-01, RN-MOV-03), clientes sin acceso al sistema y sin
   efecto sobre ventas pasadas (RN-CLI-04, RN-CLI-05) y minimización del
   carnet (RN-CLI-06).

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
- **SUP-06** *(v1.4)* — La garantía la otorga PC-Solution por los meses
  configurados en cada producto. El sistema **emite** el documento de
  garantía, pero **no gestiona reclamos** de garantía: un reclamo se
  atiende presencialmente, con la garantía y la venta como respaldo. Un
  reclamo que da lugar a reparar el equipo puede registrarse como una
  solicitud de servicio con monto cero (RN-SER-17).
- **SUP-07** *(v1.4)* — El lector de código de barras que use la empresa
  funciona en **modo teclado**: escribe los dígitos del código y termina
  con la tecla Intro, que es la configuración de fábrica de la gran
  mayoría de lectores.
- **SUP-08** *(v1.4, revisado con PA-07)* — Un producto que trae código
  de barras de fábrica se reconoce por ese código **si se registró** en
  el sistema (RN-CAT-11); los que no lo traen, o cuyo código de fábrica
  no se registró, se etiquetan con el código interno que imprime el
  sistema. Un lector apuntado a un código que no está registrado no
  encuentra el producto.

---

## 11. Decisiones resueltas

Las cinco preguntas abiertas de la versión 1.0 fueron resueltas el
2026-09-22 y ya están incorporadas al cuerpo del documento.

| # | Pregunta | Decisión | Se refleja en |
|---|---|---|---|
| **PA-01** | ¿Umbral de existencias bajas global o por producto? | **Global**: un único número configurable para todo el catálogo. | RN-CAT-07, CU-CAT-06, RF-52, RF-53, RN-IND-03, SUP-01 |
| **PA-02** | ¿Plazo límite para anular una venta propia? | **Sin límite de plazo**; el control es la trazabilidad de la anulación. | RN-VEN-11, CU-VEN-03, RF-54 |
| **PA-03** | ¿El servicio técnico registra un monto cobrado? | **Sí.** *(v1.1: lo registraba el técnico al finalizar. **Revisado en v1.2**: lo cotiza y registra el **Administrador** tras la revisión.)* | RN-SER-13, RN-SER-16, RN-SER-17, CU-SER-06, RF-56 a RF-58, RF-61, RF-62 |
| **PA-04** | ¿Quién ve cada solicitud? | **Quien la registró y el Administrador.** *(v1.1: todo el área de servicios. **Revisado en v1.2**.)* | RN-SER-15, sección 4.3, matriz 4.4, CU-SER-02 a CU-SER-05, RF-36, RF-64 |
| **PA-05** | ¿Técnico responsable distinto del registrador? | **Como anotación de texto libre**, no como entidad asignable. *(v1.1: era una asignación formal con historial de reasignaciones. **Revisado en v1.2**.)* | RN-SER-09 a RN-SER-12, CU-SER-06, RF-55, RF-59 |

### Qué cambió en la revisión de v1.2

Las tres decisiones revisadas simplifican el módulo de servicios y, de
paso, **eliminan la asimetría** que la v1.1 declaraba intencional.

1. **Ventas y servicios pasan a comportarse igual.** La v1.1 hacía de
   los servicios un espacio compartido dentro del área, y dedicaba
   varios párrafos a justificar por qué eso no era una inconsistencia
   frente al historial privado de ventas. Con PA-04 revisado, ambos
   módulos siguen el mismo modelo: **privado por usuario, con el
   Administrador viéndolo todo**. No hay asimetría que explicar.
2. **El técnico deja de ser un problema de autorización.** Al ser texto
   libre y no una cuenta, no hay que validar si está activo, ni
   reasignar cuando se bloquea, ni impedir que alguien se autoasigne.
   Desaparecen cuatro reglas y un caso de uso.
3. **Cotizar y cerrar se separan.** El Administrador cotiza tras la
   revisión; el Encargado de Servicios cierra cuando termina el trabajo.
   Eso reparte la responsabilidad —quien decide el precio no es quien
   ejecuta— y es la razón de que pasar a *En atención* ya no tenga
   guarda: el trabajo empieza antes de que exista el importe.
4. **El historial sigue siendo el control de responsabilidad**, aunque
   ahora cada usuario solo vea lo suyo: es lo que permite saber quién
   cotizó, quién cambió el estado y quién cerró.

### Una condición que la revisión no resolvía y aquí se fija

PA-03 dice cuándo y quién cotiza, pero no si una solicitud puede
cerrarse sin monto. **Se decide que no puede** (RN-SER-13): sin esa
condición, un servicio podría finalizarse sin importe y los ingresos
del panel (RN-IND-04) dejarían de reflejar lo realmente cobrado. Un
servicio gratuito se cotiza en cero, que es distinto de no cotizarlo.

---

## 12. Decisiones de la v1.4

Las tres preguntas que la v1.4 dejó abiertas se resolvieron el
2026-10-08, al aprobarla, y ya están incorporadas al cuerpo del
documento.

| # | Pregunta | Decisión | Se refleja en |
|---|---|---|---|
| **PA-06** | ¿Las solicitudes de servicio deberían poder elegir un cliente registrado, igual que las ventas? | **No en esta versión; queda para la v1.5.** Las solicitudes siguen guardando el contacto como dato propio y el Encargado de Servicios no accede a Clientes. | §2.3, §4.3, RN-CLI-07 |
| **PA-07** | ¿Debería el lector reconocer también el **código de fábrica** que traen las cajas? | **Sí.** Campo opcional por producto, único si se informa, reconocido por la búsqueda y por el lector junto al código interno. | RN-CAT-11, RN-VEN-17, RF-70, RF-74, RF-97, CU-CAT-02, CU-CAT-03, CU-CAT-05, CU-VEN-01, SUP-08 |
| **PA-08** | En «servicios por estado» de los reportes, ¿deberían contarse las **canceladas**? | **Sí, como fila informativa.** Cuentan en el recuento, nunca en los importes. | RN-REP-06 |

### Una consecuencia de PA-07 que conviene tener presente

«Único si se informa» resuelve el caso que la pregunta dejaba abierto:
si dos productos distintos traen el mismo código de fábrica, **solo uno
puede registrarlo**, y el otro se vende con su código interno. La
alternativa —permitir códigos de fábrica repetidos— obligaría a que una
lectura pudiera devolver varios productos y a preguntar cuál, que es
justo lo que el lector existe para evitar.

Y una precaución que la decisión no pedía pero que hace falta: un código
de fábrica **no puede tener la forma de un código interno** —13 dígitos
empezando por 20— (RN-CAT-11). Sin eso, un código de fábrica mal
escrito podría coincidir con el código interno de otro producto, y una
misma lectura identificaría a dos.
