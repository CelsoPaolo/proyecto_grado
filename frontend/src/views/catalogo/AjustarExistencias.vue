<script setup>
/* CU-CAT-07 — Ajustar las existencias de un producto (RF-73).

   Dos pasos dentro del mismo dialogo: primero se indica lo contado y el
   motivo; despues se revisa la diferencia y se confirma (RNF-14).

   La diferencia que se muestra es ORIENTATIVA: se calcula contra las
   existencias que tenia la pantalla al abrirse. La que se registra la
   calcula el servidor al confirmar, contra las vigentes en ese instante
   (plan.md 6.5). Si entre medias se vendio algo, el movimiento creado
   lo dira, y la pantalla avisa cuando no coincide con lo previsto. */
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { computed, ref, watch } from 'vue'

import { inventarioApi } from '@/api/inventario'
import { useErroresApi } from '@/composables/useErroresApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  producto: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'ajustado'])

const toast = useToast()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const cantidadReal = ref(null)
const motivo = ref('')
const revisando = ref(false)
const enviando = ref(false)

watch(
  () => props.visible,
  (abierto) => {
    if (!abierto) return
    limpiar()
    cantidadReal.value = null
    motivo.value = ''
    revisando.value = false
  },
)

const registradas = computed(() => props.producto?.stock ?? 0)

const diferencia = computed(() =>
  cantidadReal.value === null ? null : cantidadReal.value - registradas.value,
)

function conSigno(n) {
  return n > 0 ? `+${n}` : String(n)
}

/** Validacion minima para no pasar a la revision con el formulario a
 *  medias. Las reglas de verdad (RN-MOV-05) las aplica el servidor. */
function revisar() {
  limpiar()
  const errores = {}
  if (cantidadReal.value === null) errores.cantidad_real = ['Indique la cantidad real contada.']
  if (!motivo.value.trim()) errores.motivo = ['Indique el motivo del ajuste.']
  if (Object.keys(errores).length) {
    registrar({ errores })
    return
  }
  if (diferencia.value === 0) {
    registrar({
      detalle: 'La cantidad indicada ya es la registrada: no hay nada que ajustar.',
    })
    return
  }
  revisando.value = true
}

async function confirmar() {
  enviando.value = true
  try {
    const movimiento = await inventarioApi.ajustarExistencias(props.producto.id, {
      cantidadReal: cantidadReal.value,
      motivo: motivo.value.trim(),
    })
    const previsto = diferencia.value
    toast.add({
      severity: movimiento.cantidad === previsto ? 'success' : 'warn',
      summary: 'Existencias ajustadas',
      detail:
        movimiento.cantidad === previsto
          ? `Quedan ${movimiento.stock_resultante} unidades.`
          : `Las existencias cambiaron mientras ajustaba: la diferencia registrada ` +
            `es ${conSigno(movimiento.cantidad)}, no ${conSigno(previsto)}. ` +
            `Quedan ${movimiento.stock_resultante} unidades.`,
      life: 6000,
    })
    emit('ajustado', movimiento)
    emit('update:visible', false)
  } catch (error) {
    registrar(error)
    // Un error de campo se corrige en el formulario, no en la revision.
    if (error?.errores) revisando.value = false
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    header="Ajustar existencias"
    modal
    :style="{ width: '30rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <p class="contexto">
      <strong>{{ producto?.nombre }}</strong><br />
      Existencias registradas: <strong data-prueba="registradas">{{ registradas }}</strong>
    </p>

    <form v-if="!revisando" class="formulario" @submit.prevent="revisar">
      <div class="campo">
        <label for="cantidad_real">Cantidad real contada</label>
        <InputNumber
          input-id="cantidad_real"
          v-model="cantidadReal"
          :min="0"
          :use-grouping="false"
          :invalid="Boolean(errorDe('cantidad_real'))"
        />
        <small v-if="errorDe('cantidad_real')" class="error">
          {{ errorDe('cantidad_real') }}
        </small>
        <small v-else-if="diferencia !== null" class="ayuda" data-prueba="diferencia">
          Diferencia orientativa: {{ conSigno(diferencia) }}. Se recalcula al confirmar,
          por si se vende algo mientras tanto.
        </small>
      </div>

      <div class="campo">
        <label for="motivo">Motivo</label>
        <Textarea
          id="motivo"
          v-model="motivo"
          rows="2"
          placeholder="Por ejemplo: recuento físico, unidad dañada, error de carga"
          :invalid="Boolean(errorDe('motivo'))"
        />
        <small v-if="errorDe('motivo')" class="error">{{ errorDe('motivo') }}</small>
      </div>

      <Message v-if="mensajeGeneral" severity="warn" :closable="false">
        {{ mensajeGeneral }}
      </Message>

      <div class="pie">
        <Button label="Cancelar" text @click="emit('update:visible', false)" />
        <Button type="submit" label="Revisar ajuste" icon="pi pi-arrow-right" />
      </div>
    </form>

    <div v-else class="revision" data-prueba="revision">
      <p>
        Las existencias pasarán de <strong>{{ registradas }}</strong> a
        <strong>{{ cantidadReal }}</strong> ({{ conSigno(diferencia) }}).
      </p>
      <p>Motivo: «{{ motivo.trim() }}»</p>
      <p class="ayuda">
        El ajuste queda registrado en el historial del producto y no se puede
        editar ni borrar. Un error se corrige con otro ajuste.
      </p>

      <Message v-if="mensajeGeneral" severity="warn" :closable="false">
        {{ mensajeGeneral }}
      </Message>

      <div class="pie">
        <Button label="Volver" text :disabled="enviando" @click="revisando = false" />
        <Button
          label="Confirmar ajuste"
          icon="pi pi-check"
          :loading="enviando"
          data-prueba="confirmar"
          @click="confirmar"
        />
      </div>
    </div>
  </Dialog>
</template>

<style scoped>
.contexto {
  margin-top: 0;
}

.formulario,
.revision {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.revision p {
  margin: 0;
}

.campo {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.error {
  color: var(--p-red-600, #dc2626);
}

.ayuda {
  color: var(--p-text-muted-color, #71717a);
}

.pie {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
