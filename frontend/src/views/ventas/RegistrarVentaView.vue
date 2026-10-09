<script setup>
/* CU-VEN-01 — Registrar una venta (RF-15, RF-16, RF-17, RNF-16).

   La lista de productos que se va armando es estado LOCAL de esta
   pantalla: no se persiste, no se comparte y desaparece al salir. No
   es un carrito de comercio electrónico, que spec.md sección 2.2
   excluye expresamente; es el equivalente a anotar en un papel antes
   de confirmar.

   Los precios se muestran para que el encargado vea el total, pero el
   importe real lo calcula el servidor al confirmar (RN-VEN-04).

   Campo de codigo (RF-74, RN-VEN-17, RNF-27, plan.md 7.9). Un lector en
   modo teclado escribe el codigo y pulsa Intro, como una persona: no
   hace falta configurarlo ni detectarlo. Al recibir Intro:
     - el campo se vacia EN EL ACTO y conserva el foco, listo para la
       lectura siguiente (RNF-16: sin pasos entre lectura y lectura);
     - las lecturas se procesan en COLA y en orden: un lector puede
       enviar la segunda antes de que responda la primera, y dos
       lecturas del mismo codigo deben sumar dos unidades;
     - solo una coincidencia exacta con un producto activo y con
       existencias agrega algo; si no, se avisa junto al campo y el
       codigo leido vuelve al campo seleccionado, para que la lectura
       siguiente lo sustituya. */
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import { useToast } from 'primevue/usetoast'
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'

import { productosApi } from '@/api/catalogo'
import { clientesApi } from '@/api/clientes'
import { ventasApi } from '@/api/ventas'
import { useErroresApi } from '@/composables/useErroresApi'
import FormularioCliente from '@/views/clientes/FormularioCliente.vue'

const router = useRouter()
const toast = useToast()
const { mensajeGeneral, codigo, registrar, limpiar, errorDe } = useErroresApi()

// RF-79: cliente ocasional (como hasta la v1.3) o cliente registrado.
const MODOS = [
  { label: 'Cliente ocasional', value: 'ocasional' },
  { label: 'Cliente registrado', value: 'registrado' },
]
const modoCliente = ref('ocasional')
const clienteNombre = ref('')
const clienteTelefono = ref('')
const clienteElegido = ref(null)
const sugerenciasClientes = ref([])
const dialogoCliente = ref(false)

/** Solo clientes ACTIVOS (RN-CLI-03): un inactivo no se ofrece. */
async function buscarClientes(evento) {
  try {
    const datos = await clientesApi.listar({ buscar: evento.query, activo: 'true', page_size: 10 })
    sugerenciasClientes.value = datos.results
  } catch {
    sugerenciasClientes.value = []
  }
}

/** Un cliente registrado desde la venta queda elegido (RNF-16). */
function alRegistrarCliente(cliente) {
  modoCliente.value = 'registrado'
  clienteElegido.value = cliente
}
const lineas = ref([])
const sugerencias = ref([])
const productoElegido = ref(null)
const confirmando = ref(false)

const codigoLeido = ref('')
const avisoCodigo = ref(null)
const campoCodigo = ref(null)
let colaDeLecturas = Promise.resolve()

/** Detalle enriquecido del 422 de stock: qué falta y cuánto hay. */
const faltantes = ref([])

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

const total = computed(() =>
  lineas.value.reduce((suma, l) => suma + Number(l.precio) * l.cantidad, 0),
)

const puedeConfirmar = computed(
  () =>
    lineas.value.length > 0 &&
    (modoCliente.value === 'registrado'
      ? Boolean(clienteElegido.value?.id)
      : clienteNombre.value.trim() !== '' && clienteTelefono.value.trim() !== ''),
)

async function buscarProductos(evento) {
  try {
    const datos = await productosApi.listar({
      search: evento.query,
      page_size: 20,
    })
    // Un producto agotado no puede venderse (RN-CAT-05): se excluye
    // del buscador en lugar de dejar que el servidor lo rechace luego.
    sugerencias.value = datos.results.filter((p) => p.stock > 0)
  } catch {
    sugerencias.value = []
  }
}

