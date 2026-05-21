<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  deleteReport,
  getCurrentAuthIdentity,
  getMyReports,
  getRideSmartUserId,
  getStoredAuthIdentity,
  loginWithUsername,
  registerUsername,
  updateReport,
} from '../services/api'

const authIdentity = ref(getStoredAuthIdentity())
const registerUsernameInput = ref('')
const loginUsernameInput = ref('')
const authMessage = ref('')
const authErrorMessage = ref('')
const authMode = ref('register')
const isAuthLoading = ref(false)
const route = useRoute()
const reports = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const actionMessage = ref('')
const editingReportId = ref('')
const editingDescription = ref('')
const savingReportId = ref('')
const deletingReportId = ref('')
let profileReportsRefreshTimer = null

const userId = computed(() => authIdentity.value.user_id || getRideSmartUserId())
const displayUsername = computed(() => authIdentity.value.username || '')
const isRegistered = computed(() => Boolean(authIdentity.value.is_registered))

const badgeCatalog = [
  {
    id: 'first-report',
    name: 'First Report',
    detail: 'Submit your first cycling gap report.',
    thresholdLabel: '1 report',
    requirement: (stats) => stats.submittedReports >= 1,
    progress: (stats) => Math.min(stats.submittedReports / 1, 1),
  },
  {
    id: 'gap-spotter',
    name: 'Gap Spotter',
    detail: 'Submit 5 cycling gap reports from this device.',
    thresholdLabel: '5 reports',
    requirement: (stats) => stats.submittedReports >= 5,
    progress: (stats) => Math.min(stats.submittedReports / 5, 1),
  },
  {
    id: 'safety-builder',
    name: 'Safety Builder',
    detail: 'Receive at least 50 likes on your submitted reports.',
    thresholdLabel: '50 likes',
    requirement: (stats) => stats.likesReceived >= 50,
    progress: (stats) => Math.min(stats.likesReceived / 50, 1),
  },
  {
    id: 'local-guide',
    name: 'Local Guide',
    detail: 'Reach 100 safety points through reports and community support.',
    thresholdLabel: '100 points',
    requirement: (stats) => stats.safetyPoints >= 100,
    progress: (stats) => Math.min(stats.safetyPoints / 100, 1),
  },
]

function normaliseStatus(status) {
  return String(status || 'submitted').toLowerCase()
}

function displayReportStatus(status) {
  const normalisedStatus = normaliseStatus(status)

  if (['pending', 'pending sync', 'submitted'].includes(normalisedStatus)) {
    return 'Submitted'
  }

  return normalisedStatus
    .split(' ')
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(' ')
}

const submittedReports = computed(() => reports.value.length)

const validatedReports = computed(
  () => reports.value.filter((report) => normaliseStatus(report.status) === 'validated').length,
)

const pendingReports = computed(
  () => reports.value.filter((report) => ['submitted', 'pending', 'pending sync'].includes(normaliseStatus(report.status))).length,
)

const resolvedReports = computed(
  () => reports.value.filter((report) => normaliseStatus(report.status) === 'resolved').length,
)

function getBackendReportLikes(report) {
  const likes = Number(report?.like_count ?? report?.likes ?? report?.likeCount)
  return Number.isFinite(likes) && likes >= 0 ? likes : null
}

function getProfileReportLikes(report) {
  const backendLikes = getBackendReportLikes(report)

  return backendLikes ?? 0
}

const safetyPoints = computed(() => {
  const rewardPoints = Number(authIdentity.value.reward_points)

  return Number.isFinite(rewardPoints) && rewardPoints >= 0 ? rewardPoints : 0
})

const routesImproved = computed(() => validatedReports.value + resolvedReports.value)

const likesReceived = computed(() =>
  reports.value.reduce((total, report) => total + getProfileReportLikes(report), 0),
)

const stats = computed(() => ({
  submittedReports: submittedReports.value,
  validatedReports: validatedReports.value,
  resolvedReports: resolvedReports.value,
  likesReceived: likesReceived.value,
  safetyPoints: safetyPoints.value,
}))

const earnedBadges = computed(() =>
  badgeCatalog.map((badge) => {
    const progress = badge.progress(stats.value)

    return {
      ...badge,
      earned: badge.requirement(stats.value),
      progress,
      progressPercent: Math.round(progress * 100),
    }
  }),
)

