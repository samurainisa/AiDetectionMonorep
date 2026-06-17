import { createApp } from 'vue'
import { createPinia } from 'pinia'

// Стили - импортируем первыми
import './assets/tailwind.css'
import './assets/styles.scss'
import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './router'

// PrimeVue
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'

// PrimeVue сервисы
import Tooltip from 'primevue/tooltip'
import ToastService from 'primevue/toastservice'

const app = createApp(App)

// Pinia
app.use(createPinia())

// Router
app.use(router)

// PrimeVue
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',
      darkModeSelector: 'system',
      cssLayer: false,
    },
  },
})

// Toast service
app.use(ToastService)

// Директивы
app.directive('tooltip', Tooltip)

app.mount('#app')
