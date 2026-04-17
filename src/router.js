import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'map', component: () => import('./views/MapView.vue') },
  { path: '/map', redirect: '/' },
  { path: '/report', name: 'report', component: () => import('./views/ReportView.vue') },
  { path: '/profile', name: 'profile', component: () => import('./views/ProfileView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
