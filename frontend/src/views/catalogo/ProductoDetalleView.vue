<script setup>
/* Detalle de un producto (plan.md 7.4).

   Lo ven el Administrador y el Encargado de Ventas. Solo el
   Administrador ve el historial de movimientos y la accion «Ajustar
   existencias» (RN-MOV-06): para Ventas el servidor responderia 403, y
   aqui se evita mostrar una puerta que no se abre.

   El codigo de barras y la etiqueta (CU-CAT-09) son para los dos: quien
   vende tambien etiqueta el estante. La etiqueta se imprime con la
   impresion del navegador; la hoja de estilos de impresion de abajo
   oculta todo salvo ella (plan.md 7.9). */
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { productosApi } from '@/api/catalogo'
import { inventarioApi } from '@/api/inventario'
import CodigoBarras from '@/components/CodigoBarras.vue'
import TablaMovimientos from '@/components/TablaMovimientos.vue'
import { usePermisos } from '@/composables/usePermisos'
import AjustarExistencias from './AjustarExistencias.vue'

const route = useRoute()
const toast = useToast()
const { puedeGestionarInventario } = usePermisos()

const producto = ref(null)
const error = ref(null)

const historial = ref([])
const totalHistorial = ref(0)
const cargandoHistorial = ref(false)
const paginaHistorial = ref({ page: 1, page_size: 20 })

const dialogoAjuste = ref(false)

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

async function cargarProducto() {
  try {
    producto.value = await productosApi.obtener(route.params.id)
  } catch (e) {
    error.value = e.detalle ?? 'No se pudo cargar el producto.'
  }
}

async function cargarHistorial() {
  if (!puedeGestionarInventario.value) return
  cargandoHistorial.value = true
  try {
    const datos = await inventarioApi.historialDe(route.params.id, paginaHistorial.value)
    historial.value = datos.results
    totalHistorial.value = datos.count
  } catch (e) {
    toast.add({ severity: 'error', summary: e.detalle, life: 5000 })
  } finally {
    cargandoHistorial.value = false
  }
}

function alPaginar(evento) {
  paginaHistorial.value = { page: evento.page + 1, page_size: evento.rows }
  cargarHistorial()
}

/** Tras ajustar se vuelve a pedir todo al servidor: las existencias
 *  que valen son las que el registro, no las que calculo la pantalla. */
async function alAjustar() {
  paginaHistorial.value.page = 1
  await Promise.all([cargarProducto(), cargarHistorial()])
}

/** Imprime solo la etiqueta: codigo de barras, cifras y nombre. */
function imprimirEtiqueta() {
  window.print()
}

onMounted(() => {
  cargarProducto()
  cargarHistorial()
})
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'catalogo' }" class="volver">
      <i class="pi pi-arrow-left" aria-hidden="true" /> Catálogo
    </RouterLink>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <template v-if="producto">
      <header class="encabezado">
        <div class="identidad">
          <img v-if="producto.imagen" :src="producto.imagen" :alt="producto.nombre" />
          <div>
            <h1>{{ producto.nombre }}</h1>
            <p class="subtitulo">
              {{ producto.categoria_nombre }}
              <Tag v-if="!producto.activo" value="Retirado del catálogo" severity="secondary" />
            </p>
          </div>
        </div>
        <Button
          v-if="puedeGestionarInventario"
          label="Ajustar existencias"
          icon="pi pi-sliders-h"
          data-prueba="ajustar"
          @click="dialogoAjuste = true"
        />
      </header>

      <div class="codigos">
        <div class="etiqueta-imprimible" data-prueba="etiqueta">
          <CodigoBarras :valor="producto.codigo" />
          <p class="etiqueta-nombre">{{ producto.nombre }}</p>
        </div>
        <dl class="datos-codigo">
          <div>
            <dt>Código interno</dt>
            <dd data-prueba="codigo">{{ producto.codigo }}</dd>
          </div>
          <div>
            <dt>Código de fábrica</dt>
            <dd data-prueba="codigo-fabrica">{{ producto.codigo_fabrica || 'No registrado' }}</dd>
          </div>
          <Button
            label="Imprimir etiqueta"
            icon="pi pi-print"
            severity="secondary"
            outlined
            data-prueba="imprimir"
            @click="imprimirEtiqueta"
          />
        </dl>
      </div>

      <dl class="datos">
        <div>
          <dt>Precio</dt>
          <dd>{{ bolivianos.format(producto.precio) }}</dd>
        </div>
        <div>
          <dt>Existencias</dt>
          <dd data-prueba="existencias">
            <Tag
              :value="String(producto.stock)"
              :severity="producto.stock === 0 ? 'danger' : producto.stock_bajo ? 'warn' : 'success'"
            />
          </dd>
        </div>
        <div v-if="producto.descripcion" class="ancho">
          <dt>Descripción</dt>
          <dd>{{ producto.descripcion }}</dd>
        </div>
      </dl>

      <template v-if="puedeGestionarInventario">
        <h2>Historial de movimientos</h2>
        <TablaMovimientos
          :movimientos="historial"
          :total="totalHistorial"
          :filas="paginaHistorial.page_size"
          :cargando="cargandoHistorial"
          @pagina="alPaginar"
        />
        <AjustarExistencias
          v-model:visible="dialogoAjuste"
          :producto="producto"
          @ajustado="alAjustar"
        />
      </template>
    </template>
  </section>
</template>

<style scoped>
.volver {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
  margin-bottom: 1rem;
  color: var(--p-primary-color, #7c3aed);
  text-decoration: none;
}

.encabezado {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.identidad {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.identidad img {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 8px;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
}

h2 {
  font-size: 1.1rem;
  margin: 1.5rem 0 0.75rem;
}

.subtitulo {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color, #71717a);
}

.datos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 1rem;
  margin: 0;
}

.datos .ancho {
  grid-column: 1 / -1;
}

dt {
  color: var(--p-text-muted-color, #71717a);
  font-size: 0.85rem;
}

dd {
  margin: 0.25rem 0 0;
}

.codigos {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  align-items: center;
  margin-bottom: 1.25rem;
}

.etiqueta-imprimible {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: #ffffff;
  border: 1px solid var(--p-surface-200, #e4e4e7);
  border-radius: 6px;
}

.etiqueta-nombre {
  margin: 0;
  max-width: 16rem;
  font-size: 0.85rem;
  text-align: center;
  color: #000000;
}

.datos-codigo {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 0;
}
</style>

<!-- Sin scoped: la impresión afecta a toda la página. Se oculta todo y
     se deja visible solo la etiqueta, arriba a la izquierda, sin borde. -->
<style>
@media print {
  body * {
    visibility: hidden;
  }

  .etiqueta-imprimible,
  .etiqueta-imprimible * {
    visibility: visible;
  }

  .etiqueta-imprimible {
    position: fixed;
    top: 0;
    left: 0;
    border: none;
  }
}
</style>
