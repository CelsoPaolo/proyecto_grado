/**
 * T-1.9 — Cliente HTTP: interceptores y refresco de token.
 *
 * El criterio central: un 401 debe disparar UN SOLO refresco aunque
 * haya varias peticiones en vuelo. Con rotacion de tokens activada en
 * el backend, varios refrescos simultaneos harian que todos menos el
 * primero usaran un refresh ya invalidado, y el usuario perderia la
 * sesion sin motivo.
 */

import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { conectarSesion, http, normalizarError } from '../api/http'

vi.mock('axios', async () => {
  const real = await vi.importActual('axios')
  return { ...real, default: { ...real.default, post: vi.fn() } }
})

function estadoDeSesion(accessInicial = 'access-viejo') {
  const estado = {
    access: accessInicial,
    refresh: 'refresh-valido',
    cerrada: false,
  }
  conectarSesion({
    obtenerAccess: () => estado.access,
    obtenerRefresh: () => estado.refresh,
    guardarTokens: ({ access, refresh }) => {
      estado.access = access
      if (refresh) estado.refresh = refresh
    },
    cerrarSesion: () => {
      estado.cerrada = true
      estado.access = null
      estado.refresh = null
    },
  })
  return estado
}

/** Sustituye el adaptador de axios para simular respuestas del servidor. */
function simularServidor(manejador) {
  http.defaults.adapter = manejador
}

beforeEach(() => {
  vi.clearAllMocks()
  http.defaults.adapter = undefined
})

describe('interceptor de peticion', () => {
  it('adjunta el token de acceso a las peticiones protegidas', async () => {
    estadoDeSesion('token-abc')
    let cabeceraVista = null
    simularServidor(async (config) => {
      cabeceraVista = config.headers.Authorization
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    })

    await http.get('/usuarios')

    expect(cabeceraVista).toBe('Bearer token-abc')
  })

  it('no adjunta token al iniciar sesion', async () => {
    estadoDeSesion('token-abc')
    let cabeceraVista = 'no-tocada'
    simularServidor(async (config) => {
      cabeceraVista = config.headers.Authorization
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    })

    await http.post('/auth/login', { username: 'a', password: 'b' })

    expect(cabeceraVista).toBeUndefined()
  })
})

describe('refresco de token ante un 401', () => {
  it('dispara UN SOLO refresco aunque fallen varias peticiones a la vez', async () => {
    const estado = estadoDeSesion()
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo' } })

    let intentos = 0
    simularServidor(async (config) => {
      intentos += 1
      const esReintento = config.headers.Authorization === 'Bearer access-nuevo'
      if (!esReintento) {
        const error = new Error('401')
        error.config = config
        error.response = { status: 401, data: { codigo: 'NO_AUTENTICADO' } }
        throw error
      }
      return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config }
    })

    // Cinco peticiones simultaneas, todas con el token caducado.
    const respuestas = await Promise.all([
      http.get('/usuarios'),
      http.get('/productos'),
      http.get('/ventas'),
      http.get('/solicitudes'),
      http.get('/panel/resumen'),
    ])

    expect(axios.post).toHaveBeenCalledTimes(1)
    expect(respuestas).toHaveLength(5)
    expect(respuestas.every((r) => r.data.ok)).toBe(true)
    expect(estado.access).toBe('access-nuevo')
    expect(intentos).toBe(10) // 5 fallidas + 5 reintentos
  })

  it('reintenta la peticion original con el token nuevo', async () => {
    estadoDeSesion()
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo' } })
    const tokensUsados = []

    simularServidor(async (config) => {
      tokensUsados.push(config.headers.Authorization)
      if (config.headers.Authorization === 'Bearer access-viejo') {
        const error = new Error('401')
        error.config = config
        error.response = { status: 401, data: {} }
        throw error
      }
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    })

    await http.get('/usuarios')

    expect(tokensUsados).toEqual(['Bearer access-viejo', 'Bearer access-nuevo'])
  })

  it('cierra la sesion si el refresco falla', async () => {
    const estado = estadoDeSesion()
    const fallo = new Error('cuenta bloqueada')
    fallo.response = { status: 403, data: { codigo: 'CUENTA_BLOQUEADA', detalle: 'x' } }
    axios.post.mockRejectedValue(fallo)

    simularServidor(async (config) => {
      const error = new Error('401')
      error.config = config
      error.response = { status: 401, data: {} }
      throw error
    })

    await expect(http.get('/usuarios')).rejects.toMatchObject({
      codigo: 'CUENTA_BLOQUEADA',
    })
    expect(estado.cerrada).toBe(true)
  })

  it('no intenta refrescar cuando el 401 viene del propio login', async () => {
    estadoDeSesion()
    simularServidor(async (config) => {
      const error = new Error('401')
      error.config = config
      error.response = {
        status: 401,
        data: { codigo: 'CREDENCIALES_INVALIDAS', detalle: 'Usuario o contraseña incorrectos.' },
      }
      throw error
    })

    await expect(
      http.post('/auth/login', { username: 'a', password: 'mala' }),
    ).rejects.toMatchObject({ codigo: 'CREDENCIALES_INVALIDAS' })
    expect(axios.post).not.toHaveBeenCalled()
  })

  it('no reintenta indefinidamente si el 401 persiste', async () => {
    estadoDeSesion()
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo' } })
    let intentos = 0

    simularServidor(async (config) => {
      intentos += 1
      const error = new Error('401')
      error.config = config
      error.response = { status: 401, data: {} }
      throw error
    })

    await expect(http.get('/usuarios')).rejects.toBeTruthy()
    expect(intentos).toBe(2) // original + un unico reintento
  })
})

describe('normalizacion de errores (plan.md 4.3)', () => {
  it('conserva codigo, detalle y errores del backend', () => {
    const normalizado = normalizarError({
      response: {
        status: 400,
        data: {
          codigo: 'VALIDACION',
          detalle: 'Revise los datos ingresados.',
          errores: { precio: ['Debe ser mayor que cero.'] },
        },
      },
    })

    expect(normalizado.codigo).toBe('VALIDACION')
    expect(normalizado.errores.precio).toEqual(['Debe ser mayor que cero.'])
    expect(normalizado.estado).toBe(400)
  })

  it('da la misma forma a un fallo de red, que no viene del backend', () => {
    const normalizado = normalizarError(new Error('Network Error'))

    expect(normalizado.codigo).toBe('SIN_CONEXION')
    expect(normalizado).toHaveProperty('detalle')
    expect(normalizado).toHaveProperty('errores')
    expect(normalizado).toHaveProperty('estado')
  })
})
