/**
 * T-10.6 — Garantía en la interfaz (RF-77, RN-VEN-14).
 *
 * El botón aparece solo en ventas confirmadas con alguna línea con
 * garantía; recién confirmada, además se ofrece emitirla; la descarga
 * usa el cuadro de guardado de useDescarga.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { tieneGarantia, ventasApi } from '../api/ventas'
import { localeEs } from '../locale/es'
import VentaDetalleView from '../views/ventas/VentaDetalleView.vue'

let query = {}
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRoute: () => ({ params: { id: 42 }, query }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('../api/ventas', async () => ({
  ...(await vi.importActual('../api/ventas')),
  ventasApi: { obtener: vi.fn(), anular: vi.fn(), garantiaPdf: vi.fn() },
}))

const VENTA = {
  id: 42,
  estado: 'CONFIRMADA',
  estado_display: 'Confirmada',
  fecha_hora: '2026-10-09T15:00:00-04:00',
  cliente_nombre: 'María',
  cliente_telefono: '70012345',
  usuario: { nombre_completo: 'Víctor' },
  total: '700.00',
  items: [
    { producto_id: 1, producto_nombre: 'Disco', precio_unitario: '350.00', cantidad: 2, meses_garantia: 12, subtotal: '700.00' },
  ],
}
const SIN = { ...VENTA, items: [{ ...VENTA.items[0], meses_garantia: 0 }] }

function montar() {
  return mount(VentaDetalleView, {
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
      stubs: { RouterLink: { template: '<a><slot /></a>' }, Dialog: true },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  query = {}
  delete window.showSaveFilePicker
})

describe('cuándo hay garantía (RN-VEN-14)', () => {
  it('solo confirmada y con alguna línea con meses', () => {
    expect(tieneGarantia(VENTA)).toBe(true)
    expect(tieneGarantia(SIN)).toBe(false)
    expect(tieneGarantia({ ...VENTA, estado: 'ANULADA' })).toBe(false)
    expect(tieneGarantia(null)).toBe(false)
  })
})

describe('detalle de venta', () => {
  it.each([
    ['con garantía', VENTA, true],
    ['sin garantía', SIN, false],
    ['anulada', { ...VENTA, estado: 'ANULADA', estado_display: 'Anulada' }, false],
  ])('%s: botón visible = %s', async (_, venta, visible) => {
    ventasApi.obtener.mockResolvedValue(venta)
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.find('[data-prueba="garantia"]').exists()).toBe(visible)
  })

  it('recién confirmada ofrece emitirla; desde el historial, no', async () => {
    ventasApi.obtener.mockResolvedValue(VENTA)
    query = { recien: '1' }
    const recien = montar()
    await flushPromises()
    expect(recien.find('[data-prueba="ofrecer-garantia"]').exists()).toBe(true)

    query = {}
    const historial = montar()
    await flushPromises()
    expect(historial.find('[data-prueba="ofrecer-garantia"]').exists()).toBe(false)
  })

  it('descarga con el cuadro de guardado y el nombre propuesto', async () => {
    ventasApi.obtener.mockResolvedValue(VENTA)
    ventasApi.garantiaPdf.mockResolvedValue(new Blob(['%PDF'], { type: 'application/pdf' }))
    const escribir = { write: vi.fn(), close: vi.fn() }
    window.showSaveFilePicker = vi.fn(() => Promise.resolve({ createWritable: () => Promise.resolve(escribir) }))
    const wrapper = montar()
    await flushPromises()

    await wrapper.find('[data-prueba="garantia"]').trigger('click')
    await flushPromises()

    expect(ventasApi.garantiaPdf).toHaveBeenCalledWith(42)
    expect(window.showSaveFilePicker.mock.calls[0][0].suggestedName).toBe('garantia-venta-42.pdf')
    expect(escribir.write).toHaveBeenCalled()
  })
})
