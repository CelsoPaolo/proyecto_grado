import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    // El limite por defecto de vitest (5 s por prueba) sirve para
    // detectar pruebas colgadas, no para medir rendimiento. Con el
    // portatil en bateria la CPU queda en su frecuencia base y la suite
    // tarda unas 5 veces mas (medido el 2026-10-09: el frontend de la
    // v1.3, sin cambios, pasa de 5-6 s a 31 s). La primera prueba de un
    // archivo, que paga la carga de los componentes, superaba los 5 s
    // sin que nada estuviera roto. 15 s mantiene la deteccion de
    // cuelgues y deja que la suite pase igual enchufada que en bateria,
    // como podria estar el dia de la defensa.
    testTimeout: 15000,
  },
})
