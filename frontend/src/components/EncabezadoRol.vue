<script setup>
/* Encabezado de bienvenida del Inicio (plan.md 7.6).
   Puramente presentacional: recibe el usuario y lo pinta. No consulta
   nada ni conoce el store. */
import { computed } from 'vue'

import { identidadDe } from '@/config/identidadRol'

const props = defineProps({
  nombre: { type: String, default: '' },
  rolDisplay: { type: String, default: '' },
  rol: { type: String, default: null },
})

const identidad = computed(() => identidadDe(props.rol))

/* La fecha se calcula en el navegador, con la zona horaria del equipo.
   No es un dato del sistema: es el mismo reloj que el encargado tiene
   delante, y por eso no hace falta pedirsela al servidor. */
const hoy = computed(() =>
  new Intl.DateTimeFormat('es-BO', { dateStyle: 'full' }).format(new Date()),
)
</script>

<template>
  <header class="bienvenida" :style="{ background: identidad.degradado }">
    <i :class="identidad.icono" aria-hidden="true" />
    <div>
      <h1>Hola, {{ nombre }}</h1>
      <p class="rol">{{ rolDisplay }}</p>
      <p class="fecha">{{ hoy }}</p>
    </div>
  </header>
</template>

<style scoped>
.bienvenida {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.75rem;
  border-radius: 12px;
  /* Blanco fijo, no un token: el fondo es siempre uno de los tres
     degradados morados, nunca la superficie del tema. */
  color: #ffffff;
}

.bienvenida > i {
  font-size: 2.25rem;
  /* Circulo translucido en lugar de un color solido, para que el
     degradado siga viendose por detras del icono. */
  background: rgba(255, 255, 255, 0.15);
  border-radius: 50%;
  padding: 0.9rem;
  line-height: 1;
}

h1 {
  margin: 0;
  font-size: 1.5rem;
}

.rol {
  margin: 0.2rem 0 0;
  font-weight: 600;
  /* 0,85 de opacidad sobre los tres degradados sigue por encima de
     4,5:1; no baja mas por eso. */
  opacity: 0.85;
}

.fecha {
  margin: 0.35rem 0 0;
  font-size: 0.9rem;
  opacity: 0.75;
}

@media (max-width: 600px) {
  .bienvenida {
    padding: 1.25rem;
    gap: 0.9rem;
  }

  .bienvenida > i {
    font-size: 1.6rem;
    padding: 0.7rem;
  }

  h1 {
    font-size: 1.25rem;
  }
}
</style>
