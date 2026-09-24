<script setup>
/* Raiz de la aplicacion.

   Las rutas publicas (el ingreso) se muestran sin el marco; el resto
   va dentro de AppLayout, con su cabecera y su menu por rol. */
import ConfirmDialog from 'primevue/confirmdialog'
import ProgressSpinner from 'primevue/progressspinner'
import Toast from 'primevue/toast'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppLayout from '@/components/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const conMarco = computed(() => auth.autenticado && !route.meta?.publica)
const restaurando = computed(() => auth.cargando && !auth.usuario && auth.refresh)
</script>

<template>
  <!-- Al abrir la aplicacion con una sesion guardada hay que consultar
       al servidor antes de saber si sigue siendo valida. -->
  <div v-if="restaurando" class="cargando">
    <ProgressSpinner />
    <p>Restaurando sesión…</p>
  </div>

  <AppLayout v-else-if="conMarco">
    <RouterView />
  </AppLayout>

  <RouterView v-else />

  <Toast position="top-right" />
  <ConfirmDialog />
</template>

<style scoped>
.cargando {
  min-height: 100vh;
  display: grid;
  place-items: center;
  gap: 1rem;
  color: var(--p-text-muted-color, #64748b);
}
</style>
