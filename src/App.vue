<script setup>
const navItems = [
  { label: 'Home', to: '/' },
  { label: 'Map', to: '/map' },
  { label: 'Report', to: '/report' },
  { label: 'Profile', to: '/profile' },
]
</script>

<template>
  <div class="app-shell">
    <header class="glass-header">
      <nav class="header-nav" aria-label="Primary navigation">
        <RouterLink class="brand-logo" to="/">Ride<span>Smart</span></RouterLink>
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
          {{ item.label }}
        </RouterLink>
      </nav>
    </header>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>
