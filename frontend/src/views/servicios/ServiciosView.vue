<script setup>
/* CU-SER-05 — Lista de solicitudes (RF-36, RF-37, RF-60, RNF-18).

   El alcance lo decide el SERVIDOR: un Encargado de Servicios recibe
   solo las que registró, el Administrador todas (RN-SER-15). La
   pantalla es la misma para ambos y no filtra nada por su cuenta. */
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleButton from 'primevue/togglebutton'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  ESTADOS_SOLICITUD,
  TIPOS_SERVICIO,
  serviciosApi,
} from '@/api/servicios'
import { usePermisos } from '@/composables/usePermisos'

const router = useRouter()
const toast = useToast()
const { esAdministrador } = usePermisos()

const solicitudes = ref([])
const total = ref(0)
const cargando = ref(false)
const filtros = ref({
  estado: null,
  tipo: null,
  sin_cotizar: false,
  page: 1,
  page_size: 20,
})

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

const fecha = new Intl.DateTimeFormat('es-BO', { dateStyle: 'short' })

function comoFecha(valor) {
  return valor ? fecha.format(new Date(valor)) : '—'
}

function severidadEstado(estado) {
  return (
    {
      REGISTRADA: 'info',
      EN_ATENCION: 'warn',
      FINALIZADA: 'success',
      CANCELADA: 'danger',
    }[estado] ?? 'secondary'
  )
}

async function cargar() {
  cargando.value = true
  try {
    const params = { page: filtros.value.page, page_size: filtros.value.page_size }
    if (filtros.value.estado) params.estado = filtros.value.estado
    if (filtros.value.tipo) params.tipo = filtros.value.tipo
    if (filtros.value.sin_cotizar) params.sin_cotizar = 'true'

    const datos = await serviciosApi.listar(params)
    solicitudes.value = datos.results
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

function abrir(solicitud) {
  router.push({ name: 'servicio-detalle', params: { id: solicitud.id } })
}

onMounted(cargar)
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Servicios técnicos</h1>
        <p class="subtitulo">
          {{ esAdministrador ? 'Todas las solicitudes' : 'Mis solicitudes' }}
        </p>
      </div>
      <RouterLink :to="{ name: 'servicio-nuevo' }">
        <Button label="Registrar solicitud" icon="pi pi-plus" />
      </RouterLink>
    </header>

    <div class="filtros">
      <Select
        v-model="filtros.estado"
        :options="ESTADOS_SOLICITUD"
        option-label="label"
        option-value="value"
        placeholder="Todos los estados"
        show-clear
        @change="buscar"
      />
      <Select
        v-model="filtros.tipo"
        :options="TIPOS_SERVICIO"
        option-label="label"
        option-value="value"
        placeholder="Todos los tipos"
        show-clear
        @change="buscar"
      />
      <!-- RF-60: las que esperan la intervención del Administrador.
           Al Encargado de Servicios no se le ofrece, porque él no
           cotiza. -->
      <ToggleButton
        v-if="esAdministrador"
        v-model="filtros.sin_cotizar"
        on-label="Solo pendientes de cotizar"
        off-label="Solo pendientes de cotizar"
        on-icon="pi pi-dollar"
        off-icon="pi pi-filter"
        @change="buscar"
      />
    </div>

    <DataTable
      :value="solicitudes"
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
      <Column header="Fecha" style="width: 7rem">
        <template #body="{ data }">{{ comoFecha(data.fecha_registro) }}</template>
      </Column>
      <Column field="cliente_nombre" header="Cliente" />
      <Column header="Tipo">
        <template #body="{ data }">
          <span>{{ data.tipo_display }}</span>
          <small v-if="data.modalidad === 'DOMICILIO'" class="nota">
            a domicilio
          </small>
        </template>
      </Column>
      <Column header="Técnico">
        <template #body="{ data }">
          {{ data.tecnico || '—' }}
        </template>
      </Column>
      <Column header="Monto" style="width: 9rem">
        <template #body="{ data }">
          <span v-if="data.esta_cotizada">
            {{ bolivianos.format(data.monto_cobrado) }}
          </span>
          <!-- Sin cotizar es distinto de cotizado en cero: uno espera
               al Administrador, el otro es un servicio gratuito ya
               decidido (RN-SER-17). -->
          <Tag v-else value="Sin cotizar" severity="secondary" />
        </template>
      </Column>
      <Column header="Estado" style="width: 9rem">
        <template #body="{ data }">
          <Tag
            :value="data.estado_display"
            :severity="severidadEstado(data.estado)"
          />
        </template>
      </Column>
      <Column v-if="esAdministrador" header="Registrada por">
        <template #body="{ data }">
          {{ data.registrada_por.nombre_completo }}
        </template>
      </Column>
      <template #empty>Aún no hay solicitudes registradas.</template>
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

.nota {
  display: block;
  color: var(--p-text-muted-color, #71717a);
}
</style>
