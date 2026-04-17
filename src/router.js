import { createRouter, createWebHistory } from 'vue-router'
import AssessView from './views/AssessView.vue'
import RoutesView from './views/RoutesView.vue'
import ReportView from './views/ReportView.vue'
import CommunityView from './views/CommunityView.vue'
import ProfileView from './views/ProfileView.vue'

const routes = [
  { path: '/', name: 'assess', component: AssessView },
  { path: '/routes', name: 'routes', component: RoutesView },
  { path: '/report', name: 'report', component: ReportView },
  { path: '/community', name: 'community', component: CommunityView },
  { path: '/profile', name: 'profile', component: ProfileView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
