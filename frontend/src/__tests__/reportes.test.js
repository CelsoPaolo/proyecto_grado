/**
 * T-12.8 — Pantalla de reportes (RF-90 a RF-96).
 *
 * «Esta semana» empieza el lunes y «este mes» el día 1 (RN-REP-01); las
 * exportaciones se descargan con el cuadro de guardado; un rango sin
 * actividad muestra ceros con aviso.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { reportesApi } from '../api/reportes'
import { localeEs } from '../locale/es'
import { menuPara } from '../router'
import { rangoEsteMes, rangoEstaSemana, rangoHoy } from '../utils/rangos'
import ReportesView from '../views/reportes/ReportesView.vue'

vi.mock('../api/reportes', async () => ({
  ...(await vi.importActual('../api/reportes')),
  reportesApi: { obtener: vi.fn(), pdf: vi.fn(), xlsx: vi.fn() },
}))

const REPORTE = {
  desde: '2026-10-01',
  hasta: '2026-10-09',
  ventas: { cantidad: 2, importe: '1127.25' },
  servicios: { cantidad: 1, importe: '120.00' },
  ingreso_total: { importe: '1247.25', de_ventas: '1127.25', de_servicios: '120.00' },
  productos_mas_vendidos: [
    { producto_id: 1, codigo: '2000000000015', nombre: 'Teclado mecánico', unidades: 2, importe: '701.00' },
  ],
  ventas_por_usuario: [{ usuario_id: 4, nombre_completo: 'Juan Pérez', cantidad: 2, importe: '1127.25' }],
  servicios_por_estado: { REGISTRADA: 1, EN_ATENCION: 0, FINALIZADA: 1, CANCELADA: 1 },
}

const VACIO = {
  ...REPORTE,
  ventas: { cantidad: 0, importe: '0.00' },
  servicios: { cantidad: 0, importe: '0.00' },
  ingreso_total: { importe: '0.00', de_ventas: '0.00', de_servicios: '0.00' },
  productos_mas_vendidos: [],
  ventas_por_usuario: [],
  servicios_por_estado: { REGISTRADA: 0, EN_ATENCION: 0, FINALIZADA: 0, CANCELADA: 0 },
}

function montar() {
  return mount(ReportesView, {
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
  window.matchMedia ??= () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} })
  reportesApi.obtener.mockResolvedValue({ ...REPORTE })
  delete window.showSaveFilePicker
})

describe('atajos (RN-REP-01)', () => {
  // Jueves 9 de octubre de 2026.
  const jueves = new Date(2026, 9, 9, 15, 30)

  it('«hoy» es el día en curso', () => {
    expect(rangoHoy(jueves)).toEqual({ desde: '2026-10-09', hasta: '2026-10-09' })
  })

  it('«esta semana» empieza el lunes', () => {
    expect(rangoEstaSemana(jueves)).toEqual({ desde: '2026-10-05', hasta: '2026-10-09' })
  })

  it('un domingo pertenece a la semana que empezó el lunes anterior', () => {
    expect(rangoEstaSemana(new Date(2026, 9, 11))).toEqual({ desde: '2026-10-05', hasta: '2026-10-11' })
  })

  it('un lunes es su propio inicio de semana', () => {
    expect(rangoEstaSemana(new Date(2026, 9, 5))).toEqual({ desde: '2026-10-05', hasta: '2026-10-05' })
  })

  it('«este mes» empieza el día 1, también cruzando a otro mes', () => {
    expect(rangoEsteMes(jueves)).toEqual({ desde: '2026-10-01', hasta: '2026-10-09' })
    expect(rangoEstaSemana(new Date(2026, 9, 2))).toEqual({ desde: '2026-09-28', hasta: '2026-10-02' })
  })
})

describe('pantalla', () => {
  it('al abrir pide el reporte de este mes y muestra el ingreso desglosado', async () => {
    const wrapper = montar()
    await flushPromises()

    expect(reportesApi.obtener).toHaveBeenCalledWith(rangoEsteMes(new Date()))
    expect(wrapper.find('[data-prueba="ingreso"]').text()).toContain('1.247,25')
    expect(wrapper.text()).toContain('Teclado mecánico')
    expect(wrapper.text()).toContain('Juan Pérez')
    expect(wrapper.text()).toContain('Cancelada')
  })

  it('un rango sin actividad muestra ceros con aviso', async () => {
    reportesApi.obtener.mockResolvedValue({ ...VACIO })
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.find('[data-prueba="sin-actividad"]').exists()).toBe(true)
    expect(wrapper.find('[data-prueba="ventas-importe"]').text()).toContain('0,00')
  })

  it('con actividad no muestra el aviso', async () => {
    const wrapper = montar()
    await flushPromises()

    expect(wrapper.find('[data-prueba="sin-actividad"]').exists()).toBe(false)
  })

  it('un rango a mano pide esas fechas y quita el atajo', async () => {
    const wrapper = montar()
    await flushPromises()

    wrapper.vm.atajo = null
    wrapper.vm.fechas = [new Date(2026, 8, 1), new Date(2026, 8, 30)]
    await wrapper.vm.consultar()

    expect(reportesApi.obtener).toHaveBeenLastCalledWith({ desde: '2026-09-01', hasta: '2026-09-30' })
  })
})

describe('exportar (RF-95, RF-96)', () => {
  function cuadroDeGuardado() {
    const escribir = { write: vi.fn(), close: vi.fn() }
    window.showSaveFilePicker = vi.fn(() => Promise.resolve({ createWritable: () => Promise.resolve(escribir) }))
    return escribir
  }

  it('el PDF se descarga con el cuadro de guardado y el rango en el nombre', async () => {
    reportesApi.pdf.mockResolvedValue(new Blob(['%PDF']))
    const escribir = cuadroDeGuardado()
    const wrapper = montar()
    await flushPromises()

    await wrapper.find('[data-prueba="exportar-pdf"]').trigger('click')
    await flushPromises()

    expect(reportesApi.pdf).toHaveBeenCalledWith({ desde: '2026-10-01', hasta: '2026-10-09' })
    expect(window.showSaveFilePicker.mock.calls[0][0].suggestedName).toBe('reporte-2026-10-01_2026-10-09.pdf')
    expect(escribir.write).toHaveBeenCalled()
  })

  it('el Excel se propone como .xlsx', async () => {
    reportesApi.xlsx.mockResolvedValue(new Blob(['PK']))
    cuadroDeGuardado()
    const wrapper = montar()
    await flushPromises()

    await wrapper.find('[data-prueba="exportar-xlsx"]').trigger('click')
    await flushPromises()

    const opciones = window.showSaveFilePicker.mock.calls[0][0]
    expect(opciones.suggestedName).toBe('reporte-2026-10-01_2026-10-09.xlsx')
    expect(Object.values(opciones.types[0].accept)[0]).toEqual(['.xlsx'])
  })
})

describe('navegación (RN-REP-10)', () => {
  it('solo el Administrador tiene «Reportes»', () => {
    expect(menuPara('ADMINISTRADOR').map((o) => o.name)).toContain('reportes')
    expect(menuPara('VENTAS').map((o) => o.name)).not.toContain('reportes')
    expect(menuPara('SERVICIOS').map((o) => o.name)).not.toContain('reportes')
  })
})
