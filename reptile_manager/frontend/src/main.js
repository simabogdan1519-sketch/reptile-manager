import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import i18nPlugin from './i18n'
import App from './App.vue'
import '@fontsource-variable/bricolage-grotesque'
import '@fontsource-variable/instrument-sans'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import './style.css'
import { registerServiceWorker } from './utils/pwa'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18nPlugin)
app.mount('#app')
registerServiceWorker()
