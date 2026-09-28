<script setup>
/* CU-CAT-06 — Umbral global de existencias bajas (RF-52).

   La pantalla explica el efecto del valor porque un numero suelto no
   dice nada: el Administrador necesita saber que decide cuando el
   sistema avisa, y que el cambio no altera ninguna existencia. */
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'

import { configuracionApi } from '@/api/configuracion'
import { useErroresApi } from '@/composables/useErroresApi'

const toast = useToast()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const umbral = ref(null)
const guardado = ref(null)
const actualizadoPor = ref(null)
const actualizadoEn = ref(null)
const cargando = ref(false)
const guardando = ref(false)

const hayCambios = computed(() => umbral.value !== guardado.value)

const explicacion = computed(() => {
  if (umbral.value === null) return ''
  if (umbral.value === 0) {
    return 'Solo se avisará de los productos que se hayan agotado por completo.'
  }
  return (
    `Se avisará de los productos que tengan ${umbral.value} ` +
    `${umbral.value === 1 ? 'unidad' : 'unidades'} o menos.`
  )
})

const fechaLegible = computed(() => {
  if (!actualizadoEn.value) return null
  return new Intl.DateTimeFormat('es-BO', {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(new Date(actualizadoEn.value))
})

async function cargar() {
  cargando.value = true
  try {
    const datos = await configuracionApi.obtener()
    umbral.value = datos.umbral_stock_bajo
    guardado.value = datos.umbral_stock_bajo
    actualizadoPor.value = datos.actualizado_por_nombre
    actualizadoEn.value = datos.actualizado_en
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  } finally {
    cargando.value = false
  }
}

async function guardar() {
  limpiar()
  guardando.value = true
  try {
    const datos = await configuracionApi.actualizarUmbral(umbral.value)
    guardado.value = datos.umbral_stock_bajo
    actualizadoPor.value = datos.actualizado_por_nombre
    actualizadoEn.value = datos.actualizado_en
    toast.add({
      severity: 'success',
      summary: 'Umbral actualizado',
      detail: 'El catálogo ya refleja el nuevo valor.',
      life: 4000,
    })
  } catch (error) {
    registrar(error)
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <section>
    <header class="encabezado">
      <h1>Configuración</h1>
      <p class="subtitulo">Parámetros del sistema</p>
    </header>

    <Card class="tarjeta">
      <template #title>Existencias bajas</template>
      <template #subtitle>
        Valor único para todo el catálogo
      </template>

      <template #content>
        <form class="formulario" @submit.prevent="guardar">
          <div class="campo">
            <label for="umbral">Avisar cuando las existencias sean</label>
            <InputNumber
              input-id="umbral"
              v-model="umbral"
              :min="0"
              show-buttons
              :disabled="cargando"
              :invalid="Boolean(errorDe('umbral_stock_bajo'))"
              suffix=" unidades o menos"
            />
            <small v-if="errorDe('umbral_stock_bajo')" class="error">
              {{ errorDe('umbral_stock_bajo') }}
            </small>
            <small v-else class="ayuda">{{ explicacion }}</small>
          </div>

          <Message severity="secondary" :closable="false">
            Cambiar este valor solo afecta a los avisos del catálogo y del
            panel. No modifica ninguna existencia ni ningún precio.
          </Message>

          <Message v-if="mensajeGeneral" severity="error" :closable="false">
            {{ mensajeGeneral }}
          </Message>

          <div class="pie">
            <p v-if="actualizadoPor" class="registro">
              Última modificación: {{ actualizadoPor }} · {{ fechaLegible }}
            </p>
            <Button
              type="submit"
              label="Guardar"
              icon="pi pi-check"
              :loading="guardando"
              :disabled="!hayCambios"
            />
          </div>
        </form>
      </template>
    </Card>
  </section>
</template>

<style scoped>
.encabezado {
  margin-bottom: 1.5rem;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
}

.subtitulo {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color, #64748b);
}

.tarjeta {
  max-width: 560px;
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

.ayuda {
  color: var(--p-text-muted-color, #64748b);
}

.pie {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  justify-content: space-between;
}

.registro {
  margin: 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color, #64748b);
}
</style>
