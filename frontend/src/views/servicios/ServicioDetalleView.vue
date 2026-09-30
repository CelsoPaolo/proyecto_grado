<script setup>
/* CU-SER-02 a CU-SER-06 — Detalle, seguimiento y cotización.

   Las acciones se ofrecen según el estado Y el rol:
   - cotizar solo al Administrador (RF-56, RF-57);
   - finalizar solo si ya hay monto, y si no lo hay se explica que el
     administrador debe cotizar primero (RF-61).

   La interfaz no reimplementa las reglas: se adelanta a ellas para no
   ofrecer lo que el servidor rechazaría, pero cuando el servidor
   rechaza muestra SU mensaje. */
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import Timeline from 'primevue/timeline'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { serviciosApi } from '@/api/servicios'
import { useErroresApi } from '@/composables/useErroresApi'
import { usePermisos } from '@/composables/usePermisos'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { esAdministrador } = usePermisos()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const solicitud = ref(null)
const trabajando = ref(false)

const dialogo = ref(null) // 'cotizar' | 'finalizar' | 'cancelar'
const monto = ref(null)
const tecnico = ref('')
const observaciones = ref('')
const motivo = ref('')

const bolivianos = new Intl.NumberFormat('es-BO', {
  style: 'currency',
  currency: 'BOB',
  minimumFractionDigits: 2,
})

