<script setup>
/* Detalle de un cliente (RF-85, RF-87, RF-89).

   Es la ÚNICA pantalla que muestra el carnet (RN-CLI-06). Desactivar y
   reactivar son solo del Administrador (RN-CLI-07) y piden confirmación
   (RNF-14). No hay «eliminar»: los clientes no se borran (RN-CLI-03). */
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { clientesApi } from '@/api/clientes'
import { usePermisos } from '@/composables/usePermisos'
import { comoFechaHora } from '@/utils/fechas'
import FormularioCliente from './FormularioCliente.vue'

const route = useRoute()
const toast = useToast()
const confirm = useConfirm()
const { puedeCambiarEstadoCliente } = usePermisos()

const cliente = ref(null)
const error = ref(null)
const dialogo = ref(false)

async function cargar() {
  try {
    cliente.value = await clientesApi.obtener(route.params.id)
  } catch (e) {
    error.value = e.detalle ?? 'No se pudo cargar el cliente.'
  }
}

function confirmarCambioDeEstado() {
  const desactivar = cliente.value.activo
  confirm.require({
    header: desactivar ? 'Desactivar cliente' : 'Reactivar cliente',
    message: desactivar
      ? `¿Desactivar a «${cliente.value.nombre}»? No podrá elegirse en ventas nuevas. ` +
        'Sus datos y sus ventas anteriores se conservan, y puede reactivarse.'
      : `¿Reactivar a «${cliente.value.nombre}»? Volverá a poder elegirse en las ventas.`,
    acceptLabel: desactivar ? 'Desactivar' : 'Reactivar',
    rejectLabel: 'Cancelar',
    acceptProps: { severity: desactivar ? 'danger' : 'success' },
    accept: () => cambiarEstado(desactivar),
  })
}

async function cambiarEstado(desactivar) {
  try {
    cliente.value = desactivar
      ? await clientesApi.desactivar(cliente.value.id)
      : await clientesApi.reactivar(cliente.value.id)
    toast.add({
      severity: 'success',
      summary: desactivar ? 'Cliente desactivado' : 'Cliente reactivado',
      life: 3000,
    })
  } catch (e) {
    toast.add({ severity: 'error', summary: e.detalle, life: 5000 })
  }
}

onMounted(cargar)
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'clientes' }" class="volver">
      <i class="pi pi-arrow-left" aria-hidden="true" /> Clientes
    </RouterLink>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <template v-if="cliente">
      <header class="encabezado">
        <div>
          <h1>{{ cliente.nombre }}</h1>
          <Tag
            :value="cliente.activo ? 'Activo' : 'Inactivo'"
            :severity="cliente.activo ? 'success' : 'secondary'"
            data-prueba="estado"
          />
        </div>
        <div class="acciones">
          <Button label="Editar" icon="pi pi-pencil" outlined data-prueba="editar" @click="dialogo = true" />
          <Button
            v-if="puedeCambiarEstadoCliente"
            :label="cliente.activo ? 'Desactivar' : 'Reactivar'"
            :icon="cliente.activo ? 'pi pi-ban' : 'pi pi-replay'"
            :severity="cliente.activo ? 'danger' : 'success'"
            outlined
            data-prueba="cambiar-estado"
            @click="confirmarCambioDeEstado"
          />
        </div>
      </header>

      <dl class="datos">
        <div>
          <dt>Teléfono</dt>
          <dd>{{ cliente.telefono }}</dd>
        </div>
        <div>
          <dt>Dirección</dt>
          <dd>{{ cliente.direccion || '—' }}</dd>
        </div>
        <div>
          <dt>Carnet de identidad</dt>
          <dd data-prueba="carnet">{{ cliente.carnet || 'No registrado' }}</dd>
        </div>
        <div>
          <dt>Registrado</dt>
          <dd>{{ comoFechaHora(cliente.creado_en) }} por {{ cliente.creado_por }}</dd>
        </div>
        <div>
          <dt>Última modificación</dt>
          <dd>{{ comoFechaHora(cliente.actualizado_en) }} por {{ cliente.actualizado_por }}</dd>
        </div>
      </dl>

      <FormularioCliente v-model:visible="dialogo" :cliente="cliente" @guardado="cliente = $event" />
    </template>
  </section>
</template>

<style scoped>
.volver {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
  margin-bottom: 1rem;
  color: var(--p-primary-color, #7c3aed);
  text-decoration: none;
}

.encabezado {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.encabezado > div:first-child {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

h1 {
  margin: 0;
  font-size: 1.4rem;
}

.acciones {
  display: flex;
  gap: 0.5rem;
}

.datos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 1rem;
  margin: 0;
}

dt {
  color: var(--p-text-muted-color, #71717a);
  font-size: 0.85rem;
}

dd {
  margin: 0.25rem 0 0;
}
</style>
