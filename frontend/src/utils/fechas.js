/**
 * Fechas para los filtros de la API.
 *
 * La API espera AAAA-MM-DD y filtra por el dia en hora de Bolivia.
 * toISOString() no sirve: convierte a UTC, y una fecha elegida a las
 * 21:00 en La Paz ya seria del dia siguiente.
 */
export function fechaIso(fecha) {
  if (!fecha) return null
  const f = new Date(fecha)
  const mes = String(f.getMonth() + 1).padStart(2, '0')
  const dia = String(f.getDate()).padStart(2, '0')
  return `${f.getFullYear()}-${mes}-${dia}`
}

const fechaHora = new Intl.DateTimeFormat('es-BO', { dateStyle: 'short', timeStyle: 'short' })

export function comoFechaHora(valor) {
  return valor ? fechaHora.format(new Date(valor)) : ''
}