const fechaHora = new Intl.DateTimeFormat('es-BO', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function comoFecha(valor) {
  return valor ? fechaHora.format(new Date(valor)) : null
}

const abierta = computed(
  () => solicitud.value && !['FINALIZADA', 'CANCELADA'].includes(solicitud.value.estado),
)
const puedeIniciar = computed(() => solicitud.value?.estado === 'REGISTRADA')
const puedeFinalizar = computed(() => solicitud.value?.estado === 'EN_ATENCION')

function severidadEstado(estado) {
  return (
    {
      REGISTRADA: 'info',
      EN_ATENCION: 'warn',
      FINALIZADA: 'success',
      CANCELADA: 'danger',
    }[estado] ?? 'secondary'
  )
}

async function cargar() {
  try {
    solicitud.value = await serviciosApi.obtener(route.params.id)
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
    router.push({ name: 'servicios' })
  }
}

function abrir(cual) {
  limpiar()
  dialogo.value = cual
  if (cual === 'cotizar') {
    monto.value = solicitud.value.monto_cobrado
      ? Number(solicitud.value.monto_cobrado)
      : null
    tecnico.value = solicitud.value.tecnico ?? ''
  }
  if (cual === 'finalizar') observaciones.value = ''
  if (cual === 'cancelar') motivo.value = ''
}

async function ejecutar(accion, mensajeExito) {
  limpiar()
  trabajando.value = true
  try {
    solicitud.value = await accion()
    dialogo.value = null
    toast.add({ severity: 'success', summary: mensajeExito, life: 4000 })
  } catch (error) {
    registrar(error)
    // Los errores de proceso (falta cotizar, transición inválida) no
    // son de un campo: se muestran como aviso y el diálogo se cierra
    // para que el mensaje quede a la vista.
    if (['MONTO_REQUERIDO', 'TRANSICION_INVALIDA', 'SOLICITUD_CERRADA'].includes(
        error.codigo)) {
      dialogo.value = null
      toast.add({ severity: 'warn', summary: error.detalle, life: 8000 })
      cargar()
    }
  } finally {
    trabajando.value = false
  }
}

const iniciar = () =>
  ejecutar(() => serviciosApi.iniciar(solicitud.value.id), 'Atención iniciada')

const cotizar = () =>
  ejecutar(
    () =>
      serviciosApi.cotizar(solicitud.value.id, {
        monto: monto.value,
        tecnico: tecnico.value,
      }),
    'Solicitud cotizada',
  )

const finalizar = () =>
  ejecutar(
    () => serviciosApi.finalizar(solicitud.value.id, observaciones.value),
    'Servicio finalizado',
  )

const cancelar = () =>
  ejecutar(
    () => serviciosApi.cancelar(solicitud.value.id, motivo.value),
    'Solicitud cancelada',
  )

onMounted(cargar)
</script>

<template>
  <section v-if="solicitud">
    <header class="encabezado">
      <div>
        <h1>Solicitud #{{ solicitud.id }}</h1>
        <p class="subtitulo">
          {{ solicitud.tipo_display }} · {{ solicitud.modalidad_display }}
        </p>
      </div>
      <div class="acciones">
        <Tag
          :value="solicitud.estado_display"
          :severity="severidadEstado(solicitud.estado)"
        />
        <RouterLink :to="{ name: 'servicios' }">
          <Button label="Volver" icon="pi pi-arrow-left" text />
        </RouterLink>
      </div>
    </header>

    <!-- RF-61: se avisa antes de intentar cerrar, no después. -->
    <Message
      v-if="abierta && !solicitud.esta_cotizada"
      :severity="esAdministrador ? 'warn' : 'info'"
      :closable="false"
      class="aviso"
    >
      <span v-if="esAdministrador">
        Esta solicitud aún no está cotizada. No podrá finalizarse hasta que
        registre el monto a cobrar.
      </span>
      <span v-else>
        Esta solicitud aún no está cotizada. El administrador debe registrar
        el monto antes de que pueda finalizarse.
      </span>
    </Message>

    <div class="barra" v-if="abierta">
      <Button
        v-if="puedeIniciar"
        label="Iniciar atención"
        icon="pi pi-play"
        :loading="trabajando"
        @click="iniciar"
      />
      <!-- RF-57: al Encargado de Servicios no se le ofrece cotizar. -->
      <Button
        v-if="esAdministrador"
        :label="solicitud.esta_cotizada ? 'Ajustar cotización' : 'Cotizar'"
        icon="pi pi-dollar"
        severity="secondary"
        @click="abrir('cotizar')"
      />
      <Button
        v-if="puedeFinalizar"
        label="Finalizar"
        icon="pi pi-check"
        severity="success"
        :disabled="!solicitud.esta_cotizada"
        @click="abrir('finalizar')"
      />
      <Button
        label="Cancelar solicitud"
        icon="pi pi-times"
        severity="danger"
        outlined
        @click="abrir('cancelar')"
      />
    </div>

    <div class="columnas">
      <div class="izquierda">
        <Card>
          <template #title>Cliente</template>
          <template #content>
            <dl>
              <dt>Nombre</dt>
              <dd>{{ solicitud.cliente_nombre }}</dd>
              <dt>Teléfono</dt>
              <dd>{{ solicitud.cliente_telefono }}</dd>
              <template v-if="solicitud.direccion">
                <dt>Dirección</dt>
                <dd>{{ solicitud.direccion }}</dd>
              </template>
            </dl>
          </template>
        </Card>

        <Card>
          <template #title>Seguimiento</template>
          <template #content>
            <dl>
              <dt>Registrada por</dt>
              <dd>{{ solicitud.registrada_por.nombre_completo }}</dd>
              <dt>Técnico</dt>
              <dd>{{ solicitud.tecnico || 'Sin anotar' }}</dd>
              <dt>Monto</dt>
              <dd>
                <span v-if="solicitud.esta_cotizada">
                  {{ bolivianos.format(solicitud.monto_cobrado) }}
                </span>
                <Tag v-else value="Sin cotizar" severity="secondary" />
              </dd>
              <template v-if="solicitud.cotizada_por">
                <dt>Cotizada por</dt>
                <dd>{{ solicitud.cotizada_por.nombre_completo }}</dd>
              </template>
              <template v-if="solicitud.cerrada_por">
                <dt>Cerrada por</dt>
                <dd>{{ solicitud.cerrada_por.nombre_completo }}</dd>
              </template>
            </dl>
          </template>
        </Card>
      </div>

      <div class="derecha">
        <Card>
          <template #title>Problema reportado</template>
          <template #content>
            <p class="texto">{{ solicitud.descripcion }}</p>
          </template>
        </Card>

        <Card v-if="solicitud.observaciones">
          <template #title>Trabajo realizado</template>
          <template #content>
            <p class="texto">{{ solicitud.observaciones }}</p>
          </template>
        </Card>

        <Card v-if="solicitud.motivo_cancelacion">
          <template #title>Motivo de la cancelación</template>
          <template #content>
            <p class="texto">{{ solicitud.motivo_cancelacion }}</p>
          </template>
        </Card>

        <Card>
          <template #title>Historial</template>
          <template #content>
            <Timeline :value="solicitud.eventos">
              <template #content="{ item }">
                <p class="evento-nota">{{ item.nota }}</p>
                <small class="evento-meta">
                  {{ item.usuario.nombre_completo }} ·
                  {{ comoFecha(item.fecha_hora) }}
                </small>
              </template>
            </Timeline>
          </template>
        </Card>
      </div>
    </div>

    <!-- Cotizar (solo Administrador) -->
    <Dialog
      :visible="dialogo === 'cotizar'"
      header="Cotizar solicitud"
      modal
      :style="{ width: '30rem' }"
      @update:visible="dialogo = null"
    >
      <form class="formulario" @submit.prevent="cotizar">
        <div class="campo">
          <label for="monto">Monto a cobrar (Bs)</label>
          <InputNumber
            input-id="monto"
            v-model="monto"
            :min="0"
            mode="decimal"
            :min-fraction-digits="2"
            :max-fraction-digits="2"
            :invalid="Boolean(errorDe('monto_cobrado'))"
          />
          <small v-if="errorDe('monto_cobrado')" class="error">
            {{ errorDe('monto_cobrado') }}
          </small>
          <small v-else class="ayuda">
            Si el servicio no tiene costo, registre 0.
          </small>
        </div>

        <div class="campo">
          <label for="tecnico">Técnico que atiende</label>
          <InputText id="tecnico" v-model="tecnico" placeholder="Opcional" />
          <small class="ayuda">
            Solo una anotación de seguimiento; no da acceso al sistema.
          </small>
        </div>

        <Message v-if="mensajeGeneral" severity="error" :closable="false">
          {{ mensajeGeneral }}
        </Message>

        <div class="pie">
          <Button label="Cancelar" text @click="dialogo = null" />
          <Button type="submit" label="Guardar" icon="pi pi-check" :loading="trabajando" />
        </div>
      </form>
    </Dialog>

    <!-- Finalizar -->
    <Dialog
      :visible="dialogo === 'finalizar'"
      header="Finalizar servicio"
      modal
      :style="{ width: '32rem' }"
      @update:visible="dialogo = null"
    >
      <form class="formulario" @submit.prevent="finalizar">
        <Message severity="secondary" :closable="false">
          Se cerrará con un monto de
          <strong>{{ bolivianos.format(solicitud.monto_cobrado ?? 0) }}</strong>.
          Una vez finalizada no podrá modificarse.
        </Message>

        <div class="campo">
          <label for="observaciones">Trabajo realizado</label>
          <Textarea
            id="observaciones"
            v-model="observaciones"
            rows="4"
            :invalid="Boolean(errorDe('observaciones'))"
          />
          <small v-if="errorDe('observaciones')" class="error">
            {{ errorDe('observaciones') }}
          </small>
        </div>

        <Message v-if="mensajeGeneral" severity="error" :closable="false">
          {{ mensajeGeneral }}
        </Message>

        <div class="pie">
          <Button label="Cancelar" text @click="dialogo = null" />
          <Button
            type="submit"
            label="Finalizar"
            icon="pi pi-check"
            severity="success"
            :loading="trabajando"
            :disabled="!observaciones.trim()"
          />
        </div>
      </form>
    </Dialog>

    <!-- Cancelar -->
    <Dialog
      :visible="dialogo === 'cancelar'"
      header="Cancelar solicitud"
      modal
      :style="{ width: '30rem' }"
      @update:visible="dialogo = null"
    >
      <form class="formulario" @submit.prevent="cancelar">
        <Message severity="warn" :closable="false">
          La solicitud quedará cerrada sin atención. No se elimina.
        </Message>

        <div class="campo">
          <label for="motivo">Motivo</label>
          <Textarea
            id="motivo"
            v-model="motivo"
            rows="3"
            :invalid="Boolean(errorDe('motivo'))"
          />
          <small v-if="errorDe('motivo')" class="error">{{ errorDe('motivo') }}</small>
        </div>

        <Message v-if="mensajeGeneral" severity="error" :closable="false">
          {{ mensajeGeneral }}
        </Message>

        <div class="pie">
          <Button label="Volver" text @click="dialogo = null" />
          <Button
            type="submit"
            label="Cancelar solicitud"
            icon="pi pi-times"
            severity="danger"
            :loading="trabajando"
            :disabled="!motivo.trim()"
          />
        </div>
      </form>
    </Dialog>
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
  color: var(--p-text-muted-color, #71717a);
}

.acciones {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.aviso {
  margin-bottom: 1rem;
}

.barra {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.columnas {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 2fr;
  gap: 1rem;
  align-items: start;
}

@media (max-width: 900px) {
  .columnas {
    grid-template-columns: 1fr;
  }
}

.izquierda,
.derecha {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

dl {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.4rem 1rem;
  align-items: baseline;
}

dt {
  font-weight: 600;
  color: var(--p-text-muted-color, #71717a);
}

dd {
  margin: 0;
}

.texto {
  margin: 0;
  white-space: pre-wrap;
}

.evento-nota {
  margin: 0;
}

.evento-meta {
  color: var(--p-text-muted-color, #71717a);
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

.ayuda {
  color: var(--p-text-muted-color, #71717a);
}

.pie {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
