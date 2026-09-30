/**
 * Pantalla de Inicio por rol (plan.md 7.6).
 *
 * Dos criterios importan aqui, y el segundo mas que el primero:
 *
 *   1. Cada rol ve su propia identidad: su icono, su degradado y su
 *      frase.
 *   2. El Inicio NO navega. El problema que esta pantalla vino a
 *      resolver era que duplicaba la barra lateral; si manana alguien
 *      vuelve a colgar accesos aqui, esta prueba lo detiene.
 */

import { createTestingPinia } from '@pinia/testing'
import { mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import { describe, expect, it, vi } from 'vitest'

import EncabezadoRol from '../components/EncabezadoRol.vue'
import IlustracionRol from '../components/IlustracionRol.vue'
import { IDENTIDADES, identidadDe } from '../config/identidadRol'
import { localeEs } from '../locale/es'
import InicioView from '../views/InicioView.vue'

const USUARIOS = {
  ADMINISTRADOR: {
    id: 1,
    username: 'admin',
    nombre_completo: 'Carlos Vargas',
    rol: 'ADMINISTRADOR',
    rol_display: 'Administrador',
  },
  VENTAS: {
    id: 2,
    username: 'jperez',
    nombre_completo: 'Juan Pérez',
    rol: 'VENTAS',
    rol_display: 'Encargado de Ventas',
  },
  SERVICIOS: {
    id: 3,
    username: 'arojas',
    nombre_completo: 'Ana Rojas',
    rol: 'SERVICIOS',
    rol_display: 'Encargado de Servicios',
  },
}

function montar(rol) {
  return mount(InicioView, {
    global: {
      plugins: [
        createTestingPinia({
          createSpy: vi.fn,
          initialState: { auth: { usuario: rol ? USUARIOS[rol] : null } },
        }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
      ],
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
    },
  })
}

const ROLES = ['ADMINISTRADOR', 'VENTAS', 'SERVICIOS']

describe('identidad de cada rol', () => {
  it.each(ROLES)('%s ve su nombre, su rol y su frase', (rol) => {
    const wrapper = montar(rol)
    const texto = wrapper.text()

    expect(texto).toContain(USUARIOS[rol].nombre_completo)
    expect(texto).toContain(USUARIOS[rol].rol_display)
    expect(texto).toContain(IDENTIDADES[rol].frase)
  })

  it.each(ROLES)('%s ve su icono y su degradado', (rol) => {
    const wrapper = montar(rol)
    const encabezado = wrapper.findComponent(EncabezadoRol)

    expect(encabezado.find('i').classes().join(' ')).toContain(
      IDENTIDADES[rol].icono.replace('pi pi-', 'pi-'),
    )
    expect(encabezado.find('header').attributes('style')).toContain(
      IDENTIDADES[rol].degradado,
    )
  })

  it.each(ROLES)('%s ve un simbolo distinto en la ilustracion', (rol) => {
    const wrapper = montar(rol)
    const simbolo = wrapper.findComponent(IlustracionRol).find('.simbolo')

    expect(simbolo.html()).not.toBe('')
    expect(simbolo.element.children.length).toBeGreaterThan(0)
  })

  it('las tres frases son distintas entre si', () => {
    /* Una frase repetida haria que la pantalla no distinguiera nada, y
       pasaria desapercibida porque cada prueba de arriba mira un solo
       rol. */
    const frases = ROLES.map((r) => IDENTIDADES[r].frase)
    expect(new Set(frases).size).toBe(3)
  })

  it('un rol todavia sin cargar no rompe la pantalla', () => {
    /* Ocurre durante el instante en que restaurarSesion() aun no
       respondio. */
    expect(() => montar(null)).not.toThrow()
    expect(identidadDe(null).frase).toBeTruthy()
  })
})

describe('el Inicio no duplica la navegacion', () => {
  it.each(ROLES)('para %s no hay ni un enlace', (rol) => {
    const wrapper = montar(rol)

    expect(wrapper.findAll('a')).toHaveLength(0)
    expect(wrapper.findAllComponents({ name: 'RouterLink' })).toHaveLength(0)
  })

  it.each(ROLES)('para %s no queda nada pulsable', (rol) => {
    /* Se comprueba que no haya NADA con lo que interactuar, y no que
       no aparezcan los rotulos del menu: «Encargado de Ventas» contiene
       «Ventas» de forma legitima, asi que buscar subcadenas daria
       falsas alarmas. Lo que define a esta pantalla es que no lleva a
       ningun sitio. */
    const wrapper = montar(rol)

    expect(wrapper.findAll('button')).toHaveLength(0)
    expect(wrapper.findAll('[href]')).toHaveLength(0)
    expect(wrapper.findAll('[tabindex]')).toHaveLength(0)
  })
})

describe('la ilustracion es decorativa', () => {
  it('queda fuera del alcance de los lectores de pantalla', () => {
    /* No aporta nada que no diga ya la frase de al lado: anunciarla
       solo alargaria el recorrido sin informar (RNF-14). */
    const svg = montar('SERVICIOS').findComponent(IlustracionRol).find('svg')

    expect(svg.attributes('aria-hidden')).toBe('true')
    expect(svg.attributes('role')).toBe('presentation')
    expect(svg.find('title').exists()).toBe(false)
  })

  it('el icono del encabezado tampoco se anuncia', () => {
    const icono = montar('VENTAS').findComponent(EncabezadoRol).find('i')

    expect(icono.attributes('aria-hidden')).toBe('true')
  })

  it('el saludo sigue siendo un encabezado real', () => {
    /* La estructura del documento no depende de la decoracion. */
    const wrapper = montar('ADMINISTRADOR')

    expect(wrapper.find('h1').text()).toContain('Carlos Vargas')
  })
})
