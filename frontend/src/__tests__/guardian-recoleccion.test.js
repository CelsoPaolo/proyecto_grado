/**
 * Pruebas del guardian de recoleccion (guardian-recoleccion.js).
 *
 * El guardian protege la suite, y ya tuvo un fallo propio: su primera
 * version confundia el valor de `--exclude` con un filtro y se inhibia
 * justo cuando debia actuar. Estas pruebas lo ejercitan sin vitest de
 * por medio, con archivos falsos en una carpeta temporal y los errores
 * tal como los emite vitest, porque el caso que mas importa —un proceso
 * que no arranca— no se puede provocar a voluntad.
 */

import { mkdtempSync, rmSync, writeFileSync, mkdirSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import GuardianRecoleccion from '../../guardian-recoleccion.js'

let raiz
let argvOriginal
let salida

beforeEach(() => {
  raiz = mkdtempSync(join(tmpdir(), 'guardian-'))
  mkdirSync(join(raiz, 'src'))
  for (const nombre of ['a.test.js', 'b.test.js', 'c.test.js']) {
    writeFileSync(join(raiz, 'src', nombre), '')
  }
  argvOriginal = process.argv
  process.argv = ['node', 'vitest', 'run']
  salida = vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.spyOn(console, 'log').mockImplementation(() => {})
})

afterEach(() => {
  process.argv = argvOriginal
  // Imprescindible: si no, la propia suite terminaria con salida 1.
  process.exitCode = undefined
  vi.restoreAllMocks()
  rmSync(raiz, { recursive: true, force: true })
})

function guardian() {
  const g = new GuardianRecoleccion()
  g.onInit({ config: { root: raiz } })
  return g
}

const modulo = (nombre) => ({ moduleId: join(raiz, 'src', nombre) })
const textoImpreso = () => salida.mock.calls.flat().join('\n')

describe('recoleccion', () => {
  it('con todos los archivos recogidos no hace nada', () => {
    guardian().onTestRunEnd(['a.test.js', 'b.test.js', 'c.test.js'].map(modulo), [])

    expect(process.exitCode).toBeUndefined()
    expect(salida).not.toHaveBeenCalled()
  })

  it('si faltan archivos falla y lista recogidos y faltantes', () => {
    guardian().onTestRunEnd([modulo('a.test.js')], [])

    expect(process.exitCode).toBe(1)
    const texto = textoImpreso()
    expect(texto).toContain('+ src/a.test.js')
    expect(texto).toContain('- src/b.test.js')
    expect(texto).toContain('- src/c.test.js')
  })

  it('una ejecucion filtrada a proposito no falla', () => {
    process.argv = ['node', 'vitest', 'run', 'src/a.test.js']

    guardian().onTestRunEnd([modulo('a.test.js')], [])

    expect(process.exitCode).toBeUndefined()
  })

  it('el valor de una opcion no se toma por filtro', () => {
    // El fallo de la primera version.
    process.argv = ['node', 'vitest', 'run', '--exclude', '**/{b,c}.test.js']

    guardian().onTestRunEnd([modulo('a.test.js')], [])

    expect(process.exitCode).toBe(1)
  })
})

describe('proceso que no arranca', () => {
  it('nombra los archivos cuyo proceso no arranco', () => {
    const error = {
      message:
        `[vitest-pool]: Failed to start forks worker for test files ${join(raiz, 'src', 'b.test.js')}.`,
    }

    guardian().onTestRunEnd(['a.test.js', 'c.test.js'].map(modulo), [error])

    expect(process.exitCode).toBe(1)
    const texto = textoImpreso()
    expect(texto).toContain('no pudo arrancar el proceso')
    expect(texto).toContain('! src/b.test.js')
  })

  it('otros errores no se confunden con un arranque fallido', () => {
    guardian().onTestRunEnd(
      ['a.test.js', 'b.test.js', 'c.test.js'].map(modulo),
      [{ message: 'TypeError: algo distinto' }],
    )

    expect(textoImpreso()).not.toContain('no pudo arrancar')
  })
})
