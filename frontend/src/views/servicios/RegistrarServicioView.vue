<script setup>
/* CU-SER-01 — Registrar una solicitud (RF-28, RF-29, RNF-15).

   El campo de dirección aparece y se vuelve obligatorio SOLO para los
   tipos que se atienden a domicilio (RN-SER-04). La interfaz lo hace
   para no pedir un dato que sobra, pero la regla la sigue imponiendo
   el servidor: manipular el formulario no la evita.

   No se piden monto ni técnico: son del Administrador (RF-57). */
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { TIPOS_SERVICIO, exigeDireccion, serviciosApi } from '@/api/servicios'
import { useErroresApi } from '@/composables/useErroresApi'

const router = useRouter()
const toast = useToast()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const formulario = ref({
  clienteNombre: '',
  clienteTelefono: '',
  tipo: null,
  descripcion: '',
  direccion: '',
})
const guardando = ref(false)

const esADomicilio = computed(() => exigeDireccion(formulario.value.tipo))

const puedeGuardar = computed(() => {
  const f = formulario.value
  const base =
    f.clienteNombre.trim() && f.clienteTelefono.trim() && f.tipo && f.descripcion.trim()
  return Boolean(base && (!esADomicilio.value || f.direccion.trim()))
})

// Al pasar de domicilio a taller se limpia la dirección: el servidor
// la descarta de todos modos, y dejarla escrita haría creer que se
// guardó.
watch(esADomicilio, (aDomicilio) => {
  if (!aDomicilio) formulario.value.direccion = ''
})

async function guardar() {
  limpiar()
  guardando.value = true
  try {
    const solicitud = await serviciosApi.registrar(formulario.value)
    toast.add({
      severity: 'success',
      summary: `Solicitud #${solicitud.id} registrada`,
      life: 4000,
    })
    router.push({ name: 'servicio-detalle', params: { id: solicitud.id } })
  } catch (error) {
    registrar(error)
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Registrar solicitud</h1>
        <p class="subtitulo">Nuevo servicio técnico</p>
      </div>
      <RouterLink :to="{ name: 'servicios' }">
        <Button label="Ver solicitudes" icon="pi pi-list" text />
      </RouterLink>
    </header>

    <Card class="tarjeta">
      <template #content>
        <form class="formulario" @submit.prevent="guardar">
          <div class="fila">
            <div class="campo">
              <label for="cliente">Nombre del cliente</label>
              <InputText
                id="cliente"
                v-model="formulario.clienteNombre"
                :invalid="Boolean(errorDe('cliente_nombre'))"
              />
              <small v-if="errorDe('cliente_nombre')" class="error">
                {{ errorDe('cliente_nombre') }}
              </small>
            </div>
            <div class="campo">
              <label for="telefono">Teléfono</label>
              <InputText
                id="telefono"
                v-model="formulario.clienteTelefono"
                :invalid="Boolean(errorDe('cliente_telefono'))"
              />
              <small v-if="errorDe('cliente_telefono')" class="error">
                {{ errorDe('cliente_telefono') }}
              </small>
            </div>
          </div>

          <div class="campo">
            <label for="tipo">Tipo de servicio</label>
            <Select
              id="tipo"
              v-model="formulario.tipo"
              :options="TIPOS_SERVICIO"
              option-label="label"
              option-value="value"
              placeholder="Seleccione el tipo"
              :invalid="Boolean(errorDe('tipo'))"
            />
            <small v-if="formulario.tipo" class="ayuda">
              {{
                esADomicilio
                  ? 'Se atiende a domicilio: requiere la dirección del cliente.'
                  : 'Se atiende en el taller: no hace falta dirección.'
              }}
            </small>
            <small v-if="errorDe('tipo')" class="error">{{ errorDe('tipo') }}</small>
          </div>

          <!-- RN-SER-04: solo para servicios a domicilio. -->
          <div v-if="esADomicilio" class="campo">
            <label for="direccion">Dirección</label>
            <InputText
              id="direccion"
              v-model="formulario.direccion"
              :invalid="Boolean(errorDe('direccion'))"
            />
            <small v-if="errorDe('direccion')" class="error">
              {{ errorDe('direccion') }}
            </small>
          </div>

          <div class="campo">
            <label for="descripcion">Descripción del problema</label>
            <Textarea
              id="descripcion"
              v-model="formulario.descripcion"
              rows="4"
              :invalid="Boolean(errorDe('descripcion'))"
            />
            <small v-if="errorDe('descripcion')" class="error">
              {{ errorDe('descripcion') }}
            </small>
          </div>

          <Message severity="secondary" :closable="false">
            El monto a cobrar lo fija el administrador después de revisar
            el trabajo.
          </Message>

          <Message v-if="mensajeGeneral" severity="error" :closable="false">
            {{ mensajeGeneral }}
          </Message>

          <div class="pie">
            <Button
              type="submit"
              label="Registrar solicitud"
              icon="pi pi-check"
              :loading="guardando"
              :disabled="!puedeGuardar"
            />
          </div>
        </form>
      </template>
    </Card>
  </section>
</template>

<style scoped>
.encabezado {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
}

.subtitulo {
  margin: 0.25rem 0 0;
  color: var(--p-text-muted-color, #64748b);
}

.tarjeta {
  max-width: 720px;
}

.formulario {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.fila {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 600px) {
  .fila {
    grid-template-columns: 1fr;
  }
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

.ayuda {
  color: var(--p-text-muted-color, #64748b);
}

.pie {
  display: flex;
  justify-content: flex-end;
}
</style>
