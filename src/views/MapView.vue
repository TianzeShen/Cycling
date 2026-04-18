<script setup>
import { computed, onMounted, ref } from 'vue'
import MapboxMap from '../components/map/MapboxMap.vue'
import RouteCard from '../components/RouteCard.vue'
import ScorePanel from '../components/ScorePanel.vue'
import { communityReports as demoCommunityReports } from '../data/mockData'
import {
  defaultCoordinates,
  evaluateFeasibility,
  getMelbourneSa2Heatmap,
  recommendRoute,
  reverseMapboxPlace,
  searchMapboxPlaces,
} from '../services/api'

const mapModes = {
  routeInput: 'routeInput',
  routeAnalysis: 'routeAnalysis',
  heatmapPanel: 'heatmapPanel',
  heatmapMapOnly: 'heatmapMapOnly',
}

const mode = ref(mapModes.routeInput)
const start = ref('')
const destination = ref('')
const startCoordinate = ref([defaultCoordinates.start_lat, defaultCoordinates.start_lng])
const endCoordinate = ref(null)
const hasStartCoordinate = ref(false)
const hasDestinationCoordinate = ref(false)
const isInitialLocationResolved = ref(false)
const startSuggestions = ref([])
const destinationSuggestions = ref([])
const activeSearchField = ref(null)
const searchTimers = {
  start: null,
  destination: null,
}
const isLoading = ref(false)
const isSearching = ref(false)
const errorMessage = ref('')
const result = ref(null)
const routes = ref([])
const routeAlerts = ref([])
const routeSegments = ref([])
const heatmapRegions = ref([])
const communityReports = ref(demoCommunityReports)
const isHeatmapLoading = ref(false)
const heatmapError = ref('')
const locationStatus = ref('Locating your current position...')

function riskTone(riskLevel) {
  const normalisedRisk = String(riskLevel || '').toLowerCase()

  if (normalisedRisk === 'red') {
    return 'red'
  }

  if (normalisedRisk === 'yellow') {
    return 'yellow'
  }

  return 'green'
}

function buildRouteCards(segments, alerts) {
  if (!segments.length) {
    return []
  }

  const riskRank = { green: 1, yellow: 2, red: 3 }
  const highestRisk = segments.reduce((current, segment) => {
    const tone = riskTone(segment.risk_level)
    return riskRank[tone] > riskRank[current] ? tone : current
  }, 'green')

  const gapCount = segments.filter((segment) => segment.is_gap).length

  return [
    {
      id: 'recommended',
      name: 'Recommended',
      time: 'Route ready',
      distance: `${segments.length} segments`,
      risk: highestRisk.toUpperCase(),
      tone: highestRisk,
      summary:
        gapCount > 0
          ? `${gapCount} infrastructure gap${gapCount > 1 ? 's' : ''} detected along this route.`
          : 'No infrastructure gaps detected in the returned route segments.',
    },
    {
      id: 'alerts',
      name: 'Warnings',
      time: `${alerts.length} alert${alerts.length === 1 ? '' : 's'}`,
      distance: 'Live route data',
      risk: alerts.length,
      tone: alerts.length ? 'yellow' : 'green',
      summary: alerts.length
        ? 'Review warning points before starting the trip.'
        : 'No route warning points were returned by the backend.',
    },
  ]
}

function formatAlertLocation(location) {
  if (!Array.isArray(location)) {
    return ''
  }

  return `${location[0].toFixed(4)}, ${location[1].toFixed(4)}`
}

function queueAddressSearch(field, query) {
  clearTimeout(searchTimers[field])

  if (field === 'destination') {
    hasDestinationCoordinate.value = false
  }

  if (field === 'start') {
    hasStartCoordinate.value = false
  }

  if (query.trim().length < 3) {
    if (field === 'start') {
      startSuggestions.value = []
    } else {
      destinationSuggestions.value = []
    }

    return
  }

  searchTimers[field] = setTimeout(async () => {
    activeSearchField.value = field
    isSearching.value = true

    try {
      const results = await searchMapboxPlaces(query, startCoordinate.value)

      if (field === 'start') {
        startSuggestions.value = results
      } else {
        destinationSuggestions.value = results
      }
    } catch (error) {
      errorMessage.value = 'Address search is unavailable right now.'
    } finally {
      isSearching.value = false
    }
  }, 300)
}

