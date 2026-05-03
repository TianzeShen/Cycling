<script setup>
import { computed, onMounted, ref } from 'vue'
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
})
</script>

<template>
  <section class="report-view-container">
    <header class="report-page-header">
      <span class="eyebrow-dark">Community Intelligence</span>
      <h1>Report a cycling hazard.</h1>
      <p>
        Your local knowledge helps the AI build safer routes. Pinpoint missing lanes, unsafe merges,
        or obstructions to instantly alert other riders.
      </p>
    </header>

    <div class="report-content-grid">
      <div class="report-form-wrapper">
        <form class="glass-panel dynamic-report-form" @submit.prevent="submitReport">
          <div class="form-group locked-group">
            <label>Issue Type</label>
            <div class="locked-input-pill">
              <span class="indicator-dot red"></span>
              Infrastructure Gap
              <svg
                class="lock-icon"
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
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
            </div>
            <small class="helper-text-left">Auto-categorized from the selected map point.</small>
          </div>

          <div class="form-group">
            <label>Description & Context</label>
            <textarea
              v-model="description"
              maxlength="500"
              class="premium-textarea"
              placeholder="Describe the hazard, for example: Bike lane suddenly ends before a heavy traffic merge."
            ></textarea>
            <div class="char-counter">{{ description.length }} / 500</div>
          </div>

          <div class="form-actions">
            <button type="button" class="btn-outline map-picker-btn" @click="openMap">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              {{ hasSelectedLocation ? 'Change Map Location' : 'Choose on Map' }}
            </button>

            <button type="submit" class="btn-primary-glow submit-btn" :disabled="isSubmitting || !hasSelectedLocation">
              {{ isSubmitting ? 'Syncing to Network...' : 'Broadcast Report' }}
            </button>
          </div>

          <transition name="fade">
            <div v-if="statusMessage" class="status-banner success">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              {{ statusMessage }}
            </div>
          </transition>

          <transition name="fade">
            <div v-if="errorMessage" class="status-banner error">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              {{ errorMessage }}
            </div>
          </transition>
        </form>
      </div>

      <aside class="report-meta-sidebar">
        <article class="meta-widget location-widget">
          <div class="widget-header">
            <span class="widget-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 10c0 4.99-5.53 10.19-7.4 11.77a1 1 0 0 1-1.2 0C9.53 20.19 4 14.99 4 10a8 8 0 1 1 16 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
            </span>
            <h3>Target Coordinates</h3>
            <span class="status-dot" :class="hasSelectedLocation ? 'active' : 'inactive'"></span>
          </div>
          <div class="widget-body">
            <p v-if="isResolvingLocation" class="resolving-text">Scanning map data...</p>
            <h4 v-else class="location-name">{{ locationName || 'Awaiting map selection...' }}</h4>
            <div class="coordinate-display">
              <div class="coord-box">
                <span>LAT</span>
                <strong>{{ formatCoordinate(latitude) }}</strong>
              </div>
              <div class="coord-box">
                <span>LNG</span>
                <strong>{{ formatCoordinate(longitude) }}</strong>
              </div>
            </div>
          </div>
        </article>

        <article class="meta-widget user-widget">
          <div class="widget-header">
            <span class="widget-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21a8 8 0 0 0-16 0"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </span>
            <h3>Reporter Identity</h3>
          </div>
          <div class="widget-body">
            <p class="mono-id">{{ userId }}</p>
            <span class="local-tag">Local Device Synced</span>
          </div>
        </article>

        <article class="meta-widget history-widget">
          <div class="widget-header">
            <span class="widget-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M8 2v4"></path>
                <path d="M16 2v4"></path>
                <rect width="18" height="18" x="3" y="4" rx="2"></rect>
                <path d="M8 11h8"></path>
                <path d="M8 15h5"></path>
              </svg>
            </span>
            <h3>My Contribution Log</h3>
            <span class="report-badge">{{ reports.length }}</span>
          </div>

          <div class="widget-body history-body">
            <p v-if="isLoadingReports" class="loading-text">Fetching secure logs...</p>
            <div v-else-if="reports.length" class="timeline-container">
              <div v-for="report in reports" :key="report.report_id" class="timeline-item">
                <div class="timeline-node"></div>
                <div class="timeline-content">
                  <div class="timeline-meta">
                    <span class="timeline-status">{{ report.status || 'Submitted' }}</span>
                    <span class="timeline-date">{{ formatReportTime(report.reported_at) }}</span>
                  </div>
                  <p class="timeline-desc">{{ report.description || 'No additional details provided.' }}</p>
                  <span class="timeline-gps">
                    {{ formatCoordinate(report.latitude) }}, {{ formatCoordinate(report.longitude) }}
                  </span>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <p>No hazards reported from this device yet.</p>
            </div>
          </div>
        </article>
      </aside>
    </div>
  </section>
</template>
