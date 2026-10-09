<script setup>
/* Codigo de barras de un producto (RF-71, plan.md 7.9).

   Se dibuja en el navegador con JsBarcode y como SVG: un SVG imprime
   nitido a cualquier tamano, que es lo que un lector necesita para leer
   la etiqueta impresa.

   El codigo interno es siempre un EAN-13 valido (RN-CAT-08), y se
   dibuja como EAN-13 para que cualquier lector estandar lo lea. Un
   codigo de fabrica puede no serlo (UPC, Code128...); si no es un EAN-13
   valido se dibuja en Code128, que admite cualquier texto. */
import JsBarcode from 'jsbarcode'
import { onMounted, ref, watch } from 'vue'

import { esEan13Valido } from '@/utils/codigos'

const props = defineProps({
  valor: { type: String, required: true },
  alto: { type: Number, default: 60 },
})

const svg = ref(null)
const error = ref(false)

function dibujar() {
  if (!svg.value || !props.valor) return
  const formato = esEan13Valido(props.valor) ? 'EAN13' : 'CODE128'
  try {
    JsBarcode(svg.value, props.valor, {
      format: formato,
      height: props.alto,
      displayValue: true,
      fontSize: 14,
      margin: 8,
      background: '#ffffff',
      lineColor: '#000000',
    })
    svg.value.dataset.formato = formato
    error.value = false
  } catch {
    error.value = true
  }
}

onMounted(dibujar)
watch(() => props.valor, dibujar)
</script>

<template>
  <!-- role="img" con su etiqueta: un lector de pantalla anuncia el
       código en cifras en lugar de cientos de rectángulos. -->
  <svg v-show="!error" ref="svg" role="img" :aria-label="`Código de barras ${valor}`" />
  <span v-if="error" class="error">No se pudo dibujar el código {{ valor }}.</span>
</template>

<style scoped>
.error {
  color: var(--p-red-600, #dc2626);
}
</style>
