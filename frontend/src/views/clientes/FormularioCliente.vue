<script setup>
/* Alta y edición de un cliente (RF-84, RF-85).

   Lo usan la pantalla de clientes y, para registrar uno nuevo sin salir
   de la venta, el registro de venta (RF-79). Las reglas —nombre,
   teléfono y carnet obligatorios, carnet único (v1.5)— las aplica el
   servidor; aquí se avisa antes de enviar y se muestran sus errores
   junto a cada campo (RNF-15). Un carnet repetido
   llega como 409 CARNET_DUPLICADO con el error en el campo carnet. */
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { computed, ref, watch } from 'vue'

import { clientesApi } from '@/api/clientes'
import { useErroresApi } from '@/composables/useErroresApi'
import { MENSAJE_CARNET, carnetValido, soloDigitosDeCarnet } from '@/utils/carnet'
import { MENSAJE_TELEFONO, soloDigitosDeTelefono, telefonoValido } from '@/utils/telefono'

const props = defineProps({
  visible: { type: Boolean, default: false },
  /** El cliente a editar, CON carnet (viene del detalle); null para alta. */
  cliente: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'guardado'])

const toast = useToast()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const VACIO = { nombre: '', telefono: '', direccion: '', carnet: '' }
const formulario = ref({ ...VACIO })
const guardando = ref(false)
const editando = computed(() => Boolean(props.cliente))

watch(
  () => props.visible,
  (abierto) => {
    if (!abierto) return
    limpiar()
    formulario.value = props.cliente
      ? {
          nombre: props.cliente.nombre,
          telefono: props.cliente.telefono,
          direccion: props.cliente.direccion ?? '',
          carnet: props.cliente.carnet ?? '',
        }
      : { ...VACIO }
  },
)

async function guardar() {
  limpiar()
  // RF-100 y RF-101: se avisa antes de enviar, de los dos campos a la
  // vez; el servidor vuelve a comprobarlo.
  const errores = {}
  if (!telefonoValido(formulario.value.telefono)) errores.telefono = [MENSAJE_TELEFONO]
  if (!carnetValido(formulario.value.carnet)) errores.carnet = [MENSAJE_CARNET]
  if (Object.keys(errores).length) {
    registrar({ errores })
    return
  }
  guardando.value = true
  try {
    const guardado = editando.value
      ? await clientesApi.actualizar(props.cliente.id, formulario.value)
      : await clientesApi.crear(formulario.value)
    toast.add({
      severity: 'success',
      summary: editando.value ? 'Cliente actualizado' : 'Cliente registrado',
      life: 3000,
    })
    emit('guardado', guardado)
    emit('update:visible', false)
  } catch (error) {
    registrar(error)
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="editando ? 'Editar cliente' : 'Nuevo cliente'"
    modal
    :style="{ width: '30rem' }"
    @update:visible="emit('update:visible', $event)"
  >
    <form class="formulario" @submit.prevent="guardar">
      <div class="campo">
        <label for="cliente-nombre">Nombre</label>
        <InputText id="cliente-nombre" v-model="formulario.nombre" :invalid="Boolean(errorDe('nombre'))" />
        <small v-if="errorDe('nombre')" class="error">{{ errorDe('nombre') }}</small>
      </div>
      <div class="campo">
        <label for="cliente-telefono">Teléfono</label>
        <!-- Solo dígitos, como máximo 8, al escribir. Un teléfono anterior
             que no cumple se muestra tal cual, para que se corrija. -->
        <InputText
          id="cliente-telefono"
          :model-value="formulario.telefono"
          inputmode="numeric"
          maxlength="8"
          :invalid="Boolean(errorDe('telefono'))"
          @update:model-value="formulario.telefono = soloDigitosDeTelefono($event)"
        />
        <small v-if="errorDe('telefono')" class="error">{{ errorDe('telefono') }}</small>
        <small v-else class="ayuda">8 dígitos.</small>
      </div>
      <div class="campo">
        <label for="cliente-direccion">Dirección <span class="ayuda">(opcional)</span></label>
        <InputText id="cliente-direccion" v-model="formulario.direccion" />
      </div>
      <div class="campo">
        <label for="cliente-carnet">Carnet de identidad</label>
        <!-- RF-101: obligatorio, solo dígitos y como máximo 8 al escribir. -->
        <InputText
          id="cliente-carnet"
          :model-value="formulario.carnet"
          inputmode="numeric"
          maxlength="8"
          :invalid="Boolean(errorDe('carnet'))"
          @update:model-value="formulario.carnet = soloDigitosDeCarnet($event)"
        />
        <small v-if="errorDe('carnet')" class="error">{{ errorDe('carnet') }}</small>
        <small v-else class="ayuda">
          7 u 8 dígitos, sin complemento. Dato personal: solo se verá en el
          detalle del cliente.
        </small>
      </div>

      <Message v-if="mensajeGeneral" severity="error" :closable="false">{{ mensajeGeneral }}</Message>

      <div class="pie">
        <Button label="Cancelar" text @click="emit('update:visible', false)" />
        <Button type="submit" :label="editando ? 'Guardar cambios' : 'Registrar'" :loading="guardando" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
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

.error {
  color: var(--p-red-600, #dc2626);
}

.ayuda {
  color: var(--p-text-muted-color, #71717a);
  font-size: 0.85rem;
}

.pie {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
