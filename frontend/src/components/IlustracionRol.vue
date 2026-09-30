<script setup>
/* Ilustracion del Inicio (plan.md 7.6).
   SVG en linea: ni dependencias ni archivos de imagen nuevos, y
   dibujado con los tokens del tema para que acompane a la paleta sin
   retoques.

   El motivo son trazos de circuito, los mismos del logo de
   PC-Solution. Sobre ese fondo comun, cada rol pone su simbolo en el
   chip central.

   Es DECORACION: no transmite ninguna informacion que no este ya
   escrita al lado en texto. Por eso lleva aria-hidden y no lleva
   <title>: un lector de pantalla que lo anunciara solo estaria
   entorpeciendo. */
defineProps({
  rol: { type: String, default: null },
})
</script>

<template>
  <svg
    class="ilustracion"
    viewBox="0 0 320 200"
    role="presentation"
    aria-hidden="true"
    focusable="false"
  >
    <!-- Trazos de circuito: iguales para los tres roles. -->
    <g class="circuito" fill="none" stroke-width="2" stroke-linecap="round">
      <path d="M8 40 H60 V76 H112" />
      <path d="M8 160 H48 V124 H112" />
      <path d="M312 56 H268 V88 H208" />
      <path d="M312 150 H252 V120 H208" />
      <path d="M160 148 V182 H236" />
      <path d="M160 52 V22 H84" />
    </g>
    <g class="nodos" stroke="none">
      <circle cx="8" cy="40" r="4" />
      <circle cx="8" cy="160" r="4" />
      <circle cx="312" cy="56" r="4" />
      <circle cx="312" cy="150" r="4" />
      <circle cx="236" cy="182" r="4" />
      <circle cx="84" cy="22" r="4" />
    </g>

    <!-- El chip que sostiene el simbolo del rol. -->
    <rect class="chip" x="112" y="52" width="96" height="96" rx="16" />

    <!-- Simbolo del rol, dibujado en una rejilla de 24 y escalado. -->
    <g
      class="simbolo"
      transform="translate(132 72) scale(2.3333)"
      fill="none"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path
        v-if="rol === 'ADMINISTRADOR'"
        d="M12 2 L20 5.2 V11 C20 16 16.5 19.6 12 21.2 C7.5 19.6 4 16 4 11 V5.2 Z
           M8.8 11.6 L11 13.8 L15.4 9.4"
      />
      <g v-else-if="rol === 'VENTAS'">
        <path d="M2 3 H4.6 L6.8 13.6 A1.8 1.8 0 0 0 8.6 15 H17.8 A1.8 1.8 0 0 0 19.6 13.6 L21 6.6 H5.6" />
        <circle cx="9" cy="19.4" r="1.5" />
        <circle cx="17.6" cy="19.4" r="1.5" />
      </g>
      <path
        v-else-if="rol === 'SERVICIOS'"
        d="M20.4 3.6 L16.8 7.2 L18.2 8.6 L21.8 5 A5.6 5.6 0 0 1 14 12.8
           L7.6 19.2 A2.2 2.2 0 0 1 4.5 16.1 L10.9 9.7 A5.6 5.6 0 0 1 20.4 3.6 Z"
      />
      <!-- Sin rol todavia: el chip se queda vacio en lugar de mostrar
           un simbolo que luego cambiaria de golpe. -->
    </g>
  </svg>
</template>

<style scoped>
.ilustracion {
  display: block;
  width: 100%;
  max-width: 320px;
  height: auto;
  margin: 0 auto;
}

.circuito {
  stroke: var(--p-surface-300, #d4d4d8);
}

.nodos {
  fill: var(--p-surface-400, #a1a1aa);
}

.chip {
  fill: var(--p-primary-50, #f5f3ff);
  stroke: var(--p-primary-200, #ddd6fe);
  stroke-width: 2;
}

.simbolo {
  stroke: var(--p-primary-color, #7c3aed);
}
</style>