function selectSuggestion(field, suggestion) {
  if (field === 'start') {
    start.value = suggestion.label
    startCoordinate.value = suggestion.coordinate
    hasStartCoordinate.value = true
    startSuggestions.value = []
  } else {
    destination.value = suggestion.label
    endCoordinate.value = suggestion.coordinate
    hasDestinationCoordinate.value = true
    destinationSuggestions.value = []
  }

  activeSearchField.value = null
}

const isHeatmapMode = computed(
  () => mode.value === mapModes.heatmapPanel || mode.value === mapModes.heatmapMapOnly,
)

const showRouteControls = computed(() => !isHeatmapMode.value)
const showAnalysis = computed(() => mode.value === mapModes.routeAnalysis && result.value)
const showHeatmapPanel = computed(() => mode.value === mapModes.heatmapPanel)
const mapDisplayMode = computed(() => (isHeatmapMode.value ? 'heatmap' : 'route'))

async function loadMelbourneSa2Heatmap() {
  if (heatmapRegions.value.length || isHeatmapLoading.value) {
    return
  }

  isHeatmapLoading.value = true
  heatmapError.value = ''

  try {
    const response = await getMelbourneSa2Heatmap()
    heatmapRegions.value = response.regions || []
  } catch (error) {
    heatmapError.value = 'SA2 safety layer failed to load from the backend.'
  } finally {
    isHeatmapLoading.value = false
  }
}

async function evaluateJourney() {
  errorMessage.value = ''

  if (!isInitialLocationResolved.value) {
    errorMessage.value = 'Wait for current location before evaluating.'
    return
  }

  if (!start.value || !hasStartCoordinate.value || !destination.value || !hasDestinationCoordinate.value) {
    errorMessage.value = 'Enter both a start location and destination.'
    mode.value = mapModes.routeInput
    return
  }

  isLoading.value = true
  const payload = {
    start_lat: startCoordinate.value[0],
    start_lng: startCoordinate.value[1],
    end_lat: endCoordinate.value[0],
    end_lng: endCoordinate.value[1],
  }

  try {
    const [feasibilityResponse, routeResponse] = await Promise.all([
      evaluateFeasibility(payload),
      recommendRoute(payload),
    ])

    result.value = feasibilityResponse
    routeAlerts.value = routeResponse.alerts || []
    routeSegments.value = routeResponse.route_segments || []
    routes.value = buildRouteCards(routeSegments.value, routeAlerts.value)
  } catch (error) {
    result.value = null
    routes.value = []
    routeAlerts.value = []
    routeSegments.value = []
    errorMessage.value = 'Backend request failed. No route data was returned.'
  } finally {
    mode.value = result.value ? mapModes.routeAnalysis : mapModes.routeInput
    isLoading.value = false
  }
}

function showRouteMode() {
  mode.value = result.value ? mapModes.routeAnalysis : mapModes.routeInput
}

async function showHeatmapPanelMode() {
  mode.value = mapModes.heatmapPanel
  await loadMelbourneSa2Heatmap()
}

function showHeatmapMapOnlyMode() {
  mode.value = mapModes.heatmapMapOnly
}

async function resolveCurrentLocationLabel() {
  try {
    const place = await reverseMapboxPlace(startCoordinate.value)

    if (place?.label) {
      start.value = place.address && place.address !== place.label ? `${place.label}, ${place.address}` : place.label
    } else {
      start.value = 'Current location'
    }
  } catch (error) {
    start.value = 'Current location'
  }
}

function handleLocationFound(location) {
  startCoordinate.value = [location.lat, location.lng]
  start.value = ''
  hasStartCoordinate.value = true
  startSuggestions.value = []
  locationStatus.value = 'Using your current location as the start point.'
}

async function useCurrentLocationAsStart() {
  start.value = 'Resolving current address...'
  await resolveCurrentLocationLabel()
  hasStartCoordinate.value = true
  locationStatus.value = 'Using your current location as the start point.'
}

function locateUserOnLoad() {
  if (!navigator.geolocation) {
    locationStatus.value = 'Browser location is unavailable. Using Melbourne Central as a fallback.'
    isInitialLocationResolved.value = true
    return
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      handleLocationFound({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      })
      isInitialLocationResolved.value = true
    },
    () => {
      locationStatus.value = 'Location permission was not granted. Using Melbourne Central as a fallback.'
      isInitialLocationResolved.value = true
    },
    {
      enableHighAccuracy: true,
      maximumAge: 60000,
      timeout: 10000,
    },
  )
}

onMounted(() => {
  locateUserOnLoad()
})
</script>

