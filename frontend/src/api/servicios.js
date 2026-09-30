/** Llamadas a /solicitudes (plan.md seccion 4.4). */

import http from './http'

export const TIPOS_SERVICIO = [
  { label: 'Mantenimiento', value: 'MANTENIMIENTO', domicilio: false },
  { label: 'Reparación', value: 'REPARACION', domicilio: false },
  { label: 'Instalación de redes', value: 'REDES', domicilio: true },
  { label: 'Videovigilancia', value: 'VIDEOVIGILANCIA', domicilio: true },
]

export const ESTADOS_SOLICITUD = [
  { label: 'Registrada', value: 'REGISTRADA' },
  { label: 'En atención', value: 'EN_ATENCION' },
  { label: 'Finalizada', value: 'FINALIZADA' },
  { label: 'Cancelada', value: 'CANCELADA' },
]

/** RN-SER-01: qué tipos se atienden a domicilio y por tanto exigen dirección. */
export function exigeDireccion(tipo) {
  return TIPOS_SERVICIO.find((t) => t.value === tipo)?.domicilio ?? false
}

export const serviciosApi = {
  listar: (params = {}) =>
    http.get('/solicitudes', { params }).then((r) => r.data),

  obtener: (id) => http.get(`/solicitudes/${id}`).then((r) => r.data),

  /**
   * No envía `modalidad`: la deriva el servidor del tipo (RN-SER-01).
   * Tampoco monto ni técnico: son del Administrador (RF-57).
   */
  registrar: ({ clienteNombre, clienteTelefono, tipo, descripcion, direccion }) =>
    http
      .post('/solicitudes', {
        cliente_nombre: clienteNombre,
        cliente_telefono: clienteTelefono,
        tipo,
        descripcion,
        ...(exigeDireccion(tipo) ? { direccion } : {}),
      })
      .then((r) => r.data),

  /** Solo Administrador (RF-56). Monto, técnico, o ambos. */
  cotizar: (id, { monto, tecnico }) =>
    http
      .post(`/solicitudes/${id}/cotizar`, {
        ...(monto !== undefined && monto !== null ? { monto_cobrado: monto } : {}),
        ...(tecnico !== undefined ? { tecnico } : {}),
      })
      .then((r) => r.data),

  iniciar: (id) => http.post(`/solicitudes/${id}/iniciar`).then((r) => r.data),

  finalizar: (id, observaciones) =>
    http
      .post(`/solicitudes/${id}/finalizar`, { observaciones })
      .then((r) => r.data),

  cancelar: (id, motivo) =>
    http.post(`/solicitudes/${id}/cancelar`, { motivo }).then((r) => r.data),

  /**
   * RF-67 — el informe en PDF, generado por el servidor.
   *
   * `responseType: 'blob'` hace que axios no intente interpretar los
   * bytes como texto; sin él, el PDF llegaría corrompido. El
   * interceptor de http.js sabe desempaquetar el cuerpo de error que
   * llega como blob cuando la petición falla.
   */
  informePdf: (id) =>
    http
      .get(`/solicitudes/${id}/pdf`, { responseType: 'blob' })
      .then((r) => r.data),
}
