<script setup>
defineProps({
  route: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <article class="route-card" :class="`route-${route.tone}`">
    <div>
      <span class="pill">{{ route.name }}</span>
      <h3>{{ route.time }}</h3>
      <p>{{ route.summary }}</p>
    </div>
    <dl>
      <div>
        <dt>Distance</dt>
        <dd>{{ route.distance }}</dd>
      </div>
      <div>
        <dt>Risk</dt>
        <dd>{{ route.risk }}</dd>
      </div>
    </dl>
  </article>
</template>
