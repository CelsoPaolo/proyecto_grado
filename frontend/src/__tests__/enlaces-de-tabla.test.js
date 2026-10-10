/**
 * T-14.2 — Nombres sin estilo de enlace en las listas (plan.md 7.13).
 *
 * Dos cosas: que cada nombre que abre un detalle lleve la clase comun
 * `enlace-de-tabla`, y que esa clase haga lo pedido —color del texto,
 * sin subrayado, tambien visitado, cursor de mano— SIN quitar el
 * indicador de foco del teclado. jsdom no calcula estilos de hojas
 * externas, asi que la regla se comprueba leyendo la hoja de estilos.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { productosApi } from '../api/catalogo'
import { clientesApi } from '../api/clientes'
import TablaMovimientos from '../components/TablaMovimientos.vue'
import { localeEs } from '../locale/es'
import ClientesView from '../views/clientes/ClientesView.vue'
import ProductosView from '../views/catalogo/ProductosView.vue'

vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRoute: () => ({ params: {}, query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../api/catalogo', () => ({
  productosApi: { listar: vi.fn() },
  categoriasApi: { listar: vi.fn(() => Promise.resolve({ results: [] })) },
}))
vi.mock('../api/clientes', () => ({ clientesApi: { listar: vi.fn() } }))

const global = {
  plugins: [
    createTestingPinia({ createSpy: vi.fn, initialState: { auth: { usuario: { id: 1, rol: 'ADMINISTRADOR' } } } }),
    [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
    ToastService,
    ConfirmationService,
  ],
  // El enlace se renderiza como <a>, como RouterLink de verdad.
  stubs: { RouterLink: { props: ['to'], template: '<a href="#"><slot /></a>' } },
}

beforeEach(() => {
  vi.clearAllMocks()
  window.matchMedia ??= () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} })
  productosApi.listar.mockResolvedValue({
    count: 1,
    results: [{ id: 7, codigo: '2000000000077', nombre: 'Disco SSD', categoria_nombre: 'X', precio: '1', stock: 3, stock_bajo: false }],
  })
  clientesApi.listar.mockResolvedValue({
    count: 1,
    results: [{ id: 5, nombre: 'María Gutiérrez', telefono: '1', direccion: '', activo: true }],
  })
})

function enlaceCon(wrapper, texto) {
  return wrapper.findAll('a').find((a) => a.text() === texto)
}

describe('cada nombre que abre un detalle usa la clase común', () => {
  it('Catálogo: el nombre del producto', async () => {
    const wrapper = mount(ProductosView, { global })
    await flushPromises()

    expect(enlaceCon(wrapper, 'Disco SSD').classes()).toContain('enlace-de-tabla')
  })

  it('Clientes: el nombre del cliente', async () => {
    const wrapper = mount(ClientesView, { global })
    await flushPromises()

    expect(enlaceCon(wrapper, 'María Gutiérrez').classes()).toContain('enlace-de-tabla')
  })

  it('Movimientos: el nombre del producto', () => {
    const wrapper = mount(TablaMovimientos, {
      props: {
        conProducto: true,
        total: 1,
        movimientos: [{
          id: 1, producto: 7, producto_nombre: 'Disco SSD', tipo: 'ALTA', tipo_display: 'Alta',
          cantidad: 3, stock_resultante: 3, usuario_nombre: 'Ana', venta: null, motivo: '', fecha_hora: '2026-10-10T10:00:00-04:00',
        }],
      },
      global,
    })

    expect(enlaceCon(wrapper, 'Disco SSD').classes()).toContain('enlace-de-tabla')
  })
})

describe('la regla de estilo', () => {
  const css = readFileSync(resolve(__dirname, '../assets/main.css'), 'utf8')
  const bloque = (selector) => {
    const inicio = css.indexOf(selector)
    expect(inicio, `falta la regla ${selector}`).toBeGreaterThan(-1)
    return css.slice(inicio, css.indexOf('}', inicio))
  }

  it('hereda el color del texto, sin subrayado, también visitado, con cursor de mano', () => {
    const regla = bloque('.enlace-de-tabla,')
    expect(regla).toContain('.enlace-de-tabla:visited')
    expect(regla).toMatch(/color:\s*inherit/)
    expect(regla).toMatch(/text-decoration:\s*none/)
    expect(regla).toMatch(/cursor:\s*pointer/)
  })

  it('conserva y marca el foco de teclado: nunca outline: none', () => {
    expect(bloque('.enlace-de-tabla:focus-visible')).toMatch(/outline:\s*2px solid/)
    const todas = css.split('.enlace-de-tabla').slice(1).map((r) => r.slice(0, r.indexOf('}')))
    expect(todas.some((r) => /outline:\s*(none|0)\b/.test(r))).toBe(false)
  })
})
