/** Llamadas a /reportes (plan.md seccion 4.4). Solo el Administrador. */

import http from './http'

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

export const reportesApi = {
  /** El reporte del rango en JSON (RF-90 a RF-94). */
  obtener: ({ desde, hasta }) => http.get('/reportes', { params: { desde, hasta } }).then((r) => r.data),

  /** RF-95. `blob`, como el informe de servicio: axios no debe tocar los bytes. */
  pdf: ({ desde, hasta }) =>
    http.get('/reportes/pdf', { params: { desde, hasta }, responseType: 'blob' }).then((r) => r.data),

  /** RF-96. */
  xlsx: ({ desde, hasta }) =>
    http.get('/reportes/xlsx', { params: { desde, hasta }, responseType: 'blob' }).then((r) => r.data),
}

export const TIPO_XLSX = XLSX
