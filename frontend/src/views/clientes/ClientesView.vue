<script setup>
/* Lista de clientes (RF-86).

   Sin carnet: la lista viene del servidor sin él (RN-CLI-06), y esta
   pantalla no tiene columna donde ponerlo. Se puede BUSCAR por carnet
   exacto; el resultado muestra al cliente, no su carnet. */
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { clientesApi } from '@/api/clientes'
import FormularioCliente from './FormularioCliente.vue'

const toast = useToast()
const router = useRouter()

const ESTADOS = [
  { label: 'Activos', value: 'true' },
  { label: 'Inactivos', value: 'false' },
]

const clientes = ref([])
const total = ref(0)
const cargando = ref(false)
const filtros = ref({ buscar: '', activo: 'true', page: 1, page_size: 20 })
const dialogo = ref(false)

async function cargar() {
  cargando.value = true
  try {
    const params = { page: filtros.value.page, page_size: filtros.value.page_size }
    if (filtros.value.buscar.trim()) params.buscar = filtros.value.buscar.trim()
    if (filtros.value.activo) params.activo = filtros.value.activo
    const datos = await clientesApi.listar(params)
    clientes.value = datos.results
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

function alRegistrar(cliente) {
  router.push({ name: 'cliente-detalle', params: { id: cliente.id } })
}

onMounted(cargar)

defineExpose({ filtros, cargar })
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Clientes</h1>
        <p class="subtitulo">Datos de contacto. Los clientes no tienen cuenta ni acceso al sistema.</p>
      </div>
      <Button label="Nuevo cliente" icon="pi pi-plus" data-prueba="nuevo" @click="dialogo = true" />
    </header>

    <div class="filtros">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filtros.buscar"
          placeholder="Nombre, teléfono o carnet"
          data-prueba="buscar"
          @keyup.enter="buscar"
        />
      </IconField>
      <Select
        v-model="filtros.activo"
        :options="ESTADOS"
        option-label="label"
        option-value="value"
        placeholder="Todos"
        show-clear
        @change="buscar"
      />
    </div>

    <DataTable
      :value="clientes"
      :loading="cargando"
      lazy
      paginator
      :rows="filtros.page_size"
      :total-records="total"
      :rows-per-page-options="[20, 50, 100]"
      data-key="id"
      @page="alPaginar"
    >
      <Column header="Nombre">
        <template #body="{ data }">
          <RouterLink :to="{ name: 'cliente-detalle', params: { id: data.id } }">{{ data.nombre }}</RouterLink>
        </template>
      </Column>
      <Column field="telefono" header="Teléfono" />
      <Column field="direccion" header="Dirección" />
      <Column header="Estado" style="width: 8rem">
        <template #body="{ data }">
          <Tag :value="data.activo ? 'Activo' : 'Inactivo'" :severity="data.activo ? 'success' : 'secondary'" />
        </template>
      </Column>
      <template #empty>Sin clientes que coincidan con la búsqueda.</template>
    </DataTable>

    <FormularioCliente v-model:visible="dialogo" @guardado="alRegistrar" />
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
