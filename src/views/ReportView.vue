<script setup>
import { ref } from 'vue'

const issueTypes = ['Lane gap', 'Unsafe merge', 'Blocked bike lane', 'Poor lighting']
const selectedType = ref(issueTypes[0])
const status = ref('Ready to create a report with GPS, time, and route context.')

function submitReport() {
  status.value = `${selectedType.value} report saved locally and ready to sync.`
}
</script>

<template>
  <section class="report-layout">
    <div class="panel report-action">
      <span class="eyebrow">Smart gap reporting</span>
      <h2>Report an unsafe cycling spot</h2>
      <p>Location, time, and journey context will be attached automatically.</p>

      <label>
        Suggested issue type
        <select v-model="selectedType">
          <option v-for="type in issueTypes" :key="type">{{ type }}</option>
        </select>
      </label>

      <button type="button" @click="submitReport">Create report</button>
      <p class="status-text">{{ status }}</p>
    </div>

    <div class="report-meta">
      <article class="panel">
        <span class="pill">Auto-filled</span>
        <h3>GPS coordinates</h3>
        <p>-37.8155, 144.9655</p>
      </article>
      <article class="panel">
        <span class="pill">Duplicate check</span>
        <h3>Nearby reports</h3>
        <p>2 similar issues within 300 m</p>
      </article>
    </div>
  </section>
</template>
