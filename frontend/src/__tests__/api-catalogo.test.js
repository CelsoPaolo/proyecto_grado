/**
 * Cuerpo de las peticiones de producto (api/catalogo.js).
 *
 * Con imagen, el producto viaja como multipart. La cadena vacia debe
 * viajar tambien: es como se vacia un campo de texto. Antes se omitia, y
 * al editar un producto subiendo una imagen nueva no habia forma de
 * vaciar la descripcion ni de quitar el codigo de fabrica (T-9.7).
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { productosApi } from '../api/catalogo'
import http from '../api/http'

vi.mock('../api/http', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(),
  },
}))

beforeEach(() => vi.clearAllMocks())

describe('productosApi.actualizar', () => {
  it('sin imagen envía JSON, con la cadena vacía incluida', async () => {
    await productosApi.actualizar(7, { nombre: 'X', codigo_fabrica: '', imagen: null })

    const [, cuerpo] = http.patch.mock.calls[0]
    expect(cuerpo).toEqual({ nombre: 'X', codigo_fabrica: '' })
  })

  it('con imagen envía multipart, también con la cadena vacía, y omite lo nulo', async () => {
    const imagen = new File(['x'], 'foto.png', { type: 'image/png' })

    await productosApi.actualizar(7, {
      nombre: 'X',
      descripcion: '',
      codigo_fabrica: '',
      precio: null,
      imagen,
    })

    const [, cuerpo] = http.patch.mock.calls[0]
    expect(cuerpo).toBeInstanceOf(FormData)
    expect(cuerpo.get('codigo_fabrica')).toBe('')
    expect(cuerpo.get('descripcion')).toBe('')
    expect(cuerpo.has('precio')).toBe(false)
    expect(cuerpo.get('imagen')).toBeInstanceOf(File)
  })
})
