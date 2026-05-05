<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
  durationLabel: {
    type: String,
    default: '',
  },
  distanceLabel: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close'])

const displayScore = computed(() => {
  const value = Number(props.result.score)

  return Number.isFinite(value) ? Math.round(value) : null
})

const scoreColor = computed(() => {
  if (displayScore.value === null) {
    return '#94a3b8'
  }

  if (displayScore.value >= 80) {
    return 'var(--primary)'
  }

  if (displayScore.value >= 50) {
    return '#f59e0b'
  }

  return '#ef4444'
})

const scoreLabel = computed(() => {
  if (displayScore.value === null) {
    return 'Score Pending'
  }

  if (displayScore.value >= 80) {
    return 'Optimal Route'
  }

  if (displayScore.value >= 50) {
    return 'Caution Advised'
  }

  return 'High Risk'
})

const warningMessage = computed(() => {
  if (displayScore.value === null) {
    return 'The routing service did not return a safety score for this route yet.'
  }

  if (props.result.warning_message) {
    return props.result.warning_message
  }

  if (props.result.is_supported_area === false) {
    return 'This route is outside the currently supported scoring area. Please review the route carefully before riding.'
  }

  return 'Connected infrastructure makes cycling practical.'
})
</script>

<template>
  <div class="glass-panel score-panel-vibrant">
    <div class="score-panel-head">
      <div>
        <h3>Safety Score</h3>
        <div
          class="score-value score-tooltip-anchor"
          tabindex="0"
          aria-describedby="score-explanation-tooltip"
        >
          <span :style="{ color: scoreColor }">{{ displayScore ?? '--' }}</span>
          <span class="score-total">/100</span>
          <span id="score-explanation-tooltip" class="score-tooltip" role="tooltip">
            This score is based on bike lane quality, traffic volume, speed limits, and route distance,
            with extra penalties for lane gaps and roads with elevated crash history. Higher scores indicate
            safer cycling routes.
          </span>
        </div>
      </div>
      <div class="score-actions">
        <div class="score-dot" :style="{ background: scoreColor }"></div>
      </div>
    </div>

    <div v-if="durationLabel || distanceLabel" class="score-route-metrics">
      <div v-if="durationLabel" class="score-route-metric">
        <span>Time</span>
        <strong>{{ durationLabel }}</strong>
      </div>
      <div v-if="distanceLabel" class="score-route-metric">
        <span>Distance</span>
        <strong>{{ distanceLabel }}</strong>
      </div>
    </div>

    <h2>{{ scoreLabel }}</h2>
    <p>{{ warningMessage }}</p>
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

.score-tooltip-anchor {
  cursor: help;
  outline: none;
  position: relative;
  width: max-content;
}

.score-tooltip-anchor:focus-visible {
  border-radius: 8px;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.18);
}

.score-tooltip {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.24);
  color: var(--dark);
  font-size: 0.82rem;
  font-weight: 600;
  left: 0;
  line-height: 1.45;
  max-width: min(320px, calc(100vw - 4rem));
  opacity: 0;
  padding: 0.85rem 0.95rem;
  pointer-events: none;
  position: absolute;
  top: calc(100% + 0.75rem);
  transform: translateY(4px);
  transition: opacity 0.16s ease, transform 0.16s ease;
  width: 300px;
  z-index: 80;
}

.score-tooltip::after {
  background: #ffffff;
  border-left: 1px solid rgba(15, 23, 42, 0.12);
  border-top: 1px solid rgba(15, 23, 42, 0.12);
  content: "";
  height: 10px;
  left: 1.25rem;
  position: absolute;
  top: -6px;
  transform: rotate(45deg);
  width: 10px;
}

.score-tooltip-anchor:hover .score-tooltip,
.score-tooltip-anchor:focus-visible .score-tooltip {
  opacity: 1;
  transform: translateY(0);
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

.score-route-metrics {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0 0 1.1rem;
}

.score-route-metric {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 0;
  padding: 0.75rem 0.85rem;
}

.score-route-metric span {
  color: #94a3b8;
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
}

.score-route-metric strong {
  color: #ffffff;
  font-size: 1rem;
  line-height: 1.2;
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
