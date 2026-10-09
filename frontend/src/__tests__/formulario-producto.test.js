/**
 * Formulario de producto y existencias (RN-CAT-10, revisada el 2026-10-09).
 *
 * El servidor rechaza con 400 una edicion que incluya las existencias.
 * El formulario las enviaba siempre al editar, aunque no cambiaran: sin
 * esta correccion, TODA edicion hecha desde la interfaz fallaria. Al
 * crear, en cambio, las existencias iniciales si se envian.
 */

import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { productosApi } from '../api/catalogo'
import { localeEs } from '../locale/es'
import FormularioProducto from '../views/catalogo/FormularioProducto.vue'

vi.mock('../api/catalogo', () => ({
  productosApi: {
    crear: vi.fn(() => Promise.resolve({})),
    actualizar: vi.fn(() => Promise.resolve({})),
  },
}))

const PRODUCTO = {
  id: 7,
  nombre: 'Teclado mecánico',
  descripcion: 'Switches rojos',
  precio: '350.00',
  stock: 12,
  categoria: 3,
  imagen: null,
}

/** El formulario se rellena al ABRIRSE (watch de `visible`), como en la
 *  aplicacion: se monta cerrado y luego se abre. */
async function abrir(producto) {
  const wrapper = mount(FormularioProducto, {
    props: { visible: false, producto, categorias: [{ id: 3, nombre: 'Periféricos' }] },
    global: {
      plugins: [[PrimeVue, { theme: { preset: Aura }, locale: localeEs }], ToastService],
      // El Dialog de PrimeVue se teletransporta al body; aqui basta con
      // su contenido.
      stubs: { Dialog: { template: '<div><slot /></div>' } },
    },
  })
  await wrapper.setProps({ visible: true })
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  // El Select de PrimeVue consulta matchMedia al montarse, y jsdom no
  // lo implementa.
  window.matchMedia ??= () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  })
})

describe('al editar', () => {
  it('no envia las existencias, aunque no hayan cambiado', async () => {
    const wrapper = await abrir(PRODUCTO)

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(productosApi.actualizar).toHaveBeenCalledTimes(1)
    const [id, datos] = productosApi.actualizar.mock.calls[0]
    expect(id).toBe(7)
    expect(datos).not.toHaveProperty('stock')
    expect(datos).toMatchObject({ nombre: 'Teclado mecánico', precio: 350 })
  })

  it('muestra las existencias sin dejar cambiarlas', async () => {
    const wrapper = await abrir(PRODUCTO)

    const campo = wrapper.find('#stock')
    expect(campo.element.value).toContain('12')
    expect(campo.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('ajuste de inventario')
  })
})

describe('al crear', () => {
  it('si envia las existencias iniciales', async () => {
    const wrapper = await abrir(null)
    await wrapper.find('#nombre').setValue('Monitor 24')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(productosApi.crear).toHaveBeenCalledTimes(1)
    expect(productosApi.crear.mock.calls[0][0]).toHaveProperty('stock', 0)
  })

  it('deja cambiar las existencias', async () => {
    const wrapper = await abrir(null)

    expect(wrapper.find('#stock').attributes('disabled')).toBeUndefined()
  })
})

describe('código de fábrica (RF-97)', () => {
  it('al editar carga el que tiene y envía el corregido', async () => {
    const wrapper = await abrir({ ...PRODUCTO, codigo_fabrica: '7501031311309' })
    expect(wrapper.find('#codigo_fabrica').element.value).toBe('7501031311309')

    await wrapper.find('#codigo_fabrica').setValue('7501031311316')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(productosApi.actualizar.mock.calls[0][1]).toMatchObject({ codigo_fabrica: '7501031311316' })
  })

  it('vaciarlo envía la cadena vacía, que es como se quita', async () => {
    const wrapper = await abrir({ ...PRODUCTO, codigo_fabrica: '7501031311309' })

    await wrapper.find('#codigo_fabrica').setValue('')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(productosApi.actualizar.mock.calls[0][1]).toHaveProperty('codigo_fabrica', '')
  })

  it('muestra junto al campo el rechazo del servidor', async () => {
    productosApi.crear.mockRejectedValueOnce({
      codigo: 'VALIDACION',
      detalle: 'Revise los datos.',
      errores: { codigo_fabrica: ['Ese código de fábrica ya está registrado en «Teclado USB».'] },
    })
    const wrapper = await abrir(null)

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('ya está registrado en «Teclado USB»')
  })
})
