/**
 * T-1.11 — Pantalla de inicio de sesion (RF-01, RF-02, RF-03).
 *
 * Verifica ademas que PrimeVue y el locale estan correctamente
 * montados sobre una pantalla real del sistema, que es lo que T-0.8
 * comprobaba sobre el andamiaje.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LoginView from '../views/auth/LoginView.vue'
import { localeEs } from '../locale/es'
import { useAuthStore } from '../stores/auth'

const push = vi.fn()

// Mock PARCIAL: el login importa el router real para decidir el destino
// (destinoTrasLogin), y ese modulo necesita createRouter de verdad.
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRouter: () => ({ push }),
  useRoute: () => ({ query: {} }),
}))

function montar() {
  const wrapper = mount(LoginView, {
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn, stubActions: true }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
      ],
      stubs: { RouterLink: true },
    },
  })
  return { wrapper, auth: useAuthStore() }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('pantalla de ingreso', () => {
  it('monta componentes de PrimeVue', () => {
    const { wrapper } = montar()

    expect(wrapper.find('.p-card').exists()).toBe(true)
    expect(wrapper.find('.p-button').exists()).toBe(true)
    expect(wrapper.find('input#username').exists()).toBe(true)
  })

  it('esta en espanol (RNF-13)', () => {
    const { wrapper } = montar()
    const texto = wrapper.text()

    expect(texto).toContain('Usuario')
    expect(texto).toContain('Contraseña')
    expect(texto).toContain('Ingresar')
  })

  it('llama al store con las credenciales escritas', async () => {
    const { wrapper, auth } = montar()

    await wrapper.find('input#username').setValue('jperez')
    await wrapper.find('input#password').setValue('ClaveSegura123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(auth.iniciarSesion).toHaveBeenCalledWith('jperez', 'ClaveSegura123')
  })

  it('muestra el mensaje generico ante credenciales invalidas (RF-02)', async () => {
    const { wrapper, auth } = montar()
    auth.iniciarSesion.mockRejectedValue({
      codigo: 'CREDENCIALES_INVALIDAS',
      detalle: 'Usuario o contraseña incorrectos.',
      errores: null,
    })

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Usuario o contraseña incorrectos.')
  })

  it('distingue visualmente la cuenta bloqueada (RF-03)', async () => {
    /* CU-AUT-01 pide informar el bloqueo, no tratarlo como una
       credencial equivocada: el titular debe saber que su cuenta fue
       inhabilitada y a quien consultar. */
    const { wrapper, auth } = montar()
    auth.iniciarSesion.mockRejectedValue({
      codigo: 'CUENTA_BLOQUEADA',
      detalle: 'Esta cuenta está inhabilitada. Consulte al administrador.',
      errores: null,
    })

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('inhabilitada')
    expect(wrapper.find('.p-message-warn').exists()).toBe(true)
  })

  it('muestra los errores de validacion junto a su campo (RNF-15)', async () => {
    const { wrapper, auth } = montar()
    auth.iniciarSesion.mockRejectedValue({
      codigo: 'VALIDACION',
      detalle: 'Revise los datos ingresados.',
      errores: { password: ['Este campo es obligatorio.'] },
    })

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Este campo es obligatorio.')
  })

  // spec.md v1.4.1 (CU-AUT-01): tras ingresar, cada rol va directo a su
  // espacio de trabajo; ya no hay pantalla de inicio.
  it.each([
    ['ADMINISTRADOR', 'panel'],
    ['VENTAS', 'venta-nueva'],
    ['SERVICIOS', 'servicios'],
  ])('tras ingresar, %s va a su espacio de trabajo (%s)', async (rol, destino) => {
    const { wrapper, auth } = montar()
    auth.iniciarSesion.mockImplementation(async () => {
      auth.usuario = { rol }
      return auth.usuario
    })

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(push).toHaveBeenCalledWith({ name: destino })
  })
})