function agregar(producto) {
  if (!producto) return

  const existente = lineas.value.find((l) => l.producto_id === producto.id)
  if (existente) {
    // Se suma en lugar de duplicar la línea: el servidor agrupa por
    // producto de todos modos, y dos líneas del mismo artículo
    // confundirían al encargado.
    existente.cantidad += 1
  } else {
    lineas.value.push({
      producto_id: producto.id,
      nombre: producto.nombre,
      precio: producto.precio,
      stock: producto.stock,
      cantidad: 1,
    })
  }
  productoElegido.value = null
  faltantes.value = []
}

function elementoCodigo() {
  const componente = campoCodigo.value
  return componente?.$el ?? componente ?? null
}

/** Intro en el campo de codigo. */
function leerCodigo() {
  const valor = codigoLeido.value.trim()
  codigoLeido.value = ''
  if (!valor) return colaDeLecturas
  colaDeLecturas = colaDeLecturas.then(() => procesarCodigo(valor))
  return colaDeLecturas
}

async function procesarCodigo(valor) {
  avisoCodigo.value = null
  let producto = null
  try {
    const datos = await productosApi.listar({ codigo: valor, activo: 'true' })
    producto = datos.results[0] ?? null
  } catch (error) {
    return rechazarLectura(valor, error.detalle ?? 'No se pudo consultar el código.')
  }

  if (!producto) {
    return rechazarLectura(
      valor,
      `Ningún producto del catálogo tiene el código ${valor}. No se agregó nada.`,
    )
  }
  if (producto.stock <= 0) {
    return rechazarLectura(valor, `«${producto.nombre}» no tiene existencias. No se agregó.`)
  }
  const enLaVenta = lineas.value.find((l) => l.producto_id === producto.id)
  if (enLaVenta && enLaVenta.cantidad >= producto.stock) {
    return rechazarLectura(
      valor,
      `Ya hay ${enLaVenta.cantidad} de «${producto.nombre}» en la venta y no quedan más existencias.`,
    )
  }
  agregar(producto)
  await enfocarCodigo()
}

/** El codigo vuelve al campo, seleccionado, solo si nadie escribio otro
 *  mientras tanto: no se pisa una lectura que ya llego. */
async function rechazarLectura(valor, mensaje) {
  avisoCodigo.value = mensaje
  if (!codigoLeido.value) codigoLeido.value = valor
  await enfocarCodigo()
  elementoCodigo()?.select?.()
}

async function enfocarCodigo() {
  await nextTick()
  elementoCodigo()?.focus?.()
}

function quitar(linea) {
  lineas.value = lineas.value.filter((l) => l.producto_id !== linea.producto_id)
  faltantes.value = []
}

function limpiarTodo() {
  clienteNombre.value = ''
  clienteTelefono.value = ''
  clienteElegido.value = null
  lineas.value = []
  faltantes.value = []
  limpiar()
}

