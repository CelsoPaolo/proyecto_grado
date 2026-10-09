/**
 * T-11.5 — Pantallas de clientes (RF-84 a RF-89, RNF-14).
 *
 * El carnet solo aparece en el detalle; desactivar y reactivar piden
 * confirmación y solo los ve el Administrador.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clientesApi } from '../api/clientes'
import { localeEs } from '../locale/es'
import { menuPara, puedeEntrar, rutas } from '../router'
import ClienteDetalleView from '../views/clientes/ClienteDetalleView.vue'
import ClientesView from '../views/clientes/ClientesView.vue'
import FormularioCliente from '../views/clientes/FormularioCliente.vue'

const requerir = vi.fn()
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: requerir }) }))

vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRoute: () => ({ params: { id: 5 }, query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('../api/clientes', () => ({
  clientesApi: {
    listar: vi.fn(),
    obtener: vi.fn(),
    crear: vi.fn(),
    actualizar: vi.fn(),
    desactivar: vi.fn(),
    reactivar: vi.fn(),
  },
}))

const DETALLE = {
  id: 5,
  nombre: 'María Gutiérrez',
  telefono: '70012345',
  direccion: 'Calle Junín 123',
  carnet: '1234567-1A',
  activo: true,
  creado_por: 'Víctor',
  creado_en: '2026-10-09T10:00:00-04:00',
  actualizado_por: 'Víctor',
  actualizado_en: '2026-10-09T10:00:00-04:00',
}

const plugins = (rol) => [
  createTestingPinia({
    createSpy: vi.fn,
    stubActions: false,
    initialState: { auth: { usuario: { id: 1, rol } } },
  }),
  [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
  ToastService,
]

const STUBS = {
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
  Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /></div>' },
}

function montar(componente, rol = 'VENTAS') {
  return mount(componente, { global: { plugins: plugins(rol), stubs: STUBS } })
}

beforeEach(() => {
  vi.clearAllMocks()
  window.matchMedia ??= () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} })
  clientesApi.listar.mockResolvedValue({
    count: 1,
    results: [{ id: 5, nombre: 'María Gutiérrez', telefono: '70012345', direccion: '', activo: true }],
  })
  clientesApi.obtener.mockResolvedValue({ ...DETALLE })
})

describe('carnet solo en el detalle (RN-CLI-06)', () => {
  it('la lista no tiene columna ni dato de carnet', async () => {
    const wrapper = montar(ClientesView)
    await flushPromises()

    expect(wrapper.text()).toContain('María Gutiérrez')
    expect(wrapper.findAll('th').map((th) => th.text())).not.toContain('Carnet de identidad')
    expect(wrapper.text()).not.toMatch(/carnet de identidad/i)
  })

  it('el detalle sí muestra el carnet', async () => {
    const wrapper = montar(ClienteDetalleView)
    await flushPromises()

    expect(wrapper.find('[data-prueba="carnet"]').text()).toBe('1234567-1A')
  })

  it('la lista pide por defecto los activos y busca con el texto escrito', async () => {
    const wrapper = montar(ClientesView)
    await flushPromises()
    expect(clientesApi.listar).toHaveBeenLastCalledWith({ page: 1, page_size: 20, activo: 'true' })

    await wrapper.find('[data-prueba="buscar"]').setValue(' 1234567-1a ')
    await wrapper.find('[data-prueba="buscar"]').trigger('keyup', { key: 'Enter' })
    expect(clientesApi.listar).toHaveBeenLastCalledWith(
      expect.objectContaining({ buscar: '1234567-1a', page: 1 }),
    )
  })
})

describe('desactivar y reactivar (RN-CLI-07, RNF-14)', () => {
  it('el Encargado de Ventas no ve la acción', async () => {
    const wrapper = montar(ClienteDetalleView, 'VENTAS')
    await flushPromises()

    expect(wrapper.find('[data-prueba="cambiar-estado"]').exists()).toBe(false)
    expect(wrapper.find('[data-prueba="editar"]').exists()).toBe(true)
  })

  it('el Administrador la ve, y pide confirmación antes de llamar a la API', async () => {
    clientesApi.desactivar.mockResolvedValue({ ...DETALLE, activo: false })
    const wrapper = montar(ClienteDetalleView, 'ADMINISTRADOR')
    await flushPromises()

    await wrapper.find('[data-prueba="cambiar-estado"]').trigger('click')
    expect(requerir).toHaveBeenCalledTimes(1)
    expect(clientesApi.desactivar).not.toHaveBeenCalled()

    requerir.mock.calls[0][0].accept()
    await flushPromises()
    expect(clientesApi.desactivar).toHaveBeenCalledWith(5)
    expect(wrapper.find('[data-prueba="estado"]').text()).toBe('Inactivo')
  })

  it('un cliente inactivo ofrece reactivar', async () => {
    clientesApi.obtener.mockResolvedValue({ ...DETALLE, activo: false })
    clientesApi.reactivar.mockResolvedValue({ ...DETALLE, activo: true })
    const wrapper = montar(ClienteDetalleView, 'ADMINISTRADOR')
    await flushPromises()

    await wrapper.find('[data-prueba="cambiar-estado"]').trigger('click')
    requerir.mock.calls[0][0].accept()
    await flushPromises()

    expect(clientesApi.reactivar).toHaveBeenCalledWith(5)
  })
})

describe('formulario', () => {
  async function abrir(cliente = null) {
    const wrapper = mount(FormularioCliente, {
      props: { visible: false, cliente },
      global: { plugins: plugins('VENTAS'), stubs: STUBS },
    })
    await wrapper.setProps({ visible: true })
    return wrapper
  }

  it('registra y emite el cliente creado', async () => {
    clientesApi.crear.mockResolvedValue({ ...DETALLE, id: 9 })
    const wrapper = await abrir()
    await wrapper.find('#cliente-nombre').setValue('María')
    await wrapper.find('#cliente-telefono').setValue('70012345')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(clientesApi.crear).toHaveBeenCalledWith(
      expect.objectContaining({ nombre: 'María', telefono: '70012345' }),
    )
    expect(wrapper.emitted('guardado')[0][0]).toMatchObject({ id: 9 })
  })

  it('muestra el carnet duplicado junto a su campo', async () => {
    clientesApi.crear.mockRejectedValue({
      codigo: 'CARNET_DUPLICADO',
      detalle: 'Ya hay un cliente registrado con ese carnet.',
      errores: { carnet: ['Ya hay un cliente registrado con ese carnet.'] },
    })
    const wrapper = await abrir()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Ya hay un cliente registrado con ese carnet.')
    expect(wrapper.emitted('guardado')).toBeUndefined()
  })

  it('al editar carga los datos, carnet incluido', async () => {
    const wrapper = await abrir(DETALLE)

    expect(wrapper.find('#cliente-carnet').element.value).toBe('1234567-1A')
  })
})

describe('navegación (PA-06)', () => {
  const ruta = (nombre) => rutas.find((r) => r.name === nombre)

  it('Administrador y Ventas tienen «Clientes»; Servicios no entra', () => {
    expect(menuPara('ADMINISTRADOR').map((o) => o.name)).toContain('clientes')
    expect(menuPara('VENTAS').map((o) => o.name)).toContain('clientes')
    expect(menuPara('SERVICIOS').map((o) => o.name)).not.toContain('clientes')
    expect(puedeEntrar(ruta('cliente-detalle'), 'SERVICIOS')).toBe(false)
  })
})
