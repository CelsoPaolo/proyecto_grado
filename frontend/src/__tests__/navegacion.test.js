/**
 * T-14.1 — Espacio de trabajo por rol, sin pantalla de Inicio
 * (spec.md v1.4.1, CU-AUT-01; plan.md 7.12).
 *
 * Se usa el router REAL con su guard: lo que se prueba es adonde
 * termina cada navegacion, no una funcion suelta. Es navegacion, no
 * seguridad (RN-ACC-04): el servidor sigue respondiendo 403.
 */

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { destinoTrasLogin, espacioDeTrabajo, menuPara, router, rutas } from '../router'
import { useAuthStore } from '../stores/auth'

vi.mock('../api/auth', () => ({
  authApi: { yo: vi.fn(), iniciarSesion: vi.fn(), cerrarSesion: vi.fn(), refrescar: vi.fn() },
}))

const ESPACIOS = {
  ADMINISTRADOR: 'panel',
  VENTAS: 'venta-nueva',
  SERVICIOS: 'servicios',
}

let auth

beforeEach(async () => {
  setActivePinia(createPinia())
  auth = useAuthStore()
  auth.usuario = null
  auth.refresh = null
  // Punto de partida neutro para cada prueba.
  await router.push('/login')
})

async function ir(destino) {
  await router.push(destino)
  await router.isReady()
  return router.currentRoute.value.name
}

describe('el Inicio ya no existe', () => {
  it('no hay ruta ni entrada de menú «inicio» para ningún rol', () => {
    expect(rutas.some((r) => r.name === 'inicio' || r.path === '/inicio')).toBe(false)
    for (const rol of Object.keys(ESPACIOS)) {
      expect(menuPara(rol).map((o) => o.name)).not.toContain('inicio')
    }
  })

  it('«/inicio» ya no lleva a ninguna pantalla', () => {
    expect(router.resolve('/inicio').matched).toEqual([])
  })
})

describe.each(Object.entries(ESPACIOS))('%s', (rol, espacio) => {
  beforeEach(() => {
    auth.usuario = { id: 1, rol }
  })

  it(`su espacio de trabajo es «${espacio}» y puede entrar en él`, async () => {
    expect(espacioDeTrabajo(rol)).toEqual({ name: espacio })
    expect(await ir({ name: espacio })).toBe(espacio)
  })

  it('al abrir «/» va a su espacio de trabajo', async () => {
    expect(await ir('/')).toBe(espacio)
  })

  it('si ya tiene sesión y vuelve al login, va a su espacio de trabajo', async () => {
    await ir({ name: espacio })
    expect(await ir('/login')).toBe(espacio)
  })

  it('tras iniciar sesión, sin destino pedido, va a su espacio de trabajo', () => {
    expect(destinoTrasLogin(undefined, rol)).toEqual({ name: espacio })
  })
})

describe('el destino pedido antes de iniciar sesión (?redirigir=)', () => {
  it('se respeta si el rol puede abrirlo', () => {
    expect(destinoTrasLogin('/ventas', 'VENTAS')).toBe('/ventas')
  })

  it('se ignora si el rol no puede abrirlo: va a su espacio, no a «Sin permiso»', () => {
    expect(destinoTrasLogin('/usuarios', 'VENTAS')).toEqual({ name: 'venta-nueva' })
    expect(destinoTrasLogin('/panel', 'SERVICIOS')).toEqual({ name: 'servicios' })
  })

  it.each([
    ['https://otro-sitio.com', 'externa'],
    ['//otro-sitio.com/x', 'externa sin esquema'],
    ['/no-existe', 'inexistente'],
    ['/login', 'el propio login'],
    ['/inicio', 'la pantalla retirada'],
  ])('se ignora una ruta %s (%s)', (redirigir) => {
    expect(destinoTrasLogin(redirigir, 'ADMINISTRADOR')).toEqual({ name: 'panel' })
  })
})

describe('sin bucles ni pantalla en blanco', () => {
  it('sin sesión, «/» lleva al login', async () => {
    expect(await ir('/')).toBe('login')
  })

  it('con la sesión por restaurar, «/» termina en el espacio de trabajo', async () => {
    const { authApi } = await import('../api/auth')
    authApi.yo.mockResolvedValue({ id: 3, rol: 'SERVICIOS' })
    auth.refresh = 'refresh-guardado'

    expect(await ir('/')).toBe('servicios')
  })

  it('un rol desconocido termina en «Sin permiso» sin rebotar', async () => {
    auth.usuario = { id: 9, rol: 'DESCONOCIDO' }

    expect(espacioDeTrabajo('DESCONOCIDO')).toEqual({ name: 'sin-permiso' })
    expect(await ir('/')).toBe('sin-permiso')
    expect(await ir('/login')).toBe('sin-permiso')
  })

  it('una ruta ajena lleva a «Sin permiso», como antes', async () => {
    auth.usuario = { id: 2, rol: 'VENTAS' }

    expect(await ir('/usuarios')).toBe('sin-permiso')
  })
})
