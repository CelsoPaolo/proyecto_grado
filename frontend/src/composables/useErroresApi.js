/**
 * Mapea el cuerpo de error de la API a los campos de un formulario.
 *
 * El backend devuelve siempre {codigo, detalle, errores} (plan.md 4.3),
 * donde `errores` es el diccionario de DRF. Este composable lo traduce
 * a algo que cada campo pueda mostrar junto a si mismo (RNF-15), y deja
 * aparte el mensaje general para los errores que no son de un campo.
 */

import { ref } from 'vue'

export function useErroresApi() {
  const erroresDeCampo = ref({})
  const mensajeGeneral = ref(null)
  const codigo = ref(null)

  function limpiar() {
    erroresDeCampo.value = {}
    mensajeGeneral.value = null
    codigo.value = null
  }

  function registrar(error) {
    limpiar()
    if (!error) return

    codigo.value = error.codigo ?? null

    if (error.errores && typeof error.errores === 'object') {
      const mapa = {}
      for (const [campo, mensajes] of Object.entries(error.errores)) {
        mapa[campo] = Array.isArray(mensajes) ? mensajes.join(' ') : String(mensajes)
      }
      erroresDeCampo.value = mapa
    }

    // El mensaje general solo se muestra si no hay errores por campo:
    // repetir "Revise los datos ingresados" encima de campos que ya
    // explican su problema solo añade ruido.
    if (Object.keys(erroresDeCampo.value).length === 0) {
      mensajeGeneral.value = error.detalle ?? 'No se pudo completar la operación.'
    }
  }

  function errorDe(campo) {
    return erroresDeCampo.value[campo] ?? null
  }

  return { erroresDeCampo, mensajeGeneral, codigo, registrar, limpiar, errorDe }
}
