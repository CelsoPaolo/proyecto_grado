<script setup>
/* Destino del guard cuando un rol intenta entrar donde no le
   corresponde. Es usabilidad: el servidor ya habria respondido 403
   igualmente (RN-ACC-04). */
import Button from 'primevue/button'
import Card from 'primevue/card'
import { computed } from 'vue'

import { espacioDeTrabajo } from '@/router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const destino = computed(() => espacioDeTrabajo(auth.rol))
</script>

<template>
  <Card class="tarjeta">
    <template #title>Sin permiso</template>
    <template #content>
      <p>
        Su rol no tiene acceso a esa sección. Si cree que debería tenerlo,
        consulte con el administrador del sistema.
      </p>
    </template>
    <template #footer>
      <RouterLink v-if="destino.name !== 'sin-permiso'" :to="destino">
        <Button label="Ir a mi espacio de trabajo" icon="pi pi-arrow-left" />
      </RouterLink>
    </template>
  </Card>
</template>

<style scoped>
.tarjeta {
  max-width: 520px;
}
</style>
