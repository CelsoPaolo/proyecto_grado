<script setup>
/* Reportes por rango de fechas (RF-90 a RF-96). Solo el Administrador
   (RN-REP-10).

   Los atajos se resuelven aquí en dos fechas (utils/rangos.js); el
   servidor solo conoce rangos. Las cifras vienen tal cual del servidor:
   la pantalla no suma ni recalcula nada, y por eso coincide con el PDF
   y el Excel del mismo rango (RN-REP-07). */
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'

import { TIPO_XLSX, reportesApi } from '@/api/reportes'
import { useDescarga } from '@/composables/useDescarga'
import { useErroresApi } from '@/composables/useErroresApi'
import { fechaIso } from '@/utils/fechas'
import { ATAJOS } from '@/utils/rangos'

const toast = useToast()
const { descargando, guardar } = useDescarga()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const ETIQUETAS_ESTADO = {
  REGISTRADA: 'Registrada',
  EN_ATENCION: 'En atención',
  FINALIZADA: 'Finalizada',
  CANCELADA: 'Cancelada',
}

const atajo = ref('mes')
const fechas = ref(null)
const reporte = ref(null)
const cargando = ref(false)

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

function rangoActual() {
  if (atajo.value) return ATAJOS.find((a) => a.value === atajo.value).calcular(new Date())
  const [desde, hasta] = fechas.value ?? []
  return { desde: fechaIso(desde), hasta: fechaIso(hasta ?? desde) }
}

const sinActividad = computed(
  () =>
    reporte.value &&
    reporte.value.ventas.cantidad === 0 &&
    reporte.value.servicios.cantidad === 0 &&
    Object.values(reporte.value.servicios_por_estado).every((n) => n === 0),
)

const filasEstado = computed(() =>
  Object.entries(reporte.value?.servicios_por_estado ?? {}).map(([estado, cantidad]) => ({
    estado: ETIQUETAS_ESTADO[estado] ?? estado,
    cantidad,
  })),
)

async function consultar() {
  limpiar()
  const rango = rangoActual()
  if (!rango.desde || !rango.hasta) {
    registrar({ detalle: 'Elija un atajo o un rango de fechas.' })
    return
  }
  cargando.value = true
  try {
    reporte.value = await reportesApi.obtener(rango)
  } catch (error) {
    reporte.value = null
    registrar(error)
  } finally {
    cargando.value = false
  }
}

function alElegirAtajo() {
  fechas.value = null
  if (atajo.value) consultar()
}

function alElegirFechas() {
  atajo.value = null
  const [desde, hasta] = fechas.value ?? []
  if (desde && hasta) consultar()
}

