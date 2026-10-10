/**
 * T-1.10 — Rutas y guards por rol (RF-06).
 *
 * El criterio central: el menu de cada rol debe coincidir con la matriz
 * de spec.md seccion 4.4, y ambos se derivan de la MISMA definicion de
 * rutas, de modo que no puedan divergir.
 */

import { describe, expect, it } from 'vitest'

import { menuPara, puedeEntrar, rutas } from '../router'

const ADMIN = 'ADMINISTRADOR'
const VENTAS = 'VENTAS'
const SERVICIOS = 'SERVICIOS'

function ruta(nombre) {
  return rutas.find((r) => r.name === nombre)
}

describe('guards por rol (spec.md matriz 4.4)', () => {
  it('solo el Administrador entra a la gestion de usuarios', () => {
    const usuarios = ruta('usuarios')

    expect(puedeEntrar(usuarios, ADMIN)).toBe(true)
    expect(puedeEntrar(usuarios, VENTAS)).toBe(false)
    expect(puedeEntrar(usuarios, SERVICIOS)).toBe(false)
  })

  it('el catalogo lo consultan Administrador y Ventas, no Servicios', () => {
    /* spec.md matriz 4.4: el Encargado de Servicios no consulta el
       catalogo. */
    const catalogo = ruta('catalogo')

    expect(puedeEntrar(catalogo, ADMIN)).toBe(true)
    expect(puedeEntrar(catalogo, VENTAS)).toBe(true)
    expect(puedeEntrar(catalogo, SERVICIOS)).toBe(false)
  })

  it('solo el Administrador gestiona categorias', () => {
    /* RF-07: la gestion del catalogo es exclusiva del Administrador,
       aunque el Encargado de Ventas pueda consultar los productos. */
    const categorias = ruta('categorias')

    expect(puedeEntrar(categorias, ADMIN)).toBe(true)
    expect(puedeEntrar(categorias, VENTAS)).toBe(false)
    expect(puedeEntrar(categorias, SERVICIOS)).toBe(false)
  })

  it('las ventas las llevan Administrador y Ventas, no Servicios', () => {
    /* spec.md matriz 4.4. El alcance dentro del rol (propias frente a
       todas) lo decide el servidor, no el router: aqui solo se
       controla quien puede entrar. */
    for (const nombre of ['ventas', 'venta-nueva', 'venta-detalle']) {
      expect(puedeEntrar(ruta(nombre), ADMIN)).toBe(true)
      expect(puedeEntrar(ruta(nombre), VENTAS)).toBe(true)
      expect(puedeEntrar(ruta(nombre), SERVICIOS)).toBe(false)
    }
  })

  it('registrar y ver detalle no aparecen en el menu', () => {
    /* Se llega a ellas desde el historial, no desde el menu lateral:
       una ruta con parametro no tiene sentido como entrada de menu. */
    const enMenu = menuPara(ADMIN).map((o) => o.name)

    expect(enMenu).toContain('ventas')
    expect(enMenu).not.toContain('venta-nueva')
    expect(enMenu).not.toContain('venta-detalle')
  })

  it('solo el Administrador configura el umbral', () => {
    /* RF-52: configurar el umbral de existencias bajas es exclusivo
       del Administrador, aunque el aviso que produce lo vea tambien el
       Encargado de Ventas en el catalogo. */
    const configuracion = ruta('configuracion')

    expect(puedeEntrar(configuracion, ADMIN)).toBe(true)
    expect(puedeEntrar(configuracion, VENTAS)).toBe(false)
    expect(puedeEntrar(configuracion, SERVICIOS)).toBe(false)
  })

  it('los tres roles entran a su propia cuenta y a «Sin permiso»', () => {
    for (const nombre of ['cambiar-password', 'sin-permiso']) {
      for (const rol of [ADMIN, VENTAS, SERVICIOS]) {
        expect(puedeEntrar(ruta(nombre), rol)).toBe(true)
      }
    }
  })

  it('sin rol no se entra a ninguna ruta protegida', () => {
    for (const r of rutas.filter((r) => !r.meta?.publica && r.name)) {
      expect(puedeEntrar(r, null)).toBe(false)
    }
  })

  it('el ingreso es la unica ruta publica', () => {
    const publicas = rutas.filter((r) => r.meta?.publica).map((r) => r.name)

    expect(publicas).toEqual(['login'])
  })
})

describe('menu derivado de las rutas', () => {
  it('el Administrador ve la gestion de usuarios en su menu', () => {
    const etiquetas = menuPara(ADMIN).map((o) => o.name)

    expect(etiquetas).toContain('usuarios')
  })

  it('los otros roles no ven usuarios en su menu', () => {
    for (const rol of [VENTAS, SERVICIOS]) {
      expect(menuPara(rol).map((o) => o.name)).not.toContain('usuarios')
    }
  })

  it('sin sesion el menu esta vacio', () => {
    expect(menuPara(null)).toEqual([])
  })

  it('el menu de cada rol coincide exactamente con lo que puede navegar', () => {
    /* El criterio que hace util derivar ambos de la misma fuente: no
       puede haber una opcion visible que el guard rechace, ni una ruta
       navegable que el menu esconda sin marcarla como oculta. */
    for (const rol of [ADMIN, VENTAS, SERVICIOS]) {
      for (const opcion of menuPara(rol)) {
        expect(puedeEntrar(ruta(opcion.name), rol)).toBe(true)
      }

      const navegablesEnMenu = rutas
        .filter(
          (r) =>
            r.name &&
            r.meta?.icono &&
            r.meta.enMenu !== false &&
            puedeEntrar(r, rol),
        )
        .map((r) => r.name)

      expect(menuPara(rol).map((o) => o.name).sort()).toEqual(
        navegablesEnMenu.sort(),
      )
    }
  })

  it('las rutas auxiliares no aparecen en el menu', () => {
    const nombresEnMenu = menuPara(ADMIN).map((o) => o.name)

    expect(nombresEnMenu).not.toContain('sin-permiso')
    expect(nombresEnMenu).not.toContain('cambiar-password')
  })
})

describe('coherencia de la definicion de rutas', () => {
  it('toda ruta protegida declara sus roles', () => {
    for (const r of rutas.filter((r) => r.name && !r.meta?.publica)) {
      expect(Array.isArray(r.meta?.roles), `${r.name} no declara meta.roles`).toBe(
        true,
      )
      expect(r.meta.roles.length).toBeGreaterThan(0)
    }
  })

  it('los roles declarados son validos', () => {
    const validos = [ADMIN, VENTAS, SERVICIOS]

    for (const r of rutas.filter((r) => r.meta?.roles)) {
      for (const rol of r.meta.roles) {
        expect(validos).toContain(rol)
      }
    }
  })
})
