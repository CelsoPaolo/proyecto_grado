/**
 * T-6.3 — Pantalla del panel (RF-48 a RF-51, RF-65, RF-66).
 *
 * El criterio que más importa: el ingreso del día NUNCA se presenta
 * como una cifra sola. RN-IND-05 exige que se distinga siempre cuánto
 * vino de ventas y cuánto de servicios.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { panelApi } from '../api/panel'
import { localeEs } from '../locale/es'
import { menuPara, puedeEntrar, rutas } from '../router'
import PanelView from '../views/panel/PanelView.vue'

vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: {} }),
}))

vi.mock('../api/panel', () => ({
  panelApi: { resumen: vi.fn() },
}))

const RESUMEN = {
  fecha: '2026-09-29',
  ventas_dia: { cantidad: 12, importe: '8450.00' },
  servicios_dia: { cantidad: 5, importe: '1300.00' },
  ingreso_total: {
    importe: '9750.00',
    de_ventas: '8450.00',
    de_servicios: '1300.00',
  },
  servicios_pendientes: {
    total: 9,
    registradas: 4,
    en_atencion: 5,
    sin_cotizar: 3,
  },
  stock_bajo: {
    umbral: 5,
    cantidad: 3,
    productos: [
      { id: 1, nombre: 'Teclado mecánico', stock: 1 },
      { id: 2, nombre: 'Cable HDMI', stock: 4 },
    ],
  },
}

function montar() {
  return mount(PanelView, {
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
    },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  panelApi.resumen.mockResolvedValue(structuredClone(RESUMEN))
})

describe('RN-IND-05 — el ingreso siempre desglosado', () => {
  it('muestra el total junto a sus dos orígenes', async () => {
    const wrapper = montar()
    await flushPromises()
    const texto = wrapper.text()

    expect(texto).toContain('9.750,00')
    expect(texto).toContain('8.450,00')
    expect(texto).toContain('1.300,00')
    expect(texto).toContain('Ventas')
    expect(texto).toContain('Servicios')
  })

  it('indica cuántas ventas y cuántos servicios componen cada cifra', async () => {
    const wrapper = montar()
    await flushPromises()
    const texto = wrapper.text()

    expect(texto).toContain('12 ventas')
    expect(texto).toContain('5 servicios finalizados')
  })

  it('usa el singular cuando corresponde', async () => {
    panelApi.resumen.mockResolvedValue({
      ...structuredClone(RESUMEN),
      ventas_dia: { cantidad: 1, importe: '100.00' },
      servicios_dia: { cantidad: 1, importe: '50.00' },
    })
    const wrapper = montar()
    await flushPromises()
    const texto = wrapper.text()

    expect(texto).toContain('1 venta')
    expect(texto).toContain('1 servicio finalizado')
  })

  it('con cero ingresos lo dice en palabras, no solo con un Bs 0,00', async () => {
    panelApi.resumen.mockResolvedValue({
      ...structuredClone(RESUMEN),
      ventas_dia: { cantidad: 0, importe: '0.00' },
      servicios_dia: { cantidad: 0, importe: '0.00' },
      ingreso_total: { importe: '0.00', de_ventas: '0.00', de_servicios: '0.00' },
    })
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('Aún no se registraron ingresos hoy')
  })
})

describe('RF-49 — servicios pendientes', () => {
  it('muestra el total y su desglose', async () => {
    const wrapper = montar()
    await flushPromises()
    const texto = wrapper.text()

    expect(texto).toContain('Servicios pendientes')
    expect(texto).toContain('Sin cotizar')
  })

  it('ofrece ir a cotizar cuando hay pendientes', async () => {
    /* Lo que espera al Administrador: sin cotizar no pueden cerrarse
       (RN-SER-13), así que el panel le da el atajo. */
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('Cotizar pendientes')
  })

  it('no ofrece el atajo si no hay nada sin cotizar', async () => {
    panelApi.resumen.mockResolvedValue({
      ...structuredClone(RESUMEN),
      servicios_pendientes: {
        total: 2,
        registradas: 1,
        en_atencion: 1,
        sin_cotizar: 0,
      },
    })
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Cotizar pendientes')
  })
})

describe('RF-50 — existencias bajas', () => {
  it('explica el umbral en lugar de mostrar un número sin criterio', async () => {
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('5 unidades o menos')
  })

  it('lista los productos más urgentes', async () => {
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('Teclado mecánico')
    expect(wrapper.text()).toContain('Cable HDMI')
  })

  it('avisa de que la lista está recortada', async () => {
    /* El panel resume; el catálogo tiene la lista completa. Sin este
       aviso, el administrador creería que hay 2 productos escasos
       cuando hay 3. */
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('Se muestran 2 de 3')
  })

  it('no avisa cuando la lista está completa', async () => {
    panelApi.resumen.mockResolvedValue({
      ...structuredClone(RESUMEN),
      stock_bajo: {
        umbral: 5,
        cantidad: 2,
        productos: RESUMEN.stock_bajo.productos,
      },
    })
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Se muestran')
  })

  it('con el inventario sano lo dice', async () => {
    panelApi.resumen.mockResolvedValue({
      ...structuredClone(RESUMEN),
      stock_bajo: { umbral: 5, cantidad: 0, productos: [] },
    })
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.text()).toContain('Ningún producto está por debajo del umbral')
  })
})

describe('RF-51 — acceso al módulo desde cada indicador', () => {
  it('una sola llamada trae todos los indicadores', async () => {
    /* Cinco llamadas harían que las cifras aparecieran a destiempo. */
    montar()
    await flushPromises()

    expect(panelApi.resumen).toHaveBeenCalledTimes(1)
  })
})

describe('acceso al panel', () => {
  const ruta = (nombre) => rutas.find((r) => r.name === nombre)

  it('solo el Administrador entra', () => {
    expect(puedeEntrar(ruta('panel'), 'ADMINISTRADOR')).toBe(true)
    expect(puedeEntrar(ruta('panel'), 'VENTAS')).toBe(false)
    expect(puedeEntrar(ruta('panel'), 'SERVICIOS')).toBe(false)
  })

  it('aparece en el menú del Administrador y en ningún otro', () => {
    expect(menuPara('ADMINISTRADOR').map((o) => o.name)).toContain('panel')
    expect(menuPara('VENTAS').map((o) => o.name)).not.toContain('panel')
    expect(menuPara('SERVICIOS').map((o) => o.name)).not.toContain('panel')
  })
})
