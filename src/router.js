import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('./views/HomeView.vue') },
  { path: '/map', name: 'map', component: () => import('./views/MapView.vue') },
  { path: '/report', name: 'report', component: () => import('./views/ReportView.vue') },
  { path: '/profile', name: 'profile', component: () => import('./views/ProfileView.vue') },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
