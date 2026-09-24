<script setup>
/* CU-USU-05 y acciones de cuenta (RF-39 a RF-47).

   Las reglas RN-USU-02 a RN-USU-04 NO se reimplementan aqui: la
   interfaz desactiva lo que no procede sobre la propia cuenta, pero
   cuando el servidor rechaza una operacion se muestra SU mensaje.
   Reimplementar la regla en el frontend crearia dos fuentes de verdad
   que acabarian divergiendo. */
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'

import { usuariosApi } from '@/api/usuarios'
import { useErroresApi } from '@/composables/useErroresApi'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const toast = useToast()
const confirm = useConfirm()
const { mensajeGeneral, registrar, limpiar, errorDe } = useErroresApi()

const ROLES = [
  { label: 'Administrador', value: 'ADMINISTRADOR' },
  { label: 'Encargado de Ventas', value: 'VENTAS' },
  { label: 'Encargado de Servicios', value: 'SERVICIOS' },
]

const usuarios = ref([])
const total = ref(0)
const cargando = ref(false)
const filtros = ref({ search: '', rol: null, page: 1, page_size: 20 })

const dialogo = ref(false)
const editando = ref(null)
const guardando = ref(false)
const formulario = ref({ username: '', nombre_completo: '', rol: null, password: '' })

const dialogoPassword = ref(false)
const objetivoPassword = ref(null)
const passwordNueva = ref('')

async function cargar() {
  cargando.value = true
  try {
    const params = { page: filtros.value.page, page_size: filtros.value.page_size }
    if (filtros.value.search) params.search = filtros.value.search
    if (filtros.value.rol) params.rol = filtros.value.rol
    const datos = await usuariosApi.listar(params)
    usuarios.value = datos.results
    total.value = datos.count
  } catch (error) {
    toast.add({ severity: 'error', summary: error.detalle, life: 5000 })
  } finally {
    cargando.value = false
  }
}

function alPaginar(evento) {
  filtros.value.page = evento.page + 1
  filtros.value.page_size = evento.rows
  cargar()
}

function buscar() {
  filtros.value.page = 1
  cargar()
}

function abrirNuevo() {
  limpiar()
  editando.value = null
  formulario.value = { username: '', nombre_completo: '', rol: null, password: '' }
  dialogo.value = true
}

function abrirEdicion(usuario) {
  limpiar()
  editando.value = usuario
  formulario.value = {
    username: usuario.username,
    nombre_completo: usuario.nombre_completo,
    rol: usuario.rol,
    password: '',
  }
  dialogo.value = true
}

async function guardar() {
  limpiar()
  guardando.value = true
  try {
    if (editando.value) {
      await usuariosApi.actualizar(editando.value.id, {
        nombre_completo: formulario.value.nombre_completo,
        rol: formulario.value.rol,
      })
      toast.add({ severity: 'success', summary: 'Cuenta actualizada', life: 3000 })
    } else {
      await usuariosApi.crear(formulario.value)
      toast.add({ severity: 'success', summary: 'Cuenta creada', life: 3000 })
    }
    dialogo.value = false
    cargar()
  } catch (error) {
    registrar(error)
  } finally {
    guardando.value = false
  }
}

function confirmarBloqueo(usuario) {
  confirm.require({
    header: usuario.bloqueado ? 'Desbloquear cuenta' : 'Bloquear cuenta',
    message: usuario.bloqueado
      ? `¿Restituir el acceso de ${usuario.nombre_completo}? Deberá iniciar sesión nuevamente.`
      : `¿Bloquear a ${usuario.nombre_completo}? Perderá el acceso de inmediato, incluso si tiene la sesión abierta.`,
    acceptLabel: usuario.bloqueado ? 'Desbloquear' : 'Bloquear',
    rejectLabel: 'Cancelar',
    accept: () => alternarBloqueo(usuario),
  })
}

async function alternarBloqueo(usuario) {
  try {
    if (usuario.bloqueado) await usuariosApi.desbloquear(usuario.id)
    else await usuariosApi.bloquear(usuario.id)
    toast.add({
      severity: 'success',
      summary: usuario.bloqueado ? 'Cuenta desbloqueada' : 'Cuenta bloqueada',
      life: 3000,
    })
    cargar()
  } catch (error) {
    // Mensaje del servidor: la regla vive alli (RN-USU-03, RN-USU-04).
    toast.add({ severity: 'warn', summary: error.detalle, life: 6000 })
  }
}

function abrirPassword(usuario) {
  objetivoPassword.value = usuario
  passwordNueva.value = ''
  limpiar()
  dialogoPassword.value = true
}

async function restablecer() {
  limpiar()
  guardando.value = true
  try {
    await usuariosApi.restablecerPassword(objetivoPassword.value.id, passwordNueva.value)
    toast.add({
      severity: 'success',
      summary: 'Contraseña restablecida',
      detail: 'Las sesiones abiertas de esa cuenta quedaron cerradas.',
      life: 5000,
    })
    dialogoPassword.value = false
  } catch (error) {
    registrar(error)
  } finally {
    guardando.value = false
  }
}

const esUnoMismo = (usuario) => usuario.id === auth.usuario?.id

onMounted(cargar)
</script>

