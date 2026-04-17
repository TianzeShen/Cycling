<script setup>
defineProps({
  result: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <section class="panel score-panel">
    <div class="score-ring" :style="{ '--score': result.score }">
      <strong>{{ result.score }}</strong>
      <span>/100</span>
    </div>
    <div class="score-copy">
      <span class="eyebrow">Cycling feasibility</span>
      <h2>Strong option for this journey</h2>
      <p v-if="result.warning_message">{{ result.warning_message }}</p>
      <p v-else>Connected infrastructure and short travel distance make cycling practical.</p>
    </div>
  </section>
</template>
