/**
 * Atajos del reporte (RN-REP-01, plan.md 4.4).
 *
 * Los resuelve el FRONTEND en fechas concretas: el servidor solo conoce
 * rangos. `hoy` se recibe como parámetro para que las pruebas fijen el
 * día sin tocar el reloj.
 *
 *   hoy          el día en curso
 *   esta semana  desde el LUNES de la semana en curso hasta hoy
 *   este mes     desde el día 1 del mes en curso hasta hoy
 */

import { fechaIso } from './fechas'

function soloFecha(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

export function rangoHoy(hoy = new Date()) {
  const d = soloFecha(hoy)
  return { desde: fechaIso(d), hasta: fechaIso(d) }
}

export function rangoEstaSemana(hoy = new Date()) {
  const d = soloFecha(hoy)
  // getDay(): 0 domingo … 6 sábado. La semana empieza el lunes, así que
  // el domingo pertenece a la semana que empezó seis días antes.
  const desdeLunes = (d.getDay() + 6) % 7
  const lunes = new Date(d.getFullYear(), d.getMonth(), d.getDate() - desdeLunes)
  return { desde: fechaIso(lunes), hasta: fechaIso(d) }
}

export function rangoEsteMes(hoy = new Date()) {
  const d = soloFecha(hoy)
  return { desde: fechaIso(new Date(d.getFullYear(), d.getMonth(), 1)), hasta: fechaIso(d) }
}

export const ATAJOS = [
  { label: 'Hoy', value: 'hoy', calcular: rangoHoy },
  { label: 'Esta semana', value: 'semana', calcular: rangoEstaSemana },
  { label: 'Este mes', value: 'mes', calcular: rangoEsteMes },
]
