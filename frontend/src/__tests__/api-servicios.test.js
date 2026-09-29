/**
 * T-5.10 — Cliente de API de servicios.
 *
 * Verifica lo que el cuerpo lleva y lo que NO lleva. Tres reglas se
 * apoyan en ello:
 *
 *   RN-SER-01  la modalidad la deriva el servidor del tipo
 *   RN-SER-04  la dirección solo aplica a los servicios a domicilio
 *   RF-57      monto y técnico son del Administrador
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

import http from '../api/http'
import { serviciosApi } from '../api/servicios'

vi.mock('../api/http', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('registro de una solicitud', () => {
  it('no envía la modalidad: la deriva el servidor del tipo', () => {
    serviciosApi.registrar({
      clienteNombre: 'María Gutiérrez',
      clienteTelefono: '70012345',
      tipo: 'REPARACION',
      descripcion: 'No enciende',
    })

    const [ruta, cuerpo] = http.post.mock.calls[0]

    expect(ruta).toBe('/solicitudes')
    expect(cuerpo).not.toHaveProperty('modalidad')
  })

  it('no envía dirección para un servicio en taller', () => {
    /* El servidor la descarta igualmente (RN-SER-04); no mandarla
       evita dar a entender que se guardará. */
    serviciosApi.registrar({
      clienteNombre: 'X',
      clienteTelefono: '7',
      tipo: 'MANTENIMIENTO',
      descripcion: 'Algo',
      direccion: 'Calle Falsa 123',
    })

    expect(http.post.mock.calls[0][1]).not.toHaveProperty('direccion')
  })

  it('sí envía dirección para un servicio a domicilio', () => {
    serviciosApi.registrar({
      clienteNombre: 'X',
      clienteTelefono: '7',
      tipo: 'REDES',
      descripcion: 'Cableado',
      direccion: 'Av. Siempre Viva 742',
    })

    expect(http.post.mock.calls[0][1].direccion).toBe('Av. Siempre Viva 742')
  })

  it('nunca envía monto ni técnico al registrar', () => {
    /* RF-57: ambos son del Administrador. El servidor los ignoraría,
       pero mandarlos sugeriría que quien registra puede fijarlos. */
    serviciosApi.registrar({
      clienteNombre: 'X',
      clienteTelefono: '7',
      tipo: 'REPARACION',
      descripcion: 'Algo',
    })

    const cuerpo = http.post.mock.calls[0][1]

    expect(cuerpo).not.toHaveProperty('monto_cobrado')
    expect(cuerpo).not.toHaveProperty('tecnico')
  })
})

describe('cotización', () => {
  it('permite enviar solo el monto', () => {
    serviciosApi.cotizar(5, { monto: 250 })

    const [ruta, cuerpo] = http.post.mock.calls[0]

    expect(ruta).toBe('/solicitudes/5/cotizar')
    expect(cuerpo).toEqual({ monto_cobrado: 250 })
  })

  it('permite enviar solo el técnico', () => {
    serviciosApi.cotizar(5, { tecnico: 'Pedro Mamani' })

    expect(http.post.mock.calls[0][1]).toEqual({ tecnico: 'Pedro Mamani' })
  })

  it('envía un monto de cero, que es una cotización válida', () => {
    /* RN-SER-17: cero significa garantía o cortesía. Si el cliente lo
       descartara por ser un valor falso, el servicio quedaría sin
       cotizar y no podría cerrarse. */
    serviciosApi.cotizar(5, { monto: 0 })

    expect(http.post.mock.calls[0][1]).toEqual({ monto_cobrado: 0 })
  })
})

describe('acciones de ciclo de vida', () => {
  it('cada transición es una acción con nombre propio', () => {
    serviciosApi.iniciar(5)
    serviciosApi.finalizar(5, 'Se cambió la fuente')
    serviciosApi.cancelar(5, 'El cliente desistió')

    const rutas = http.post.mock.calls.map((c) => c[0])

    expect(rutas).toEqual([
      '/solicitudes/5/iniciar',
      '/solicitudes/5/finalizar',
      '/solicitudes/5/cancelar',
    ])
  })

  it('no existe un método para eliminar una solicitud', () => {
    /* RN-SER-08: se cancelan, no se borran. */
    expect(serviciosApi.eliminar).toBeUndefined()
    expect(http.delete).toBeUndefined()
  })
})
