<script setup>
/* CU-CAT-08 — Movimientos de stock (RF-82). Solo el Administrador
   (RN-MOV-06).

   Los filtros se combinan y los aplica el servidor. El producto puede
   llegar en la URL (?producto=) para abrir la pantalla ya filtrada. */
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { productosApi } from '@/api/catalogo'
import { TIPOS_DE_MOVIMIENTO, inventarioApi } from '@/api/inventario'
import TablaMovimientos from '@/components/TablaMovimientos.vue'
import { fechaIso } from '@/utils/fechas'

const route = useRoute()
const toast = useToast()

const movimientos = ref([])
const total = ref(0)
const cargando = ref(false)
const filtros = ref({ producto: null, tipo: null, rango: null, page: 1, page_size: 20 })
const sugerencias = ref([])

/** Parametros que se envian; exportado para las pruebas. */
function parametros() {
  const f = filtros.value
  const params = { page: f.page, page_size: f.page_size }
  if (f.producto?.id) params.producto = f.producto.id
  if (f.tipo) params.tipo = f.tipo
  const [desde, hasta] = f.rango ?? []
  if (desde) params.desde = fechaIso(desde)
  if (hasta) params.hasta = fechaIso(hasta)
  return params
}

async function cargar() {
  cargando.value = true
  try {
    const datos = await inventarioApi.listarMovimientos(parametros())
    movimientos.value = datos.results
    total.value = datos.count
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  } finally {
    cargando.value = false
  }
}

/** Busca entre vigentes y retirados: un producto retirado sigue
 *  teniendo historial que auditar. */
async function buscarProductos(evento) {
  try {
    const [vigentes, retirados] = await Promise.all([
      productosApi.listar({ search: evento.query, page_size: 10 }),
      productosApi.listar({ search: evento.query, page_size: 10, activo: 'false' }),
    ])
    sugerencias.value = [...vigentes.results, ...retirados.results]
  } catch {
    sugerencias.value = []
  }
}

function buscar() {
  filtros.value.page = 1
  cargar()
}

function limpiar() {
  filtros.value = { producto: null, tipo: null, rango: null, page: 1, page_size: 20 }
  cargar()
}

function alPaginar(evento) {
  filtros.value.page = evento.page + 1
  filtros.value.page_size = evento.rows
  cargar()
}

onMounted(async () => {
  const id = route.query?.producto
  if (id) {
    try {
      filtros.value.producto = await productosApi.obtener(id)
    } catch {
      /* producto inexistente: se lista sin ese filtro */
    }
  }
  cargar()
})

defineExpose({ parametros, filtros, cargar })
</script>

<template>
  <section>
    <header class="encabezado">
      <h1>Movimientos de stock</h1>
      <p class="subtitulo">
        Cada cambio de existencias, con su autor y su motivo. No se editan ni se borran.
      </p>
    </header>

    <div class="filtros">
      <AutoComplete
        v-model="filtros.producto"
        :suggestions="sugerencias"
        option-label="nombre"
        placeholder="Producto"
        force-selection
        input-id="filtro-producto"
        @complete="buscarProductos"
        @option-select="buscar"
        @clear="buscar"
      />
      <Select
        v-model="filtros.tipo"
        :options="TIPOS_DE_MOVIMIENTO"
        option-label="label"
        option-value="value"
        placeholder="Todos los tipos"
        show-clear
        @change="buscar"
      />
      <DatePicker
        v-model="filtros.rango"
        selection-mode="range"
        :manual-input="false"
        date-format="dd/mm/yy"
        placeholder="Rango de fechas"
        show-button-bar
        @date-select="buscar"
        @clear-click="buscar"
      />
      <Button label="Limpiar filtros" text icon="pi pi-filter-slash" @click="limpiar" />
    </div>

    <TablaMovimientos
      :movimientos="movimientos"
      :total="total"
      :filas="filtros.page_size"
      :cargando="cargando"
      con-producto
      @pagina="alPaginar"
    />
  </section>
</template>

<style scoped>
.encabezado {
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
