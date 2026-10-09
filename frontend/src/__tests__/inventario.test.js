/**
 * T-8.7 — Pantallas de movimientos y ajuste (RF-73, RF-82, RF-83).
 *
 * Lo que mas importa comprobar:
 *  - el ajuste pide confirmacion mostrando la diferencia (RNF-14), y
 *    solo envia lo contado y el motivo: la diferencia la calcula el
 *    servidor contra las existencias de ese instante;
 *  - si el servidor registro otra diferencia (se vendio mientras tanto),
 *    el usuario se entera;
 *  - el Encargado de Ventas no ve ni el menu ni las acciones
 *    (RN-MOV-06), y su pantalla ni siquiera pide el historial.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { productosApi } from '../api/catalogo'
import { inventarioApi } from '../api/inventario'
import TablaMovimientos from '../components/TablaMovimientos.vue'
import { localeEs } from '../locale/es'
import { menuPara, puedeEntrar, rutas } from '../router'
import AjustarExistencias from '../views/catalogo/AjustarExistencias.vue'
import ProductoDetalleView from '../views/catalogo/ProductoDetalleView.vue'
import MovimientosView from '../views/inventario/MovimientosView.vue'

const toastAdd = vi.fn()

vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRoute: () => ({ params: { id: 7 }, query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('../api/inventario', async () => {
  const real = await vi.importActual('../api/inventario')
  return {
    ...real,
    inventarioApi: {
      listarMovimientos: vi.fn(),
      historialDe: vi.fn(),
      ajustarExistencias: vi.fn(),
    },
  }
})

vi.mock('../api/catalogo', () => ({
  productosApi: { obtener: vi.fn(), listar: vi.fn() },
  categoriasApi: { listar: vi.fn() },
}))

const PRODUCTO = {
  id: 7,
  nombre: 'Disco SSD 480 GB',
  categoria_nombre: 'Almacenamiento',
  precio: '250.00',
  stock: 10,
  stock_bajo: false,
  activo: true,
  descripcion: '',
  imagen: null,
}

const MOVIMIENTO = {
  id: 31,
  producto: 7,
  producto_nombre: 'Disco SSD 480 GB',
  tipo: 'AJUSTE',
  tipo_display: 'Ajuste manual',
  cantidad: -3,
  stock_resultante: 7,
  usuario: 1,
  usuario_nombre: 'Ana Rojas',
  venta: null,
  motivo: 'Recuento físico',
  fecha_hora: '2026-10-09T14:30:00-04:00',
}

const plugins = (rol = 'ADMINISTRADOR') => [
  createTestingPinia({
    createSpy: vi.fn,
    stubActions: false,
    initialState: { auth: { usuario: { id: 1, rol } } },
  }),
  [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
  ToastService,
]

const STUBS = {
  // El Dialog de PrimeVue se teletransporta al body; aqui basta con su
  // contenido.
  Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /></div>' },
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
}

beforeEach(() => {
  vi.clearAllMocks()
  window.matchMedia ??= () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  })
  productosApi.obtener.mockResolvedValue({ ...PRODUCTO })
  inventarioApi.historialDe.mockResolvedValue({ count: 1, results: [MOVIMIENTO] })
  inventarioApi.listarMovimientos.mockResolvedValue({ count: 0, results: [] })
})

// ─────────────────────────────────────────────────────────────────────
// Dialogo «Ajustar existencias» (CU-CAT-07)
// ─────────────────────────────────────────────────────────────────────
async function abrirAjuste(producto = PRODUCTO) {
  const wrapper = mount(AjustarExistencias, {
    props: { visible: false, producto },
    global: { plugins: plugins(), stubs: STUBS },
  })
  await wrapper.setProps({ visible: true })
  return wrapper
}

async function rellenar(wrapper, { cantidad, motivo }) {
  if (cantidad !== undefined) wrapper.vm.$.setupState.cantidadReal = cantidad
  if (motivo !== undefined) await wrapper.find('#motivo').setValue(motivo)
  await wrapper.vm.$nextTick()
}

describe('ajustar existencias', () => {
  it('muestra la diferencia orientativa con signo', async () => {
    const wrapper = await abrirAjuste()
    await rellenar(wrapper, { cantidad: 7 })

    expect(wrapper.find('[data-prueba="diferencia"]').text()).toContain('-3')
  })

  it('pide confirmación mostrando de cuánto a cuánto pasan, antes de enviar nada', async () => {
    const wrapper = await abrirAjuste()
    await rellenar(wrapper, { cantidad: 12, motivo: 'Recuento físico' })

    await wrapper.find('form').trigger('submit')

    const revision = wrapper.find('[data-prueba="revision"]')
    expect(revision.exists()).toBe(true)
    expect(revision.text()).toContain('de 10 a 12 (+2)')
    expect(revision.text()).toContain('Recuento físico')
    expect(inventarioApi.ajustarExistencias).not.toHaveBeenCalled()
  })

  it('al confirmar envía solo lo contado y el motivo, no la diferencia', async () => {
    inventarioApi.ajustarExistencias.mockResolvedValue({ ...MOVIMIENTO })
    const wrapper = await abrirAjuste()
    await rellenar(wrapper, { cantidad: 7, motivo: '  Recuento físico  ' })
    await wrapper.find('form').trigger('submit')

    await wrapper.find('[data-prueba="confirmar"]').trigger('click')
    await flushPromises()

    expect(inventarioApi.ajustarExistencias).toHaveBeenCalledWith(7, {
      cantidadReal: 7,
      motivo: 'Recuento físico',
    })
    expect(wrapper.emitted('ajustado')[0][0]).toMatchObject({ id: 31 })
    expect(wrapper.emitted('update:visible').at(-1)).toEqual([false])
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success' }))
  })

  it('avisa si el servidor registró otra diferencia porque se vendió mientras tanto', async () => {
    // La pantalla veía 10 y se contaron 7 (−3); el servidor tenía 9 al
    // confirmar, así que registró −2.
    inventarioApi.ajustarExistencias.mockResolvedValue({ ...MOVIMIENTO, cantidad: -2 })
    const wrapper = await abrirAjuste()
    await rellenar(wrapper, { cantidad: 7, motivo: 'Recuento' })
    await wrapper.find('form').trigger('submit')

    await wrapper.find('[data-prueba="confirmar"]').trigger('click')
    await flushPromises()

    const aviso = toastAdd.mock.calls[0][0]
    expect(aviso.severity).toBe('warn')
    expect(aviso.detail).toContain('-2')
    expect(aviso.detail).toContain('-3')
  })

  it('sin motivo no pasa a la revisión y lo dice junto al campo', async () => {
    const wrapper = await abrirAjuste()
    await rellenar(wrapper, { cantidad: 7, motivo: '   ' })

    await wrapper.find('form').trigger('submit')

    expect(wrapper.find('[data-prueba="revision"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Indique el motivo del ajuste.')
  })

  it('si lo contado es lo registrado avisa que no hay nada que ajustar', async () => {
    const wrapper = await abrirAjuste()
    await rellenar(wrapper, { cantidad: 10, motivo: 'Recuento' })

    await wrapper.find('form').trigger('submit')

    expect(wrapper.find('[data-prueba="revision"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('no hay nada que ajustar')
  })

  it('un error de campo del servidor vuelve al formulario y se muestra junto al campo', async () => {
    inventarioApi.ajustarExistencias.mockRejectedValue({
      codigo: 'VALIDACION',
      detalle: 'Revise los datos.',
      errores: { motivo: ['El motivo no puede superar los 500 caracteres.'] },
    })
    const wrapper = await abrirAjuste()
    await rellenar(wrapper, { cantidad: 7, motivo: 'x' })
    await wrapper.find('form').trigger('submit')

    await wrapper.find('[data-prueba="confirmar"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('form').exists()).toBe(true)
    expect(wrapper.text()).toContain('no puede superar los 500')
    expect(wrapper.emitted('ajustado')).toBeUndefined()
  })

  it('el 409 del servidor se muestra sin cerrar el diálogo', async () => {
    inventarioApi.ajustarExistencias.mockRejectedValue({
      codigo: 'AJUSTE_SIN_DIFERENCIA',
      detalle: 'La cantidad indicada ya es la registrada: no hay nada que ajustar.',
    })
    const wrapper = await abrirAjuste()
    await rellenar(wrapper, { cantidad: 7, motivo: 'Recuento' })
    await wrapper.find('form').trigger('submit')

    await wrapper.find('[data-prueba="confirmar"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('no hay nada que ajustar')
    expect(wrapper.emitted('update:visible')).toBeUndefined()
  })
})

// ─────────────────────────────────────────────────────────────────────
// Detalle de producto: historial y accion, solo Administrador
// ─────────────────────────────────────────────────────────────────────
function montarDetalle(rol) {
  return mount(ProductoDetalleView, { global: { plugins: plugins(rol), stubs: STUBS } })
}

describe('detalle de producto', () => {
  it('el Administrador ve el historial del producto y la acción de ajustar', async () => {
    const wrapper = montarDetalle('ADMINISTRADOR')
    await flushPromises()

    expect(inventarioApi.historialDe).toHaveBeenCalledWith(7, { page: 1, page_size: 20 })
    expect(wrapper.text()).toContain('Historial de movimientos')
    expect(wrapper.text()).toContain('Recuento físico')
    expect(wrapper.find('[data-prueba="ajustar"]').exists()).toBe(true)
  })

  it('el Encargado de Ventas ve el producto, pero ni el historial ni el ajuste', async () => {
    const wrapper = montarDetalle('VENTAS')
    await flushPromises()

    expect(wrapper.text()).toContain('Disco SSD 480 GB')
    expect(wrapper.text()).not.toContain('Historial de movimientos')
    expect(wrapper.find('[data-prueba="ajustar"]').exists()).toBe(false)
    // Ni siquiera lo pide: el servidor respondería 403.
    expect(inventarioApi.historialDe).not.toHaveBeenCalled()
  })

  it('tras ajustar vuelve a pedir el producto y el historial al servidor', async () => {
    const wrapper = montarDetalle('ADMINISTRADOR')
    await flushPromises()
    productosApi.obtener.mockResolvedValue({ ...PRODUCTO, stock: 7 })

    wrapper.findComponent(AjustarExistencias).vm.$emit('ajustado', MOVIMIENTO)
    await flushPromises()

    expect(productosApi.obtener).toHaveBeenCalledTimes(2)
    expect(inventarioApi.historialDe).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-prueba="existencias"]').text()).toBe('7')
  })
})

// ─────────────────────────────────────────────────────────────────────
// Pantalla de movimientos (RF-82)
// ─────────────────────────────────────────────────────────────────────
describe('pantalla de movimientos', () => {
  it('combina los filtros y envía las fechas en el día local, no en UTC', async () => {
    const wrapper = mount(MovimientosView, { global: { plugins: plugins(), stubs: STUBS } })
    await flushPromises()

    wrapper.vm.filtros.producto = { id: 7, nombre: 'Disco SSD 480 GB' }
    wrapper.vm.filtros.tipo = 'AJUSTE'
    // 21:30 del 30 de septiembre en hora local: en UTC ya sería el 1.
    wrapper.vm.filtros.rango = [new Date(2026, 8, 1), new Date(2026, 8, 30, 21, 30)]

    expect(wrapper.vm.parametros()).toEqual({
      page: 1,
      page_size: 20,
      producto: 7,
      tipo: 'AJUSTE',
      desde: '2026-09-01',
      hasta: '2026-09-30',
    })
  })

  it('sin filtros pide la primera página', async () => {
    mount(MovimientosView, { global: { plugins: plugins(), stubs: STUBS } })
    await flushPromises()

    expect(inventarioApi.listarMovimientos).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })
})

describe('tabla de movimientos', () => {
  it('muestra la cantidad con signo, la venta de referencia y el saldo inicial sin autor', () => {
    const wrapper = mount(TablaMovimientos, {
      props: {
        movimientos: [
          { ...MOVIMIENTO, id: 1, tipo: 'VENTA', tipo_display: 'Venta', cantidad: -2, venta: 15, motivo: '' },
          { ...MOVIMIENTO, id: 2, tipo: 'ANULACION', tipo_display: 'Anulación', cantidad: 2, venta: 15, motivo: '' },
          { ...MOVIMIENTO, id: 3, tipo: 'SALDO_INICIAL', tipo_display: 'Saldo inicial', cantidad: 10, usuario: null, usuario_nombre: null, motivo: '' },
        ],
        total: 3,
      },
      global: { plugins: plugins(), stubs: STUBS },
    })

    const texto = wrapper.text()
    expect(texto).toContain('-2')
    expect(texto).toContain('+2')
    expect(texto).toContain('Venta n.º 15')
    expect(texto).toContain('Sistema (saldo inicial)')
  })
})

// ─────────────────────────────────────────────────────────────────────
// Navegacion (RN-MOV-06)
// ─────────────────────────────────────────────────────────────────────
describe('navegación', () => {
  const ruta = (nombre) => rutas.find((r) => r.name === nombre)

  it('solo el Administrador tiene «Movimientos» en el menú y puede entrar', () => {
    expect(menuPara('ADMINISTRADOR').map((o) => o.name)).toContain('movimientos')
    expect(menuPara('VENTAS').map((o) => o.name)).not.toContain('movimientos')
    expect(menuPara('SERVICIOS').map((o) => o.name)).not.toContain('movimientos')
    expect(puedeEntrar(ruta('movimientos'), 'VENTAS')).toBe(false)
  })

  it('el detalle de producto lo abren quienes consultan el catálogo, sin entrada de menú', () => {
    expect(puedeEntrar(ruta('producto-detalle'), 'ADMINISTRADOR')).toBe(true)
    expect(puedeEntrar(ruta('producto-detalle'), 'VENTAS')).toBe(true)
    expect(puedeEntrar(ruta('producto-detalle'), 'SERVICIOS')).toBe(false)
    expect(menuPara('ADMINISTRADOR').map((o) => o.name)).not.toContain('producto-detalle')
  })
})
