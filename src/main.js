import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { getRideSmartUserId } from './services/api'
import './style.css'

getRideSmartUserId()

createApp(App).use(router).mount('#app')