async function confirmar() {
  limpiar()
  faltantes.value = []
  confirmando.value = true
  try {
    const venta = await ventasApi.registrar({
      clienteId: modoCliente.value === 'registrado' ? clienteElegido.value?.id : null,
      clienteNombre: clienteNombre.value,
      clienteTelefono: clienteTelefono.value,
      items: lineas.value,
    })
    toast.add({
      severity: 'success',
      summary: `Venta #${venta.id} registrada`,
      detail: `Total: ${bolivianos.format(venta.total)}`,
      life: 5000,
    })
    limpiarTodo()
    // RF-77: el detalle ofrece la garantía al llegar desde aquí.
    router.push({ name: 'venta-detalle', params: { id: venta.id }, query: { recien: '1' } })
  } catch (error) {
    registrar(error)
    if (error.codigo === 'STOCK_INSUFICIENTE') {
      faltantes.value = error.errores?.items ?? []
    }
  } finally {
    confirmando.value = false
  }
}
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Registrar venta</h1>
        <p class="subtitulo">Nueva venta de mostrador</p>
      </div>
      <RouterLink :to="{ name: 'ventas' }">
        <Button label="Ver historial" icon="pi pi-list" text />
      </RouterLink>
    </header>

    <div class="columnas">
      <Card class="panel">
        <template #title>Cliente</template>
        <template #content>
          <SelectButton
            v-model="modoCliente"
            :options="MODOS"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            class="modo-cliente"
            data-prueba="modo-cliente"
          />

          <div v-if="modoCliente === 'registrado'" class="campos">
            <div class="campo">
              <label for="cliente-registrado">Cliente</label>
              <AutoComplete
                v-model="clienteElegido"
                input-id="cliente-registrado"
                :suggestions="sugerenciasClientes"
                option-label="nombre"
                placeholder="Buscar por nombre, teléfono o carnet"
                force-selection
                fluid
                :invalid="Boolean(errorDe('cliente_id'))"
                @complete="buscarClientes"
              >
                <template #option="{ option }">
                  <div class="sugerencia">
                    <span>{{ option.nombre }}</span>
                    <small>{{ option.telefono }}</small>
                  </div>
                </template>
              </AutoComplete>
              <small v-if="errorDe('cliente_id')" class="error">{{ errorDe('cliente_id') }}</small>
              <small v-if="clienteElegido?.id" class="ayuda" data-prueba="cliente-elegido">
                {{ clienteElegido.nombre }} · {{ clienteElegido.telefono }}
              </small>
            </div>
            <Button
              label="Registrar cliente nuevo"
              icon="pi pi-user-plus"
              text
              size="small"
              data-prueba="nuevo-cliente"
              @click="dialogoCliente = true"
            />
          </div>

          <div v-else class="campos">
            <div class="campo">
              <label for="cliente">Nombre</label>
              <InputText
                id="cliente"
                v-model="clienteNombre"
                :invalid="Boolean(errorDe('cliente_nombre'))"
              />
              <small v-if="errorDe('cliente_nombre')" class="error">
                {{ errorDe('cliente_nombre') }}
              </small>
            </div>
            <div class="campo">
              <label for="telefono">Teléfono</label>
              <InputText
                id="telefono"
                v-model="clienteTelefono"
                :invalid="Boolean(errorDe('cliente_telefono'))"
              />
              <small v-if="errorDe('cliente_telefono')" class="error">
                {{ errorDe('cliente_telefono') }}
              </small>
            </div>
          </div>
          <small class="ayuda">
            El nombre y el teléfono quedan copiados en la venta. Ningún
            cliente tiene cuenta ni acceso al sistema.
          </small>
          <FormularioCliente v-model:visible="dialogoCliente" @guardado="alRegistrarCliente" />
        </template>
      </Card>

      <Card class="panel">
        <template #title>Productos</template>
        <template #content>
          <div class="campo campo-codigo">
            <label for="codigo-producto">Código</label>
            <InputText
              id="codigo-producto"
              ref="campoCodigo"
              v-model="codigoLeido"
              placeholder="Escanee o escriba el código y pulse Intro"
              autocomplete="off"
              autofocus
              :invalid="Boolean(avisoCodigo)"
              data-prueba="codigo"
              @keydown.enter.prevent="leerCodigo"
            />
            <small v-if="avisoCodigo" class="error" role="alert" data-prueba="aviso-codigo">
              {{ avisoCodigo }}
            </small>
          </div>

          <AutoComplete
            v-model="productoElegido"
            :suggestions="sugerencias"
            option-label="nombre"
            placeholder="O búsquelo por nombre"
            fluid
            complete-on-focus
            @complete="buscarProductos"
            @option-select="agregar($event.value)"
          >
            <template #option="{ option }">
              <div class="sugerencia">
                <span>{{ option.nombre }}</span>
                <small>
                  {{ bolivianos.format(option.precio) }} ·
                  {{ option.stock }} disponibles
                </small>
              </div>
            </template>
          </AutoComplete>

          <DataTable :value="lineas" class="lineas" data-key="producto_id">
            <Column field="nombre" header="Producto" />
            <Column header="Precio" style="width: 8rem">
              <template #body="{ data }">
                {{ bolivianos.format(data.precio) }}
              </template>
            </Column>
            <Column header="Cantidad" style="width: 9rem">
              <template #body="{ data }">
                <InputNumber
                  v-model="data.cantidad"
                  :min="1"
                  :max="data.stock"
                  show-buttons
                  button-layout="horizontal"
                  :input-style="{ width: '2.5rem' }"
                />
              </template>
            </Column>
            <Column header="Subtotal" style="width: 9rem">
              <template #body="{ data }">
                {{ bolivianos.format(data.precio * data.cantidad) }}
              </template>
            </Column>
            <Column style="width: 3rem">
              <template #body="{ data }">
                <Button
                  icon="pi pi-times"
                  text
                  rounded
                  severity="danger"
                  aria-label="Quitar"
                  @click="quitar(data)"
                />
              </template>
            </Column>
            <template #empty>
              Busque un producto arriba para agregarlo a la venta.
            </template>
          </DataTable>

          <!-- RF-17: el 422 de stock se muestra enriquecido, diciendo
               qué falta y cuánto hay, no como un error genérico. -->
          <Message
            v-if="faltantes.length"
            severity="error"
            :closable="false"
            class="faltantes"
          >
            <p><strong>No hay existencias suficientes.</strong></p>
            <ul>
              <li v-for="f in faltantes" :key="f.producto_id">
                {{ f.nombre }}: pidió {{ f.solicitado }}, hay
                {{ f.disponible }} disponibles.
              </li>
            </ul>
            <p class="nota">Ningún producto fue descontado.</p>
          </Message>

          <Message
            v-else-if="mensajeGeneral && codigo !== 'STOCK_INSUFICIENTE'"
            severity="error"
            :closable="false"
          >
            {{ mensajeGeneral }}
          </Message>

          <div class="cierre">
            <div class="total">
              <span>Total</span>
              <strong>{{ bolivianos.format(total) }}</strong>
            </div>
            <div class="botones">
              <Button label="Limpiar" text @click="limpiarTodo" />
              <Button
                label="Confirmar venta"
                icon="pi pi-check"
                :loading="confirmando"
                :disabled="!puedeConfirmar"
                @click="confirmar"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
  </section>
