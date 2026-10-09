/**
 * Permisos de la interfaz, derivados del rol del usuario.
 *
 * Refleja la matriz de spec.md seccion 4.4. Es USABILIDAD, no
 * seguridad: evita mostrar puertas que no se pueden abrir. La
 * autorizacion real vive en el servidor (RN-ACC-04).
 */

import { storeToRefs } from 'pinia'
import { computed } from 'vue'

import { useAuthStore } from '@/stores/auth'

export function usePermisos() {
  const store = useAuthStore()
  const { rol, esAdministrador, puedeVender, puedeAtenderServicios } =
    storeToRefs(store)

  return {
    rol,
    esAdministrador,
    puedeVender,
    puedeAtenderServicios,

    // Catalogo: gestion solo Administrador, consulta tambien Ventas.
    puedeGestionarCatalogo: esAdministrador,
    puedeConsultarCatalogo: puedeVender,

    // Inventario: ajustar y consultar movimientos, solo Administrador
    // (RN-MOV-06). Ventas consulta el catalogo, pero no su libro.
    puedeGestionarInventario: esAdministrador,

    // Ventas: el historial propio lo ve quien vende; todas, el Administrador.
    puedeRegistrarVentas: puedeVender,
    puedeVerTodasLasVentas: esAdministrador,

    // Servicios: espacio compartido dentro del area (RN-SER-15).
    puedeGestionarServicios: puedeAtenderServicios,

    puedeGestionarUsuarios: esAdministrador,
    puedeVerPanel: esAdministrador,
    puedeConfigurar: esAdministrador,

    tieneAlgunRol: computed(() => rol.value !== null),
  }
}
