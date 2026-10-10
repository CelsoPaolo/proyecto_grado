/**
 * Guardado de archivos generados por el servidor (RF-68).
 *
 * Una pagina web NO puede escribir donde quiera: la carpeta la decide
 * el navegador, no la aplicacion. Lo que si puede es ABRIR el cuadro de
 * guardado nativo, y entonces es el usuario quien elige Descargas,
 * Documentos o donde prefiera.
 *
 *   - Con showSaveFilePicker (Chrome, Edge): se abre el cuadro de
 *     Windows con el nombre ya propuesto.
 *   - Sin el (Firefox, Safari): descarga normal a la carpeta
 *     predeterminada. No es un fallo, es lo que esos navegadores
 *     permiten, y por eso RF-68 dice «cuando el navegador lo permita».
 *
 * Vive en un composable y no dentro de la vista del detalle para que
 * el dia que haya un comprobante de venta no se reescriba lo mismo.
 */

import { ref } from 'vue'

/** Descarga por enlace temporal: el camino de siempre. */
function descargaDirecta(blob, nombre) {
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  // Sin revocar, el blob queda retenido en memoria mientras viva la
  // pestaña. Se da un margen para que el navegador inicie la descarga.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function useDescarga() {
  const descargando = ref(false)

  /**
   * Pide el archivo y lo guarda.
   *
   * @param obtener  funcion que devuelve el Blob (una llamada a la API)
   * @param nombre   nombre propuesto, p. ej. informe-servicio-12.pdf
   * @returns true si se guardo, false si el usuario cancelo el cuadro
   * @throws el error normalizado de la API si la peticion falla
   */
  async function guardar(
    obtener,
    nombre,
    { tipo = 'application/pdf', extension = '.pdf', descripcion = 'Documento PDF' } = {},
  ) {
    descargando.value = true
    try {
      const blob = await obtener()

      if (window.showSaveFilePicker) {
        let destino
        try {
          destino = await window.showSaveFilePicker({
            suggestedName: nombre,
            types: [
              {
                description: descripcion,
                accept: { [tipo]: [extension] },
              },
            ],
          })
        } catch (error) {
          // Cerrar el cuadro de guardado es una decision del usuario,
          // no un error: no debe acabar en un mensaje rojo. Cualquier
          // otro fallo si se propaga.
          if (error?.name === 'AbortError') return false
          // El cuadro puede estar prohibido por la politica de
          // permisos (por ejemplo dentro de un iframe). En ese caso se
          // cae a la descarga normal en vez de dejar al usuario sin
          // archivo.
          descargaDirecta(blob, nombre)
          return true
        }

        const flujo = await destino.createWritable()
        await flujo.write(blob)
        await flujo.close()
        return true
      }

      descargaDirecta(blob, nombre)
      return true
    } finally {
      descargando.value = false
    }
  }

  return { descargando, guardar }
}
