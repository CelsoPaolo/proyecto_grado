<script setup>
/* CU-AUT-03 - Cambiar la propia contrasena (RF-05).

   Al cambiarla, el backend invalida los tokens anteriores
   (CHECK_REVOKE_TOKEN), asi que la sesion actual deja de valer: se
   cierra y se lleva al ingreso, en lugar de dejar la aplicacion
   colgada con un token muerto. */
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { authApi } from '@/api/auth'
import { useErroresApi } from '@/composables/useErroresApi'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const passwordActual = ref('')
const passwordNueva = ref('')
const guardando = ref(false)
const listo = ref(false)

async function guardar() {
  limpiar()
  guardando.value = true
  try {
    await authApi.cambiarPasswordPropia(passwordActual.value, passwordNueva.value)
    listo.value = true
    auth.limpiar()
    setTimeout(() => router.push({ name: 'login' }), 1500)
  } catch (error) {
    registrar(error)
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <Card class="tarjeta">
    <template #title>Cambiar contraseña</template>
    <template #subtitle>
      Por seguridad, al cambiarla deberá iniciar sesión nuevamente.
    </template>

    <template #content>
      <Message v-if="listo" severity="success" :closable="false">
        Contraseña actualizada. Redirigiendo al inicio de sesión…
      </Message>

      <form v-else class="formulario" @submit.prevent="guardar">
        <div class="campo">
          <label for="actual">Contraseña actual</label>
          <Password
            input-id="actual"
            v-model="passwordActual"
            :feedback="false"
            toggle-mask
            fluid
            :invalid="Boolean(errorDe('password_actual'))"
          />
          <small v-if="errorDe('password_actual')" class="error">
            {{ errorDe('password_actual') }}
          </small>
        </div>

        <div class="campo">
          <label for="nueva">Contraseña nueva</label>
          <Password input-id="nueva" v-model="passwordNueva" toggle-mask fluid
            :invalid="Boolean(errorDe('password_nueva'))" />
          <small v-if="errorDe('password_nueva')" class="error">
            {{ errorDe('password_nueva') }}
          </small>
        </div>

        <Message v-if="mensajeGeneral" severity="error" :closable="false">
          {{ mensajeGeneral }}
        </Message>

        <Button type="submit" label="Guardar" icon="pi pi-check" :loading="guardando" />
      </form>
    </template>
  </Card>
</template>

<style scoped>
.tarjeta {
  max-width: 480px;
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
