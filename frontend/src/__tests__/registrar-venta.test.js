/**
 * T-4.9 — Pantalla de registro de venta (RF-15, RF-16, RF-17).
 *
 * Lo que mas importa comprobar aqui es el tratamiento del 422 de
 * stock: es el unico error que debe mostrarse enriquecido, diciendo
 * que falta y cuanto hay, y dejando claro que NADA se descontó.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { productosApi } from '../api/catalogo'
import { ventasApi } from '../api/ventas'
import { localeEs } from '../locale/es'
import RegistrarVentaView from '../views/ventas/RegistrarVentaView.vue'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
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

function montar() {
  return mount(RegistrarVentaView, {
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
      stubs: { RouterLink: true },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  productosApi.listar.mockResolvedValue({
    results: [
      { id: 1, nombre: 'Teclado mecánico', precio: '350.00', stock: 10 },
      { id: 2, nombre: 'Monitor agotado', precio: '1250.00', stock: 0 },
    ],
  })
})

describe('busqueda de productos', () => {
  it('excluye los productos agotados del buscador (RN-CAT-05)', async () => {
    /* Un producto sin existencias no puede venderse. Excluirlo del
       buscador evita que el encargado lo agregue y descubra el
       problema solo al confirmar. */
    const wrapper = montar()
    await wrapper.vm.buscarProductos({ query: 'a' })
    await flushPromises()

    const nombres = wrapper.vm.sugerencias.map((p) => p.nombre)
    expect(nombres).toContain('Teclado mecánico')
    expect(nombres).not.toContain('Monitor agotado')
  })
})

describe('armado de la venta', () => {
  it('agregar dos veces el mismo producto suma la cantidad', async () => {
    /* El servidor agrupa por producto de todos modos, y dos lineas del
       mismo articulo confundirian al encargado. */
    const wrapper = montar()
    const producto = { id: 1, nombre: 'Teclado mecánico', precio: '350.00', stock: 10 }

    wrapper.vm.agregar(producto)
    wrapper.vm.agregar(producto)
    await flushPromises()

    expect(wrapper.vm.lineas).toHaveLength(1)
    expect(wrapper.vm.lineas[0].cantidad).toBe(2)
  })

  it('calcula el total en vivo (RF-16)', async () => {
    const wrapper = montar()
    wrapper.vm.agregar({ id: 1, nombre: 'Teclado', precio: '350.00', stock: 10 })
    wrapper.vm.agregar({ id: 2, nombre: 'Monitor', precio: '750.00', stock: 5 })
    await flushPromises()

    expect(wrapper.vm.total).toBe(1100)
  })

  it('no deja confirmar sin cliente o sin productos', async () => {
    const wrapper = montar()
    expect(wrapper.vm.puedeConfirmar).toBe(false)

    wrapper.vm.agregar({ id: 1, nombre: 'Teclado', precio: '350.00', stock: 10 })
    await flushPromises()
    expect(wrapper.vm.puedeConfirmar).toBe(false) // falta el cliente

    wrapper.vm.clienteNombre = 'María Gutiérrez'
    wrapper.vm.clienteTelefono = '70012345'
    await flushPromises()
    expect(wrapper.vm.puedeConfirmar).toBe(true)
  })
})

describe('confirmacion', () => {
  it('delega el registro en el cliente de API con lo que se armo', async () => {
    /* El recorte de campos que exige RN-VEN-04 ocurre dentro de
       ventasApi.registrar, no aqui; se verifica en
       api-ventas.test.js, que ejercita ese modulo de verdad. */
    ventasApi.registrar.mockResolvedValue({ id: 7, total: '700.00' })
    const wrapper = montar()
    wrapper.vm.agregar({ id: 1, nombre: 'Teclado', precio: '350.00', stock: 10 })
    wrapper.vm.clienteNombre = 'María'
    wrapper.vm.clienteTelefono = '70012345'
    await flushPromises()

    await wrapper.vm.confirmar()

    const enviado = ventasApi.registrar.mock.calls[0][0]
    expect(enviado.clienteNombre).toBe('María')
    expect(enviado.items).toHaveLength(1)
    expect(enviado.items[0].producto_id).toBe(1)
  })

  it('muestra el detalle del 422 diciendo que falta y cuanto hay', async () => {
    /* El criterio central de T-4.9 (RF-17). */
    ventasApi.registrar.mockRejectedValue({
      codigo: 'STOCK_INSUFICIENTE',
      detalle: 'No hay existencias suficientes para confirmar la venta.',
      errores: {
        items: [
          { producto_id: 1, nombre: 'Teclado mecánico', solicitado: 5, disponible: 2 },
        ],
      },
    })
    const wrapper = montar()
    wrapper.vm.agregar({ id: 1, nombre: 'Teclado mecánico', precio: '350.00', stock: 10 })
    wrapper.vm.clienteNombre = 'María'
    wrapper.vm.clienteTelefono = '70012345'
    await flushPromises()

    await wrapper.vm.confirmar()
    await flushPromises()

    const texto = wrapper.text()
    expect(texto).toContain('Teclado mecánico')
    expect(texto).toContain('pidió 5')
    expect(texto).toContain('hay 2 disponibles')
  })

  it('aclara que ningun producto fue descontado (RN-VEN-02)', async () => {
    /* Sin este aviso, el encargado podria creer que la venta quedo a
       medias y revisar el inventario producto por producto. */
    ventasApi.registrar.mockRejectedValue({
      codigo: 'STOCK_INSUFICIENTE',
      detalle: 'No hay existencias suficientes.',
      errores: { items: [{ producto_id: 1, nombre: 'X', solicitado: 5, disponible: 2 }] },
    })
    const wrapper = montar()
    wrapper.vm.agregar({ id: 1, nombre: 'X', precio: '100.00', stock: 10 })
    wrapper.vm.clienteNombre = 'María'
    wrapper.vm.clienteTelefono = '70012345'
    await flushPromises()

    await wrapper.vm.confirmar()
    await flushPromises()

    expect(wrapper.text()).toContain('Ningún producto fue descontado')
  })

  it('la venta no se pierde tras un error de stock', async () => {
    /* El encargado debe poder corregir la cantidad y reintentar, no
       volver a armar la venta desde cero. */
    ventasApi.registrar.mockRejectedValue({
      codigo: 'STOCK_INSUFICIENTE',
      detalle: 'Sin stock',
      errores: { items: [] },
    })
    const wrapper = montar()
    wrapper.vm.agregar({ id: 1, nombre: 'Teclado', precio: '350.00', stock: 10 })
    wrapper.vm.clienteNombre = 'María'
    wrapper.vm.clienteTelefono = '70012345'
    await flushPromises()

    await wrapper.vm.confirmar()
    await flushPromises()

    expect(wrapper.vm.lineas).toHaveLength(1)
    expect(wrapper.vm.clienteNombre).toBe('María')
  })

  it('tras confirmar lleva al detalle de la venta creada', async () => {
    ventasApi.registrar.mockResolvedValue({ id: 42, total: '350.00' })
    const wrapper = montar()
    wrapper.vm.agregar({ id: 1, nombre: 'Teclado', precio: '350.00', stock: 10 })
    wrapper.vm.clienteNombre = 'María'
    wrapper.vm.clienteTelefono = '70012345'
    await flushPromises()

    await wrapper.vm.confirmar()
    await flushPromises()

    expect(push).toHaveBeenCalledWith({
      name: 'venta-detalle',
      params: { id: 42 },
    })
  })
})