</template>

<style scoped>
.encabezado {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
}

.subtitulo {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color, #71717a);
}

.columnas {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 2fr;
  gap: 1rem;
  align-items: start;
}

@media (max-width: 900px) {
  .columnas {
    grid-template-columns: 1fr;
  }
}

.campos {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.campo {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.modo-cliente {
  margin-bottom: 0.75rem;
}

.campo-codigo {
  margin-bottom: 0.75rem;
}

.campo-codigo input {
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace;
}

.campo label {
  font-weight: 600;
  font-size: 0.9rem;
}

.error {
  color: var(--p-red-500, #ef4444);
}

.ayuda {
  display: block;
  margin-top: 0.75rem;
  color: var(--p-text-muted-color, #71717a);
}

.sugerencia {
  display: flex;
  flex-direction: column;
}

.sugerencia small {
  color: var(--p-text-muted-color, #71717a);
}

.lineas {
  margin-top: 1rem;
}

.faltantes ul {
  margin: 0.5rem 0;
  padding-left: 1.2rem;
}

.faltantes .nota {
  margin: 0;
  font-style: italic;
}

.cierre {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--p-surface-200, #e4e4e7);
}

.total {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
}

.total strong {
  font-size: 1.4rem;
}

.botones {
  display: flex;
  gap: 0.5rem;
}
</style>
