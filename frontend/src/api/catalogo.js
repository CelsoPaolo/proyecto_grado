/** Llamadas al catalogo (plan.md seccion 4.4). */

import http from './http'

export const categoriasApi = {
  listar: (params = {}) =>
    http.get('/categorias', { params }).then((r) => r.data),

  crear: (datos) => http.post('/categorias', datos).then((r) => r.data),

  actualizar: (id, datos) =>
    http.patch(`/categorias/${id}`, datos).then((r) => r.data),

  eliminar: (id) => http.delete(`/categorias/${id}`),
}

/**
 * Los productos viajan como multipart solo cuando llevan imagen: enviar
 * siempre multipart obligaria a serializar numeros y booleanos a texto
 * y complicaria la validacion del lado del servidor sin necesidad.
 */
function cuerpoDe(datos) {
  const llevaArchivo = datos.imagen instanceof File
  if (!llevaArchivo) {
    const { imagen, ...resto } = datos
    return { cuerpo: resto, config: {} }
  }

  // La cadena vacia SI viaja: es como se vacia un campo de texto (la
  // descripcion, el codigo de fabrica). Omitirla hacia que, al editar un
  // producto subiendo a la vez una imagen nueva, vaciar esos campos no
  // tuviera efecto. Solo se omite lo que no tiene valor.
  const formulario = new FormData()
  for (const [clave, valor] of Object.entries(datos)) {
    if (valor !== null && valor !== undefined) {
      formulario.append(clave, valor)
    }
  }
  return {
    cuerpo: formulario,
    config: { headers: { 'Content-Type': 'multipart/form-data' } },
  }
}

export const productosApi = {
  listar: (params = {}) =>
    http.get('/productos', { params }).then((r) => r.data),

  obtener: (id) => http.get(`/productos/${id}`).then((r) => r.data),

  crear: (datos) => {
    const { cuerpo, config } = cuerpoDe(datos)
    return http.post('/productos', cuerpo, config).then((r) => r.data)
  },

  actualizar: (id, datos) => {
    const { cuerpo, config } = cuerpoDe(datos)
    return http.patch(`/productos/${id}`, cuerpo, config).then((r) => r.data)
  },

  /** Retira el producto del catalogo: no lo borra (CU-CAT-04). */
  retirar: (id) => http.delete(`/productos/${id}`).then((r) => r.data),
}
