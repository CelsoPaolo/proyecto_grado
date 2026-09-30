<script setup>
/* CU-PAN-01 — Panel de indicadores (RF-48 a RF-51, RF-65, RF-66).

   Dos decisiones de presentación que vienen de la especificación:

   - El ingreso del día NUNCA se muestra como una sola cifra: siempre
     con su desglose por origen (RN-IND-05). La API tampoco lo ofrece
     de otra forma.
   - Cada indicador enlaza a su módulo (RF-51): un número suelto no
     sirve de nada si no se puede ir a ver de qué se compone. */
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'

import { panelApi } from '@/api/panel'

const toast = useToast()

const resumen = ref(null)
const cargando = ref(true)

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

const fechaLarga = computed(() => {
  if (!resumen.value) return ''
  // La fecha llega como 'YYYY-MM-DD'; se construye local para que no
  // se desplace un día al interpretarla como UTC.
  const [anio, mes, dia] = resumen.value.fecha.split('-').map(Number)
  return new Intl.DateTimeFormat('es-BO', { dateStyle: 'full' }).format(
    new Date(anio, mes - 1, dia),
  )
})

const hayIngresos = computed(
  () => resumen.value && Number(resumen.value.ingreso_total.importe) > 0,
)

async function cargar() {
  cargando.value = true
  try {
    resumen.value = await panelApi.resumen()
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Panel</h1>
        <p class="subtitulo">{{ fechaLarga }}</p>
      </div>
      <Button
        icon="pi pi-refresh"
        label="Actualizar"
        text
        :loading="cargando"
        @click="cargar"
      />
    </header>

    <div v-if="cargando && !resumen" class="cargando">
      <ProgressSpinner />
    </div>

    <template v-else-if="resumen">
      <!-- Ingresos del día, siempre desglosados (RN-IND-05) -->
      <Card class="ingresos">
        <template #content>
          <div class="total">
            <span class="etiqueta">Ingresos de hoy</span>
            <strong class="cifra">
              {{ bolivianos.format(resumen.ingreso_total.importe) }}
            </strong>
          </div>

          <div class="desglose">
            <RouterLink :to="{ name: 'ventas' }" class="origen">
              <i class="pi pi-shopping-cart" />
              <div>
                <span class="origen-etiqueta">Ventas</span>
                <strong>
                  {{ bolivianos.format(resumen.ingreso_total.de_ventas) }}
                </strong>
                <small>
                  {{ resumen.ventas_dia.cantidad }}
                  {{ resumen.ventas_dia.cantidad === 1 ? 'venta' : 'ventas' }}
                </small>
              </div>
            </RouterLink>

            <RouterLink :to="{ name: 'servicios' }" class="origen">
              <i class="pi pi-wrench" />
              <div>
                <span class="origen-etiqueta">Servicios</span>
                <strong>
                  {{ bolivianos.format(resumen.ingreso_total.de_servicios) }}
                </strong>
                <small>
                  {{ resumen.servicios_dia.cantidad }}
                  {{
                    resumen.servicios_dia.cantidad === 1
                      ? 'servicio finalizado'
                      : 'servicios finalizados'
                  }}
                </small>
              </div>
            </RouterLink>
          </div>

          <Message v-if="!hayIngresos" severity="secondary" :closable="false">
            Aún no se registraron ingresos hoy.
          </Message>
        </template>
      </Card>

      <div class="tarjetas">
        <!-- Servicios pendientes (RF-49) -->
        <Card>
          <template #title>
            <div class="titulo">
              <span>Servicios pendientes</span>
              <RouterLink :to="{ name: 'servicios' }">
                <Button icon="pi pi-arrow-right" text rounded aria-label="Ver" />
              </RouterLink>
            </div>
          </template>
          <template #content>
            <p class="numero">{{ resumen.servicios_pendientes.total }}</p>
            <ul class="detalle">
              <li>
                <span>Registradas</span>
                <strong>{{ resumen.servicios_pendientes.registradas }}</strong>
              </li>
              <li>
                <span>En atención</span>
                <strong>{{ resumen.servicios_pendientes.en_atencion }}</strong>
              </li>
              <!-- Lo que espera al Administrador: sin cotizar no
                   pueden cerrarse (RN-SER-13). -->
              <li
                :class="{ urgente: resumen.servicios_pendientes.sin_cotizar > 0 }"
              >
                <span>Sin cotizar</span>
                <strong>{{ resumen.servicios_pendientes.sin_cotizar }}</strong>
              </li>
            </ul>
            <RouterLink
              v-if="resumen.servicios_pendientes.sin_cotizar > 0"
              :to="{ name: 'servicios' }"
            >
              <Button
                label="Cotizar pendientes"
                icon="pi pi-dollar"
                size="small"
                severity="warn"
                outlined
              />
            </RouterLink>
          </template>
        </Card>

        <!-- Existencias bajas (RF-50) -->
        <Card class="stock">
          <template #title>
            <div class="titulo">
              <span>Existencias bajas</span>
              <RouterLink :to="{ name: 'catalogo' }">
                <Button icon="pi pi-arrow-right" text rounded aria-label="Ver" />
              </RouterLink>
            </div>
          </template>
          <template #subtitle>
            {{ resumen.stock_bajo.umbral }} unidades o menos
          </template>
          <template #content>
            <p class="numero">{{ resumen.stock_bajo.cantidad }}</p>

            <DataTable
              v-if="resumen.stock_bajo.productos.length"
              :value="resumen.stock_bajo.productos"
              data-key="id"
              size="small"
            >
              <Column field="nombre" header="Producto" />
              <Column header="Existencias" style="width: 7rem">
                <template #body="{ data }">
                  <Tag
                    :value="String(data.stock)"
                    :severity="data.stock === 0 ? 'danger' : 'warn'"
                  />
                </template>
              </Column>
            </DataTable>

            <Message v-else severity="secondary" :closable="false">
              Ningún producto está por debajo del umbral.
            </Message>

            <!-- El panel resume; el catálogo tiene la lista completa. -->
            <small
              v-if="resumen.stock_bajo.cantidad > resumen.stock_bajo.productos.length"
              class="nota"
            >
              Se muestran {{ resumen.stock_bajo.productos.length }} de
              {{ resumen.stock_bajo.cantidad }}. Vea el catálogo para el resto.
            </small>
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
  margin-bottom: 1.25rem;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
}

.subtitulo {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color, #71717a);
}

.cargando {
  display: grid;
  place-items: center;
  min-height: 240px;
}

.ingresos {
  margin-bottom: 1rem;
}

.total {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-bottom: 1rem;
}

.etiqueta {
  color: var(--p-text-muted-color, #71717a);
  font-size: 0.9rem;
}

.cifra {
  font-size: 2.2rem;
  line-height: 1.1;
}

.desglose {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
}

.origen {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem;
  border: 1px solid var(--p-surface-200, #e4e4e7);
  border-radius: var(--pcs-radio);
  color: inherit;
  text-decoration: none;
}

.origen:hover {
  background: var(--p-surface-50, #fafafa);
}

.origen i {
  font-size: 1.4rem;
  color: var(--p-primary-color, #7c3aed);
}

.origen div {
  display: flex;
  flex-direction: column;
}

.origen-etiqueta {
  color: var(--p-text-muted-color, #71717a);
  font-size: 0.85rem;
}

.origen strong {
  font-size: 1.15rem;
}

.origen small {
  color: var(--p-text-muted-color, #71717a);
}

.tarjetas {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
  align-items: start;
}

.titulo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.numero {
  margin: 0 0 0.75rem;
  font-size: 2rem;
  font-weight: 700;
}

.detalle {
  margin: 0 0 1rem;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.detalle li {
  display: flex;
  justify-content: space-between;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--p-surface-100, #f4f4f5);
}

.detalle li.urgente strong {
  color: var(--p-orange-500, #f97316);
}

.nota {
  display: block;
  margin-top: 0.75rem;
  color: var(--p-text-muted-color, #71717a);
}
</style>
