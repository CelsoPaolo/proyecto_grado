/**
 * T-15.8 — Aviso del código de unidad en Registrar venta (RF-105, RN-VEN-21).
 *
 * Un código de unidad (prefijo 21) identifica una unidad ya vendida, no
 * un producto del catálogo. Si alguien lo escribe o lo escanea en el
 * campo del código, el sistema lo dice en lugar de «no se encontró», y
 * no agrega nada.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { productosApi } from '../api/catalogo'
import { localeEs } from '../locale/es'
import { esCodigoDeUnidad } from '../utils/codigos'
import RegistrarVentaView from '../views/ventas/RegistrarVentaView.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: {} }),
  RouterLink: { template: '<a><slot /></a>' },
}))

vi.mock('../api/ventas', () => ({
  ventasApi: { registrar: vi.fn() },
}))

vi.mock('../api/catalogo', () => ({
  productosApi: { listar: vi.fn() },
  categoriasApi: { listar: vi.fn() },
}))

const TECLADO = { id: 1, codigo: '2000000000015', codigo_fabrica: '', nombre: 'Teclado mecánico', precio: '350.00', stock: 3 }
/** Un producto cuyo código de fábrica, por casualidad, empieza por 21. */
const RARO = { id: 2, codigo: '2000000000022', codigo_fabrica: '2112345678903', nombre: 'Producto raro', precio: '10.00', stock: 3 }
const ACTIVOS = [TECLADO, RARO]

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
const aviso = () => wrapper.find('[data-prueba="aviso-codigo"]')
const lineas = () => wrapper.vm.lineas.map((l) => [l.nombre, l.cantidad])

async function leer(codigo) {
  campo().element.focus()
  await campo().setValue(codigo)
  await campo().trigger('keydown', { key: 'Enter' })
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  productosApi.listar.mockImplementation(({ codigo }) =>
    Promise.resolve({
      results: ACTIVOS.filter((p) => p.codigo === codigo || p.codigo_fabrica === codigo),
    }),
  )
})

afterEach(() => wrapper?.unmount())

describe('la forma de un código de unidad', () => {
  it('13 dígitos que empiezan por 21', () => {
    expect(esCodigoDeUnidad('2100000000012')).toBe(true)
    for (const valor of ['2000000000015', '210000000001', '21000000000123', '21ABC00000012', '', null]) {
      expect(esCodigoDeUnidad(valor)).toBe(false)
    }
  })
})

describe('en el campo del código', () => {
  it('un código de unidad avisa que no es de producto y no agrega nada', async () => {
    montar()
    await leer('2100000000012')

    expect(aviso().text()).toContain('Este es un código de unidad, no de producto')
    expect(lineas()).toEqual([])
  })

  it('primero se busca el producto: el servidor se consulta igual', async () => {
    montar()
    await leer('2100000000012')

    expect(productosApi.listar).toHaveBeenCalledWith({ codigo: '2100000000012', activo: 'true' })
  })

  it('un código desconocido de otra forma da el aviso de siempre', async () => {
    montar()
    await leer('2000000009999')

    expect(aviso().text()).toContain('Ningún producto del catálogo tiene el código 2000000009999')
    expect(aviso().text()).not.toContain('código de unidad')
  })

  it('un producto encontrado se agrega aunque su código empiece por 21', async () => {
    montar()
    await leer('2112345678903')

    expect(lineas()).toEqual([['Producto raro', 1]])
    expect(aviso().exists()).toBe(false)
  })

  it('después del aviso, una lectura correcta agrega normalmente', async () => {
    montar()
    await leer('2100000000012')
    await leer('2000000000015')

    expect(lineas()).toEqual([['Teclado mecánico', 1]])
  })
})
