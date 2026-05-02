<script setup>
import { computed, onMounted, ref } from 'vue'
import { getMyReports, getRideSmartUserId } from '../services/api'

const userId = getRideSmartUserId()
const reports = ref([])
const isLoading = ref(false)
const errorMessage = ref('')

const submittedReports = computed(() => reports.value.length)
const validatedReports = computed(
  () => reports.value.filter((report) => String(report.status || '').toLowerCase() === 'validated').length,
)
const safetyPoints = computed(() => submittedReports.value * 10 + validatedReports.value * 15)
const routesImproved = computed(() => validatedReports.value)

const earnedBadges = computed(() => {
  const badges = []

  if (submittedReports.value >= 1) {
    badges.push({
      name: 'First Report',
      detail: 'Submitted your first cycling gap report',
    })
  }

  if (submittedReports.value >= 5) {
    badges.push({
      name: 'Gap Spotter',
      detail: 'Submitted 5 user-reported cycling gaps',
    })
  }

  if (validatedReports.value >= 1) {
    badges.push({
      name: 'Safety Builder',
      detail: 'Had a report validated by the community',
    })
  }

  return badges.length
    ? badges
    : [
        {
          name: 'Ready Rider',
          detail: 'Submit your first map report to start earning badges',
        },
      ]
})

function formatReportTime(value) {
  if (!value) {
    return 'Time pending'
  }

  return new Date(value).toLocaleString()
}

async function loadProfileReports() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await getMyReports()
    reports.value = Array.isArray(response.reports) ? response.reports : []
  } catch (error) {
    reports.value = []
    errorMessage.value = 'Unable to load your report activity right now.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadProfileReports)
</script>

<template>
  <section class="profile-grid">
    <article class="panel profile-summary">
      <span class="eyebrow">Contribution impact</span>
      <h2>{{ safetyPoints }} safety points</h2>
      <p>
        {{ submittedReports }} reports submitted - {{ validatedReports }} validations received -
        {{ routesImproved }} routes improved
      </p>
      <p class="mono-text">Local user ID: {{ userId }}</p>
    </article>

    <article class="panel profile-stat-card">
      <span class="pill">Reports</span>
      <h3>{{ submittedReports }}</h3>
      <p>Gap reports submitted from this browser.</p>
    </article>

    <article class="panel profile-stat-card">
      <span class="pill">Validated</span>
      <h3>{{ validatedReports }}</h3>
      <p>Reports marked as validated by backend/community status.</p>
    </article>

    <article class="panel profile-stat-card">
      <span class="pill">Points</span>
      <h3>{{ safetyPoints }}</h3>
      <p>Local reward score generated from report activity.</p>
    </article>

    <article v-for="badge in earnedBadges" :key="badge.name" class="panel badge-card">
      <span class="badge-icon">{{ badge.name.charAt(0) }}</span>
      <h3>{{ badge.name }}</h3>
      <p>{{ badge.detail }}</p>
    </article>

    <article class="panel profile-activity-card">
      <span class="eyebrow">Recent activity</span>
      <h3>My submitted reports</h3>
      <p v-if="isLoading">Loading activity...</p>
      <p v-else-if="errorMessage" class="status-text">{{ errorMessage }}</p>
      <div v-else-if="reports.length" class="my-report-list">
        <article v-for="report in reports.slice(0, 5)" :key="report.report_id" class="my-report-item">
          <strong>{{ report.status || 'submitted' }}</strong>
          <span>{{ Number(report.latitude).toFixed(6) }}, {{ Number(report.longitude).toFixed(6) }}</span>
          <p>{{ report.description || 'No description provided.' }}</p>
          <small>{{ formatReportTime(report.reported_at) }}</small>
        </article>
      </div>
      <p v-else>No report activity yet.</p>
    </article>
  </section>
</template>
