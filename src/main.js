import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { getCurrentAuthIdentity, getRideSmartUserId } from './services/api'
import './style.css'

getRideSmartUserId()
getCurrentAuthIdentity().catch(() => {})

createApp(App).use(router).mount('#app')
