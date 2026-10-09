/**
 * Guardian de la recoleccion de pruebas del frontend.
 *
 * Una ejecucion de la suite recogio 2 archivos de prueba en lugar de
 * 13: el resumen decia «Test Files 2 passed (2)». No se reprodujo en
 * 31 intentos.
 *
 * Causa probable, encontrada despues (2026-10-09): un proceso de
 * vitest que NO ARRANCA a tiempo. Volvio a pasar con un solo archivo:
 * «[vitest-pool]: Failed to start forks worker … Timeout waiting for
 * worker to respond», y el archivo desaparecio del recuento («Test
 * Files no tests») con una linea aparte «Errors 1 error». En la
 * investigacion original la salida se filtro con
 * grep "Test Files|Tests ", y ese filtro ocultaba justo la linea
 * «Errors». Es transitorio —el segundo intento arranco normal—, propio
 * de Windows bajo carga.
 *
 * Este reporter hace dos cosas: si se recogen menos archivos de los que
 * hay en disco, la ejecucion FALLA; y si la causa es un proceso que no
 * arranco, lo DICE, con los archivos afectados.
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

/** Archivos cuyos procesos de vitest no llegaron a arrancar. */
function archivosSinProceso(errores) {
  const PATRON = /Failed to start \w+ worker for test files (.+?)\.?$/m
  return errores
    .map((e) => PATRON.exec(e?.message ?? '')?.[1])
    .filter(Boolean)
    .flatMap((lista) => lista.split(/,\s*/))
}

export default class GuardianRecoleccion {
  onInit(vitest) {
    this.raiz = vitest.config.root
  }

  onTestRunEnd(testModules, unhandledErrors = []) {
    const sinProceso = archivosSinProceso(unhandledErrors)
    if (sinProceso.length > 0) {
      console.error(
        [
          '',
          '[guardian de recoleccion] FALLO: vitest no pudo arrancar el proceso de estos archivos,',
          'que por eso no se ejecutaron (suele ser transitorio en Windows bajo carga;',
          'repita la ejecucion):',
          ...sinProceso.map((f) => `    ! ${normalizar(relative(this.raiz, f))}`),
          '',
        ].join('\n'),
      )
      process.exitCode = 1
    }

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
