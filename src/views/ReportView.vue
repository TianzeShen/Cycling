<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createReport, getMyReports, getRideSmartUserId } from '../services/api'

const route = useRoute()
const router = useRouter()

const userId = getRideSmartUserId()
const latitude = ref('')
const longitude = ref('')
const description = ref('')
const reports = ref([])
const isSubmitting = ref(false)
const isLoadingReports = ref(false)
const statusMessage = ref('')
const errorMessage = ref('')

const hasSelectedLocation = computed(() =>
  Number.isFinite(Number(latitude.value)) && Number.isFinite(Number(longitude.value)),
)

function formatCoordinate(value) {
  const number = Number(value)

  return Number.isFinite(number) ? number.toFixed(6) : 'Not selected'
}

function formatReportTime(value) {
  if (!value) {
    return 'Time pending'
  }

  return new Date(value).toLocaleString()
}

function syncLocationFromQuery() {
  const queryLatitude = Number(route.query.lat)
  const queryLongitude = Number(route.query.lng)

  if (Number.isFinite(queryLatitude)) {
    latitude.value = String(queryLatitude)
  }

  if (Number.isFinite(queryLongitude)) {
    longitude.value = String(queryLongitude)
  }
}

async function loadReports() {
  isLoadingReports.value = true

  try {
    const response = await getMyReports()
    reports.value = Array.isArray(response.reports) ? response.reports : []
  } catch (error) {
    reports.value = []
  } finally {
    isLoadingReports.value = false
  }
}

async function submitReport() {
  errorMessage.value = ''
  statusMessage.value = ''

  if (!hasSelectedLocation.value) {
    errorMessage.value = 'Choose a location from the map before submitting a report.'
    return
  }

  isSubmitting.value = true

  try {
    const report = await createReport({
      latitude: Number(latitude.value),
      longitude: Number(longitude.value),
      description: description.value.trim(),
    })

    reports.value = [report, ...reports.value.filter((item) => item.report_id !== report.report_id)]
    description.value = ''
    statusMessage.value = 'Gap report submitted and linked to your local RideSmart ID.'
  } catch (error) {
    errorMessage.value = 'Report submission failed. Please try again.'
  } finally {
    isSubmitting.value = false
  }
}

function openMap() {
  router.push({ name: 'map' })
}

onMounted(() => {
  syncLocationFromQuery()
  loadReports()
})
</script>

<template>
  <section class="report-layout">
    <form class="panel report-action" @submit.prevent="submitReport">
      <span class="eyebrow">Smart gap reporting</span>
      <h2>Report a cycling gap</h2>
      <p>Right-click a location on the map, then submit a user-reported gap for backend storage.</p>

      <div class="report-location-grid">
        <label>
          Latitude
          <input v-model="latitude" type="number" step="any" readonly />
        </label>
        <label>
          Longitude
          <input v-model="longitude" type="number" step="any" readonly />
        </label>
      </div>

      <label>
        Issue type
        <select value="gap" disabled>
          <option value="gap">Gap</option>
        </select>
      </label>

      <label>
        Description
        <textarea
          v-model="description"
          maxlength="500"
          placeholder="Add optional detail about the missing lane, unsafe merge, obstruction, or lighting issue."
        ></textarea>
      </label>

      <div class="report-actions-row">
        <button type="button" class="secondary" @click="openMap">Choose on map</button>
        <button type="submit" class="primary" :disabled="isSubmitting || !hasSelectedLocation">
          {{ isSubmitting ? 'Submitting...' : 'Submit report' }}
        </button>
      </div>

      <p v-if="statusMessage" class="success-text">{{ statusMessage }}</p>
      <p v-if="errorMessage" class="status-text">{{ errorMessage }}</p>
    </form>

    <div class="report-meta">
      <article class="panel">
        <span class="pill">Auto-filled</span>
        <h3>Selected location</h3>
        <p>{{ formatCoordinate(latitude) }}, {{ formatCoordinate(longitude) }}</p>
      </article>

      <article class="panel">
        <span class="pill">Local user</span>
        <h3>Report owner</h3>
        <p class="mono-text">{{ userId }}</p>
      </article>

      <article class="panel my-reports-panel">
        <span class="pill">My reports</span>
        <h3>{{ reports.length }} submitted</h3>
        <p v-if="isLoadingReports">Loading reports...</p>
        <div v-else-if="reports.length" class="my-report-list">
          <article v-for="report in reports" :key="report.report_id" class="my-report-item">
            <strong>{{ report.status || 'submitted' }}</strong>
            <span>{{ formatCoordinate(report.latitude) }}, {{ formatCoordinate(report.longitude) }}</span>
            <p>{{ report.description || 'No description provided.' }}</p>
            <small>{{ formatReportTime(report.reported_at) }}</small>
          </article>
        </div>
        <p v-else>No reports submitted from this browser yet.</p>
      </article>
    </div>
  </section>
</template>
