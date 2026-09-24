/** Llamadas a /usuarios/ (plan.md seccion 4.4). Solo Administrador. */

import http from './http'

export const usuariosApi = {
  listar: (params = {}) =>
    http.get('/usuarios', { params }).then((r) => r.data),

  obtener: (id) => http.get(`/usuarios/${id}`).then((r) => r.data),

  crear: (datos) => http.post('/usuarios', datos).then((r) => r.data),

  actualizar: (id, datos) =>
    http.patch(`/usuarios/${id}`, datos).then((r) => r.data),

  bloquear: (id) => http.post(`/usuarios/${id}/bloquear`).then((r) => r.data),

  desbloquear: (id) =>
    http.post(`/usuarios/${id}/desbloquear`).then((r) => r.data),

  restablecerPassword: (id, passwordNueva) =>
    http.post(`/usuarios/${id}/restablecer-password`, {
      password_nueva: passwordNueva,
    }),
}
