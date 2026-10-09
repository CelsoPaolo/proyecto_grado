/**
 * T-11.6 — Selector de cliente en el registro de venta (RF-79, RNF-16).
 *
 * Tres caminos: elegir un cliente registrado, registrar uno nuevo sin
 * salir de la venta, o escribir un cliente ocasional como en la v1.3
 * (ese ya lo cubre registrar-venta.test.js, que no cambió).
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clientesApi } from '../api/clientes'
import http from '../api/http'
import { ventasApi } from '../api/ventas'
import { localeEs } from '../locale/es'
import RegistrarVentaView from '../views/ventas/RegistrarVentaView.vue'
import FormularioCliente from '../views/clientes/FormularioCliente.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: {} }),
  RouterLink: { template: '<a><slot /></a>' },
}))

vi.mock('../api/ventas', async () => ({
  ...(await vi.importActual('../api/ventas')),
  ventasApi: { registrar: vi.fn(), listar: vi.fn(), obtener: vi.fn(), anular: vi.fn() },
}))
vi.mock('../api/catalogo', () => ({ productosApi: { listar: vi.fn() }, categoriasApi: { listar: vi.fn() } }))
vi.mock('../api/clientes', () => ({ clientesApi: { listar: vi.fn(), crear: vi.fn() } }))

const MARIA = { id: 5, nombre: 'María Gutiérrez', telefono: '70012345', direccion: '', activo: true }

function montar() {
  return mount(RegistrarVentaView, {
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
      stubs: { RouterLink: true, Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /></div>' } },
    },
  })
}

async function conProducto(wrapper) {
  wrapper.vm.agregar({ id: 1, nombre: 'Teclado', precio: '350.00', stock: 10 })
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  window.matchMedia ??= () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} })
  clientesApi.listar.mockResolvedValue({ results: [MARIA] })
  ventasApi.registrar.mockResolvedValue({ id: 42, total: '350.00' })
})

describe('cliente registrado', () => {
  it('solo se buscan clientes activos', async () => {
    const wrapper = montar()

    await wrapper.vm.buscarClientes({ query: 'mar' })

    expect(clientesApi.listar).toHaveBeenCalledWith({ buscar: 'mar', activo: 'true', page_size: 10 })
  })

  it('elegir un cliente rellena sus datos y la venta se envía con su id', async () => {
    const wrapper = montar()
    await conProducto(wrapper)
    wrapper.vm.modoCliente = 'registrado'
    wrapper.vm.clienteElegido = MARIA
    await flushPromises()

    expect(wrapper.find('[data-prueba="cliente-elegido"]').text()).toContain('María Gutiérrez')
    expect(wrapper.vm.puedeConfirmar).toBe(true)

    await wrapper.vm.confirmar()
    expect(ventasApi.registrar.mock.calls[0][0]).toMatchObject({ clienteId: 5 })
  })

  it('en modo registrado no deja confirmar sin elegir uno', async () => {
    const wrapper = montar()
    await conProducto(wrapper)
    wrapper.vm.modoCliente = 'registrado'
    wrapper.vm.clienteNombre = 'Escrito a mano'
    wrapper.vm.clienteTelefono = '70000000'
    await flushPromises()

    expect(wrapper.vm.puedeConfirmar).toBe(false)
  })

  it('registrar uno nuevo desde la venta lo deja elegido', async () => {
    const wrapper = montar()
    await wrapper.find('[data-prueba="modo-cliente"]').findAll('button').at(1).trigger('click')
    await wrapper.find('[data-prueba="nuevo-cliente"]').trigger('click')
    await flushPromises()

    wrapper.findComponent(FormularioCliente).vm.$emit('guardado', { ...MARIA, id: 9, nombre: 'Nuevo' })
    await flushPromises()

    expect(wrapper.vm.modoCliente).toBe('registrado')
    expect(wrapper.vm.clienteElegido).toMatchObject({ id: 9 })
  })
})

describe('cuerpo de la petición', () => {
  it('con cliente registrado solo viaja su id; sin él, nombre y teléfono', async () => {
    const real = (await vi.importActual('../api/ventas')).ventasApi
    const post = vi.spyOn(http, 'post').mockResolvedValue({ data: {} })
    const items = [{ producto_id: 1, cantidad: 2 }]

    await real.registrar({ clienteId: 5, clienteNombre: 'X', clienteTelefono: 'Y', items })
    await real.registrar({ clienteNombre: 'Ocasional', clienteTelefono: '70000000', items })

    expect(post.mock.calls[0][1]).toEqual({ cliente_id: 5, items })
    expect(post.mock.calls[1][1]).toEqual({
      cliente_nombre: 'Ocasional',
      cliente_telefono: '70000000',
      items,
    })
    post.mockRestore()
  })
})
