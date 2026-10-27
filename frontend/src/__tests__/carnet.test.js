/**
 * T-15.9 — Carnet obligatorio de 7 u 8 dígitos en la interfaz (RF-101).
 *
 * El campo no deja escribir más de 8 dígitos ni nada que no sea un
 * dígito, y el formulario avisa —sin enviar— si el carnet falta o tiene
 * menos de 7.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clientesApi } from '../api/clientes'
import { localeEs } from '../locale/es'
import { MENSAJE_CARNET, carnetValido, soloDigitosDeCarnet } from '../utils/carnet'
import FormularioCliente from '../views/clientes/FormularioCliente.vue'

vi.mock('../api/clientes', () => ({
  clientesApi: { crear: vi.fn(), actualizar: vi.fn() },
}))

async function abrir() {
  const wrapper = mount(FormularioCliente, {
    props: { visible: false },
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
      stubs: { Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /></div>' } },
    },
  })
  await wrapper.setProps({ visible: true })
  await wrapper.find('#cliente-nombre').setValue('Ana')
  await wrapper.find('#cliente-telefono').setValue('70012345')
  return wrapper
}

beforeEach(() => vi.clearAllMocks())

describe('la regla, igual que en el servidor', () => {
  it('7 u 8 dígitos son válidos; 6, 9, letras, complemento o vacío no', () => {
    expect(carnetValido('1234567')).toBe(true)
    expect(carnetValido('12345678')).toBe(true)
    for (const valor of ['123456', '123456789', '1234567-1A', '1234567a', '', null]) {
      expect(carnetValido(valor)).toBe(false)
    }
  })

  it('al escribir quedan solo dígitos, como máximo 8', () => {
    expect(soloDigitosDeCarnet('1234567-1A')).toBe('12345671')
    expect(soloDigitosDeCarnet('1234567890')).toBe('12345678')
  })
})

describe('el campo del carnet', () => {
  it('no deja escribir más de 8 dígitos', async () => {
    const wrapper = await abrir()
    const campo = wrapper.find('#cliente-carnet')

    await campo.setValue('1234567890123456')

    expect(campo.element.value).toBe('12345678')
    expect(campo.attributes('maxlength')).toBe('8')
  })

  it('descarta letras y guiones del complemento', async () => {
    const wrapper = await abrir()
    const campo = wrapper.find('#cliente-carnet')

    await campo.setValue('765-43 21LP')

    expect(campo.element.value).toBe('7654321')
  })

  it('ya no dice «opcional»', async () => {
    const wrapper = await abrir()

    expect(wrapper.find('label[for="cliente-carnet"]').text()).not.toContain('opcional')
  })
})

describe('al registrar', () => {
  it.each([
    ['vacío', ''],
    ['con 6 dígitos', '123456'],
  ])('un carnet %s avisa junto al campo y no se envía', async (_, carnet) => {
    const wrapper = await abrir()
    await wrapper.find('#cliente-carnet').setValue(carnet)

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(clientesApi.crear).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain(MENSAJE_CARNET)
  })

  it.each(['1234567', '12345678'])('con %s se envía', async (carnet) => {
    clientesApi.crear.mockResolvedValue({ id: 9 })
    const wrapper = await abrir()
    await wrapper.find('#cliente-carnet').setValue(carnet)

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(clientesApi.crear).toHaveBeenCalledWith(expect.objectContaining({ carnet }))
  })

  it('avisa del teléfono y del carnet a la vez', async () => {
    const wrapper = await abrir()
    await wrapper.find('#cliente-telefono').setValue('7001')
    await wrapper.find('#cliente-carnet').setValue('123')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain(MENSAJE_CARNET)
    expect(wrapper.text()).toContain('El teléfono debe tener exactamente 8 dígitos')
  })
})
