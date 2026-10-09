<script setup>
/* Tabla del libro de movimientos (CU-CAT-08).

   La comparten la pantalla de movimientos (RF-82) y el historial del
   detalle de producto (RF-83), para que ambas muestren lo mismo de la
   misma forma. Es solo presentacion: la paginacion la hace el servidor
   (RNF-18) y la pantalla que la usa decide que pedir. */
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import { RouterLink } from 'vue-router'

import { comoFechaHora } from '@/utils/fechas'

defineProps({
  movimientos: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  filas: { type: Number, default: 20 },
  cargando: { type: Boolean, default: false },
  conProducto: { type: Boolean, default: false },
})
const emit = defineEmits(['pagina'])

const SEVERIDAD = {
  SALDO_INICIAL: 'secondary',
  ALTA: 'info',
  VENTA: 'contrast',
  ANULACION: 'warn',
  AJUSTE: 'help',
}

function conSigno(n) {
  return n > 0 ? `+${n}` : String(n)
}
</script>

<template>
  <DataTable
    :value="movimientos"
    :loading="cargando"
    lazy
    paginator
    :rows="filas"
    :total-records="total"
    :rows-per-page-options="[20, 50, 100]"
    data-key="id"
    @page="emit('pagina', $event)"
  >
    <Column header="Fecha y hora">
      <template #body="{ data }">{{ comoFechaHora(data.fecha_hora) }}</template>
    </Column>
    <Column v-if="conProducto" header="Producto">
      <template #body="{ data }">
        <RouterLink :to="{ name: 'producto-detalle', params: { id: data.producto } }">
          {{ data.producto_nombre }}
        </RouterLink>
      </template>
    </Column>
    <Column header="Tipo">
      <template #body="{ data }">
        <Tag :value="data.tipo_display" :severity="SEVERIDAD[data.tipo]" />
      </template>
    </Column>
    <Column header="Cantidad">
      <template #body="{ data }">
        <span :class="data.cantidad < 0 ? 'resta' : 'suma'">{{ conSigno(data.cantidad) }}</span>
      </template>
    </Column>
    <Column field="stock_resultante" header="Quedan" />
    <Column header="Autor">
      <!-- RN-MOV-02: solo el saldo inicial carece de autor; lo creo la
           migracion, no una persona. -->
      <template #body="{ data }">{{ data.usuario_nombre ?? 'Sistema (saldo inicial)' }}</template>
    </Column>
    <Column header="Referencia">
      <template #body="{ data }">
        <RouterLink v-if="data.venta" :to="{ name: 'venta-detalle', params: { id: data.venta } }">
          Venta n.º {{ data.venta }}
        </RouterLink>
        <span v-else>{{ data.motivo }}</span>
      </template>
    </Column>
    <template #empty>Sin movimientos que coincidan con los filtros.</template>
  </DataTable>
</template>

<style scoped>
.suma {
  color: var(--p-green-700, #15803d);
  font-weight: 600;
}

.resta {
  color: var(--p-red-600, #dc2626);
  font-weight: 600;
}
</style>
