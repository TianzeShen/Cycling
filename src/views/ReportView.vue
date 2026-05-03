<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createReport, getMyReports, getRideSmartUserId, reverseMapboxPlace } from '../services/api'

const route = useRoute()
const router = useRouter()

const userId = getRideSmartUserId()
const latitude = ref('')
const longitude = ref('')
const locationName = ref('')
const isResolvingLocation = ref(false)
const description = ref('')
const reports = ref([])
const isSubmitting = ref(false)
const isLoadingReports = ref(false)
const statusMessage = ref('')
const errorMessage = ref('')
const reportMain = ref(null)
const reportMainHeight = ref(0)
let reportMainResizeObserver = null

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

async function resolveSelectedLocationName() {
  if (!hasSelectedLocation.value) {
    locationName.value = ''
    return
  }

  isResolvingLocation.value = true

  try {
    const place = await reverseMapboxPlace([Number(latitude.value), Number(longitude.value)])
    locationName.value = place?.address || place?.label || 'Selected map location'
  } catch (error) {
    locationName.value = 'Selected map location'
  } finally {
    isResolvingLocation.value = false
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
  resolveSelectedLocationName()
  loadReports()

  if (reportMain.value && window.ResizeObserver) {
    reportMainResizeObserver = new ResizeObserver(([entry]) => {
      reportMainHeight.value = Math.ceil(entry.contentRect.height)
    })
    reportMainResizeObserver.observe(reportMain.value)
  }
})

onBeforeUnmount(() => {
  reportMainResizeObserver?.disconnect()
})
</script>

<template>
  <section class="rs-report-layout">
    <div class="rs-report-grid" :style="reportMainHeight ? { '--report-main-height': `${reportMainHeight}px` } : null">
      <div ref="reportMain" class="rs-report-main">
        <header class="rs-header-clean">
          <span class="rs-kicker">Community Intelligence</span>
          <h1>Report a Hazard</h1>
          <p>
            Your local knowledge helps refine our AI routing. Pinpoint missing infrastructure to
            instantly alert other riders.
          </p>
        </header>

        <form class="rs-form-clean" @submit.prevent="submitReport">
          <section class="rs-location-inline">
            <div class="rs-meta-header">
              <h3>Selected Map Location</h3>
              <span class="rs-status-pulse" :class="{ active: hasSelectedLocation }"></span>
            </div>
            <div class="rs-location-display">
              <div v-if="isResolvingLocation" class="rs-loading-text">Resolving spatial data...</div>
              <h4 v-else class="rs-location-title">{{ locationName || 'Awaiting map input...' }}</h4>
              <div class="rs-coord-row">
                <span class="rs-mono">LAT {{ formatCoordinate(latitude) }}</span>
                <span class="rs-mono">LNG {{ formatCoordinate(longitude) }}</span>
              </div>
            </div>
          </section>

          <div class="rs-field-group">
            <label>Auto-detected Type</label>
            <div class="rs-pseudo-input">
              <span class="rs-dot error"></span>
              Infrastructure Gap
            </div>
          </div>

          <div class="rs-field-group">
            <label>Field Notes</label>
            <textarea
              v-model="description"
              maxlength="500"
              class="rs-textarea-clean"
              placeholder="Provide context... (e.g., 'Bike lane ends abruptly, forced merge with heavy traffic.')"
            ></textarea>
            <div class="rs-char-counter">{{ description.length }} / 500</div>
          </div>

          <div class="rs-form-actions">
            <button type="button" class="rs-btn-ghost" @click="openMap">
              {{ hasSelectedLocation ? 'Relocate on Map' : 'Select on Map' }}
            </button>
            <button type="submit" class="rs-btn-solid" :disabled="isSubmitting || !hasSelectedLocation">
              {{ isSubmitting ? 'Syncing...' : 'Broadcast Report' }}
            </button>
          </div>

          <transition name="rs-fade">
            <div v-if="statusMessage" class="rs-feedback success">{{ statusMessage }}</div>
          </transition>
          <transition name="rs-fade">
            <div v-if="errorMessage" class="rs-feedback error">{{ errorMessage }}</div>
          </transition>
        </form>
      </div>

      <aside class="rs-report-sidebar">
        <div class="rs-sidebar-panel">
          <section class="rs-meta-section">
            <div class="rs-meta-header">
              <h3>Reporter Identity</h3>
            </div>
            <div class="rs-id-display">
              <span class="rs-mono block">{{ userId }}</span>
              <span class="rs-tag">Local Device</span>
            </div>
          </section>

          <section class="rs-meta-section rs-history-section">
            <div class="rs-meta-header">
              <h3>Contribution Log</h3>
              <span class="rs-count-badge">{{ reports.length }}</span>
            </div>

            <div class="rs-history-scroll">
              <div v-if="isLoadingReports" class="rs-loading-text">Fetching logs...</div>
              <div v-else-if="reports.length" class="rs-history-list">
                <div v-for="report in reports" :key="report.report_id" class="rs-history-row">
                  <div class="rs-row-top">
                    <span class="rs-status-tag">{{ report.status || 'Submitted' }}</span>
                    <span class="rs-time-tag">{{ formatReportTime(report.reported_at) }}</span>
                  </div>
                  <p class="rs-row-desc">{{ report.description || 'No notes provided.' }}</p>
                  <span class="rs-row-gps rs-mono">
                    {{ formatCoordinate(report.latitude) }}, {{ formatCoordinate(report.longitude) }}
                  </span>
                </div>
              </div>
              <div v-else class="rs-empty-log">No hazards reported yet.</div>
            </div>
          </section>
        </div>
      </aside>
    </div>
  </section>
</template>