async function exportar(formato) {
  const rango = { desde: reporte.value.desde, hasta: reporte.value.hasta }
  const nombre = `reporte-${rango.desde}_${rango.hasta}.${formato}`
  try {
    const guardado =
      formato === 'pdf'
        ? await guardar(() => reportesApi.pdf(rango), nombre)
        : await guardar(() => reportesApi.xlsx(rango), nombre, {
            tipo: TIPO_XLSX,
            extension: '.xlsx',
            descripcion: 'Libro de Excel',
          })
    if (guardado) toast.add({ severity: 'success', summary: 'Reporte descargado', life: 3000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  }
}

onMounted(consultar)

defineExpose({ atajo, fechas, reporte, consultar, exportar, rangoActual })
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Reportes</h1>
        <p class="subtitulo">Ventas, servicios e ingresos de un período</p>
      </div>
      <div v-if="reporte" class="exportar">
        <Button
          label="PDF"
          icon="pi pi-file-pdf"
          outlined
          :loading="descargando"
          data-prueba="exportar-pdf"
          @click="exportar('pdf')"
        />
        <Button
          label="Excel"
          icon="pi pi-file-excel"
          outlined
          :loading="descargando"
          data-prueba="exportar-xlsx"
          @click="exportar('xlsx')"
        />
      </div>
    </header>

    <div class="filtros">
      <SelectButton
        v-model="atajo"
        :options="ATAJOS"
        option-label="label"
        option-value="value"
        data-prueba="atajos"
        @change="alElegirAtajo"
      />
      <DatePicker
        v-model="fechas"
        selection-mode="range"
        :manual-input="false"
        date-format="dd/mm/yy"
        placeholder="Otro rango"
        :invalid="Boolean(errorDe('desde') || errorDe('hasta'))"
        @date-select="alElegirFechas"
      />
    </div>

    <Message v-if="mensajeGeneral" severity="error" :closable="false">{{ mensajeGeneral }}</Message>
    <Message v-else-if="errorDe('desde')" severity="error" :closable="false">{{ errorDe('desde') }}</Message>

    <template v-if="reporte">
      <p class="rango" data-prueba="rango">
        Del {{ reporte.desde.split('-').reverse().join('/') }} al
        {{ reporte.hasta.split('-').reverse().join('/') }}
      </p>

      <Message v-if="sinActividad" severity="info" :closable="false" data-prueba="sin-actividad">
        No hubo actividad en este período: las cifras están en cero.
      </Message>

      <div class="tarjetas">
        <Card>
          <template #title>Ventas</template>
          <template #content>
            <p class="cifra" data-prueba="ventas-importe">{{ bolivianos.format(reporte.ventas.importe) }}</p>
            <p class="nota">{{ reporte.ventas.cantidad }} ventas confirmadas</p>
          </template>
        </Card>
        <Card>
          <template #title>Servicios</template>
          <template #content>
            <p class="cifra">{{ bolivianos.format(reporte.servicios.importe) }}</p>
            <p class="nota">{{ reporte.servicios.cantidad }} servicios finalizados</p>
          </template>
        </Card>
        <Card>
          <template #title>Ingreso total</template>
          <template #content>
            <!-- RN-REP-03: el total, siempre con su desglose. -->
            <p class="cifra" data-prueba="ingreso">{{ bolivianos.format(reporte.ingreso_total.importe) }}</p>
            <p class="nota">
              Ventas {{ bolivianos.format(reporte.ingreso_total.de_ventas) }} · Servicios
              {{ bolivianos.format(reporte.ingreso_total.de_servicios) }}
            </p>
          </template>
        </Card>
      </div>

      <div class="tablas">
        <Card>
          <template #title>Productos más vendidos</template>
          <template #content>
            <DataTable :value="reporte.productos_mas_vendidos" data-key="producto_id" size="small">
              <Column field="codigo" header="Código" />
              <Column field="nombre" header="Producto" />
              <Column field="unidades" header="Unidades" />
              <Column header="Importe">
                <template #body="{ data }">{{ bolivianos.format(data.importe) }}</template>
              </Column>
              <template #empty>Sin ventas en el período.</template>
            </DataTable>
          </template>
        </Card>
        <Card>
          <template #title>Ventas por usuario</template>
          <template #content>
            <DataTable :value="reporte.ventas_por_usuario" data-key="usuario_id" size="small">
              <Column field="nombre_completo" header="Usuario" />
              <Column field="cantidad" header="Ventas" />
              <Column header="Importe">
                <template #body="{ data }">{{ bolivianos.format(data.importe) }}</template>
              </Column>
              <template #empty>Sin ventas en el período.</template>
            </DataTable>
          </template>
        </Card>
        <Card>
          <template #title>Servicios registrados por estado</template>
          <template #content>
            <DataTable :value="filasEstado" data-key="estado" size="small">
              <Column field="estado" header="Estado" />
              <Column field="cantidad" header="Solicitudes" />
            </DataTable>
            <small class="nota">Las canceladas se muestran para saber cuántas se perdieron; no suman ingreso.</small>
          </template>
        </Card>
      </div>
    </template>
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

.subtitulo,
.nota,
.rango {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color, #71717a);
}

.exportar,
.filtros {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.filtros {
  margin-bottom: 1rem;
}

.tarjetas,
.tablas {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.cifra {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}
</style>
