/**
 * Codigos de producto (RN-CAT-08, RN-CAT-11).
 *
 * Mismo calculo que backend/catalogo/codigos.py: suma ponderada 1-3 de
 * las doce primeras cifras y complemento a 10.
 */
export function esEan13Valido(codigo) {
  if (!/^[0-9]{13}$/.test(codigo ?? '')) return false
  const suma = [...codigo.slice(0, 12)].reduce(
    (total, cifra, i) => total + Number(cifra) * (i % 2 ? 3 : 1),
    0,
  )
  return (10 - (suma % 10)) % 10 === Number(codigo[12])
}
