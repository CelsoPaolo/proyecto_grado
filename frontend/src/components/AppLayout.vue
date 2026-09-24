<script setup>
/* Marco de la aplicacion: cabecera, menu lateral por rol y contenido.
   El menu se construye desde la definicion de rutas (menuPara), de
   modo que lo visible y lo navegable no puedan divergir. */
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Tag from 'primevue/tag'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { menuPara } from '@/router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const menuUsuario = ref(null)

const opciones = computed(() => menuPara(auth.rol))

const opcionesCuenta = computed(() => [
  {
    label: 'Cambiar contraseña',
    icon: 'pi pi-key',
    command: () => router.push({ name: 'cambiar-password' }),
  },
  {
    label: 'Cerrar sesión',
    icon: 'pi pi-sign-out',
    command: async () => {
      await auth.cerrarSesion()
      router.push({ name: 'login' })
    },
  },
])
</script>

<template>
  <div class="marco">
    <header class="cabecera">
      <div class="marca">
        <i class="pi pi-desktop" />
        <span>PC-Solution</span>
      </div>

      <div class="identidad">
        <Tag :value="auth.usuario?.rol_display" severity="secondary" />
        <Button
          type="button"
          text
          :label="auth.usuario?.nombre_completo"
          icon="pi pi-user"
          aria-haspopup="true"
          @click="menuUsuario.toggle($event)"
        />
        <Menu ref="menuUsuario" :model="opcionesCuenta" :popup="true" />
      </div>
    </header>

    <div class="cuerpo">
      <nav class="lateral" aria-label="Menú principal">
        <RouterLink
          v-for="opcion in opciones"
          :key="opcion.name"
          :to="opcion.to"
          class="opcion"
          active-class="activa"
        >
          <i :class="opcion.icon" />
          <span>{{ opcion.label }}</span>
        </RouterLink>
      </nav>

      <main class="contenido">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.marco {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  background: var(--p-surface-0, #fff);
  border-bottom: 1px solid var(--p-surface-200, #e2e8f0);
}

.marca {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.1rem;
}

.identidad {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cuerpo {
  display: flex;
  flex: 1;
  min-height: 0;
}

.lateral {
  width: 220px;
  flex-shrink: 0;
  padding: 1rem 0.75rem;
  background: var(--p-surface-0, #fff);
  border-right: 1px solid var(--p-surface-200, #e2e8f0);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.opcion {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--pcs-radio);
  color: inherit;
  text-decoration: none;
}

.opcion:hover {
  background: var(--p-surface-100, #f1f5f9);
}

.opcion.activa {
  background: var(--p-primary-color, #10b981);
  color: var(--p-primary-contrast-color, #fff);
}

.contenido {
  flex: 1;
  min-width: 0;
  padding: 1.5rem;
}

/* En tableta el menu pasa a una barra horizontal para no comerse el
   ancho util de las tablas (RNF-12). */
@media (max-width: 900px) {
  .cuerpo {
    flex-direction: column;
  }

  .lateral {
    width: 100%;
    flex-direction: row;
    overflow-x: auto;
    border-right: none;
    border-bottom: 1px solid var(--p-surface-200, #e2e8f0);
  }

  .contenido {
    padding: 1rem;
  }
}
</style>
