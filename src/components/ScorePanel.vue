<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
})

const scoreColor = computed(() => {
  if (props.result.score >= 80) {
    return 'var(--primary)'
  }

  if (props.result.score >= 50) {
    return '#f59e0b'
  }

  return '#ef4444'
})

const scoreLabel = computed(() => {
  if (props.result.score >= 80) {
    return 'Optimal Route'
  }

  if (props.result.score >= 50) {
    return 'Caution Advised'
  }

  return 'High Risk'
})
</script>

<template>
  <div class="glass-panel score-panel-vibrant">
    <div class="score-panel-head">
      <div>
        <h3>Feasibility Score</h3>
        <div class="score-value">
          <span :style="{ color: scoreColor }">{{ result.score }}</span>
          <span class="score-total">/100</span>
        </div>
      </div>
      <div class="score-dot" :style="{ background: scoreColor }"></div>
    </div>

    <h2>{{ scoreLabel }}</h2>
    <p>{{ result.warning_message || 'Connected infrastructure makes cycling practical.' }}</p>
  </div>
</template>

<style scoped>
.score-panel-vibrant {
  background: var(--dark);
  border-color: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.score-panel-head {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
}

.score-panel-vibrant h3 {
  color: #94a3b8;
  font-size: 0.8rem;
  font-weight: 800;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
}

.score-value {
  font-size: 3.5rem;
  font-weight: 900;
  line-height: 1;
  margin-bottom: 1rem;
}

.score-total {
  color: #94a3b8;
  font-size: 1.5rem;
}

.score-dot {
  border-radius: 50%;
  height: 12px;
  width: 12px;
}

.score-panel-vibrant h2 {
  font-size: 1.2rem;
}

.score-panel-vibrant p {
  color: #94a3b8;
}
</style>