<template>
  <section class="map-view-wrapper">
    <div class="mapbox-shell">
      <MapboxMap
        v-if="isInitialLocationResolved"
        :mode="mapDisplayMode"
        :route-segments="routeSegments"
        :heatmap-regions="heatmapRegions"
        :alerts="routeAlerts"
        :start-point="startCoordinate"
        :end-point="endCoordinate"
        :reports="[]"
        @location-found="handleLocationFound"
      />
      <div v-else class="glass-panel locating-panel">
        <h2>Locating...</h2>
        <p>Requesting GPS access</p>
      </div>
    </div>

    <div class="floating-controls" aria-label="Map mode controls">
      <button type="button" :class="{ secondary: isHeatmapMode }" @click="showRouteMode">Route</button>
      <button type="button" :class="{ secondary: !isHeatmapMode }" @click="showHeatmapPanelMode">
        {{ isHeatmapLoading ? 'Loading...' : 'Heatmap' }}
      </button>
      <button v-if="isHeatmapMode" type="button" class="secondary" @click="showHeatmapMapOnlyMode">
        Map Only
      </button>
    </div>

    <aside class="map-side-panel">
      <form v-if="showRouteControls" class="glass-panel journey-form" @submit.prevent="evaluateJourney">
        <div>
          <h2>Trip Planner</h2>
          <p>Find the safest path.</p>
        </div>

        <div class="suggestion-field">
          <label>Origin</label>
          <input
            v-model="start"
            type="text"
            placeholder="Current Location"
            autocomplete="off"
            @input="queueAddressSearch('start', start)"
            @focus="activeSearchField = 'start'"
          />
          <ul v-if="activeSearchField === 'start' && startSuggestions.length" class="suggestion-list">
            <li v-for="suggestion in startSuggestions" :key="suggestion.id">
              <button type="button" @click="selectSuggestion('start', suggestion)">
                {{ suggestion.label }}
              </button>
            </li>
          </ul>
        </div>

        <button
          v-if="isInitialLocationResolved"
          type="button"
          class="secondary inline-action"
          @click="useCurrentLocationAsStart"
        >
          Use current location
        </button>

        <div class="suggestion-field">
          <label>Destination</label>
          <input
            v-model="destination"
            type="text"
            placeholder="Where to?"
            autocomplete="off"
            @input="queueAddressSearch('destination', destination)"
            @focus="activeSearchField = 'destination'"
          />
          <ul v-if="activeSearchField === 'destination' && destinationSuggestions.length" class="suggestion-list">
            <li v-for="suggestion in destinationSuggestions" :key="suggestion.id">
              <button type="button" @click="selectSuggestion('destination', suggestion)">
                {{ suggestion.label }}
              </button>
            </li>
          </ul>
        </div>

        <button type="submit" class="primary full-width-action" :disabled="isLoading || !isInitialLocationResolved">
          {{ isLoading ? 'Computing...' : 'Generate Route' }}
        </button>
        <p v-if="isSearching" class="helper-text">Searching addresses...</p>
        <p v-if="errorMessage" class="status-text">{{ errorMessage }}</p>
      </form>

      <section v-if="showHeatmapPanel" class="glass-panel heatmap-panel">
        <h2>Safety Layer</h2>
        <p>{{ heatmapRegions.length }} SA2 regions loaded.</p>
        <p v-if="heatmapError" class="status-text">{{ heatmapError }}</p>

        <div class="heatmap-legend" aria-label="Heatmap legend">
          <span><i class="legend-critical"></i> Critical</span>
          <span><i class="legend-high"></i> High</span>
          <span><i class="legend-medium"></i> Safe</span>
        </div>

        <div class="community-list">
          <article v-for="report in communityReports" :key="report.id" class="community-card-minimal">
            <div>
              <h3>{{ report.type }}</h3>
              <p>{{ report.area }}</p>
            </div>
            <span class="pill pill-red">{{ report.votes }} votes</span>
          </article>
        </div>
      </section>
    </aside>

    <div class="analysis-bottom">
      <transition name="fade">
        <section v-if="showAnalysis" class="analysis-grid">
          <ScorePanel :result="result" />
          <div class="glass-panel">
            <h3 class="panel-kicker">Route Overview</h3>
            <div class="route-list route-list-horizontal">
              <RouteCard v-for="route in routes" :key="route.id" :route="route" />
            </div>
          </div>
        </section>
      </transition>
    </div>
  </section>
</template>
