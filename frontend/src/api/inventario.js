/** Llamadas al libro de movimientos de stock (plan.md seccion 4.4). */

import http from './http'

export const inventarioApi = {
  /** CU-CAT-08 (RF-82). Filtros: producto, tipo, desde, hasta. */
  listarMovimientos: (params = {}) =>
    http.get('/movimientos-stock', { params }).then((r) => r.data),

  /** Historial de un producto (RF-83), del mas reciente al mas antiguo. */
  historialDe: (productoId, params = {}) =>
    http.get(`/productos/${productoId}/movimientos`, { params }).then((r) => r.data),

  /**
   * CU-CAT-07 (RF-73). Solo viajan lo contado y el motivo: la diferencia
   * la calcula el servidor contra las existencias de ESE instante, no
   * contra las que mostraba la pantalla (plan.md 6.5).
   */
  ajustarExistencias: (productoId, { cantidadReal, motivo }) =>
    http
      .post(`/productos/${productoId}/ajustar-existencias`, {
        cantidad_real: cantidadReal,
        motivo,
      })
      .then((r) => r.data),
}

/** Los tipos de movimiento, con el texto que ve el usuario (RN-MOV-02). */
export const TIPOS_DE_MOVIMIENTO = [
  { label: 'Saldo inicial', value: 'SALDO_INICIAL' },
  { label: 'Alta', value: 'ALTA' },
  { label: 'Venta', value: 'VENTA' },
  { label: 'Anulación', value: 'ANULACION' },
  { label: 'Ajuste manual', value: 'AJUSTE' },
]
