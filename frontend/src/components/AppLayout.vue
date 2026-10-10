<script setup>
/* Marco de la aplicacion: cabecera, menu lateral por rol y contenido.
   El menu se construye desde la definicion de rutas (menuPara), de
   modo que lo visible y lo navegable no puedan divergir. */
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Tag from 'primevue/tag'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { espacioDeTrabajo, menuPara } from '@/router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const menuUsuario = ref(null)

const opciones = computed(() => menuPara(auth.rol))
const inicioDelRol = computed(() => espacioDeTrabajo(auth.rol))

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
      <!-- El logo lleva al espacio de trabajo del rol (plan.md 7.12). -->
      <RouterLink :to="inicioDelRol" class="marca" aria-label="PC-Solution: ir a mi espacio de trabajo">
        <i class="pi pi-desktop" aria-hidden="true" />
        <span>PC-Solution</span>
      </RouterLink>

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

/* Cabecera y barra lateral van en negro; el area de trabajo sigue
   clara. Los colores salen de los tokens --pcs-cromo-* de main.css,
   no se escriben aqui, para que el cromo se ajuste desde un solo
   sitio. */
.cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  background: var(--pcs-cromo-fondo, #09090b);
  border-bottom: 1px solid var(--pcs-cromo-borde, #27272a);
  color: var(--pcs-cromo-texto, #f4f4f5);
}

.marca {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--pcs-cromo-texto, #f4f4f5);
  text-decoration: none;
}

.identidad {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* El boton de cuenta es `text`, asi que hereda el color del tema y
   sobre negro quedaria ilegible. */
.identidad :deep(.p-button.p-button-text) {
  color: var(--pcs-cromo-texto, #f4f4f5);
}

.identidad :deep(.p-button.p-button-text:hover) {
  background: var(--pcs-cromo-hover, #27272a);
  color: var(--pcs-cromo-texto, #f4f4f5);
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
  background: var(--pcs-cromo-fondo, #09090b);
  border-right: 1px solid var(--pcs-cromo-borde, #27272a);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

/* Las opciones inactivas van atenuadas (#a1a1aa sobre negro = 7,4:1)
   para que la activa destaque sin necesidad de negrita. */
.opcion {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--pcs-radio);
  color: var(--pcs-cromo-texto-tenue, #a1a1aa);
  text-decoration: none;
  transition: background-color 0.15s, color 0.15s;
}

.opcion:hover {
  background: var(--pcs-cromo-hover, #27272a);
  color: var(--pcs-cromo-texto, #f4f4f5);
}

.opcion.activa {
  background: var(--p-primary-color, #7c3aed);
  color: var(--p-primary-contrast-color, #fff);
}

/* El foco tiene que verse sobre fondo negro: el anillo por defecto del
   tema es morado oscuro y se perderia. */
.opcion:focus-visible {
  outline: 2px solid var(--p-primary-400, #a78bfa);
  outline-offset: 2px;
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
    border-bottom: 1px solid var(--pcs-cromo-borde, #27272a);
  }

  .contenido {
    padding: 1rem;
  }
}
</style>
