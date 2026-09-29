/**
 * Cliente HTTP unico del sistema (plan.md seccion 7.2).
 *
 * Es la UNICA puerta del frontend hacia los datos: no existe acceso
 * directo a la base ni ningun otro canal (RNF-20). Que todo pase por
 * aqui es lo que permite resolver en un solo lugar la autenticacion,
 * el refresco de token y el formato de error.
 *
 * Concentra tres comportamientos para que ninguna vista tenga que
 * ocuparse de ellos:
 *
 *   1. Adjuntar el token de acceso a cada peticion.
 *   2. Renovar el token ante un 401, UNA sola vez aunque haya varias
 *      peticiones en vuelo.
 *   3. Normalizar el cuerpo de error al formato de plan.md 4.3.
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const http = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

/** Rutas que no llevan token: quien aun no lo tiene no puede presentarlo. */
const RUTAS_PUBLICAS = ['/auth/login', '/auth/refresh']

/*
 * Estado del refresco en curso.
 *
 * `refrescoEnCurso` guarda la promesa del refresco activo. Las
 * peticiones que reciban un 401 mientras esta pendiente se enganchan a
 * ella en lugar de lanzar su propio refresco: sin esto, cinco
 * peticiones simultaneas dispararian cinco refrescos, y con rotacion de
 * tokens activada los cuatro ultimos usarian un refresh ya invalidado
 * y cerrarian la sesion del usuario sin motivo.
 */
let refrescoEnCurso = null

/** Ganchos que inyecta el store de sesion para evitar una dependencia circular. */
let ganchos = {
  obtenerAccess: () => null,
  obtenerRefresh: () => null,
  guardarTokens: () => {},
  cerrarSesion: () => {},
}

export function conectarSesion(nuevosGanchos) {
  ganchos = { ...ganchos, ...nuevosGanchos }
}

// ── 1. Interceptor de peticion ────────────────────────────────────────
http.interceptors.request.use((config) => {
  const esPublica = RUTAS_PUBLICAS.some((ruta) => config.url?.startsWith(ruta))
  const access = ganchos.obtenerAccess()

  if (!esPublica && access) {
    config.headers.Authorization = `Bearer ${access}`
  }
  return config
})

async function renovarToken() {
  const refresh = ganchos.obtenerRefresh()
  if (!refresh) throw new Error('No hay refresh token')

  // Instancia limpia: si usara `http`, su propio 401 volveria a entrar
  // en el interceptor y provocaria una recursion infinita.
  const { data } = await axios.post(`${BASE_URL}/auth/refresh`, { refresh })
  ganchos.guardarTokens({ access: data.access, refresh: data.refresh ?? refresh })
  return data.access
}

// ── 2 y 3. Interceptor de respuesta ───────────────────────────────────
http.interceptors.response.use(
  (respuesta) => respuesta,
  async (error) => {
    const original = error.config
    const estado = error.response?.status

    const puedeReintentar =
      estado === 401 &&
      original &&
      !original._reintentado &&
      !RUTAS_PUBLICAS.some((ruta) => original.url?.startsWith(ruta))

    if (puedeReintentar) {
      original._reintentado = true

      try {
        // Un unico refresco compartido por todas las peticiones que
        // fallaron a la vez.
        refrescoEnCurso = refrescoEnCurso ?? renovarToken()
        const access = await refrescoEnCurso
        original.headers.Authorization = `Bearer ${access}`
        return http(original)
      } catch (fallo) {
        // El refresco fallo: la cuenta fue bloqueada, el refresh
        // caduco o se cerro sesion en otro sitio. No hay forma de
        // recuperar; se cierra la sesion.
        ganchos.cerrarSesion()
        return Promise.reject(normalizarError(fallo))
      } finally {
        refrescoEnCurso = null
      }
    }

    return Promise.reject(normalizarError(error))
  },
)

/**
 * Normaliza cualquier fallo al formato uniforme de plan.md 4.3.
 *
 * Incluye los que no vienen del backend (red caida, tiempo agotado),
 * para que las vistas tengan un unico camino de tratamiento.
 */
export function normalizarError(error) {
  const cuerpo = error.response?.data

  if (cuerpo?.codigo) {
    return {
      codigo: cuerpo.codigo,
      detalle: cuerpo.detalle,
      errores: cuerpo.errores ?? null,
      estado: error.response.status,
    }
  }

  if (!error.response) {
    return {
      codigo: 'SIN_CONEXION',
      detalle: 'No se pudo contactar con el servidor. Revise su conexión.',
      errores: null,
      estado: 0,
    }
  }

  return {
    codigo: 'ERROR_INTERNO',
    detalle: 'Ocurrió un error inesperado. Inténtelo nuevamente.',
    errores: null,
    estado: error.response.status,
  }
}

export default http
