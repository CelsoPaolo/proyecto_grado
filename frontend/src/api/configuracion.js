/** Llamadas a /configuracion (plan.md seccion 4.4). Solo Administrador. */

import http from './http'

export const configuracionApi = {
  obtener: () => http.get('/configuracion').then((r) => r.data),

  actualizarUmbral: (umbral) =>
    http
      .patch('/configuracion', { umbral_stock_bajo: umbral })
      .then((r) => r.data),
}
