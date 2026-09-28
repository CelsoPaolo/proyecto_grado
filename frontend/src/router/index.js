/**
 * Rutas y control de acceso de la interfaz (RF-06).
 *
 * Cada ruta declara en `meta.roles` quien puede verla, segun la matriz
 * de spec.md seccion 4.4, y el menu lateral se construye A PARTIR DE
 * ESTA MISMA DEFINICION (ver `menuPara`). Asi, lo que se muestra y lo
 * que se permite navegar no pueden divergir: no hay dos listas que
 * mantener sincronizadas.
 *
 * Esto es USABILIDAD, no seguridad (RN-ACC-04). Un usuario que escriba
 * la URL a mano igual recibira 403 del servidor. El router solo evita
 * mostrar puertas que no se pueden abrir.
 */

import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const ADMIN = 'ADMINISTRADOR'
const VENTAS = 'VENTAS'
const SERVICIOS = 'SERVICIOS'

export const rutas = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { publica: true, titulo: 'Iniciar sesión' },
  },
  {
    path: '/',
    redirect: () => ({ name: 'inicio' }),
  },
  {
    path: '/inicio',
    name: 'inicio',
    component: () => import('@/views/InicioView.vue'),
    meta: { roles: [ADMIN, VENTAS, SERVICIOS], titulo: 'Inicio', icono: 'pi pi-home' },
  },
  {
    path: '/mi-cuenta/password',
    name: 'cambiar-password',
    component: () => import('@/views/auth/CambiarPasswordView.vue'),
    meta: {
      roles: [ADMIN, VENTAS, SERVICIOS],
      titulo: 'Cambiar contraseña',
      enMenu: false,
    },
  },
  {
    path: '/catalogo',
    name: 'catalogo',
    component: () => import('@/views/catalogo/ProductosView.vue'),
    meta: { roles: [ADMIN, VENTAS], titulo: 'Catálogo', icono: 'pi pi-box' },
  },
  {
    path: '/ventas',
    name: 'ventas',
    component: () => import('@/views/ventas/VentasView.vue'),
    meta: { roles: [ADMIN, VENTAS], titulo: 'Ventas', icono: 'pi pi-shopping-cart' },
  },
  {
    path: '/ventas/nueva',
    name: 'venta-nueva',
    component: () => import('@/views/ventas/RegistrarVentaView.vue'),
    meta: { roles: [ADMIN, VENTAS], titulo: 'Registrar venta', enMenu: false },
  },
  {
    path: '/ventas/:id',
    name: 'venta-detalle',
    component: () => import('@/views/ventas/VentaDetalleView.vue'),
    meta: { roles: [ADMIN, VENTAS], titulo: 'Detalle de venta', enMenu: false },
  },
  {
    path: '/categorias',
    name: 'categorias',
    component: () => import('@/views/catalogo/CategoriasView.vue'),
    meta: { roles: [ADMIN], titulo: 'Categorías', icono: 'pi pi-tags' },
  },
  {
    path: '/usuarios',
    name: 'usuarios',
    component: () => import('@/views/usuarios/UsuariosView.vue'),
    meta: { roles: [ADMIN], titulo: 'Usuarios', icono: 'pi pi-users' },
  },
  {
    path: '/configuracion',
    name: 'configuracion',
    component: () => import('@/views/configuracion/ConfiguracionView.vue'),
    meta: { roles: [ADMIN], titulo: 'Configuración', icono: 'pi pi-cog' },
  },
  {
    path: '/sin-permiso',
    name: 'sin-permiso',
    component: () => import('@/views/SinPermisoView.vue'),
    meta: { roles: [ADMIN, VENTAS, SERVICIOS], titulo: 'Sin permiso', enMenu: false },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes: rutas,
})

/**
 * Construye el menu lateral para un rol, a partir de las mismas rutas.
 *
 * Una ruta entra en el menu si admite el rol, tiene titulo e icono y no
 * esta marcada con `enMenu: false`.
 */
export function menuPara(rol) {
  if (!rol) return []
  return rutas
    .filter(
      (ruta) =>
        ruta.meta?.roles?.includes(rol) &&
        ruta.meta.enMenu !== false &&
        ruta.meta.icono,
    )
    .map((ruta) => ({
      label: ruta.meta.titulo,
      icon: ruta.meta.icono,
      name: ruta.name,
      to: ruta.path,
    }))
}

/** Decide si un rol puede entrar a una ruta. */
export function puedeEntrar(ruta, rol) {
  if (ruta.meta?.publica) return true
  if (!rol) return false
  return ruta.meta?.roles?.includes(rol) ?? false
}

router.beforeEach(async (destino) => {
  const auth = useAuthStore()

  // Al abrir la aplicacion solo hay un refresh guardado: hay que
  // recuperar los datos del usuario antes de decidir nada.
  if (!auth.autenticado && auth.refresh) {
    await auth.restaurarSesion()
  }

  if (destino.meta?.publica) {
    // Quien ya tiene sesion no necesita ver el formulario de ingreso.
    return auth.autenticado ? { name: 'inicio' } : true
  }

  if (!auth.autenticado) {
    return { name: 'login', query: { redirigir: destino.fullPath } }
  }

  if (!puedeEntrar(destino, auth.rol)) {
    return { name: 'sin-permiso' }
  }

  return true
})

export default router
