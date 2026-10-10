/**
 * T-14.3 — Cabecera y menú lateral fijos al desplazarse (plan.md 7.5,
 * RNF-12).
 *
 * jsdom no calcula el diseño, así que no puede «desplazar» la página.
 * Se comprueba lo que sí puede fallar en el código: que las reglas que
 * fijan cabecera y menú estén en el componente, que el menú tenga su
 * propio scroll, que la cabecera quede por DEBAJO de los diálogos de
 * PrimeVue, que la impresión las devuelva al flujo normal y que el logo
 * lleve al espacio de trabajo. La comprobación visual en los tres anchos
 * queda para revisión humana.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { createTestingPinia } from '@pinia/testing'
import { mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue, { defaultOptions } from 'primevue/config'
import { describe, expect, it, vi } from 'vitest'

import AppLayout from '../components/AppLayout.vue'

const fuente = readFileSync(resolve(__dirname, '../components/AppLayout.vue'), 'utf8')
const estilos = fuente.slice(fuente.indexOf('<style'))

function regla(selector, desde = estilos) {
  const inicio = desde.indexOf(`${selector} {`)
  expect(inicio, `falta la regla ${selector}`).toBeGreaterThan(-1)
  return desde.slice(inicio, desde.indexOf('}', inicio))
}

function bloqueMedia(consulta) {
  const inicio = estilos.indexOf(`@media ${consulta} {`)
  expect(inicio, `falta @media ${consulta}`).toBeGreaterThan(-1)
  return estilos.slice(inicio)
}

describe('la cabecera queda fija arriba', () => {
  const cabecera = regla('.cabecera')

  it('es sticky en top: 0, con altura fija', () => {
    expect(cabecera).toMatch(/position:\s*sticky/)
    expect(cabecera).toMatch(/top:\s*0/)
    expect(cabecera).toMatch(/height:\s*var\(--pcs-alto-cabecera\)/)
  })

  it('queda por encima del contenido pero por debajo de diálogos y menús de PrimeVue', () => {
    const z = Number(cabecera.match(/z-index:\s*(\d+)/)[1])
    expect(z).toBeGreaterThan(0)
    expect(z).toBeLessThan(defaultOptions.zIndex.overlay)
    expect(z).toBeLessThan(defaultOptions.zIndex.modal)
  })
})

describe('el menú lateral queda fijo bajo la cabecera', () => {
  const lateral = regla('.lateral')

  it('es sticky justo debajo de la cabecera, del alto de la ventana', () => {
    expect(lateral).toMatch(/position:\s*sticky/)
    expect(lateral).toMatch(/top:\s*var\(--pcs-alto-cabecera\)/)
    expect(lateral).toMatch(/height:\s*calc\(100vh - var\(--pcs-alto-cabecera\)\)/)
  })

  it('si no cabe, tiene su propio scroll interno', () => {
    expect(lateral).toMatch(/overflow-y:\s*auto/)
  })

  it('en tableta la barra horizontal sigue fija y conserva su scroll horizontal', () => {
    const tableta = regla('.lateral', bloqueMedia('(max-width: 900px)'))
    expect(tableta).toMatch(/overflow-x:\s*auto/)
    expect(tableta).toMatch(/height:\s*auto/)
    expect(tableta).not.toMatch(/position:\s*static/)
  })
})

describe('la impresión no se ve afectada', () => {
  it('al imprimir, cabecera y menú vuelven al flujo normal', () => {
    const impresion = bloqueMedia('print')
    const reglaImpresion = impresion.slice(0, impresion.indexOf('}'))
    expect(reglaImpresion).toMatch(/\.cabecera,\s*\.lateral/)
    expect(reglaImpresion).toMatch(/position:\s*static/)
  })
})

describe('estructura', () => {
  it('cabecera, menú lateral y contenido; el logo lleva al espacio de trabajo', () => {
    const wrapper = mount(AppLayout, {
      slots: { default: '<p id="pagina">contenido</p>' },
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: { auth: { usuario: { id: 1, rol: 'VENTAS', nombre_completo: 'Víctor' } } },
          }),
          [PrimeVue, { theme: { preset: Aura } }],
        ],
        stubs: { RouterLink: { props: ['to'], template: '<a :data-destino="JSON.stringify(to)"><slot /></a>' } },
      },
    })

    expect(wrapper.find('header.cabecera').exists()).toBe(true)
    expect(wrapper.find('nav.lateral').exists()).toBe(true)
    expect(wrapper.find('main.contenido #pagina').exists()).toBe(true)
    const logo = wrapper.find('header .marca')
    expect(logo.element.tagName).toBe('A')
    expect(JSON.parse(logo.attributes('data-destino'))).toEqual({ name: 'venta-nueva' })
  })
})
