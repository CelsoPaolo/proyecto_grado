/** Llamadas a /auth/ (plan.md seccion 4.4). */

import http from './http'

export const authApi = {
  login: (username, password) =>
    http.post('/auth/login', { username, password }).then((r) => r.data),

  logout: (refresh) => http.post('/auth/logout', { refresh }),

  yo: () => http.get('/auth/me').then((r) => r.data),

  cambiarPasswordPropia: (passwordActual, passwordNueva) =>
    http.post('/auth/me/password', {
      password_actual: passwordActual,
      password_nueva: passwordNueva,
    }),
}
