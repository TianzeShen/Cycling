<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const navItems = [
  { label: 'Home', to: '/' },
  { label: 'Map', to: '/map' },
  { label: 'Report', to: '/report' },
  { label: 'Profile', to: '/profile' },
]

const route = useRoute()
const isHelpOpen = ref(false)
const activeHelpStep = ref(0)
const HELP_SEEN_STORAGE_KEY_PREFIX = 'ridesmart-help-shown'

const helpContentByRoute = {
  home: {
    title: 'Welcome to RideSmart',
    summary: 'Start here to understand what the app does before planning a ride.',
    steps: [
      {
        title: 'Explore the main actions',
        body: 'Use Launch Map to begin route planning, or jump to Report Issue if you want to log a hazard immediately.',
      },
      {
        title: 'Scan the core capabilities',
        body: 'The home page introduces routing, safety heatmaps, and community reporting so new users can understand what each section is for.',
      },
      {
        title: 'Read the data disclaimer',
        body: 'The footer explains where the data comes from and reminds riders that live road conditions can still change in the real world.',
      },
    ],
  },
  map: {
    title: 'Plan a safer trip',
    summary: 'Use the map workspace to search for places, compare signals, and review route warnings.',
    steps: [
      {
        title: 'Set your start point',
        body: 'Type an address or tap the location icon to use your current position. Suggestions will appear as you type.',
      },
      {
        title: 'Choose a destination',
        body: 'Enter where you want to go and select the best-matching suggestion from the list so the route uses exact coordinates.',
      },
      {
        title: 'Generate and review the route',
        body: 'Select Generate Route to request a route score, route warnings, and coloured map segments from the backend.',
      },
      {
        title: 'Switch map modes',
        body: 'Use Route and Heatmap at the top-right of the map to swap between turn-by-turn analysis and the city-wide safety layer.',
      },
    ],
  },
  report: {
    title: 'Submit a safety report',
    summary: 'The reporting page helps riders log hazards that can improve future route awareness.',
    steps: [
      {
        title: 'Pick the issue type',
        body: 'Choose the closest hazard type from the dropdown so the report is categorized consistently.',
      },
      {
        title: 'Use the auto-filled context',
        body: 'GPS and nearby duplicate information are shown beside the form to help users avoid submitting the same issue twice.',
      },
      {
        title: 'Create the report',
        body: 'Select Create report to save the issue locally and prepare it for future syncing.',
      },
    ],
  },
  profile: {
    title: 'Track your impact',
    summary: 'The profile page shows how a rider has contributed to safer cycling decisions over time.',
    steps: [
      {
        title: 'Read your contribution summary',
        body: 'The top card highlights total safety points, submitted reports, validations, and routes improved.',
      },
      {
        title: 'Review badges',
        body: 'Each badge explains a type of contribution so riders can quickly see how they have helped the community.',
      },
    ],
  },
}

const activeHelpContent = computed(() => helpContentByRoute[route.name] || helpContentByRoute.home)
const activeHelpSteps = computed(() => activeHelpContent.value.steps)
const currentHelpStep = computed(() => activeHelpSteps.value[activeHelpStep.value] || activeHelpSteps.value[0])
const isFirstHelpStep = computed(() => activeHelpStep.value === 0)
const isLastHelpStep = computed(() => activeHelpStep.value === activeHelpSteps.value.length - 1)

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
  },
  { immediate: true },
)
</script>

<template>
  <div class="app-shell">
    <header class="glass-header">
      <nav class="header-nav" aria-label="Primary navigation">
        <RouterLink class="brand-logo" to="/">Ride<span>Smart</span></RouterLink>
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
          {{ item.label }}
        </RouterLink>
        <button type="button" class="help-trigger" @click="openHelpPanel">Help</button>
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
