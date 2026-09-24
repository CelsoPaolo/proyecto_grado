import { createApp } from 'vue'
import { createPinia } from 'pinia'

import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import 'primeicons/primeicons.css'

import router from './router'
import { localeEs } from './locale/es'
import './assets/main.css'
import App from './App.vue'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.use(PrimeVue, {
  theme: { preset: Aura, options: { darkModeSelector: false } },
  locale: localeEs,
})

// ConfirmationService: toda accion destructiva pide confirmacion (RNF-14).
// ToastService: informa el resultado de cada operacion (RNF-14).
app.use(ConfirmationService)
app.use(ToastService)

app.mount('#app')