<template>
  <section>
    <header class="encabezado">
      <div>
        <h1>Usuarios</h1>
        <p class="subtitulo">Cuentas del personal de PC-Solution</p>
      </div>
      <Button label="Nueva cuenta" icon="pi pi-plus" @click="abrirNuevo" />
    </header>

    <div class="filtros">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filtros.search"
          placeholder="Buscar por nombre o usuario"
          @keyup.enter="buscar"
        />
      </IconField>
      <Select
        v-model="filtros.rol"
        :options="ROLES"
        option-label="label"
        option-value="value"
        placeholder="Todos los roles"
        show-clear
        @change="buscar"
      />
    </div>

    <DataTable
      :value="usuarios"
      :loading="cargando"
      lazy
      paginator
      :rows="filtros.page_size"
      :total-records="total"
      :rows-per-page-options="[20, 50, 100]"
      data-key="id"
      @page="alPaginar"
    >
      <Column field="nombre_completo" header="Nombre" />
      <Column field="username" header="Usuario" />
      <Column header="Rol">
        <template #body="{ data }">
          <Tag :value="data.rol_display" severity="secondary" />
        </template>
      </Column>
      <Column header="Estado">
        <template #body="{ data }">
          <Tag
            :value="data.bloqueado ? 'Bloqueada' : 'Activa'"
            :severity="data.bloqueado ? 'danger' : 'success'"
          />
        </template>
      </Column>
      <Column header="Acciones" style="width: 12rem">
        <template #body="{ data }">
          <div class="acciones">
            <Button
              icon="pi pi-pencil"
              text
              rounded
              aria-label="Editar"
              @click="abrirEdicion(data)"
            />
            <Button
              icon="pi pi-key"
              text
              rounded
              aria-label="Restablecer contraseña"
              @click="abrirPassword(data)"
            />
            <!-- RN-USU-03: nadie se bloquea a si mismo. Se desactiva
                 para no ofrecer una accion que el servidor rechazara. -->
            <Button
              :icon="data.bloqueado ? 'pi pi-lock-open' : 'pi pi-lock'"
              text
              rounded
              :severity="data.bloqueado ? 'success' : 'danger'"
              :disabled="esUnoMismo(data)"
              :aria-label="data.bloqueado ? 'Desbloquear' : 'Bloquear'"
              @click="confirmarBloqueo(data)"
            />
          </div>
        </template>
      </Column>
      <template #empty>Sin cuentas que coincidan con la búsqueda.</template>
    </DataTable>

    <Dialog
      v-model:visible="dialogo"
      :header="editando ? 'Editar cuenta' : 'Nueva cuenta'"
      modal
      :style="{ width: '32rem' }"
    >
      <form class="formulario" @submit.prevent="guardar">
        <div class="campo">
          <label for="nombre">Nombre completo</label>
          <InputText
            id="nombre"
            v-model="formulario.nombre_completo"
            :invalid="Boolean(errorDe('nombre_completo'))"
          />
          <small v-if="errorDe('nombre_completo')" class="error">
            {{ errorDe('nombre_completo') }}
          </small>
        </div>

        <div class="campo">
          <label for="usuario">Identificador de acceso</label>
          <InputText
            id="usuario"
            v-model="formulario.username"
            :disabled="Boolean(editando)"
            :invalid="Boolean(errorDe('username'))"
          />
          <small v-if="errorDe('username')" class="error">
            {{ errorDe('username') }}
          </small>
        </div>

        <div class="campo">
          <label for="rol">Rol</label>
          <Select
            id="rol"
            v-model="formulario.rol"
            :options="ROLES"
            option-label="label"
            option-value="value"
            placeholder="Seleccione un rol"
            :disabled="Boolean(editando) && esUnoMismo(editando)"
            :invalid="Boolean(errorDe('rol'))"
          />
          <!-- RN-USU-02: nadie cambia su propio rol. -->
          <small v-if="editando && esUnoMismo(editando)" class="ayuda">
            No puede cambiar su propio rol.
          </small>
          <small v-if="errorDe('rol')" class="error">{{ errorDe('rol') }}</small>
        </div>

        <div v-if="!editando" class="campo">
          <label for="clave">Contraseña inicial</label>
          <Password
            input-id="clave"
            v-model="formulario.password"
            toggle-mask
            fluid
            :invalid="Boolean(errorDe('password'))"
          />
          <small v-if="errorDe('password')" class="error">
            {{ errorDe('password') }}
          </small>
        </div>

        <Message v-if="mensajeGeneral" severity="error" :closable="false">
          {{ mensajeGeneral }}
        </Message>

        <div class="pie">
          <Button label="Cancelar" text @click="dialogo = false" />
          <Button type="submit" label="Guardar" icon="pi pi-check" :loading="guardando" />
        </div>
      </form>
    </Dialog>

    <Dialog
      v-model:visible="dialogoPassword"
      header="Restablecer contraseña"
      modal
      :style="{ width: '28rem' }"
    >
      <form class="formulario" @submit.prevent="restablecer">
        <p class="subtitulo">
          Se asignará una contraseña nueva a
          <strong>{{ objetivoPassword?.nombre_completo }}</strong>. Sus sesiones
          abiertas se cerrarán.
        </p>
        <div class="campo">
          <label for="nuevaclave">Contraseña nueva</label>
          <Password
            input-id="nuevaclave"
            v-model="passwordNueva"
            toggle-mask
            fluid
            :invalid="Boolean(errorDe('password_nueva'))"
          />
          <small v-if="errorDe('password_nueva')" class="error">
            {{ errorDe('password_nueva') }}
          </small>
        </div>
        <Message v-if="mensajeGeneral" severity="error" :closable="false">
          {{ mensajeGeneral }}
        </Message>
        <div class="pie">
          <Button label="Cancelar" text @click="dialogoPassword = false" />
          <Button
            type="submit"
            label="Restablecer"
            icon="pi pi-key"
            :loading="guardando"
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
  color: var(--p-text-muted-color, #64748b);
}

.filtros {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.acciones {
  display: flex;
  gap: 0.15rem;
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
  color: var(--p-text-muted-color, #64748b);
}

.pie {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
