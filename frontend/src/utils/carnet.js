/**
 * Formato del carnet (RN-CLI-02, RF-101, spec.md v1.5, PA-10).
 *
 * La misma regla que `carnet_valido` en `core/validadores.py`: de 7 u 8
 * dígitos, solo números y sin complemento. Aquí solo sirve para avisar
 * antes de enviar; quien decide es el servidor (RNF-05).
 */

export const MAXIMO_DIGITOS_CARNET = 8
export const MENSAJE_CARNET = 'El carnet debe tener 7 u 8 dígitos, solo números.'

/** Lo que se escribe en el campo: solo dígitos, como máximo 8. */
export function soloDigitosDeCarnet(texto) {
  return String(texto ?? '')
    .replace(/[^0-9]/g, '')
    .slice(0, MAXIMO_DIGITOS_CARNET)
}

export function carnetValido(texto) {
  return /^[0-9]{7,8}$/.test(String(texto ?? ''))
}
