/**
 * T-15.4 — Teléfono de 8 dígitos en la interfaz (RF-100, RF-15, RNF-15).
 *
 * Los tres formularios que piden un teléfono avisan antes de enviar uno
 * inválido, y el campo solo admite dígitos, como máximo 8. En la venta,
 * el teléfono del cliente ocasional es opcional (PA-09).
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clientesApi } from '../api/clientes'
import { serviciosApi } from '../api/servicios'
import { ventasApi } from '../api/ventas'
import { localeEs } from '../locale/es'
import { MENSAJE_TELEFONO, soloDigitosDeTelefono, telefonoValido } from '../utils/telefono'
import FormularioCliente from '../views/clientes/FormularioCliente.vue'
import RegistrarServicioView from '../views/servicios/RegistrarServicioView.vue'
import RegistrarVentaView from '../views/ventas/RegistrarVentaView.vue'

vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRoute: () => ({ params: {}, query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('../api/clientes', () => ({
  clientesApi: { listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn() },
}))

vi.mock('../api/ventas', () => ({
  ventasApi: { registrar: vi.fn() },
}))

vi.mock('../api/servicios', async (importOriginal) => ({
  ...(await importOriginal()),
  serviciosApi: { registrar: vi.fn() },
}))

vi.mock('../api/catalogo', () => ({
  productosApi: { listar: vi.fn() },
  categoriasApi: { listar: vi.fn() },
}))

function montar(componente, props = {}) {
  return mount(componente, {
    props,
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
      stubs: {
        RouterLink: true,
        Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /></div>' },
      },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  window.matchMedia ??= () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} })
})

describe('la regla, igual que en el servidor', () => {
  it('8 dígitos es válido; 7, 9, letras o vacío no', () => {
    expect(telefonoValido('70012345')).toBe(true)
    for (const valor of ['7001234', '700123456', '7001234a', '7001 2345', '', null]) {
      expect(telefonoValido(valor)).toBe(false)
    }
  })

  it('al escribir quedan solo dígitos, como máximo 8', () => {
    expect(soloDigitosDeTelefono('700-123 45abc')).toBe('70012345')
    expect(soloDigitosDeTelefono('7001234599')).toBe('70012345')
  })
})

describe('registro de cliente', () => {
  async function abrir() {
    const wrapper = montar(FormularioCliente, { visible: false })
    await wrapper.setProps({ visible: true })
    return wrapper
  }

  it('el campo filtra lo que no son dígitos y limita a 8', async () => {
    const wrapper = await abrir()
    const campo = wrapper.find('#cliente-telefono')

    await campo.setValue('7a0b0-1234599')

    expect(campo.element.value).toBe('70012345')
    expect(campo.attributes('maxlength')).toBe('8')
  })

  it('un teléfono de 7 dígitos avisa junto al campo y no se envía', async () => {
    const wrapper = await abrir()
    await wrapper.find('#cliente-nombre').setValue('Ana')
    await wrapper.find('#cliente-telefono').setValue('7001234')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(clientesApi.crear).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(MENSAJE_TELEFONO)
  })

  it('con 8 dígitos se envía', async () => {
    clientesApi.crear.mockResolvedValue({ id: 9, nombre: 'Ana', telefono: '70012345' })
    const wrapper = await abrir()
    await wrapper.find('#cliente-nombre').setValue('Ana')
    await wrapper.find('#cliente-telefono').setValue('70012345')
    await wrapper.find('#cliente-carnet').setValue('1234567')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(clientesApi.crear).toHaveBeenCalledWith(expect.objectContaining({ telefono: '70012345' }))
  })

  it('un cliente anterior con teléfono fuera de formato se muestra tal cual, para corregirlo', async () => {
    const wrapper = montar(FormularioCliente, { visible: false, cliente: null })
    await wrapper.setProps({
      cliente: { id: 3, nombre: 'Wilson', telefono: '563563463', direccion: '', carnet: '' },
      visible: true,
    })

    expect(wrapper.find('#cliente-telefono').element.value).toBe('563563463')
  })
})

describe('cliente ocasional de la venta (PA-09)', () => {
  const LINEA = { producto_id: 1, nombre: 'Teclado', precio: '350.00', cantidad: 1, stock: 5 }

  it('basta el nombre: se puede confirmar sin teléfono', async () => {
    ventasApi.registrar.mockResolvedValue({ id: 20, total: '350.00' })
    const wrapper = montar(RegistrarVentaView)
    wrapper.vm.lineas = [LINEA]
    wrapper.vm.clienteNombre = 'Ocasional'
    await flushPromises()

    expect(wrapper.vm.puedeConfirmar).toBe(true)
    await wrapper.vm.confirmar()

    expect(ventasApi.registrar).toHaveBeenCalledWith(expect.objectContaining({ clienteTelefono: '' }))
  })

  it('si se escribe el teléfono, con menos de 8 dígitos avisa y no se envía', async () => {
    const wrapper = montar(RegistrarVentaView)
    wrapper.vm.lineas = [LINEA]
    wrapper.vm.clienteNombre = 'Ocasional'
    wrapper.vm.clienteTelefono = '7001234'

    await wrapper.vm.confirmar()
    await flushPromises()

    expect(ventasApi.registrar).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(MENSAJE_TELEFONO)
  })

  it('el campo dice que es opcional y filtra lo que no son dígitos', async () => {
    const wrapper = montar(RegistrarVentaView)
    const campo = wrapper.find('#telefono')

    await campo.setValue('7001-2345')

    expect(campo.element.value).toBe('70012345')
    expect(wrapper.find('label[for="telefono"]').text()).toContain('opcional')
  })
})

describe('registro de servicio (RN-SER-05)', () => {
  function rellenar(wrapper, telefono) {
    wrapper.vm.formulario.clienteNombre = 'Ana'
    wrapper.vm.formulario.clienteTelefono = telefono
    wrapper.vm.formulario.tipo = 'MANTENIMIENTO'
    wrapper.vm.formulario.descripcion = 'No enciende.'
  }

  it('un teléfono de 9 dígitos avisa y no se envía', async () => {
    const wrapper = montar(RegistrarServicioView)
    rellenar(wrapper, '700123456')

    await wrapper.vm.guardar()
    await flushPromises()

    expect(serviciosApi.registrar).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(MENSAJE_TELEFONO)
  })

  it('con 8 dígitos se envía', async () => {
    serviciosApi.registrar.mockResolvedValue({ id: 11 })
    const wrapper = montar(RegistrarServicioView)
    rellenar(wrapper, '70012345')

    await wrapper.vm.guardar()

    expect(serviciosApi.registrar).toHaveBeenCalledWith(
      expect.objectContaining({ clienteTelefono: '70012345' }),
    )
  })
})
