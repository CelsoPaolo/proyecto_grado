/**
 * T-3.3 — Pantalla de configuracion del umbral (RF-52).
 *
 * Sustituye la comprobacion visual que no pudo hacerse en esta sesion
 * porque la extension del navegador se desconecto, y ademas queda
 * permanente: una prueba se ejecuta en cada cambio, un vistazo no.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { configuracionApi } from '../api/configuracion'
import { localeEs } from '../locale/es'
import ConfiguracionView from '../views/configuracion/ConfiguracionView.vue'

vi.mock('../api/configuracion', () => ({
  configuracionApi: {
    obtener: vi.fn(),
    actualizarUmbral: vi.fn(),
  },
}))

function montar() {
  return mount(ConfiguracionView, {
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  configuracionApi.obtener.mockResolvedValue({
    umbral_stock_bajo: 5,
    actualizado_por_nombre: 'Carlos Vargas',
    actualizado_en: '2026-09-28T10:00:00-04:00',
  })
})

describe('pantalla de configuracion', () => {
  it('carga y muestra el umbral vigente', async () => {
    const wrapper = montar()
    await flushPromises()

    expect(configuracionApi.obtener).toHaveBeenCalled()
    expect(wrapper.find('input#umbral').element.value).toContain('5')
  })

  it('muestra quien hizo la ultima modificacion (RN-CAT-07)', async () => {
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('Carlos Vargas')
  })

  it('explica el efecto del valor en lugar de mostrar un numero suelto', async () => {
    /* Un umbral sin explicacion no dice nada: el Administrador
       necesita saber que decide cuando el sistema avisa. */
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('5 unidades o menos')
  })

  it('el umbral cero se explica como avisar solo de lo agotado', async () => {
    configuracionApi.obtener.mockResolvedValue({
      umbral_stock_bajo: 0,
      actualizado_por_nombre: null,
      actualizado_en: null,
    })
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('agotado por completo')
  })

  it('aclara que cambiar el umbral no altera existencias ni precios', async () => {
    /* RN-CAT-07: el umbral decide como se MUESTRA el catálogo. Sin
       este aviso, un administrador podría temer que tocarlo afecte al
       inventario y no se atrevería a usarlo. */
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('No modifica ninguna existencia')
  })

  it('el boton de guardar esta desactivado si no hay cambios', async () => {
    const wrapper = montar()
    await flushPromises()

    const boton = wrapper.find('button[type="submit"]')
    expect(boton.attributes('disabled')).toBeDefined()
  })

  it('muestra el error del servidor junto al campo (RNF-15)', async () => {
    configuracionApi.actualizarUmbral.mockRejectedValue({
      codigo: 'VALIDACION',
      detalle: 'Revise los datos ingresados.',
      errores: { umbral_stock_bajo: ['El umbral no puede ser negativo.'] },
    })
    const wrapper = montar()
    await flushPromises()

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('El umbral no puede ser negativo.')
  })
})
