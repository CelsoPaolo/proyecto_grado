/** Llamadas a /clientes (plan.md seccion 4.4). */

import http from './http'

export const clientesApi = {
  /** Lista SIN carnet (RN-CLI-06). Filtros: buscar, activo, page. */
  listar: (params = {}) => http.get('/clientes', { params }).then((r) => r.data),

  /** Detalle: la única respuesta de la API que trae el carnet (RF-89). */
  obtener: (id) => http.get(`/clientes/${id}`).then((r) => r.data),

  crear: (datos) => http.post('/clientes', datos).then((r) => r.data),

  actualizar: (id, datos) => http.patch(`/clientes/${id}`, datos).then((r) => r.data),

  /** Solo el Administrador (RN-CLI-07). No hay borrado (RN-CLI-03). */
  desactivar: (id) => http.post(`/clientes/${id}/desactivar`).then((r) => r.data),

  reactivar: (id) => http.post(`/clientes/${id}/reactivar`).then((r) => r.data),
}
