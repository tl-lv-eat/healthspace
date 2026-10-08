import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'

import App from './App.vue'
import router from './router'
import './styles/global.css'
import { setUnauthorizedHandler } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)

setUnauthorizedHandler(() => {
  useAuthStore().clearSession()
  if (router.currentRoute.value.name !== 'login') {
    void router.push({ name: 'login' })
  }
})

app.use(Vant)
app.mount('#app')
