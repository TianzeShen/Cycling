<script setup>
import { ref } from 'vue'
import MapPreview from '../components/MapPreview.vue'
import ScorePanel from '../components/ScorePanel.vue'
import { defaultCoordinates } from '../services/api'
import { feasibilityResult } from '../data/mockData'

const start = ref('Melbourne Central')
const destination = ref('Southbank Promenade')
const result = ref(feasibilityResult)

function assessJourney() {
  result.value = {
    ...feasibilityResult,
    score: start.value && destination.value ? 85 : 0,
    warning_message: start.value && destination.value ? null : 'Enter both locations to assess this trip.',
  }
}
</script>

<template>
  <div class="page-grid">
    <section class="journey-panel panel">
      <span class="eyebrow">Pre-trip decision support</span>
      <h2>Check if cycling works before you leave</h2>

      <form class="journey-form" @submit.prevent="assessJourney">
        <label>
          Start
          <input v-model="start" type="text" placeholder="Start location" />
        </label>
        <label>
          Destination
          <input v-model="destination" type="text" placeholder="Destination" />
        </label>

        <div class="coordinate-grid">
          <span>Start {{ defaultCoordinates.start_lat }}, {{ defaultCoordinates.start_lng }}</span>
          <span>End {{ defaultCoordinates.end_lat }}, {{ defaultCoordinates.end_lng }}</span>
        </div>

        <button type="submit">Assess journey</button>
      </form>
    </section>

    <MapPreview />
  </div>

  <ScorePanel :result="result" />

  <section class="factor-grid">
    <article v-for="item in result.explanations" :key="item.factor" class="panel factor-card">
      <span class="pill">{{ item.impact }} impact</span>
      <h3>{{ item.factor }}</h3>
    </article>
  </section>
</template>
