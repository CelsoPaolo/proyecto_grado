<script setup>
/* CU-VEN-02 y CU-VEN-03 — Detalle y anulación (RF-23, RF-24, RF-25).

   El detalle muestra los datos CONGELADOS de la venta (RN-VEN-04): el
   nombre y el precio que tenía el producto ese día, no los actuales.
   Se advierte explícitamente, porque si no un encargado podría pensar
   que la pantalla muestra datos desactualizados.

   Garantía (CU-VEN-04, RF-77): el botón aparece solo en una venta
   confirmada con alguna línea con garantía (RN-VEN-14). Al llegar recién
   confirmada (?recien=1) además se ofrece emitirla, que es el momento en
   que el cliente sigue en el mostrador. */
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { tieneGarantia, ventasApi } from '@/api/ventas'
import { useDescarga } from '@/composables/useDescarga'
import { useErroresApi } from '@/composables/useErroresApi'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const venta = ref(null)
const cargando = ref(true)
const dialogo = ref(false)
const motivo = ref('')
const anulando = ref(false)

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

const fechaHora = new Intl.DateTimeFormat('es-BO', {
  dateStyle: 'long',
  timeStyle: 'short',
})

function comoFecha(valor) {
  return valor ? fechaHora.format(new Date(valor)) : null
}

const anulada = computed(() => venta.value?.estado === 'ANULADA')
const conGarantia = computed(() => tieneGarantia(venta.value))
const recienConfirmada = computed(() => route.query?.recien === '1')

const { descargando, guardar } = useDescarga()

async function descargarGarantia() {
  try {
    const guardado = await guardar(
      () => ventasApi.garantiaPdf(venta.value.id),
      `garantia-venta-${venta.value.id}.pdf`,
    )
    // false: el usuario cerró el cuadro de guardado; no es un error.
    if (guardado) {
      toast.add({ severity: 'success', summary: 'Garantía descargada', life: 3000 })
    }
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  }
}

async function cargar() {
  cargando.value = true
  try {
    venta.value = await ventasApi.obtener(route.params.id)
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
    router.push({ name: 'ventas' })
  } finally {
    cargando.value = false
  }
}

function abrirAnulacion() {
  limpiar()
  motivo.value = ''
  dialogo.value = true
}

