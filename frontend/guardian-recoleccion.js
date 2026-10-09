/**
 * Guardian de la recoleccion de pruebas del frontend.
 *
 * Una ejecucion de la suite recogio 2 archivos de prueba en lugar de
 * 13, sin ningun fallo: el resumen decia «Test Files 2 passed (2)». No
 * se pudo reproducir en 31 intentos ni encontrar la causa. Este
 * reporter hace que, si vuelve a ocurrir, la ejecucion FALLE en lugar
 * de pasar en verde con la mayor parte de la suite sin ejecutar.
 *
 * Cuenta los archivos de prueba del disco POR SU CUENTA, recorriendo
 * las carpetas, en vez de preguntarle a vitest: si el fallo estuviera
 * en la busqueda de vitest, consultarla a ella no lo detectaria.
 *
 * Es el mismo tipo de guardian que core/tests/test_recoleccion.py en el
 * backend, que nacio de un fallo parecido: una app cuyas pruebas la
 * suite completa no ejecutaba.
 */

import { readdirSync } from 'node:fs'
import { join, relative } from 'node:path'

// El mismo criterio que el `include` por defecto de vitest.
const ES_PRUEBA = /\.(test|spec)\.(c|m)?[jt]sx?$/
// Y las mismas carpetas que su `exclude` por defecto.
const NO_ENTRAR = new Set(['node_modules', 'dist', 'cypress', '.git', '.idea', '.cache', '.output', '.temp'])

function archivosDePruebaEnDisco(raiz, dir = raiz, encontrados = []) {
  for (const entrada of readdirSync(dir, { withFileTypes: true })) {
    if (entrada.isDirectory()) {
      if (!NO_ENTRAR.has(entrada.name)) {
        archivosDePruebaEnDisco(raiz, join(dir, entrada.name), encontrados)
      }
    } else if (ES_PRUEBA.test(entrada.name)) {
      encontrados.push(normalizar(relative(raiz, join(dir, entrada.name))))
    }
  }
  return encontrados
}

// Windows: barras invertidas y mayusculas de unidad o de carpeta
// pueden diferir entre lo que da el sistema y lo que da vitest.
function normalizar(ruta) {
  return ruta.replaceAll('\\', '/').toLowerCase()
}

/**
 * ¿Se pidio una ejecucion filtrada por archivo? Por ejemplo
 * `npm run test -- src/__tests__/inicio.test.js`. Entonces recoger
 * menos archivos es lo esperado, y el guardian no debe fallar.
 *
 * Vitest trata cada argumento suelto como un fragmento de ruta: filtra
 * los archivos cuya ruta lo contiene. Se aplica el mismo criterio, en
 * vez de considerar filtro todo argumento que no empiece por «-»: esa
 * primera version confundia el VALOR de una opcion (el patron de
 * `--exclude …`, por ejemplo) con un filtro, y se inhibia justo cuando
 * la recoleccion era incompleta. Un patron con comodines o un valor
 * como «default» no aparecen dentro de ninguna ruta.
 */
function filtrosDeArchivo(enDisco) {
  const tras = process.argv.slice(process.argv.indexOf('run') + 1)
  return tras
    .filter((a) => !a.startsWith('-'))
    .filter((a) => enDisco.some((ruta) => ruta.includes(normalizar(a))))
}

export default class GuardianRecoleccion {
  onInit(vitest) {
    this.raiz = vitest.config.root
  }

  onTestRunEnd(testModules) {
    const enDisco = archivosDePruebaEnDisco(this.raiz).sort()

    const filtros = filtrosDeArchivo(enDisco)
    if (filtros.length > 0) {
      console.log(
        `\n[guardian de recoleccion] Ejecucion filtrada (${filtros.join(' ')}): ` +
          'no se comprueba el total de archivos.',
      )
      return
    }

    const recogidos = testModules
      .map((m) => normalizar(relative(this.raiz, m.moduleId)))
      .sort()

    if (recogidos.length >= enDisco.length) return

    const recogidosSet = new Set(recogidos)
    const faltan = enDisco.filter((f) => !recogidosSet.has(f))

    console.error(
      [
        '',
        '[guardian de recoleccion] FALLO: vitest recogio menos archivos de prueba de los que hay en disco.',
        `  En disco:  ${enDisco.length}`,
        `  Recogidos: ${recogidos.length}`,
        '',
        '  Archivos recogidos:',
        ...recogidos.map((f) => `    + ${f}`),
        '',
        '  Archivos en disco que NO se recogieron:',
        ...faltan.map((f) => `    - ${f}`),
        '',
      ].join('\n'),
    )
    process.exitCode = 1
  }
}
