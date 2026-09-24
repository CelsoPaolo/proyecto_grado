/**
 * T-1.9 / T-1.14 — Store de sesion.
 *
 * Incluye la regresion del cierre de sesion detectada al verificar el
 * bloque 1 en el navegador: si se limpian los tokens ANTES de llamar
 * al servidor, la llamada va sin autenticar, el refresh nunca llega a
 * la lista negra y RF-04 queda incumplido.
 */

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'

vi.mock('../api/auth', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    yo: vi.fn(),
    cambiarPasswordPropia: vi.fn(),
  },
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  try {
    localStorage.clear()
  } catch {
    /* sin almacenamiento */
  }
})

describe('permisos derivados del rol (spec.md matriz 4.4)', () => {
  it('el Administrador hereda las capacidades de los otros roles', () => {
    const auth = useAuthStore()
    auth.usuario = { id: 1, rol: 'ADMINISTRADOR' }

    expect(auth.esAdministrador).toBe(true)
    expect(auth.puedeVender).toBe(true)
    expect(auth.puedeAtenderServicios).toBe(true)
  })

  it('el Encargado de Ventas solo puede vender', () => {
    const auth = useAuthStore()
    auth.usuario = { id: 2, rol: 'VENTAS' }

    expect(auth.esAdministrador).toBe(false)
    expect(auth.puedeVender).toBe(true)
    expect(auth.puedeAtenderServicios).toBe(false)
  })

  it('el Encargado de Servicios solo atiende servicios', () => {
    const auth = useAuthStore()
    auth.usuario = { id: 3, rol: 'SERVICIOS' }

    expect(auth.esAdministrador).toBe(false)
    expect(auth.puedeVender).toBe(false)
    expect(auth.puedeAtenderServicios).toBe(true)
  })

  it('sin sesion no hay ningun permiso', () => {
    const auth = useAuthStore()

    expect(auth.autenticado).toBe(false)
    expect(auth.rol).toBeNull()
    expect(auth.esAdministrador).toBe(false)
  })
})

describe('cierre de sesion (RF-04)', () => {
  it('llama al servidor ANTES de limpiar, para que el refresh se invalide', async () => {
    /* La regresion concreta: con el orden invertido la peticion sale
       sin token, el servidor responde 401 y el refresh se queda
       vigente en el servidor aunque el navegador lo haya olvidado. */
    const auth = useAuthStore()
    auth.guardarTokens({ access: 'access-1', refresh: 'refresh-1' })
    auth.usuario = { id: 1, rol: 'VENTAS' }

    let habiaTokenAlLlamar = null
    authApi.logout.mockImplementation(async () => {
      habiaTokenAlLlamar = auth.access
    })

    await auth.cerrarSesion()

    expect(authApi.logout).toHaveBeenCalledWith('refresh-1')
    expect(habiaTokenAlLlamar).toBe('access-1')
  })

  it('deja al usuario fuera aunque el servidor falle', async () => {
    const auth = useAuthStore()
    auth.guardarTokens({ access: 'access-1', refresh: 'refresh-1' })
    auth.usuario = { id: 1, rol: 'VENTAS' }
    authApi.logout.mockRejectedValue(new Error('servidor caído'))

    await auth.cerrarSesion()

    expect(auth.autenticado).toBe(false)
    expect(auth.access).toBeNull()
    expect(auth.refresh).toBeNull()
  })

  it('no llama al servidor si no habia sesion que cerrar', async () => {
    const auth = useAuthStore()

    await auth.cerrarSesion()

    expect(authApi.logout).not.toHaveBeenCalled()
  })
})

describe('restauracion de sesion', () => {
  it('sin refresh guardado no consulta al servidor', async () => {
    const auth = useAuthStore()

    const resultado = await auth.restaurarSesion()

    expect(resultado).toBeNull()
    expect(authApi.yo).not.toHaveBeenCalled()
  })

  it('con refresh guardado recupera los datos del usuario', async () => {
    const auth = useAuthStore()
    auth.guardarTokens({ access: null, refresh: 'refresh-1' })
    authApi.yo.mockResolvedValue({ id: 1, rol: 'ADMINISTRADOR' })

    await auth.restaurarSesion()

    expect(auth.autenticado).toBe(true)
    expect(auth.rol).toBe('ADMINISTRADOR')
  })

  it('si la cuenta fue bloqueada mientras tanto, la sesion queda cerrada', async () => {
    /* RN-ACC-05 visto desde el frontend: al abrir la aplicacion, el
       servidor rechaza y no debe quedar rastro de sesion. */
    const auth = useAuthStore()
    auth.guardarTokens({ access: null, refresh: 'refresh-1' })
    authApi.yo.mockRejectedValue({ codigo: 'CUENTA_BLOQUEADA' })

    const resultado = await auth.restaurarSesion()

    expect(resultado).toBeNull()
    expect(auth.autenticado).toBe(false)
    expect(auth.refresh).toBeNull()
  })
})
