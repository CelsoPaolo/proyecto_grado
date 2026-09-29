/**
 * T-5.11 a T-5.13 — Pantallas de servicios.
 *
 * Lo que mas importa comprobar son las dos decisiones revisadas:
 * cotizar solo se le ofrece al Administrador (PA-03, RF-57), y el
 * aviso de que falta cotizar se redacta distinto segun quien lo lea
 * (RF-61), porque a uno le toca actuar y al otro esperar.
 */

import { createTestingPinia } from '@pinia/testing'
import { flushPromises, mount } from '@vue/test-utils'
import Aura from '@primeuix/themes/aura'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { exigeDireccion, serviciosApi } from '../api/servicios'
import { localeEs } from '../locale/es'
import { useAuthStore } from '../stores/auth'
import ServicioDetalleView from '../views/servicios/ServicioDetalleView.vue'
import { menuPara, puedeEntrar, rutas } from '../router'

/* Mock PARCIAL: este archivo prueba tanto un componente (que necesita
   useRouter y useRoute simulados) como la definicion de rutas (que
   importa el router real y por tanto necesita createRouter de verdad).
   Sustituir el modulo entero rompia lo segundo. */
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal()),
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: { id: 1 } }),
}))

vi.mock('../api/servicios', async () => {
  const real = await vi.importActual('../api/servicios')
  return {
    ...real,
    serviciosApi: {
      listar: vi.fn(),
      obtener: vi.fn(),
      registrar: vi.fn(),
      cotizar: vi.fn(),
      iniciar: vi.fn(),
      finalizar: vi.fn(),
      cancelar: vi.fn(),
    },
  }
})

const SOLICITUD_SIN_COTIZAR = {
  id: 1,
  cliente_nombre: 'María Gutiérrez',
  cliente_telefono: '70012345',
  tipo: 'REPARACION',
  tipo_display: 'Reparación',
  modalidad: 'TALLER',
  modalidad_display: 'En taller',
  direccion: '',
  descripcion: 'El equipo no enciende.',
  estado: 'EN_ATENCION',
  estado_display: 'En atención',
  registrada_por: { id: 2, nombre_completo: 'Ana Rojas' },
  tecnico: '',
  monto_cobrado: null,
  esta_cotizada: false,
  cotizada_por: null,
  observaciones: '',
  motivo_cancelacion: '',
  cerrada_por: null,
  eventos: [],
}

function montarDetalle(rol) {
  const wrapper = mount(ServicioDetalleView, {
    global: {
      plugins: [
        createTestingPinia({ createSpy: vi.fn, stubActions: false }),
        [PrimeVue, { theme: { preset: Aura }, locale: localeEs }],
        ToastService,
      ],
      stubs: { RouterLink: true },
    },
  })
  const auth = useAuthStore()
  auth.usuario = { id: 9, rol }
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  serviciosApi.obtener.mockResolvedValue({ ...SOLICITUD_SIN_COTIZAR })
})

describe('RN-SER-01 — la dirección depende del tipo', () => {
  it('redes y videovigilancia exigen dirección; taller no', () => {
    expect(exigeDireccion('REDES')).toBe(true)
    expect(exigeDireccion('VIDEOVIGILANCIA')).toBe(true)
    expect(exigeDireccion('MANTENIMIENTO')).toBe(false)
    expect(exigeDireccion('REPARACION')).toBe(false)
  })
})

describe('RF-57 — cotizar es solo del Administrador', () => {
  it('al Administrador se le ofrece el botón de cotizar', async () => {
    const wrapper = montarDetalle('ADMINISTRADOR')
    await flushPromises()

    expect(wrapper.text()).toContain('Cotizar')
  })

  it('al Encargado de Servicios NO se le ofrece', async () => {
    /* El servidor lo rechazaría con 403; no ofrecerlo evita que
       intente una acción que no le corresponde. */
    const wrapper = montarDetalle('SERVICIOS')
    await flushPromises()

    const botones = wrapper.findAll('button').map((b) => b.text())
    expect(botones.some((t) => t.includes('Cotizar'))).toBe(false)
  })
})

describe('RF-61 — el aviso de falta de cotización', () => {
  it('al Administrador le dice que debe registrar el monto', async () => {
    const wrapper = montarDetalle('ADMINISTRADOR')
    await flushPromises()

    expect(wrapper.text()).toContain('hasta que registre el monto')
  })

  it('al Encargado de Servicios le dice a quién esperar', async () => {
    /* A uno le toca actuar y al otro esperar: el mismo hecho, redactado
       para lo que cada uno puede hacer al respecto. */
    const wrapper = montarDetalle('SERVICIOS')
    await flushPromises()

    expect(wrapper.text()).toContain('El administrador debe registrar')
  })

  it('el botón de finalizar está desactivado sin cotización', async () => {
    const wrapper = montarDetalle('SERVICIOS')
    await flushPromises()

    const finalizar = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Finalizar'))
    expect(finalizar.attributes('disabled')).toBeDefined()
  })

  it('con la solicitud cotizada, finalizar se habilita y el aviso desaparece', async () => {
    serviciosApi.obtener.mockResolvedValue({
      ...SOLICITUD_SIN_COTIZAR,
      monto_cobrado: '250.00',
      esta_cotizada: true,
      cotizada_por: { id: 1, nombre_completo: 'Carlos Vargas' },
    })
    const wrapper = montarDetalle('SERVICIOS')
    await flushPromises()

    expect(wrapper.text()).not.toContain('El administrador debe registrar')
    const finalizar = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Finalizar'))
    expect(finalizar.attributes('disabled')).toBeUndefined()
  })
})

describe('rutas de servicios', () => {
  const ruta = (nombre) => rutas.find((r) => r.name === nombre)

  it('las llevan Administrador y Servicios, no Ventas', () => {
    for (const nombre of ['servicios', 'servicio-nuevo', 'servicio-detalle']) {
      expect(puedeEntrar(ruta(nombre), 'ADMINISTRADOR')).toBe(true)
      expect(puedeEntrar(ruta(nombre), 'SERVICIOS')).toBe(true)
      expect(puedeEntrar(ruta(nombre), 'VENTAS')).toBe(false)
    }
  })

  it('solo la lista aparece en el menú', () => {
    const enMenu = menuPara('SERVICIOS').map((o) => o.name)

    expect(enMenu).toContain('servicios')
    expect(enMenu).not.toContain('servicio-nuevo')
    expect(enMenu).not.toContain('servicio-detalle')
  })

  it('el Encargado de Servicios ve servicios pero no ventas ni catálogo', () => {
    const enMenu = menuPara('SERVICIOS').map((o) => o.name)

    expect(enMenu).toContain('servicios')
    expect(enMenu).not.toContain('ventas')
    expect(enMenu).not.toContain('catalogo')
  })
})

/* El recorte de campos del cliente de API se verifica en
   api-servicios.test.js, que mockea http a nivel de modulo. Hacerlo
   aqui con importActual no funcionaria: devolveria una instancia
   distinta de http y el espia no interceptaria la que usa el modulo
   real. */
