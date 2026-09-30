<script setup>
/* Pantalla de entrada. Cada rol ve solo sus accesos, construidos desde
   la misma definicion de rutas que el menu lateral. */
import Card from 'primevue/card'
import { computed } from 'vue'

import { menuPara } from '@/router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const accesos = computed(() =>
  menuPara(auth.rol).filter((o) => o.name !== 'inicio'),
)
</script>

<template>
  <section>
    <h1>Hola, {{ auth.usuario?.nombre_completo }}</h1>
    <p class="subtitulo">{{ auth.usuario?.rol_display }}</p>

    <div class="accesos">
      <RouterLink v-for="acceso in accesos" :key="acceso.name" :to="acceso.to">
        <Card class="acceso">
          <template #content>
            <i :class="acceso.icon" />
            <span>{{ acceso.label }}</span>
          </template>
        </Card>
      </RouterLink>
    </div>

    <p v-if="accesos.length === 0" class="subtitulo">
      Su cuenta aún no tiene módulos asignados.
    </p>
  </section>
</template>

<style scoped>
h1 {
  margin: 0;
  font-size: 1.4rem;
}

.subtitulo {
  margin: 0.25rem 0 1.5rem;
  color: var(--p-text-muted-color, #71717a);
}

.accesos {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.accesos a {
  text-decoration: none;
  color: inherit;
}

.acceso :deep(.p-card-content) {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 600;
}

.acceso i {
  font-size: 1.4rem;
  color: var(--p-primary-color, #7c3aed);
}
</style>
