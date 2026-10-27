/**
 * Formato del teléfono (RN-CLI-09, RF-100, spec.md v1.5).
 *
 * La misma regla que `core/validadores.py` en el servidor, que es quien
 * decide (RNF-05). Aquí solo sirve para avisar antes de enviar, junto al
 * campo (RNF-15), con el mismo mensaje.
 */

export const DIGITOS_TELEFONO = 8
export const MENSAJE_TELEFONO = 'El teléfono debe tener exactamente 8 dígitos, solo números.'

/** Lo que se escribe en el campo: solo dígitos, como máximo 8. */
export function soloDigitosDeTelefono(texto) {
  return String(texto ?? '')
    .replace(/[^0-9]/g, '')
    .slice(0, DIGITOS_TELEFONO)
}

export function telefonoValido(texto) {
  return /^[0-9]{8}$/.test(String(texto ?? ''))
}
