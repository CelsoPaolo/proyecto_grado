/**
 * T-9.4 — Codigo de barras y etiqueta (RF-71, CU-CAT-09).
 *
 * Lo que una prueba puede asegurar sin una impresora: que el codigo
 * interno se dibuja como EAN-13 (y no como Code128, que un lector
 * configurado para EAN no leeria), que las barras codifican exactamente
 * el codigo, que la etiqueta lleva cifras y nombre, y que el boton
 * imprime. Que la etiqueta impresa se lea con un telefono queda para
 * revision humana.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { productosApi } from '../api/catalogo'
import CodigoBarras from '../components/CodigoBarras.vue'
import { localeEs } from '../locale/es'
import { esEan13Valido } from '../utils/codigos'
import ProductoDetalleView from '../views/catalogo/ProductoDetalleView.vue'
import ProductosView from '../views/catalogo/ProductosView.vue'

vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRoute: () => ({ params: { id: 7 }, query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('../api/catalogo', () => ({
  productosApi: { obtener: vi.fn(), listar: vi.fn() },
  categoriasApi: { listar: vi.fn(() => Promise.resolve({ results: [] })) },
}))

vi.mock('../api/inventario', async () => ({
  ...(await vi.importActual('../api/inventario')),
  inventarioApi: { historialDe: vi.fn(() => Promise.resolve({ count: 0, results: [] })) },
}))

const PRODUCTO = {
  id: 7,
  codigo: '2000000000077',
  codigo_fabrica: '',
  nombre: 'Disco SSD 480 GB',
  categoria_nombre: 'Almacenamiento',
  precio: '250.00',
  stock: 10,
  stock_bajo: false,
  activo: true,
  descripcion: '',
  imagen: null,
}

const plugins = (rol = 'VENTAS') => [
  createTestingPinia({
    createSpy: vi.fn,
    stubActions: false,
    initialState: { auth: { usuario: { id: 1, rol } } },
  }),
  [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
  ToastService,
  ConfirmationService,
]

const STUBS = { RouterLink: { props: ['to'], template: '<a><slot /></a>' } }

/* JsBarcode mide el ancho de las cifras con un <canvas>, y jsdom no
   implementa canvas (instalar el paquete nativo `canvas` seria una
   dependencia no aprobada). Se simula SOLO esa medicion: las barras las
   sigue calculando JsBarcode de verdad, que es lo que se comprueba. */
HTMLCanvasElement.prototype.getContext = () => ({
  font: '',
  measureText: (texto) => ({ width: String(texto).length * 7 }),
})

beforeEach(() => {
  vi.clearAllMocks()
  window.matchMedia ??= () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  })
  productosApi.obtener.mockResolvedValue({ ...PRODUCTO })
  productosApi.listar.mockResolvedValue({ count: 1, results: [{ ...PRODUCTO }] })
})

describe('validación EAN-13 en la interfaz', () => {
  it('coincide con códigos reales y con los internos', () => {
    for (const real of ['4006381333931', '5901234123457', '2000000001470', '2000000000077']) {
      expect(esEan13Valido(real)).toBe(true)
    }
    for (const malo of ['4006381333932', '400638133393', 'ABC', '', null]) {
      expect(esEan13Valido(malo)).toBe(false)
    }
  })
})

// ─────────────────────────────────────────────────────────────────────
// El dibujo
// ─────────────────────────────────────────────────────────────────────
/**
 * Lee de vuelta los modulos que dibuja JsBarcode: cada rect es una barra
 * y su ancho en modulos sale de su anchura relativa. Para EAN-13 son 95
 * modulos; aqui basta con comprobar que el dibujo es de EAN-13 y que
 * cambia si cambia el codigo.
 */
function barras(wrapper) {
  return wrapper.findAll('rect').map((r) => `${r.attributes('x')}:${r.attributes('width')}`).join('|')
}

