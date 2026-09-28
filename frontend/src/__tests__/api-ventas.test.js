/**
 * T-4.8 — Cliente de API de ventas.
 *
 * Verifica el recorte de campos que exige RN-VEN-04: al servidor solo
 * viajan producto_id y cantidad. Mandar el precio desde el navegador
 * no cambiaria nada —el servidor lo ignora y toma el del catalogo—,
 * pero daria la falsa impresion de que el importe se decide aqui.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

import http from '../api/http'
import { ventasApi } from '../api/ventas'

vi.mock('../api/http', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('registro de una venta', () => {
  it('envia al servidor solo producto_id y cantidad', async () => {
    await ventasApi.registrar({
      clienteNombre: 'María Gutiérrez',
      clienteTelefono: '70012345',
      items: [
        // La pantalla arrastra nombre, precio y stock para poder
        // mostrar el total en vivo; nada de eso debe salir hacia el
        // servidor.
        { producto_id: 1, nombre: 'Teclado', precio: '350.00', stock: 10, cantidad: 2 },
        { producto_id: 7, nombre: 'Monitor', precio: '750.00', stock: 4, cantidad: 1 },
      ],
    })

    const [ruta, cuerpo] = http.post.mock.calls[0]

    expect(ruta).toBe('/ventas')
    expect(cuerpo.items).toEqual([
      { producto_id: 1, cantidad: 2 },
      { producto_id: 7, cantidad: 1 },
    ])
  })

  it('no incluye ningun campo de precio en el cuerpo', () => {
    ventasApi.registrar({
      clienteNombre: 'X',
      clienteTelefono: '7',
      items: [{ producto_id: 1, precio: '1.00', precio_unitario: '1.00', cantidad: 1 }],
    })

    const cuerpo = JSON.stringify(http.post.mock.calls[0][1])

    expect(cuerpo).not.toContain('precio')
  })

  it('traduce los nombres de los campos del cliente', () => {
    ventasApi.registrar({
      clienteNombre: 'María Gutiérrez',
      clienteTelefono: '70012345',
      items: [{ producto_id: 1, cantidad: 1 }],
    })

    const cuerpo = http.post.mock.calls[0][1]

    expect(cuerpo.cliente_nombre).toBe('María Gutiérrez')
    expect(cuerpo.cliente_telefono).toBe('70012345')
  })
})

describe('anulacion', () => {
  it('llama a la accion con nombre propio, no a un DELETE', () => {
    /* RN-VEN-06: la venta no se elimina. Que el cliente de API no
       tenga siquiera un metodo de borrado lo hace explicito. */
    ventasApi.anular(42, 'Cliente se arrepintió')

    expect(http.post).toHaveBeenCalledWith('/ventas/42/anular', {
      motivo: 'Cliente se arrepintió',
    })
    expect(ventasApi.eliminar).toBeUndefined()
  })
})
