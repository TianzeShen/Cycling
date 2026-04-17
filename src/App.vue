<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { label: 'Map', to: '/' },
  { label: 'Report', to: '/report' },
  { label: 'Profile', to: '/profile' },
]

const pageLabel = computed(() => navItems.find((item) => item.to === route.path)?.label || 'Map')
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" aria-label="Primary navigation">
      <RouterLink class="brand" to="/" aria-label="RideSmart home">
        <span class="brand-mark">R</span>
        <span>
          <strong>RideSmart</strong>
          <small>Safe urban cycling</small>
        </span>
      </RouterLink>

      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div>
          <span class="eyebrow">Melbourne web app</span>
          <h1>{{ pageLabel }}</h1>
        </div>
        <RouterLink class="topbar-action" to="/report">One-tap report</RouterLink>
      </header>

      <main>
        <RouterView />
      </main>
    </div>
  </div>
</template>
