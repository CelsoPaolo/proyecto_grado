<script setup>
/* CU-VEN-02 — Historial de ventas (RF-21, RF-22, RNF-18).

   El alcance de lo que se ve lo decide el SERVIDOR: un Encargado de
   Ventas recibe solo las suyas y el Administrador todas (RF-27). La
   pantalla es la misma para ambos; no filtra nada por su cuenta. */
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ventasApi } from '@/api/ventas'
import { usePermisos } from '@/composables/usePermisos'

const router = useRouter()
const toast = useToast()
const { puedeVerTodasLasVentas } = usePermisos()

const ESTADOS = [
  { label: 'Confirmadas', value: 'CONFIRMADA' },
  { label: 'Anuladas', value: 'ANULADA' },
]

const ventas = ref([])
const total = ref(0)
const cargando = ref(false)
const filtros = ref({ estado: null, rango: null, page: 1, page_size: 20 })

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

const fechaHora = new Intl.DateTimeFormat('es-BO', {
  dateStyle: 'short',
  timeStyle: 'short',
})

function comoFecha(valor) {
  return fechaHora.format(new Date(valor))
}

function iso(fecha) {
  if (!fecha) return null
  const f = new Date(fecha)
  return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, '0')}-${String(
    f.getDate(),
  ).padStart(2, '0')}`
}

async function cargar() {
  cargando.value = true
  try {
    const params = { page: filtros.value.page, page_size: filtros.value.page_size }
    if (filtros.value.estado) params.estado = filtros.value.estado
    const [desde, hasta] = filtros.value.rango ?? []
    if (desde) params.desde = iso(desde)
    if (hasta) params.hasta = iso(hasta)

    const datos = await ventasApi.listar(params)
    ventas.value = datos.results
    total.value = datos.count
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  } finally {
    cargando.value = false
  }
}

function buscar() {
  filtros.value.page = 1
  cargar()
}

function alPaginar(evento) {
  filtros.value.page = evento.page + 1
  filtros.value.page_size = evento.rows
  cargar()
}

function abrir(venta) {
  router.push({ name: 'venta-detalle', params: { id: venta.id } })
}

onMounted(cargar)
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Ventas</h1>
        <p class="subtitulo">
          {{ puedeVerTodasLasVentas ? 'Todas las ventas' : 'Mis ventas' }}
        </p>
      </div>
      <RouterLink :to="{ name: 'venta-nueva' }">
        <Button label="Registrar venta" icon="pi pi-plus" />
      </RouterLink>
    </header>

    <div class="filtros">
      <Select
        v-model="filtros.estado"
        :options="ESTADOS"
        option-label="label"
        option-value="value"
        placeholder="Todos los estados"
        show-clear
        @change="buscar"
      />
      <DatePicker
        v-model="filtros.rango"
        selection-mode="range"
        :manual-input="false"
        placeholder="Rango de fechas"
        show-button-bar
        date-format="dd/mm/yy"
        @date-select="buscar"
        @clear-click="buscar"
      />
    </div>

    <DataTable
      :value="ventas"
      :loading="cargando"
      lazy
      paginator
      :rows="filtros.page_size"
      :total-records="total"
      :rows-per-page-options="[20, 50, 100]"
      data-key="id"
      selection-mode="single"
      @page="alPaginar"
      @row-select="abrir($event.data)"
    >
      <Column header="N.º" style="width: 5rem">
        <template #body="{ data }">#{{ data.id }}</template>
      </Column>
      <Column header="Fecha">
        <template #body="{ data }">{{ comoFecha(data.fecha_hora) }}</template>
      </Column>
      <Column field="cliente_nombre" header="Cliente" />
      <Column v-if="puedeVerTodasLasVentas" header="Registrada por">
        <template #body="{ data }">{{ data.usuario.nombre_completo }}</template>
      </Column>
      <Column header="Productos" style="width: 7rem">
        <template #body="{ data }">{{ data.cantidad_items }}</template>
      </Column>
      <Column header="Total">
        <template #body="{ data }">{{ bolivianos.format(data.total) }}</template>
      </Column>
      <Column header="Estado" style="width: 8rem">
        <template #body="{ data }">
          <Tag
            :value="data.estado_display"
            :severity="data.estado === 'ANULADA' ? 'danger' : 'success'"
          />
        </template>
      </Column>
      <template #empty>Aún no hay ventas registradas.</template>
    </DataTable>
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

.filtros {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
</style>