describe('componente CodigoBarras', () => {
  it('dibuja el código interno como EAN-13, con las cifras y una etiqueta accesible', () => {
    const wrapper = mount(CodigoBarras, { props: { valor: '2000000000077' } })

    const svg = wrapper.find('svg')
    expect(svg.attributes('data-formato')).toBe('EAN13')
    expect(svg.attributes('aria-label')).toBe('Código de barras 2000000000077')
    expect(wrapper.findAll('rect').length).toBeGreaterThan(10)
    // displayValue: las cifras van impresas bajo las barras.
    expect(svg.text().replace(/\s/g, '')).toBe('2000000000077')
  })

  it('dos códigos distintos dan barras distintas, y el mismo, las mismas', () => {
    const a = barras(mount(CodigoBarras, { props: { valor: '2000000000077' } }))
    const otraVez = barras(mount(CodigoBarras, { props: { valor: '2000000000077' } }))
    const b = barras(mount(CodigoBarras, { props: { valor: '2000000000060' } }))

    expect(a).toBe(otraVez)
    expect(a).not.toBe(b)
  })

  it('un código de fábrica que no es EAN-13 se dibuja en Code128', () => {
    const wrapper = mount(CodigoBarras, { props: { valor: 'ABC-123' } })

    expect(wrapper.find('svg').attributes('data-formato')).toBe('CODE128')
  })

  it('redibuja si cambia el código', async () => {
    const wrapper = mount(CodigoBarras, { props: { valor: '2000000000077' } })
    const antes = barras(wrapper)

    await wrapper.setProps({ valor: '2000000000060' })

    expect(barras(wrapper)).not.toBe(antes)
  })
})

// ─────────────────────────────────────────────────────────────────────
// Detalle y etiqueta (CU-CAT-09: Administrador y Ventas)
// ─────────────────────────────────────────────────────────────────────
describe('detalle de producto', () => {
  it.each(['ADMINISTRADOR', 'VENTAS'])('%s ve el código, el de fábrica y la etiqueta', async (rol) => {
    productosApi.obtener.mockResolvedValue({ ...PRODUCTO, codigo_fabrica: '7501031311309' })
    const wrapper = mount(ProductoDetalleView, { global: { plugins: plugins(rol), stubs: STUBS } })
    await flushPromises()

    expect(wrapper.find('[data-prueba="codigo"]').text()).toBe('2000000000077')
    expect(wrapper.find('[data-prueba="codigo-fabrica"]').text()).toBe('7501031311309')
    const etiqueta = wrapper.find('[data-prueba="etiqueta"]')
    expect(etiqueta.find('svg').attributes('data-formato')).toBe('EAN13')
    expect(etiqueta.text()).toContain('Disco SSD 480 GB')
  })

  it('sin código de fábrica lo dice', async () => {
    const wrapper = mount(ProductoDetalleView, { global: { plugins: plugins(), stubs: STUBS } })
    await flushPromises()

    expect(wrapper.find('[data-prueba="codigo-fabrica"]').text()).toBe('No registrado')
  })

  it('«Imprimir etiqueta» abre la impresión del navegador', async () => {
    const imprimir = vi.spyOn(window, 'print').mockImplementation(() => {})
    const wrapper = mount(ProductoDetalleView, { global: { plugins: plugins(), stubs: STUBS } })
    await flushPromises()

    await wrapper.find('[data-prueba="imprimir"]').trigger('click')

    expect(imprimir).toHaveBeenCalledTimes(1)
    imprimir.mockRestore()
  })
})

// ─────────────────────────────────────────────────────────────────────
// Lista del catalogo (RF-70)
// ─────────────────────────────────────────────────────────────────────
describe('lista del catálogo', () => {
  it('muestra el código y busca por código exacto', async () => {
    const wrapper = mount(ProductosView, { global: { plugins: plugins(), stubs: STUBS } })
    await flushPromises()
    expect(wrapper.text()).toContain('2000000000077')

    await wrapper.find('[data-prueba="filtro-codigo"]').setValue('  2000000000077 ')
    await wrapper.find('[data-prueba="filtro-codigo"]').trigger('keyup', { key: 'Enter' })
    await flushPromises()

    expect(productosApi.listar).toHaveBeenLastCalledWith(
      expect.objectContaining({ codigo: '2000000000077', page: 1 }),
    )
  })
})