const earnedBadgeCount = computed(() => earnedBadges.value.filter((badge) => badge.earned).length)

const nextBadge = computed(() => earnedBadges.value.find((badge) => !badge.earned) || null)

const impactSummary = computed(() => [
  {
    label: 'Reports submitted',
    value: submittedReports.value,
    detail: 'Infrastructure issues contributed from this browser.',
  },
  {
    label: 'Validations received',
    value: validatedReports.value,
    detail: 'Reports moved to validated status by the platform.',
  },
  {
    label: 'Likes received',
    value: likesReceived.value,
    detail: 'Community support earned across your submitted reports.',
  },
  {
    label: 'Badges earned',
    value: `${earnedBadgeCount.value}/${badgeCatalog.length}`,
    detail: 'Recognition milestones unlocked by contribution activity.',
  },
])

const statusBreakdown = computed(() => [
  { label: 'Submitted', value: pendingReports.value, tone: 'pending' },
  { label: 'Validated', value: validatedReports.value, tone: 'validated' },
  { label: 'Resolved', value: resolvedReports.value, tone: 'resolved' },
])

const recentReports = computed(() =>
  [...reports.value]
    .sort((left, right) => new Date(right.reported_at || 0) - new Date(left.reported_at || 0))
    .slice(0, 6),
)

function formatReportTime(value) {
  if (!value) {
    return 'Time pending'
  }

  return new Date(value).toLocaleString()
}

function formatCoordinate(value) {
  const number = Number(value)

  return Number.isFinite(number) ? number.toFixed(6) : 'N/A'
}

function applyAuthIdentity(identity) {
  authIdentity.value = {
    user_id: identity?.user_id || getRideSmartUserId(),
    username: identity?.username || null,
    is_registered: Boolean(identity?.is_registered),
    reward_points: Number.isFinite(Number(identity?.reward_points)) ? Number(identity.reward_points) : 0,
  }
  registerUsernameInput.value = displayUsername.value
}

async function loadAuthIdentity({ silent = false } = {}) {
  if (!silent) {
    authErrorMessage.value = ''
  }

  try {
    applyAuthIdentity(await getCurrentAuthIdentity())
  } catch (error) {
    if (!silent) {
      authErrorMessage.value = 'Unable to check sync status right now.'
    }
  }
}

async function saveUsername() {
  const username = registerUsernameInput.value.trim()

  authMessage.value = ''
  authErrorMessage.value = ''

  if (!username) {
    authErrorMessage.value = 'Enter a username to enable simple recovery.'
    return
  }

  isAuthLoading.value = true

  try {
    applyAuthIdentity(await registerUsername(username))
    authMessage.value = 'Simple recovery is now linked to this browser data.'
  } catch (error) {
    authErrorMessage.value =
      error?.status === 409 ? 'That username is already taken. Try another one.' : 'Unable to save this username right now.'
  } finally {
    isAuthLoading.value = false
  }
}

async function restoreUsername() {
  const username = loginUsernameInput.value.trim()

  authMessage.value = ''
  authErrorMessage.value = ''

  if (!username) {
    authErrorMessage.value = 'Enter the username you want to restore.'
    return
  }

  isAuthLoading.value = true

  try {
    applyAuthIdentity(await loginWithUsername(username))
    loginUsernameInput.value = ''
    authMessage.value = 'Recovered this username. Your reports and rewards will now use the restored ID.'
    await loadProfileReports()
  } catch (error) {
    authErrorMessage.value = 'Unable to restore that username right now.'
  } finally {
    isAuthLoading.value = false
  }
}

async function loadProfileReports({ silent = false } = {}) {
  if (!silent) {
    isLoading.value = true
    errorMessage.value = ''
    actionMessage.value = ''
  }

  try {
    const response = await getMyReports()
    reports.value = Array.isArray(response.reports) ? response.reports : []
  } catch (error) {
    if (!silent) {
      reports.value = []
      errorMessage.value = 'Unable to load your report activity right now.'
    }
  } finally {
    if (!silent) {
      isLoading.value = false
    }
  }
}

function startProfileReportsPolling() {
  window.clearInterval(profileReportsRefreshTimer)
  profileReportsRefreshTimer = window.setInterval(() => {
    loadAuthIdentity({ silent: true })
    loadProfileReports({ silent: true })
  }, 5000)
}