async function anular() {
  limpiar()
  anulando.value = true
  try {
    venta.value = await ventasApi.anular(venta.value.id, motivo.value)
    dialogo.value = false
    toast.add({
      severity: 'success',
      summary: 'Venta anulada',
      detail: 'Las existencias fueron devueltas al inventario.',
      life: 5000,
    })
  } catch (error) {
    registrar(error)
  } finally {
    anulando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <section v-if="venta">
    <header class="encabezado">
      <div>
        <h1>Venta #{{ venta.id }}</h1>
        <p class="subtitulo">{{ comoFecha(venta.fecha_hora) }}</p>
      </div>
      <div class="acciones">
        <Tag
          :value="venta.estado_display"
          :severity="anulada ? 'danger' : 'success'"
        />
        <RouterLink :to="{ name: 'ventas' }">
          <Button label="Volver" icon="pi pi-arrow-left" text />
        </RouterLink>
        <Button
          v-if="conGarantia"
          label="Garantía"
          icon="pi pi-verified"
          outlined
          :loading="descargando"
          data-prueba="garantia"
          @click="descargarGarantia"
        />
        <!-- RN-VEN-08: una venta anulada no se anula otra vez. -->
        <Button
          v-if="!anulada"
          label="Anular venta"
          icon="pi pi-ban"
          severity="danger"
          outlined
          @click="abrirAnulacion"
        />
      </div>
    </header>

    <Message
      v-if="recienConfirmada && conGarantia"
      severity="success"
      :closable="false"
      class="aviso"
      data-prueba="ofrecer-garantia"
    >
      <div class="oferta">
        <span>
          <strong>Venta registrada.</strong> Incluye productos con garantía:
          puede entregar el certificado ahora.
        </span>
        <Button
          label="Emitir garantía"
          icon="pi pi-verified"
          size="small"
          :loading="descargando"
          @click="descargarGarantia"
        />
      </div>
    </Message>

    <Message v-if="anulada" severity="warn" :closable="false" class="aviso">
      <p>
        <strong>Venta anulada</strong> el
        {{ comoFecha(venta.fecha_anulacion) }} por
        {{ venta.anulada_por?.nombre_completo }}.
      </p>
      <p class="motivo">Motivo: {{ venta.motivo_anulacion }}</p>
      <p class="nota">
        Las existencias de estos productos fueron devueltas al inventario.
      </p>
    </Message>

    <div class="columnas">
      <Card class="panel">
        <template #title>Cliente</template>
        <template #content>
          <dl>
            <dt>Nombre</dt>
            <dd>{{ venta.cliente_nombre }}</dd>
            <dt>Teléfono</dt>
            <dd>{{ venta.cliente_telefono }}</dd>
            <dt>Registrada por</dt>
            <dd>{{ venta.usuario.nombre_completo }}</dd>
          </dl>
        </template>
      </Card>

      <Card class="panel">
        <template #title>Detalle</template>
        <template #subtitle>
          Nombres y precios tal como estaban el día de la venta
        </template>
        <template #content>
          <DataTable :value="venta.items" data-key="producto_id">
            <Column field="producto_nombre" header="Producto" />
            <Column header="Precio unitario" style="width: 10rem">
              <template #body="{ data }">
                {{ bolivianos.format(data.precio_unitario) }}
              </template>
            </Column>
            <Column field="cantidad" header="Cantidad" style="width: 7rem" />
            <Column header="Garantía" style="width: 8rem">
              <template #body="{ data }">
                {{ data.meses_garantia > 0 ? `${data.meses_garantia} meses` : '—' }}
              </template>
            </Column>
            <Column header="Subtotal" style="width: 10rem">
              <template #body="{ data }">
                {{ bolivianos.format(data.subtotal) }}
              </template>
            </Column>
          </DataTable>

          <div class="total">
            <span>Total</span>
            <strong>{{ bolivianos.format(venta.total) }}</strong>
          </div>
        </template>
      </Card>
    </div>

    <Dialog
      v-model:visible="dialogo"
      header="Anular venta"
      modal
      :style="{ width: '32rem' }"
    >
      <form class="formulario" @submit.prevent="anular">
        <Message severity="warn" :closable="false">
          Las existencias de los productos volverán al inventario. La venta
          no se elimina: queda registrada como anulada.
        </Message>

        <div class="campo">
          <label for="motivo">Motivo de la anulación</label>
          <Textarea
            id="motivo"
            v-model="motivo"
            rows="3"
            :invalid="Boolean(errorDe('motivo'))"
          />
          <small v-if="errorDe('motivo')" class="error">
            {{ errorDe('motivo') }}
          </small>
          <small v-else class="ayuda">
            Quedará registrado junto con su nombre y la fecha.
          </small>
        </div>

        <Message v-if="mensajeGeneral" severity="error" :closable="false">
          {{ mensajeGeneral }}
        </Message>

        <div class="pie">
          <Button label="Cancelar" text @click="dialogo = false" />
          <Button
            type="submit"
            label="Anular venta"
            icon="pi pi-ban"
            severity="danger"
            :loading="anulando"
            :disabled="!motivo.trim()"
          />
        </div>
      </form>
    </Dialog>
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

.acciones {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.oferta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  justify-content: space-between;
}

.aviso {
  margin-bottom: 1rem;
}

.aviso p {
  margin: 0.15rem 0;
}

.aviso .motivo {
  font-style: italic;
}

.aviso .nota {
  font-size: 0.9rem;
}

.columnas {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 2fr;
  gap: 1rem;
  align-items: start;
}

@media (max-width: 900px) {
  .columnas {
    grid-template-columns: 1fr;
  }
}

dl {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.4rem 1rem;
}

dt {
  font-weight: 600;
  color: var(--p-text-muted-color, #71717a);
}

dd {
  margin: 0;
}

.total {
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--p-surface-200, #e4e4e7);
}

.total strong {
  font-size: 1.4rem;
}

.formulario {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.campo {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.campo label {
  font-weight: 600;
  font-size: 0.9rem;
}

.error {
  color: var(--p-red-500, #ef4444);
}

.ayuda {
  color: var(--p-text-muted-color, #71717a);
}

.pie {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
