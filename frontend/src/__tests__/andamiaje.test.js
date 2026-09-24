/**
 * Pruebas del andamiaje del frontend: T-0.8 y T-0.9.
 *
 * Verifican que PrimeVue, el tema y el locale en espanol estan montados
 * correctamente. Si el locale se rompiera, la interfaz volveria al
 * ingles en tablas y calendarios sin que nada fallara a gritos, y eso
 * incumpliria RNF-13.
 */

import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import { describe, expect, it } from 'vitest'

import App from '../App.vue'
import { localeEs } from '../locale/es'

function montarApp() {
  return mount(App, {
    global: {
      plugins: [[PrimeVue, { theme: { preset: Aura }, locale: localeEs }]],
    },
  })
}

describe('T-0.8 — andamiaje de la interfaz', () => {
  it('monta la aplicacion con componentes de PrimeVue renderizados', () => {
    const app = montarApp()

    // Button y Card de PrimeVue emiten sus propias clases.
    expect(app.find('.p-button').exists()).toBe(true)
    expect(app.find('.p-card').exists()).toBe(true)
  })

  it('muestra los cinco modulos funcionales de la especificacion', () => {
    const app = montarApp()
    const texto = app.text()

    for (const modulo of [
      'Catálogo e inventario',
      'Registro de ventas',
      'Servicios técnicos',
      'Gestión de usuarios',
      'Panel de indicadores',
    ]) {
      expect(texto).toContain(modulo)
    }
  })
})

describe('RNF-13 — interfaz en espanol', () => {
  it('el locale traduce los textos de tablas y paginacion', () => {
    expect(localeEs.emptyMessage).toBe('Sin datos para mostrar')
    expect(localeEs.aria.rowsPerPageLabel).toBe('Filas por página')
    expect(localeEs.clear).toBe('Limpiar')
  })

  it('la semana empieza en lunes y la fecha va en formato boliviano', () => {
    expect(localeEs.firstDayOfWeek).toBe(1)
    expect(localeEs.dateFormat).toBe('dd/mm/yy')
    expect(localeEs.monthNames[0]).toBe('Enero')
  })
})
