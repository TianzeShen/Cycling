<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close'])

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
      <div class="score-actions">
        <div class="score-dot" :style="{ background: scoreColor }"></div>
        <button class="score-close-btn" title="Clear route" @click="emit('close')">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
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

.score-actions {
  align-items: center;
  display: flex;
  gap: 0.75rem;
}

.score-close-btn {
  align-items: center;
  background: rgba(255, 255, 255, 0.08);
  border: 0;
  border-radius: 50%;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  justify-content: center;
  padding: 0.45rem;
}

.score-close-btn:hover {
  background: rgba(239, 68, 68, 0.16);
  color: #ffffff;
}

.score-panel-vibrant h2 {
  font-size: 1.2rem;
}

.score-panel-vibrant p {
  color: #94a3b8;
}
</style>
