<script setup>
/* CU-CAT-01 (RF-07, RF-08). Solo Administrador.

   El boton de eliminar se desactiva cuando la categoria tiene
   productos, porque RN-CAT-04 lo prohibe y el servidor responderia
   409. La cuenta de productos viene del servidor, asi que la interfaz
   no tiene que calcularla ni adivinarla. */
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'

import { categoriasApi } from '@/api/catalogo'
import { useErroresApi } from '@/composables/useErroresApi'

const toast = useToast()
const confirm = useConfirm()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const categorias = ref([])
const total = ref(0)
const cargando = ref(false)
const pagina = ref(1)

const dialogo = ref(false)
const editando = ref(null)
const guardando = ref(false)
const formulario = ref({ nombre: '', descripcion: '' })

async function cargar() {
  cargando.value = true
  try {
    const datos = await categoriasApi.listar({ page: pagina.value })
    categorias.value = datos.results
    total.value = datos.count
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  } finally {
    cargando.value = false
  }
}

function alPaginar(evento) {
  pagina.value = evento.page + 1
  cargar()
}

function abrirNueva() {
  limpiar()
  editando.value = null
  formulario.value = { nombre: '', descripcion: '' }
  dialogo.value = true
}

function abrirEdicion(categoria) {
  limpiar()
  editando.value = categoria
  formulario.value = {
    nombre: categoria.nombre,
    descripcion: categoria.descripcion ?? '',
  }
  dialogo.value = true
}

async function guardar() {
  limpiar()
  guardando.value = true
  try {
    if (editando.value) {
      await categoriasApi.actualizar(editando.value.id, formulario.value)
      toast.add({ severity: 'success', summary: 'Categoría actualizada', life: 3000 })
    } else {
      await categoriasApi.crear(formulario.value)
      toast.add({ severity: 'success', summary: 'Categoría creada', life: 3000 })
    }
    dialogo.value = false
    cargar()
  } catch (error) {
    registrar(error)
  } finally {
    guardando.value = false
  }
}

function confirmarEliminacion(categoria) {
  confirm.require({
    header: 'Eliminar categoría',
    message: `¿Eliminar la categoría "${categoria.nombre}"?`,
    acceptLabel: 'Eliminar',
    rejectLabel: 'Cancelar',
    acceptProps: { severity: 'danger' },
    accept: () => eliminar(categoria),
  })
}

async function eliminar(categoria) {
  try {
    await categoriasApi.eliminar(categoria.id)
    toast.add({ severity: 'success', summary: 'Categoría eliminada', life: 3000 })
    cargar()
  } catch (error) {
    // Mensaje del servidor: RN-CAT-04 vive allí.
    toast.add({ severity: 'warn', summary: error.detalle, life: 6000 })
  }
}

onMounted(cargar)
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Categorías</h1>
        <p class="subtitulo">Agrupaciones del catálogo</p>
      </div>
      <Button label="Nueva categoría" icon="pi pi-plus" @click="abrirNueva" />
    </header>

    <DataTable
      :value="categorias"
      :loading="cargando"
      lazy
      paginator
      :rows="20"
      :total-records="total"
      data-key="id"
      @page="alPaginar"
    >
      <Column field="nombre" header="Nombre" />
      <Column field="descripcion" header="Descripción" />
      <Column header="Productos" style="width: 9rem">
        <template #body="{ data }">{{ data.cantidad_productos }}</template>
      </Column>
      <Column header="Acciones" style="width: 8rem">
        <template #body="{ data }">
          <div class="acciones">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              aria-label="Editar"
              @click="abrirEdicion(data)"
            />
            <!-- RN-CAT-04: una categoría con productos no se elimina.
                 Se desactiva para no ofrecer lo que el servidor
                 rechazaría con un 409. -->
            <Button
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              :disabled="data.cantidad_productos > 0"
              aria-label="Eliminar"
              @click="confirmarEliminacion(data)"
            />
          </div>
        </template>
      </Column>
      <template #empty>Aún no hay categorías registradas.</template>
    </DataTable>

    <Dialog
      v-model:visible="dialogo"
      :header="editando ? 'Editar categoría' : 'Nueva categoría'"
      modal
      :style="{ width: '30rem' }"
    >
      <form class="formulario" @submit.prevent="guardar">
        <div class="campo">
          <label for="nombre">Nombre</label>
          <InputText
            id="nombre"
            v-model="formulario.nombre"
            :invalid="Boolean(errorDe('nombre'))"
          />
          <small v-if="errorDe('nombre')" class="error">{{ errorDe('nombre') }}</small>
        </div>

        <div class="campo">
          <label for="descripcion">Descripción</label>
          <Textarea id="descripcion" v-model="formulario.descripcion" rows="3" />
        </div>

        <Message v-if="mensajeGeneral" severity="error" :closable="false">
          {{ mensajeGeneral }}
        </Message>

        <div class="pie">
          <Button label="Cancelar" text @click="dialogo = false" />
          <Button
            type="submit"
            label="Guardar"
            icon="pi pi-check"
            :loading="guardando"
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
  color: var(--p-text-muted-color, #64748b);
}

.acciones {
  display: flex;
  gap: 0.15rem;
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

.pie {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
