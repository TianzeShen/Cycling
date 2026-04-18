<script setup>
defineProps({
  route: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <article class="route-card-vibrant">
    <div class="route-card-main">
      <div
        class="route-dot"
        :style="{
          background:
            route.tone === 'green' ? 'var(--primary)' : route.tone === 'yellow' ? '#f59e0b' : '#ef4444',
        }"
      ></div>
      <div>
        <h3>{{ route.name }}</h3>
        <p>{{ route.distance }} · {{ route.time }}</p>
      </div>
    </div>
    <div
      class="pill"
      :style="{
        background: route.tone === 'green' ? 'rgba(0, 242, 152, 0.15)' : 'rgba(239, 68, 68, 0.1)',
        color: route.tone === 'green' ? 'var(--primary-hover)' : '#ef4444',
      }"
    >
      {{ route.risk }}
    </div>
  </article>
</template>

<style scoped>
.route-card-vibrant {
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 12px;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
  padding: 1.2rem;
  transition: 0.3s;
}

.route-card-vibrant:hover {
  background: #ffffff;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
  transform: translateY(-3px);
}

.route-card-main {
  align-items: center;
  display: flex;
  gap: 0.8rem;
}

.route-dot {
  border-radius: 50%;
  height: 10px;
  flex: 0 0 10px;
  width: 10px;
}

h3 {
  color: var(--dark);
  font-size: 1rem;
  margin-bottom: 0.2rem;
}

p {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin: 0;
}

.pill {
  align-self: flex-end;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 800;
  margin-top: 1rem;
  padding: 0.4rem 0.8rem;
}
</style>
