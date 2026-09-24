/**
 * Estado de sesion: usuario, rol y permisos derivados.
 *
 * Es uno de los tres estados verdaderamente globales del sistema
 * (plan.md seccion 1.2); el resto vive en cada componente.
 *
 * Los permisos que se derivan aqui son para la INTERFAZ: deciden que
 * mostrar y que rutas ofrecer. La autorizacion real vive en el
 * servidor (RNF-02, RN-ACC-04): un usuario que escriba la URL a mano
 * igual recibira 403.
 */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { authApi } from '@/api/auth'
import { conectarSesion } from '@/api/http'

const CLAVE_REFRESH = 'pcs_refresh'

/**
 * El access token vive solo en memoria y el refresh en localStorage,
 * para que la sesion sobreviva a un refresco de pagina (plan.md 1.3).
 * Se protege con try/catch porque en ventana privada o con el
 * almacenamiento bloqueado, leer o escribir puede lanzar.
 */
function leerRefreshGuardado() {
  try {
    return localStorage.getItem(CLAVE_REFRESH)
  } catch {
    return null
  }
}

function guardarRefresh(valor) {
  try {
    if (valor) localStorage.setItem(CLAVE_REFRESH, valor)
    else localStorage.removeItem(CLAVE_REFRESH)
  } catch {
    /* sin persistencia: la sesion durara lo que dure la pestaña */
  }
}

export const useAuthStore = defineStore('auth', () => {
  const access = ref(null)
  const refresh = ref(leerRefreshGuardado())
  const usuario = ref(null)
  const cargando = ref(false)

  const autenticado = computed(() => Boolean(usuario.value))
  const rol = computed(() => usuario.value?.rol ?? null)

  // ── Permisos derivados del rol (spec.md matriz 4.4) ────────────────
  // El Administrador aparece en todos por RN-ACC-03.
  const esAdministrador = computed(() => rol.value === 'ADMINISTRADOR')
  const puedeVender = computed(() =>
    ['ADMINISTRADOR', 'VENTAS'].includes(rol.value),
  )
  const puedeAtenderServicios = computed(() =>
    ['ADMINISTRADOR', 'SERVICIOS'].includes(rol.value),
  )

  function guardarTokens({ access: nuevoAccess, refresh: nuevoRefresh }) {
    access.value = nuevoAccess
    if (nuevoRefresh) {
      refresh.value = nuevoRefresh
      guardarRefresh(nuevoRefresh)
    }
  }

  function limpiar() {
    access.value = null
    refresh.value = null
    usuario.value = null
    guardarRefresh(null)
  }

  async function iniciarSesion(username, password) {
    cargando.value = true
    try {
      const datos = await authApi.login(username, password)
      guardarTokens({ access: datos.access, refresh: datos.refresh })
      usuario.value = datos.usuario
      return datos.usuario
    } finally {
      cargando.value = false
    }
  }

  async function cerrarSesion() {
    const refreshActual = refresh.value
    try {
      // La llamada va ANTES de limpiar, porque necesita el access
      // token para autenticarse. Si se limpiara primero, el servidor
      // respondería 401, el refresh nunca llegaría a la lista negra y
      // RF-04 quedaría incumplido: cerrar sesión solo borraría el
      // token del navegador.
      if (refreshActual) await authApi.logout(refreshActual)
    } catch {
      /* el token ya no servía; no hay nada que reparar */
    } finally {
      // Pase lo que pase con el servidor, el usuario queda fuera.
      limpiar()
    }
  }

  /**
   * Restablece la sesion al abrir la aplicacion.
   *
   * Con solo el refresh guardado, pide un access nuevo y recupera los
   * datos del usuario. Si la cuenta fue bloqueada mientras tanto, el
   * servidor rechaza el refresco (via 2 de plan.md 1.3) y la sesion
   * queda cerrada, que es justamente lo que RN-ACC-05 exige.
   */
  async function restaurarSesion() {
    if (!refresh.value) return null
    cargando.value = true
    try {
      usuario.value = await authApi.yo()
      return usuario.value
    } catch {
      limpiar()
      return null
    } finally {
      cargando.value = false
    }
  }

  // El cliente HTTP no importa este store para no crear una
  // dependencia circular: se le inyectan los accesos que necesita.
  conectarSesion({
    obtenerAccess: () => access.value,
    obtenerRefresh: () => refresh.value,
    guardarTokens,
    cerrarSesion: limpiar,
  })

  return {
    access,
    refresh,
    usuario,
    cargando,
    autenticado,
    rol,
    esAdministrador,
    puedeVender,
    puedeAtenderServicios,
    iniciarSesion,
    cerrarSesion,
    restaurarSesion,
    guardarTokens,
    limpiar,
  }
})
