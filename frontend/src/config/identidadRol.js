/**
 * Identidad visual de cada rol (plan.md 7.6).
 *
 * Es un objeto plano, sin logica y sin consultas: solo dice con que
 * icono, que degradado y que frase se presenta cada rol en la pantalla
 * de Inicio.
 *
 * Vive aqui, y no dentro de los componentes, porque el encabezado y la
 * ilustracion necesitan los mismos valores. Duplicarlos en dos sitios
 * garantizaba que tarde o temprano divergieran.
 *
 * Los degradados son los tokens definidos en assets/main.css, donde
 * quedo verificado que los tres aguantan texto blanco (>= 4,5:1).
 */

export const IDENTIDADES = {
  ADMINISTRADOR: {
    icono: 'pi pi-shield',
    degradado: 'var(--pcs-degradado-admin)',
    frase:
      'Desde aquí gestionas el catálogo, las cuentas del personal y los ' +
      'indicadores de PC-Solution.',
  },
  VENTAS: {
    icono: 'pi pi-shopping-cart',
    degradado: 'var(--pcs-degradado-ventas)',
    frase:
      'Aquí registras las ventas de mostrador y consultas las existencias ' +
      'del catálogo.',
  },
  SERVICIOS: {
    icono: 'pi pi-wrench',
    degradado: 'var(--pcs-degradado-servicios)',
    frase:
      'Aquí registras y das seguimiento a los servicios técnicos de ' +
      'PC-Solution.',
  },
}

/**
 * Identidad de un rol, con un respaldo neutro.
 *
 * El respaldo no es defensa contra un rol inventado —el servidor solo
 * emite los tres de spec.md 4.4—, sino contra el instante en que la
 * sesion aun se esta restaurando y el rol todavia es null. Sin el, la
 * pantalla reventaria durante esa fraccion de segundo.
 */
export function identidadDe(rol) {
  return (
    IDENTIDADES[rol] ?? {
      icono: 'pi pi-user',
      degradado: 'var(--pcs-degradado-admin)',
      frase: 'Bienvenido a PC-Solution.',
    }
  )
}
