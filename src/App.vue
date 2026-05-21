<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCurrentAuthIdentity, getStoredAuthIdentity } from './services/api'

const navItems = [
  { label: 'Home', to: '/' },
  { label: 'Map', to: '/map' },
  { label: 'Report', to: '/report' },
  { label: 'Profile', to: '/profile' },
]

const route = useRoute()
const isHelpOpen = ref(false)
const activeHelpStep = ref(0)
const authIdentity = ref(getStoredAuthIdentity())
const HELP_SEEN_STORAGE_KEY_PREFIX = 'ridesmart-help-shown'
const RIDESMART_AUTH_UPDATED_EVENT = 'ridesmart-auth-updated'
const MAP_ROUTE_BODY_CLASS = 'map-route-active'

const helpContentByRoute = {
  home: {
    title: 'Welcome to RydeSmrt',
    summary: 'Start here to access your profile, understand the app, and plan a ride.',
    steps: [
      {
        title: 'Choose an entry point',
        body: 'Use Launch Map to plan a ride, or open Access Profile to create, manage, or recover your username.',
      },
      {
        title: 'Scan the core capabilities',
        body: 'The homepage introduces route comparison, SA2 safety heatmaps, community reporting, and the signals behind riding decisions.',
      },
      {
        title: 'Check riding conditions',
        body: 'Open Explore conditions to review terrain, UV, and air-quality context before deciding when and where to ride.',
      },
      {
        title: 'Read the data note',
        body: 'The footer explains that AI-generated safety signals are informational and real road conditions can still change.',
      },
    ],
  },
  map: {
    title: 'Use the map workspace',
    summary: 'Plan a route, compare safety signals, start navigation, inspect the heatmap, and report hazards.',
    steps: [
      {
        title: 'Set route locations',
        body: 'Type a start and destination, select address suggestions, or use the location icon for your current start point.',
      },
      {
        title: 'Compare route options',
        body: 'Select Generate Route, then compare route cards, travel time, distance, score, warnings, and gap signals.',
      },
      {
        title: 'Start the trip',
        body: 'Choose a route and use Start Trip for live progress. If the ride drifts off route, recalculate or end navigation.',
      },
      {
        title: 'Explore the safety layer',
        body: 'Switch to Heatmap and select an SA2 region to inspect risk level, risk score, and supporting safety metrics.',
      },
      {
        title: 'Report a hazard',
        body: 'Right-click the map on desktop or long-press on mobile, then choose Report gap here to send the location to the report form.',
      },
    ],
  },
  report: {
    title: 'Submit a hazard report',
    summary: 'Turn a selected map location into a hazard report with type, notes, and your local contribution history.',
    steps: [
      {
        title: 'Choose the location',
        body: 'Reports start from a map selection. Use Select on Map or relocate from the map if the displayed coordinates need changing.',
      },
      {
        title: 'Review map details',
        body: 'The selected place, coordinates, and current report time appear before you submit the hazard.',
      },
      {
        title: 'Describe the hazard',
        body: 'Choose the Issue Type and add Field Notes for context, such as a blocked lane, unsafe intersection, poor surface, or debris.',
      },
      {
        title: 'Broadcast the report',
        body: 'Select Broadcast Report to submit with your local identity. The sidebar keeps your reporter ID and contribution log visible.',
      },
    ],
  },
  conditions: {
    title: 'Review safety insights',
    summary: 'Use riding-condition context alongside route and heatmap signals before heading out.',
    steps: [
      {
        title: 'Read terrain context',
        body: 'The elevation section explains how Melbourne road gradients affect effort, braking, and route comfort.',
      },
      {
        title: 'Check UV exposure',
        body: 'Use the UV chart and threshold note to spot periods when sun protection matters more.',
      },
      {
        title: 'Check air quality',
        body: 'The PM2.5 chart highlights air-quality guidance and conditions where outdoor cycling may be less suitable.',
      },
    ],
  },
  profile: {
    title: 'Use your profile',
    summary: 'Access your username, review your contribution progress, and manage submitted reports.',
    steps: [
      {
        title: 'Access your username',
        body: 'Use Username Access to create a username, update the linked username, or continue with an existing username.',
      },
      {
        title: 'Read your contribution summary',
        body: 'The top section shows safety points, submitted reports, platform-validated reports, routes improved, and your local user ID.',
      },
      {
        title: 'Check progress and badges',
        body: 'Use the milestone and badge sections to see which rewards are earned and what contribution threshold comes next.',
      },
      {
        title: 'Review report status',
        body: 'The contribution pipeline groups your reports into pending, validated, and resolved states.',
      },
      {
        title: 'Manage submitted reports',
        body: 'In My submitted reports, refresh activity, edit a report description, or delete one of your submitted reports.',
      },
    ],
  },
}

