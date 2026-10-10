<script setup>
/* CU-AUT-01 - Pantalla de inicio de sesion (RF-01, RF-02, RF-03). */
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useErroresApi } from '@/composables/useErroresApi'
import { destinoTrasLogin } from '@/router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const { mensajeGeneral, codigo, registrar, limpiar, errorDe } = useErroresApi()

const username = ref('')
const password = ref('')

async function ingresar() {
  limpiar()
  try {
    await auth.iniciarSesion(username.value, password.value)
    // spec.md v1.4.1: directo al espacio de trabajo del rol, o a la
    // pagina que se habia pedido si el rol puede abrirla.
    router.push(destinoTrasLogin(route.query.redirigir, auth.rol))
  } catch (error) {
    registrar(error)
  }
}
</script>

<template>
  <div class="pantalla">
    <Card class="tarjeta">
      <template #title>
        <div class="titulo">
          <i class="pi pi-desktop" />
          <span>PC-Solution</span>
        </div>
      </template>
      <template #subtitle>Sistema interno · Ingrese con su cuenta</template>

      <template #content>
        <form class="formulario" @submit.prevent="ingresar">
          <div class="campo">
            <label for="username">Usuario</label>
            <InputText
              id="username"
              v-model="username"
              autocomplete="username"
              :invalid="Boolean(errorDe('username'))"
              autofocus
            />
            <small v-if="errorDe('username')" class="error">
              {{ errorDe('username') }}
            </small>
          </div>

          <div class="campo">
            <label for="password">Contraseña</label>
            <Password
              input-id="password"
              v-model="password"
              :feedback="false"
              toggle-mask
              fluid
              autocomplete="current-password"
              :invalid="Boolean(errorDe('password'))"
            />
            <small v-if="errorDe('password')" class="error">
              {{ errorDe('password') }}
            </small>
          </div>

          <!-- Se distingue el bloqueo de la credencial invalida: es lo
               que CU-AUT-01 pide informar al titular. -->
          <Message
            v-if="mensajeGeneral"
            :severity="codigo === 'CUENTA_BLOQUEADA' ? 'warn' : 'error'"
            :closable="false"
          >
            {{ mensajeGeneral }}
          </Message>

          <Button
            type="submit"
            label="Ingresar"
            icon="pi pi-sign-in"
            :loading="auth.cargando"
            fluid
          />
        </form>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.pantalla {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1rem;
}

.tarjeta {
  width: 100%;
  max-width: 420px;
}

.titulo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.formulario {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.campo {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.campo label {
  font-weight: 600;
  font-size: 0.9rem;
}

.error {
  color: var(--p-red-500, #ef4444);
}
</style>
