<script setup>
defineProps({
  route: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <article class="route-card-dynamic" :class="`bg-${route.tone}`">
    <div class="route-card-main">
      <div class="route-dot"></div>
      <div>
        <h3>{{ route.name }}</h3>
        <p>{{ route.distance }} · {{ route.time }}</p>
      </div>
    </div>
    <div class="pill">
      {{ route.risk }}
    </div>
  </article>
</template>

<style scoped>
.route-card-dynamic {
  align-items: flex-start;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 1.2rem;
  transition: transform 0.3s, box-shadow 0.3s;
}

.route-card-dynamic:hover {
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
  transform: translateY(-3px);
}

.route-card-main {
  align-items: center;
  display: flex;
  gap: 0.8rem;
}

.route-dot {
  background: currentColor;
  border-radius: 50%;
  height: 10px;
  opacity: 0.5;
  width: 10px;
}

h3 {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.2rem;
}

p {
  color: inherit;
  font-size: 0.85rem;
  margin: 0;
  opacity: 0.8;
}

.bg-green {
  background: var(--primary);
  color: var(--dark);
}

.bg-yellow {
  background: #f59e0b;
  color: #ffffff;
}

.bg-red {
  background: #ef4444;
  color: #ffffff;
}

.pill {
  align-self: flex-end;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  background: rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  color: inherit;
  font-size: 0.75rem;
  font-weight: 800;
  margin-top: 1rem;
  padding: 0.4rem 0.8rem;
}
</style>