const activeHelpContent = computed(() => helpContentByRoute[route.name] || helpContentByRoute.home)
const activeHelpSteps = computed(() => activeHelpContent.value.steps)
const currentHelpStep = computed(() => activeHelpSteps.value[activeHelpStep.value] || activeHelpSteps.value[0])
const isFirstHelpStep = computed(() => activeHelpStep.value === 0)
const isLastHelpStep = computed(() => activeHelpStep.value === activeHelpSteps.value.length - 1)
const navIdentityLabel = computed(() =>
  authIdentity.value.is_registered && authIdentity.value.username ? authIdentity.value.username : 'Guest',
)

function refreshStoredAuthIdentity() {
  authIdentity.value = getStoredAuthIdentity()
}

function handleAuthUpdated(event) {
  authIdentity.value = event.detail || getStoredAuthIdentity()
}

function syncMapRouteBodyClass(routeName) {
  if (typeof document === 'undefined') {
    return
  }

  document.body.classList.toggle(MAP_ROUTE_BODY_CLASS, routeName === 'map')
}

function openHelpPanel() {
  activeHelpStep.value = 0
  isHelpOpen.value = true
}

function closeHelpPanel() {
  isHelpOpen.value = false
}

function goToNextHelpStep() {
  if (isLastHelpStep.value) {
    closeHelpPanel()
    return
  }

  activeHelpStep.value += 1
}

function goToPreviousHelpStep() {
  if (isFirstHelpStep.value) {
    return
  }

  activeHelpStep.value -= 1
}

function maybeOpenHelpForRoute(routeName) {
  if (typeof window === 'undefined') {
    return
  }

  if (!routeName || !helpContentByRoute[routeName]) {
    return
  }

  const storageKey = `${HELP_SEEN_STORAGE_KEY_PREFIX}-${routeName}`
  const hasSeenHelp = window.localStorage.getItem(storageKey) === 'true'

  if (!hasSeenHelp) {
    window.localStorage.setItem(storageKey, 'true')
    openHelpPanel()
  }
}

watch(
  () => route.name,
  (routeName) => {
    activeHelpStep.value = 0
    isHelpOpen.value = false
    maybeOpenHelpForRoute(routeName)
    syncMapRouteBodyClass(routeName)
  },
  { immediate: true },
)

onMounted(() => {
  window.addEventListener(RIDESMART_AUTH_UPDATED_EVENT, handleAuthUpdated)
  getCurrentAuthIdentity()
    .then((identity) => {
      authIdentity.value = identity
    })
    .catch(refreshStoredAuthIdentity)
})

onBeforeUnmount(() => {
  window.removeEventListener(RIDESMART_AUTH_UPDATED_EVENT, handleAuthUpdated)
  document.body.classList.remove(MAP_ROUTE_BODY_CLASS)
})
</script>

<template>
  <div class="app-shell">
    <header class="glass-header">
      <nav class="header-nav" aria-label="Primary navigation">
        <RouterLink class="brand-logo" to="/">Ryde<span>Smrt</span></RouterLink>
        <div class="header-nav-main">
          <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
            {{ item.label }}
          </RouterLink>
          <button type="button" class="help-trigger" @click="openHelpPanel">Help</button>
        </div>
        <RouterLink
          class="nav-user-status"
          :class="{ registered: authIdentity.is_registered }"
          :to="{ path: '/profile', hash: '#simple-recovery' }"
          :title="authIdentity.is_registered ? `Signed in as ${navIdentityLabel}` : 'Guest mode'"
        >
          {{ navIdentityLabel }}
        </RouterLink>
      </nav>
    </header>

    <main class="main-content">
      <RouterView />
    </main>

    <transition name="fade">
      <div v-if="isHelpOpen" class="help-overlay" @click.self="closeHelpPanel">
        <aside class="help-panel glass-panel" aria-label="Interactive help guide">
          <div class="help-panel-header">
            <div>
              <span class="help-kicker">Interactive Guide</span>
              <h2>{{ activeHelpContent.title }}</h2>
              <p>{{ activeHelpContent.summary }}</p>
            </div>
            <button type="button" class="help-close-btn" aria-label="Close help" @click="closeHelpPanel">
              ×
            </button>
          </div>

          <div class="help-progress" aria-hidden="true">
            <span
              v-for="(step, index) in activeHelpSteps"
              :key="`${activeHelpContent.title}-${step.title}`"
              class="help-progress-dot"
              :class="{ active: index === activeHelpStep }"
            ></span>
          </div>

          <article class="help-step-card">
            <span class="help-step-index">Step {{ activeHelpStep + 1 }} / {{ activeHelpSteps.length }}</span>
            <h3>{{ currentHelpStep.title }}</h3>
            <p>{{ currentHelpStep.body }}</p>
          </article>

          <div class="help-panel-actions">
            <button type="button" class="secondary" :disabled="isFirstHelpStep" @click="goToPreviousHelpStep">
              Back
            </button>
            <button type="button" class="primary" @click="goToNextHelpStep">
              {{ isLastHelpStep ? 'Finish' : 'Next tip' }}
            </button>
          </div>
        </aside>
      </div>
    </transition>
  </div>
</template>
