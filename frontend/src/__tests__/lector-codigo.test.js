/**
 * T-9.5 — Entrada por código en el registro de venta (RF-74, RN-VEN-17,
 * RNF-16, RNF-27).
 *
 * Un lector en modo teclado escribe el codigo y pulsa Intro. Aqui se
 * simula exactamente eso: valor en el campo + keydown Enter. Se comprueba
 * cada punto del «hecho cuando» de T-9.5, mas la carrera entre dos
 * lecturas seguidas, que con un lector real es lo normal.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { productosApi } from '../api/catalogo'
import { localeEs } from '../locale/es'
import RegistrarVentaView from '../views/ventas/RegistrarVentaView.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: {} }),
  RouterLink: { template: '<a><slot /></a>' },
}))

vi.mock('../api/ventas', () => ({
  ventasApi: { registrar: vi.fn(), listar: vi.fn(), obtener: vi.fn(), anular: vi.fn() },
}))

vi.mock('../api/catalogo', () => ({
  productosApi: { listar: vi.fn() },
  categoriasApi: { listar: vi.fn() },
}))

const TECLADO = { id: 1, codigo: '2000000000015', codigo_fabrica: '', nombre: 'Teclado mecánico', precio: '350.00', stock: 3 }
const MOUSE = { id: 2, codigo: '2000000000022', codigo_fabrica: '7501031311309', nombre: 'Mouse inalámbrico', precio: '85.00', stock: 5 }
const AGOTADO = { id: 3, codigo: '2000000000039', codigo_fabrica: '', nombre: 'Monitor agotado', precio: '1250.00', stock: 0 }
const UPC = { id: 4, codigo: '2000000000046', codigo_fabrica: '012345678905', nombre: 'Cable HDMI', precio: '40.00', stock: 9 }
const CODE128 = { id: 5, codigo: '2000000000053', codigo_fabrica: 'ABC-123X', nombre: 'Adaptador', precio: '25.00', stock: 9 }

/** Simula al servidor: coincidencia exacta con cualquiera de los dos
 *  codigos, solo entre activos (el retirado no esta en la lista). */
const ACTIVOS = [TECLADO, MOUSE, AGOTADO, UPC, CODE128]
function servidor({ codigo }) {
  return Promise.resolve({
    results: ACTIVOS.filter((p) => p.codigo === codigo || p.codigo_fabrica === codigo),
  })
}

let wrapper

function montar() {
  wrapper = mount(RegistrarVentaView, {
    attachTo: document.body,
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
      stubs: { RouterLink: true },
    },
  })
  return wrapper
}

const campo = () => wrapper.find('[data-prueba="codigo"]')

/** Lo que hace un lector: escribir el codigo y pulsar Intro. */
async function leer(codigo) {
  campo().element.focus()
  await campo().setValue(codigo)
  await campo().trigger('keydown', { key: 'Enter' })
  await flushPromises()
}

/** Un lector TECLEA: lo que escribe se suma a lo que ya hubiera en el
 *  campo. Si el campo no se vaciara en el acto, una segunda lectura se
 *  pegaria a la primera. */
async function teclear(codigo) {
  await campo().setValue(campo().element.value + codigo)
  await campo().trigger('keydown', { key: 'Enter' })
}

const lineas = () => wrapper.vm.lineas.map((l) => [l.nombre, l.cantidad])
const aviso = () => wrapper.find('[data-prueba="aviso-codigo"]')

beforeEach(() => {
  vi.clearAllMocks()
  productosApi.listar.mockImplementation(servidor)
})

afterEach(() => wrapper?.unmount())

