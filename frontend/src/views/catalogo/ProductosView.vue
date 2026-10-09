<script setup>
/* CU-CAT-05 y gestion del catalogo (RF-09 a RF-14, RF-53).

   El Encargado de Ventas la ve en modo consulta; el Administrador ve
   las acciones completas (spec.md matriz 4.4). El control real esta en
   el servidor: aqui solo se evita mostrar botones que no funcionarian. */
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleButton from 'primevue/togglebutton'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { categoriasApi, productosApi } from '@/api/catalogo'
import { usePermisos } from '@/composables/usePermisos'
import FormularioProducto from './FormularioProducto.vue'

const { puedeGestionarCatalogo } = usePermisos()
const toast = useToast()
const confirm = useConfirm()

const productos = ref([])
const categorias = ref([])
const total = ref(0)
const cargando = ref(false)
const filtros = ref({
  search: '',
  codigo: '',
  categoria: null,
  stock_bajo: false,
  page: 1,
  page_size: 20,
})

const dialogo = ref(false)
const productoEnEdicion = ref(null)

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

async function cargar() {
  cargando.value = true
  try {
    const params = { page: filtros.value.page, page_size: filtros.value.page_size }
    if (filtros.value.search) params.search = filtros.value.search
    // RF-70: coincidencia exacta con el código interno o el de fábrica.
    if (filtros.value.codigo.trim()) params.codigo = filtros.value.codigo.trim()
    if (filtros.value.categoria) params.categoria = filtros.value.categoria
    if (filtros.value.stock_bajo) params.stock_bajo = 'true'

    const datos = await productosApi.listar(params)
    productos.value = datos.results
    total.value = datos.count
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  } finally {
    cargando.value = false
  }
}

async function cargarCategorias() {
  try {
    const datos = await categoriasApi.listar({ page_size: 100 })
    categorias.value = datos.results
  } catch {
    /* el filtro por categoría queda vacío; la lista sigue siendo usable */
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

function abrirNuevo() {
  productoEnEdicion.value = null
  dialogo.value = true
}

function abrirEdicion(producto) {
  productoEnEdicion.value = producto
  dialogo.value = true
}

function alGuardar() {
  dialogo.value = false
  cargar()
}

function confirmarRetiro(producto) {
  confirm.require({
    header: 'Eliminar del catálogo',
    message:
      `¿Eliminar "${producto.nombre}" del catálogo? Dejará de aparecer para ` +
      'nuevas ventas, pero las ventas ya registradas lo conservarán tal como ' +
      'estaba.',
    acceptLabel: 'Eliminar',
    rejectLabel: 'Cancelar',
    acceptProps: { severity: 'danger' },
    accept: () => retirar(producto),
  })
}

async function retirar(producto) {
  try {
    await productosApi.retirar(producto.id)
    toast.add({
      severity: 'success',
      summary: 'Producto retirado del catálogo',
      life: 3000,
    })
    cargar()
  } catch (error) {
    toast.add({ severity: 'warn', summary: error.detalle, life: 6000 })
  }
}

onMounted(() => {
  cargar()
  cargarCategorias()
})
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Catálogo</h1>
        <p class="subtitulo">Productos y existencias</p>
      </div>
      <Button
        v-if="puedeGestionarCatalogo"
        label="Nuevo producto"
        icon="pi pi-plus"
        @click="abrirNuevo"
      />
    </header>

    <div class="filtros">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filtros.search"
          placeholder="Buscar por nombre"
          @keyup.enter="buscar"
        />
      </IconField>
      <IconField>
        <InputIcon class="pi pi-barcode" />
        <InputText
          v-model="filtros.codigo"
          placeholder="Código exacto"
          aria-label="Buscar por código exacto"
          data-prueba="filtro-codigo"
          @keyup.enter="buscar"
        />
      </IconField>
      <Select
        v-model="filtros.categoria"
        :options="categorias"
        option-label="nombre"
        option-value="id"
        placeholder="Todas las categorías"
        show-clear
        @change="buscar"
      />
      <ToggleButton
        v-model="filtros.stock_bajo"
        on-label="Solo existencias bajas"
        off-label="Solo existencias bajas"
        on-icon="pi pi-exclamation-triangle"
        off-icon="pi pi-filter"
        @change="buscar"
      />
    </div>

    <DataTable
      :value="productos"
      :loading="cargando"
      lazy
      paginator
      :rows="filtros.page_size"
      :total-records="total"
      :rows-per-page-options="[20, 50, 100]"
      data-key="id"
      @page="alPaginar"
    >
      <Column field="codigo" header="Código">
        <template #body="{ data }">
          <span class="codigo">{{ data.codigo }}</span>
        </template>
      </Column>
      <Column header="Producto">
        <template #body="{ data }">
          <div class="producto">
            <img v-if="data.imagen" :src="data.imagen" :alt="data.nombre" />
            <i v-else class="pi pi-image sin-imagen" aria-hidden="true" />
            <RouterLink :to="{ name: 'producto-detalle', params: { id: data.id } }">
              {{ data.nombre }}
            </RouterLink>
          </div>
        </template>
      </Column>
      <Column field="categoria_nombre" header="Categoría" />
      <Column header="Precio">
        <template #body="{ data }">{{ bolivianos.format(data.precio) }}</template>
      </Column>
      <Column header="Existencias">
        <template #body="{ data }">
          <!-- RF-53: el servidor decide si el stock es bajo; aquí solo
               se representa el veredicto. -->
          <Tag
            :value="String(data.stock)"
            :severity="
              data.stock === 0 ? 'danger' : data.stock_bajo ? 'warn' : 'success'
            "
          />
          <small v-if="data.stock === 0" class="nota">sin existencias</small>
        </template>
      </Column>
      <Column v-if="puedeGestionarCatalogo" header="Acciones" style="width: 8rem">
        <template #body="{ data }">
          <div class="acciones">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              aria-label="Editar"
              @click="abrirEdicion(data)"
            />
            <Button
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              aria-label="Eliminar del catálogo"
              @click="confirmarRetiro(data)"
            />
          </div>
        </template>
      </Column>
      <template #empty>Sin productos que coincidan con la búsqueda.</template>
    </DataTable>

    <FormularioProducto
      v-model:visible="dialogo"
      :producto="productoEnEdicion"
      :categorias="categorias"
      @guardado="alGuardar"
    />
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

.producto {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.producto img {
  width: 36px;
  height: 36px;
  object-fit: cover;
  border-radius: 6px;
}

.sin-imagen {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  background: var(--p-surface-100, #f4f4f5);
  color: var(--p-text-muted-color, #a1a1aa);
}

.nota {
  display: block;
  color: var(--p-text-muted-color, #71717a);
}

.codigo {
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace;
  font-size: 0.85rem;
}

.acciones {
  display: flex;
  gap: 0.15rem;
}
</style>
