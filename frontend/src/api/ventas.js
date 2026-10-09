/** Llamadas a /ventas (plan.md seccion 4.4). */

import http from './http'

export const ventasApi = {
  listar: (params = {}) => http.get('/ventas', { params }).then((r) => r.data),

  obtener: (id) => http.get(`/ventas/${id}`).then((r) => r.data),

  /**
   * Registra y confirma la venta.
   *
   * `items` lleva solo producto_id y cantidad: el precio lo pone el
   * servidor desde el catalogo (RN-VEN-04). Enviarlo desde aqui no
   * tendria efecto, y mandarlo daria la falsa impresion de que el
   * navegador decide el importe.
   */
  registrar: ({ clienteId = null, clienteNombre, clienteTelefono, items }) =>
    http
      .post('/ventas', {
        // RF-79: con un cliente registrado basta su id; el servidor copia
        // su nombre y teléfono (RN-VEN-10). Sin él, cliente ocasional.
        ...(clienteId
          ? { cliente_id: clienteId }
          : { cliente_nombre: clienteNombre, cliente_telefono: clienteTelefono }),
        items: items.map((i) => ({
          producto_id: i.producto_id,
          cantidad: i.cantidad,
        })),
      })
      .then((r) => r.data),

  /** No es un borrado: la venta permanece, con su motivo (RN-VEN-06). */
  anular: (id, motivo) =>
    http.post(`/ventas/${id}/anular`, { motivo }).then((r) => r.data),

  /**
   * RF-76 — la garantía en PDF, generada por el servidor. Como el
   * informe de servicio: `blob` para que axios no corrompa los bytes;
   * el interceptor de http.js desempaqueta el error que llega como blob
   * (el 409 de venta anulada o sin garantía).
   */
  garantiaPdf: (id) =>
    http.get(`/ventas/${id}/garantia`, { responseType: 'blob' }).then((r) => r.data),
}

/** RN-VEN-14: solo una venta confirmada con alguna línea con garantía. */
export function tieneGarantia(venta) {
  return (
    venta?.estado === 'CONFIRMADA' && (venta.items ?? []).some((l) => l.meses_garantia > 0)
  )
}