function scrollToSimpleRecovery() {
  if (typeof document === 'undefined') {
    return
  }

  document.getElementById('simple-recovery')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

function startEditReport(report) {
  editingReportId.value = report.report_id
  editingDescription.value = report.description || ''
  errorMessage.value = ''
  actionMessage.value = ''
}

function cancelEditReport() {
  editingReportId.value = ''
  editingDescription.value = ''
}

async function saveReportEdit(report) {
  savingReportId.value = report.report_id
  errorMessage.value = ''
  actionMessage.value = ''

  try {
    const updatedReport = await updateReport(report.report_id, {
      description: editingDescription.value.trim(),
    })

    reports.value = reports.value.map((item) =>
      item.report_id === report.report_id
        ? {
            ...item,
            ...updatedReport,
            description: updatedReport?.description ?? editingDescription.value.trim(),
          }
        : item,
    )
    actionMessage.value = 'Report updated successfully.'
    cancelEditReport()
  } catch (error) {
    errorMessage.value = 'Unable to update this report right now.'
  } finally {
    savingReportId.value = ''
  }
}

async function removeReport(report) {
  const shouldDelete = window.confirm('Delete this submitted report? This action cannot be undone.')

  if (!shouldDelete) {
    return
  }

  deletingReportId.value = report.report_id
  errorMessage.value = ''
  actionMessage.value = ''

  try {
    await deleteReport(report.report_id)
    reports.value = reports.value.filter((item) => item.report_id !== report.report_id)
    loadAuthIdentity({ silent: true })
    actionMessage.value = 'Report deleted successfully.'
  } catch (error) {
    errorMessage.value = 'Unable to delete this report right now.'
  } finally {
    deletingReportId.value = ''
  }
}

onMounted(() => {
  loadAuthIdentity({ silent: true })
  loadProfileReports()
  startProfileReportsPolling()

  if (route.hash === '#simple-recovery') {
    nextTick(scrollToSimpleRecovery)
  }
})

watch(
  () => route.hash,
  (hash) => {
    if (hash === '#simple-recovery') {
      nextTick(scrollToSimpleRecovery)
    }
  },
)

onBeforeUnmount(() => {
  window.clearInterval(profileReportsRefreshTimer)
})
</script>

<template>
  <section class="profile-view-container">
    <header class="profile-hero-panel">
      <div>
        <span class="eyebrow-dark">Reward & Engagement System</span>
        <h1>{{ safetyPoints }} safety points</h1>
        <p>
          {{ submittedReports }} reports submitted - {{ validatedReports }} reports validated -
          {{ routesImproved }} routes improved
        </p>
        <p class="profile-user-id">
          {{ isRegistered ? `Simple recovery username: ${displayUsername}` : 'Guest mode: not linked to a username' }}
          <br />
          Local user ID: {{ userId }}
        </p>
      </div>

      <div class="profile-hero-actions">
        <RouterLink class="profile-action-link primary" to="/map">Report from map</RouterLink>
        <RouterLink class="profile-action-link" to="/report">View report log</RouterLink>
      </div>
    </header>

    <section class="profile-impact-grid" aria-label="Contribution impact">
      <article v-for="item in impactSummary" :key="item.label" class="profile-impact-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <p>{{ item.detail }}</p>
      </article>
    </section>

    <section class="profile-content-grid">
      <article id="simple-recovery" class="profile-panel profile-account-panel">
        <div class="profile-panel-header">
          <div>
            <span class="panel-kicker">Simple recovery</span>
            <h2>{{ isRegistered ? 'Username linked' : 'Sync this guest data' }}</h2>
          </div>
          <span class="profile-pill">{{ isRegistered ? 'Linked' : 'Guest' }}</span>
        </div>

        <p class="profile-account-note">
          This is simple username recovery without a password. Anyone who knows the username can restore the same
          RydeSmrt data.
        </p>

        <div class="profile-auth-tabs" role="tablist" aria-label="Account recovery options">
          <button
            type="button"
            :class="{ active: authMode === 'register' }"
            @click="authMode = 'register'"
          >
            Save my data
          </button>
          <button type="button" :class="{ active: authMode === 'login' }" @click="authMode = 'login'">
            Use existing username
          </button>
        </div>

        <form v-if="authMode === 'register'" class="profile-auth-form" @submit.prevent="saveUsername">
          <label for="profile-register-username">Username for this local data</label>
          <div class="profile-auth-row">
            <input
              id="profile-register-username"
              v-model="registerUsernameInput"
              autocomplete="username"
              maxlength="50"
              placeholder="e.g. Alice"
              type="text"
            />
            <button type="submit" class="profile-small-button profile-auth-submit primary" :disabled="isAuthLoading">
              {{ isAuthLoading ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>

        <form v-else class="profile-auth-form" @submit.prevent="restoreUsername">
          <label for="profile-login-username">Existing username</label>
          <div class="profile-auth-row">
            <input
              id="profile-login-username"
              v-model="loginUsernameInput"
              autocomplete="username"
              maxlength="50"
              placeholder="e.g. Alice"
              type="text"
            />
            <button type="submit" class="profile-small-button profile-auth-submit primary" :disabled="isAuthLoading">
              {{ isAuthLoading ? 'Restoring...' : 'Restore' }}
            </button>
          </div>
        </form>

        <p v-if="authMessage" class="success-text">{{ authMessage }}</p>
        <p v-if="authErrorMessage" class="status-text">{{ authErrorMessage }}</p>
      </article>

      <article class="profile-panel profile-progress-panel">
        <div class="profile-panel-header">
          <div>
            <span class="panel-kicker">Next milestone</span>
            <h2>{{ nextBadge ? nextBadge.name : 'All badges earned' }}</h2>
          </div>
          <span class="profile-pill">{{ earnedBadgeCount }} earned</span>
        </div>

        <template v-if="nextBadge">
          <p>{{ nextBadge.detail }}</p>
          <div class="profile-progress-track" aria-label="Next badge progress">
            <span :style="{ width: `${nextBadge.progressPercent}%` }"></span>
          </div>
          <p class="profile-progress-copy">{{ nextBadge.progressPercent }}% toward {{ nextBadge.thresholdLabel }}</p>
        </template>
        <p v-else>Every current reward milestone is unlocked.</p>
      </article>

      <article class="profile-panel profile-status-panel">
        <div class="profile-panel-header">
          <div>
            <span class="panel-kicker">Report status</span>
            <h2>Contribution pipeline</h2>
          </div>
        </div>

        <div class="profile-status-list">
          <div v-for="item in statusBreakdown" :key="item.label" class="profile-status-row">
            <span :class="`profile-status-dot ${item.tone}`"></span>
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </article>

      <article class="profile-panel profile-badges-panel">
        <div class="profile-panel-header">
          <div>
            <span class="panel-kicker">Badges</span>
            <h2>Recognition</h2>
          </div>
        </div>

        <div class="profile-badge-grid">
          <article
            v-for="badge in earnedBadges"
            :key="badge.id"
            class="profile-badge-card"
            :class="[`badge-${badge.id}`, { locked: !badge.earned, unlocked: badge.earned }]"
          >
            <div class="profile-badge-flip">
              <div class="profile-badge-face profile-badge-front">
                <span class="profile-badge-lock-state">{{ badge.earned ? 'Unlocked' : 'Locked' }}</span>
                <h3>{{ badge.name }}</h3>
                <p>{{ badge.detail }}</p>
                <div class="badge-progress-track">
                  <span :style="{ width: `${badge.progressPercent}%` }"></span>
                </div>
                <small>{{ badge.earned ? 'Condition complete' : `${badge.progressPercent}% complete` }}</small>
              </div>

              <div class="profile-badge-face profile-badge-back">
                <div class="profile-badge-icon" aria-hidden="true">
                  <svg v-if="badge.id === 'first-report'" viewBox="0 0 64 64" role="img">
                    <path class="badge-shield" d="M32 4 53 13v15c0 15.2-8.3 25.9-21 32C19.3 53.9 11 43.2 11 28V13L32 4Z" />
                    <path class="badge-route" d="M21 45c4.8-8.8 16.8-8.2 21-16" />
                    <circle class="badge-dot" cx="21" cy="45" r="3.6" />
                    <path class="badge-flag-pole" d="M30 17v24" />
                    <path class="badge-flag" d="M30 17h14l-3.2 5.4L44 28H30V17Z" />
                  </svg>
                  <svg v-else-if="badge.id === 'gap-spotter'" viewBox="0 0 64 64" role="img">
                    <path class="badge-shield" d="M32 4 53 13v15c0 15.2-8.3 25.9-21 32C19.3 53.9 11 43.2 11 28V13L32 4Z" />
                    <circle class="badge-lens" cx="28" cy="27" r="13" />
                    <path class="badge-handle" d="m38 37 10 10" />
                    <path class="badge-gap-left" d="M18 28h8" />
                    <path class="badge-gap-right" d="M31 28h9" />
                    <path class="badge-spark" d="M29 18v5m0 10v4" />
                  </svg>
                  <svg v-else-if="badge.id === 'safety-builder'" viewBox="0 0 64 64" role="img">
                    <path class="badge-shield" d="M32 4 53 13v15c0 15.2-8.3 25.9-21 32C19.3 53.9 11 43.2 11 28V13L32 4Z" />
                    <path class="badge-wall" d="M18 39h28M20 31h24M24 23h16" />
                    <path class="badge-check" d="m23 31 6 6 13-15" />
                  </svg>
                  <svg v-else viewBox="0 0 64 64" role="img">
                    <path class="badge-shield" d="M32 4 53 13v15c0 15.2-8.3 25.9-21 32C19.3 53.9 11 43.2 11 28V13L32 4Z" />
                    <circle class="badge-compass" cx="32" cy="31" r="15" />
                    <path class="badge-needle" d="m38 19-4 17-13 8 4-17 13-8Z" />
                    <path class="badge-route" d="M18 48c7-4 12 2 19-2 4-2.2 5-6.2 9-7" />
                  </svg>
                </div>
                <h3>{{ badge.name }}</h3>
                <small>Earned</small>
              </div>
            </div>
          </article>
        </div>
      </article>

      <article class="profile-panel profile-activity-panel">
        <div class="profile-panel-header">
          <div>
            <span class="panel-kicker">Recent activity</span>
            <h2>My submitted reports</h2>
          </div>
          <button type="button" class="profile-refresh-button" :disabled="isLoading" @click="loadProfileReports">
            {{ isLoading ? 'Refreshing...' : 'Refresh' }}
          </button>
        </div>

        <p v-if="actionMessage" class="success-text">{{ actionMessage }}</p>
        <p v-if="errorMessage" class="status-text">{{ errorMessage }}</p>
        <p v-else-if="isLoading">Loading activity...</p>
        <div v-else-if="recentReports.length" class="profile-report-list">
          <article v-for="report in recentReports" :key="report.report_id" class="profile-report-item">
            <div class="profile-report-main">
              <strong>{{ displayReportStatus(report.status) }}</strong>
              <template v-if="editingReportId === report.report_id">
                <textarea
                  v-model="editingDescription"
                  class="profile-report-edit-input"
                  maxlength="500"
                  placeholder="Update report description"
                ></textarea>
                <div class="profile-report-edit-actions">
                  <button
                    type="button"
                    class="profile-small-button primary"
                    :disabled="savingReportId === report.report_id"
                    @click="saveReportEdit(report)"
                  >
                    {{ savingReportId === report.report_id ? 'Saving...' : 'Save' }}
                  </button>
                  <button type="button" class="profile-small-button" @click="cancelEditReport">Cancel</button>
                </div>
              </template>
              <p v-else>{{ report.description || 'No description provided.' }}</p>
            </div>
            <div class="profile-report-meta">
              <span>{{ formatCoordinate(report.latitude) }}, {{ formatCoordinate(report.longitude) }}</span>
              <small>{{ formatReportTime(report.reported_at) }}</small>
              <div class="profile-report-row-actions">
                <button
                  type="button"
                  class="profile-small-button"
                  :disabled="Boolean(editingReportId)"
                  @click="startEditReport(report)"
                >
                  Edit
                </button>
                <button
                  type="button"
                  class="profile-small-button danger"
                  :disabled="deletingReportId === report.report_id"
                  @click="removeReport(report)"
                >
                  {{ deletingReportId === report.report_id ? 'Deleting...' : 'Delete' }}
                </button>
              </div>
            </div>
          </article>
        </div>
        <div v-else class="profile-empty-state">
          <h3>No contribution activity yet</h3>
          <p>Right-click a location on the map to submit your first cycling gap report.</p>
          <RouterLink class="profile-action-link primary" to="/map">Open map</RouterLink>
        </div>
      </article>
    </section>
  </section>
</template>
