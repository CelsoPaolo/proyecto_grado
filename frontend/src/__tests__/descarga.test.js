/**
 * Descarga del informe de servicio (RF-67, RF-68).
 *
 * Tres cosas que se rompen con facilidad y no se ven a simple vista:
 *
 *   1. La petición debe pedir `blob`. Sin eso axios interpreta los
 *      bytes como texto y el PDF llega corrompido, pero la descarga
 *      «funciona»: el usuario abre un archivo roto.
 *   2. Cerrar el cuadro de guardado NO es un error. Es una decisión
 *      del usuario y no debe acabar en un mensaje rojo.
 *   3. Un error que llega como blob debe recuperar su mensaje real.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

import http, { normalizarError } from '../api/http'
import { serviciosApi } from '../api/servicios'
import { useDescarga } from '../composables/useDescarga'

vi.mock('../api/http', async (importOriginal) => ({
  ...(await importOriginal()),
  default: {
    get: vi.fn(() => Promise.resolve({ data: new Blob(['%PDF-1.4']) })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

beforeEach(() => {
  vi.clearAllMocks()
  delete window.showSaveFilePicker
})

describe('la petición del informe', () => {
  it('pide el cuerpo como blob', () => {
    /* Sin responseType blob el PDF llegaría corrompido. */
    serviciosApi.informePdf(12)

    const [ruta, opciones] = http.get.mock.calls[0]

    expect(ruta).toBe('/solicitudes/12/pdf')
    expect(opciones.responseType).toBe('blob')
  })
})

describe('elección de carpeta (RF-68)', () => {
  it('abre el cuadro nativo cuando el navegador lo admite', async () => {
    const escribir = vi.fn()
    const cerrar = vi.fn()
    window.showSaveFilePicker = vi.fn(() =>
      Promise.resolve({
        createWritable: () => Promise.resolve({ write: escribir, close: cerrar }),
      }),
    )

    const { guardar } = useDescarga()
    const blob = new Blob(['%PDF-1.4'])
    const guardado = await guardar(() => Promise.resolve(blob), 'informe-12.pdf')

    expect(guardado).toBe(true)
    expect(window.showSaveFilePicker).toHaveBeenCalledWith(
      expect.objectContaining({ suggestedName: 'informe-12.pdf' }),
    )
    expect(escribir).toHaveBeenCalledWith(blob)
    expect(cerrar).toHaveBeenCalled()
  })

  it('cancelar el cuadro no es un error', async () => {
    /* Lo que evita esta prueba: un «Ocurrió un error» cada vez que
       alguien abre el cuadro y se arrepiente. */
    const abortada = new Error('cancelado')
    abortada.name = 'AbortError'
    window.showSaveFilePicker = vi.fn(() => Promise.reject(abortada))

    const { guardar } = useDescarga()
    const guardado = await guardar(
      () => Promise.resolve(new Blob(['%PDF'])),
      'informe-12.pdf',
    )

    expect(guardado).toBe(false)
  })

  it('sin cuadro nativo descarga igualmente', async () => {
    /* Firefox y Safari no lo implementan. RF-68 dice «cuando el
       navegador lo permita»: en el resto no se deja sin archivo al
       usuario. */
    const click = vi.fn()
    const original = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((etiqueta) => {
      const nodo = original(etiqueta)
      if (etiqueta === 'a') nodo.click = click
      return nodo
    })
    URL.createObjectURL = vi.fn(() => 'blob:x')
    URL.revokeObjectURL = vi.fn()

    const { guardar } = useDescarga()
    const guardado = await guardar(
      () => Promise.resolve(new Blob(['%PDF'])),
      'informe-12.pdf',
    )

    expect(guardado).toBe(true)
    expect(click).toHaveBeenCalled()

    document.createElement.mockRestore()
  })

  it('un fallo de la API se propaga en lugar de tragarse', async () => {
    const { guardar, descargando } = useDescarga()

    await expect(
      guardar(
        () => Promise.reject({ codigo: 'NO_ENCONTRADO', detalle: 'No existe.' }),
        'informe-12.pdf',
      ),
    ).rejects.toMatchObject({ codigo: 'NO_ENCONTRADO' })

    // El indicador no puede quedarse encendido tras el fallo.
    expect(descargando.value).toBe(false)
  })
})

describe('errores que llegan como blob', () => {
  it('normalizarError recupera el código real una vez desempaquetado', async () => {
    /* Con responseType blob, axios aplica ese tipo también al cuerpo
       del error. Si no se desempaqueta, un 404 se degradaría a
       «Ocurrió un error inesperado» y el usuario no sabría que la
       solicitud no es suya. */
    const cuerpo = { codigo: 'NO_ENCONTRADO', detalle: 'El recurso no existe.' }
    const blob = new Blob([JSON.stringify(cuerpo)], { type: 'application/json' })

    const sinDesempaquetar = normalizarError({
      response: { status: 404, data: blob },
    })
    expect(sinDesempaquetar.codigo).toBe('ERROR_INTERNO')

    const desempaquetado = normalizarError({
      response: { status: 404, data: JSON.parse(await blob.text()) },
    })
    expect(desempaquetado.codigo).toBe('NO_ENCONTRADO')
    expect(desempaquetado.detalle).toBe('El recurso no existe.')
  })
})
