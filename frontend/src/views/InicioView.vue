<script setup>
/* Pantalla de entrada (plan.md 7.6).

   Antes repetia el menu: las tarjetas de acceso salian de menuPara(),
   la misma funcion que construye la barra lateral, asi que eran
   literalmente los mismos enlaces dos veces. Y al Encargado de
   Servicios, que tiene un solo modulo, le quedaba una tarjeta suelta
   en una pantalla en blanco.

   Ahora es una pantalla de identidad: saluda, dice el rol y explica en
   una frase de que se ocupa. Deliberadamente NO muestra ningun dato ni
   hace ninguna consulta. La alternativa era un resumen con cifras
   reales, que se descarto: obligaba a un endpoint nuevo y a mantener
   sincronizada una segunda vista de los mismos numeros que ya da el
   panel. Lo que se pierde a cambio esta asumido: quien quiera saber
   que tiene pendiente entra a su modulo, que es donde esta la lista
   completa y al dia.

   La navegacion vive en la barra lateral, y en un solo sitio. */
import Card from 'primevue/card'
import { computed } from 'vue'

import EncabezadoRol from '@/components/EncabezadoRol.vue'
import IlustracionRol from '@/components/IlustracionRol.vue'
import { identidadDe } from '@/config/identidadRol'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const identidad = computed(() => identidadDe(auth.rol))
</script>

<template>
  <section class="inicio">
    <EncabezadoRol
      :nombre="auth.usuario?.nombre_completo"
      :rol-display="auth.usuario?.rol_display"
      :rol="auth.rol"
    />

    <Card class="presentacion">
      <template #content>
        <IlustracionRol :rol="auth.rol" />
        <p class="frase">{{ identidad.frase }}</p>
      </template>
    </Card>
  </section>
</template>

<style scoped>
.inicio {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.presentacion {
  /* Ancho acotado y centrado: estirar la ilustracion a todo el ancho
     de una pantalla de 1440 la dejaria flotando y perdida. */
  max-width: 560px;
  margin: 0 auto;
  width: 100%;
}

.presentacion :deep(.p-card-content) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  padding: 1rem 0.5rem;
}

.frase {
  margin: 0;
  max-width: 34rem;
  text-align: center;
  font-size: 1.05rem;
  line-height: 1.6;
  color: var(--p-text-muted-color, #71717a);
}

@media (max-width: 600px) {
  .frase {
    font-size: 1rem;
  }
}
</style>