describe('lecturas que agregan', () => {
  it('un código interno exacto agrega el producto', async () => {
    montar()
    await leer('2000000000015')

    expect(lineas()).toEqual([['Teclado mecánico', 1]])
    expect(productosApi.listar).toHaveBeenCalledWith({ codigo: '2000000000015', activo: 'true' })
  })

  it('un código de fábrica exacto agrega el producto', async () => {
    montar()
    await leer('7501031311309')

    expect(lineas()).toEqual([['Mouse inalámbrico', 1]])
  })

  it('el mismo código otra vez suma una unidad, sin duplicar la línea', async () => {
    montar()
    await leer('2000000000015')
    await leer('2000000000015')

    expect(lineas()).toEqual([['Teclado mecánico', 2]])
  })

  it.each([
    ['UPC de 12 cifras', '012345678905', 'Cable HDMI'],
    ['Code128 alfanumérico', 'ABC-123X', 'Adaptador'],
  ])('un código de fábrica %s también se consulta', async (_, codigo, nombre) => {
    montar()
    await leer(codigo)

    expect(productosApi.listar).toHaveBeenCalledWith({ codigo, activo: 'true' })
    expect(lineas()).toEqual([[nombre, 1]])
  })

  it('tras cada lectura el campo queda vacío y con el foco', async () => {
    montar()
    await leer('2000000000015')

    expect(campo().element.value).toBe('')
    expect(document.activeElement).toBe(campo().element)

    await leer('7501031311309')
    expect(document.activeElement).toBe(campo().element)
  })

  it('dos lecturas seguidas: ninguna se pierde y la venta queda en el orden leído', async () => {
    /* Con un lector real es lo normal: la segunda lectura llega antes de
       que responda la primera. Si el campo se vaciara al RESPONDER, la
       segunda se borraria; y sin la cola, la respuesta mas rapida se
       agregaria primero y la venta quedaria en otro orden que el leido. */
    let liberar
    productosApi.listar.mockImplementationOnce(
      (params) => new Promise((resolver) => (liberar = () => resolver(servidor(params)))),
    )
    montar()

    await teclear('2000000000015') // lenta
    await teclear('7501031311309') // responde enseguida
    await flushPromises()
    liberar()
    await flushPromises()

    expect(lineas()).toEqual([
      ['Teclado mecánico', 1],
      ['Mouse inalámbrico', 1],
    ])
  })
})

describe('lecturas que no agregan nada', () => {
  it('un código inexistente avisa, no agrega y deja el código seleccionado', async () => {
    montar()
    await leer('2999999999999')

    expect(lineas()).toEqual([])
    expect(aviso().text()).toContain('2999999999999')
    const entrada = campo().element
    expect(entrada.value).toBe('2999999999999')
    expect(document.activeElement).toBe(entrada)
    // Seleccionado entero: la lectura siguiente lo sustituye.
    expect([entrada.selectionStart, entrada.selectionEnd]).toEqual([0, 13])
  })

  it('un código incompleto no agrega nada (sin coincidencias parciales)', async () => {
    montar()
    await leer('200000000001')

    expect(lineas()).toEqual([])
    expect(aviso().exists()).toBe(true)
  })

  it('un producto retirado no se agrega (el servidor solo busca entre activos)', async () => {
    montar()
    await leer('2000000000060') // existe, pero retirado: no esta en ACTIVOS

    expect(lineas()).toEqual([])
    expect(productosApi.listar).toHaveBeenCalledWith(expect.objectContaining({ activo: 'true' }))
  })

  it('un producto sin existencias avisa y no se agrega', async () => {
    montar()
    await leer('2000000000039')

    expect(lineas()).toEqual([])
    expect(aviso().text()).toContain('no tiene existencias')
  })

  it('no suma más unidades que las existencias', async () => {
    montar()
    for (let i = 0; i < 4; i++) await leer('2000000000015') // stock 3

    expect(lineas()).toEqual([['Teclado mecánico', 3]])
    expect(aviso().text()).toContain('no quedan más existencias')
  })

  it('un Intro con el campo vacío no consulta nada', async () => {
    montar()
    await leer('   ')

    expect(productosApi.listar).not.toHaveBeenCalled()
  })

  it('una lectura correcta borra el aviso de la anterior', async () => {
    montar()
    await leer('2999999999999')
    await leer('2000000000015')

    expect(aviso().exists()).toBe(false)
  })
})
