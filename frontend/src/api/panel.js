/** Llamadas al panel de indicadores (plan.md seccion 4.4). */

import http from './http'

export const panelApi = {
  /** Un solo endpoint con los cinco indicadores (CU-PAN-01). */
  resumen: () => http.get('/panel/resumen').then((r) => r.data),
}
