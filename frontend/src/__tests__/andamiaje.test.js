/**
 * Locale en espanol (RNF-13).
 *
 * Originalmente estas pruebas montaban el App.vue de andamiaje de
 * T-0.8, que T-1.10 sustituyo por el marco real de la aplicacion. Lo
 * que sigue siendo util comprobar aqui es el locale: si se rompiera,
 * la interfaz volveria al ingles en tablas y calendarios sin que nada
 * fallara a gritos. El montaje de componentes de PrimeVue se verifica
 * ahora en login.test.js, sobre una pantalla real.
 */

import { describe, expect, it } from 'vitest'

import { localeEs } from '../locale/es'

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

  it('cubre los textos de los dialogos de confirmacion (RNF-14)', () => {
    expect(localeEs.accept).toBe('Sí')
    expect(localeEs.reject).toBe('No')
    expect(localeEs.cancel).toBe('Cancelar')
  })
})
