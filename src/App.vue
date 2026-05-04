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
        title: 'Start with the main actions',
        body: 'Use Launch Map to plan a ride, or open Report Issue when you already know the location of a cycling hazard.',
      },
      {
        title: 'Understand the intelligence signals',
        body: 'The overview explains safety scoring, risk segments, local reports, heatmaps, and the data sources behind RideSmart.',
      },
      {
        title: 'Read the data disclaimer',
        body: 'The footer explains that AI-generated safety signals are informational and that real road conditions can still change.',
      },
    ],
  },
  map: {
    title: 'Use the map workspace',
    summary: 'Plan routes, compare safety signals, inspect warnings, and choose report locations from the map.',
    steps: [
      {
        title: 'Set your start point',
        body: 'Type an address or use the location icon to set your current position as the route start.',
      },
      {
        title: 'Choose a destination',
        body: 'Enter your destination and select a suggestion so RideSmart can use exact coordinates for routing.',
      },
      {
        title: 'Generate and compare routes',
        body: 'Select Generate Route to view route options with travel time, distance, the Safety Score panel, warnings, and gap segments.',
      },
      {
        title: 'Switch map modes',
        body: 'Use Route and Heatmap controls to switch between route planning and the city-wide safety layer.',
      },
      {
        title: 'Report from the map',
        body: 'On desktop, right-click a location and choose Report gap here. On mobile, long-press the map to open the same report action.',
      },
    ],
  },
  report: {
    title: 'Submit a hazard report',
    summary: 'Create a user-reported infrastructure gap with map location, current time, notes, and local identity.',
    steps: [
      {
        title: 'Start from a map location',
        body: 'Reports are created from the map. The selected place name, coordinates, and current report time are shown at the top of the form.',
      },
      {
        title: 'Review the report type',
        body: 'The current minimum version automatically classifies the issue as an infrastructure gap.',
      },
      {
        title: 'Add field notes',
        body: 'Use Field Notes to describe the hazard, such as a missing lane, unsafe merge, obstruction, or sudden gap.',
      },
      {
        title: 'Broadcast the report',
        body: 'Select Broadcast Report to submit it with your local RideSmart user ID. The sidebar shows your identity and contribution log.',
      },
    ],
  },
  profile: {
    title: 'Track your impact',
    summary: 'Review your contribution score, reward progress, badges, report status, and submitted report history.',
    steps: [
      {
        title: 'Read your contribution summary',
        body: 'The top section shows safety points, submitted reports, validations received, routes improved, and your local user ID.',
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
        body: 'In My submitted reports, refresh activity, edit a report description, or delete your own report when the backend endpoint is available.',
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
