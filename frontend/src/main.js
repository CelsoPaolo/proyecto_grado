import { createApp } from 'vue'
import { createPinia } from 'pinia'

import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import { definePreset } from '@primeuix/themes'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import 'primeicons/primeicons.css'

import router from './router'
import { localeEs } from './locale/es'
import './assets/main.css'
import App from './App.vue'

/**
 * Paleta de PC-Solution: negro y morado.
 *
 * ESTE ES EL SITIO ÚNICO donde viven los colores. Los componentes leen
 * los tokens con var(--p-*), así que cambiar algo aquí se propaga a
 * toda la aplicación sin tocar ni un archivo .vue.
 *
 * Decisión deliberada: los estados semánticos NO pasan a morado.
 * El sistema usa el color como información, no como decoración —
 * existencias agotadas en rojo, sin cotizar en ámbar, confirmado en
 * verde—. Volverlo todo morado borraría la señal de «esto está mal».
 * El morado queda para identidad, navegación y acciones primarias.
 */
const PcSolution = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#f5f3ff',
      100: '#ede9fe',
      200: '#ddd6fe',
      300: '#c4b5fd',
      400: '#a78bfa',
      500: '#8b5cf6',
      600: '#7c3aed',
      700: '#6d28d9',
      800: '#5b21b6',
      900: '#4c1d95',
      950: '#2e1065',
    },
    colorScheme: {
      light: {
        primary: {
          // 600 sobre blanco da 5,3:1: pasa AA para texto normal.
          // El 500 (#8b5cf6) se queda en 3,9:1, así que no se usa como
          // color de acción, solo como acento o borde.
          color: '{primary.600}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.700}',
          activeColor: '{primary.800}',
        },
        highlight: {
          background: '{primary.50}',
          focusBackground: '{primary.100}',
          color: '{primary.700}',
          focusColor: '{primary.800}',
        },
        // Grises fríos hacia el negro. El área de trabajo sigue clara
        // (decisión: cromo oscuro, fondo claro); el negro se aplica a
        // la barra lateral y la cabecera desde AppLayout.
        surface: {
          0: '#ffffff',
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#09090b',
        },
      },
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.use(PrimeVue, {
  theme: { preset: PcSolution, options: { darkModeSelector: false } },
  locale: localeEs,
})

// ConfirmationService: toda accion destructiva pide confirmacion (RNF-14).
// ToastService: informa el resultado de cada operacion (RNF-14).
app.use(ConfirmationService)
app.use(ToastService)

app.mount('#app')
