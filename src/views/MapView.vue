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
  <section class="map-page">
    <div class="map-toolbar panel">
      <div>
        <span class="eyebrow">Core map workspace</span>
        <h2>Plan safer cycling trips in one place</h2>
        <p class="helper-text">SA2 safety layer uses backend heatmap regions.</p>
      </div>

      <div class="mode-switch" aria-label="Map mode controls">
        <button type="button" :class="{ secondary: isHeatmapMode }" @click="showRouteMode">
          Route
        </button>
        <button
          type="button"
          :class="{ secondary: !isHeatmapMode }"
          @click="showHeatmapPanelMode"
        >
          {{ isHeatmapLoading ? 'Loading heatmap...' : 'Heatmap' }}
        </button>
        <button
          v-if="isHeatmapMode"
          type="button"
          class="secondary"
          @click="showHeatmapMapOnlyMode"
        >
          Map only
        </button>
      </div>
    </div>

    <div class="map-workspace">
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
      <section v-else class="mapbox-shell locating-panel">
        <div class="panel mapbox-token-empty">
          <span class="eyebrow">Finding your location</span>
          <h2>Preparing your map</h2>
          <p>Allow browser location access to start from your current position.</p>
        </div>
      </section>

      <aside class="map-side-panel">
        <form v-if="showRouteControls" class="panel journey-form" @submit.prevent="evaluateJourney">
          <span class="eyebrow">Route mode</span>
          <div class="suggestion-field">
            <label>
              Start location
              <input
                v-model="start"
                type="text"
                placeholder="Start location"
                autocomplete="off"
                @input="queueAddressSearch('start', start)"
                @focus="activeSearchField = 'start'"
              />
            </label>
            <ul v-if="activeSearchField === 'start' && startSuggestions.length" class="suggestion-list">
              <li v-for="suggestion in startSuggestions" :key="suggestion.id">
                <button type="button" @click="selectSuggestion('start', suggestion)">
                  <span>{{ suggestion.label }}</span>
                  <em v-if="suggestion.address">{{ suggestion.address }}</em>
                  <small>{{ suggestion.type }}</small>
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
            <label>
              Destination location
              <input
                v-model="destination"
                type="text"
                placeholder="Destination"
                autocomplete="off"
                @input="queueAddressSearch('destination', destination)"
                @focus="activeSearchField = 'destination'"
              />
            </label>
            <ul
              v-if="activeSearchField === 'destination' && destinationSuggestions.length"
              class="suggestion-list"
            >
              <li v-for="suggestion in destinationSuggestions" :key="suggestion.id">
                <button type="button" @click="selectSuggestion('destination', suggestion)">
                  <span>{{ suggestion.label }}</span>
                  <em v-if="suggestion.address">{{ suggestion.address }}</em>
                  <small>{{ suggestion.type }}</small>
                </button>
              </li>
            </ul>
          </div>

          <p class="helper-text">{{ locationStatus }}</p>

          <button type="submit" :disabled="isLoading || !isInitialLocationResolved">
            {{ isLoading ? 'Evaluating...' : 'Evaluate' }}
          </button>
          <p v-if="isSearching" class="helper-text">Searching addresses...</p>
          <p v-if="errorMessage" class="status-text">{{ errorMessage }}</p>
        </form>

        <section v-if="showHeatmapPanel" class="panel heatmap-panel">
          <span class="eyebrow">SA2 safety layer</span>
          <h2>Melbourne heatmap regions</h2>
          <p>
            Backend connected via <code>/api/heatmap/melbourne-sa2</code>.
            {{ heatmapRegions.length }} SA2 regions loaded.
          </p>
          <p v-if="heatmapError" class="status-text">{{ heatmapError }}</p>

          <div class="heatmap-legend" aria-label="Heatmap legend">
            <span><i class="legend-critical"></i> Critical</span>
            <span><i class="legend-high"></i> High</span>
            <span><i class="legend-medium"></i> Medium</span>
          </div>

          <span class="eyebrow">Demo community reports</span>
          <p class="helper-text">
            This report list is mock/demo data until a reports endpoint is available.
          </p>
          <div class="community-list">
            <article v-for="report in communityReports" :key="report.id" class="community-card">
              <div>
                <span class="pill">{{ report.status }}</span>
                <h3>{{ report.type }}</h3>
                <p>{{ report.area }}</p>
              </div>
              <strong>{{ report.votes }}</strong>
            </article>
          </div>
        </section>
      </aside>
    </div>

    <section v-if="showAnalysis" class="analysis-grid">
      <ScorePanel :result="result" />

      <div class="panel">
        <span class="eyebrow">Why this score</span>
        <div class="factor-grid compact">
          <article v-for="item in result.explanations" :key="item.factor" class="factor-card">
            <span class="pill">{{ item.impact }} impact</span>
            <h3>{{ item.factor }}</h3>
          </article>
        </div>
      </div>

      <div class="panel route-results">
        <span class="eyebrow">Recommended routes</span>
        <div class="route-list">
          <RouteCard v-for="route in routes" :key="route.id" :route="route" />
        </div>
      </div>

      <div class="panel">
        <span class="eyebrow">Warnings and alerts</span>
        <div class="alert-list">
          <article v-for="alert in routeAlerts" :key="alert.message || alert.title" class="alert-row">
            <strong>{{ alert.message || alert.title }}</strong>
            <span v-if="alert.location">{{ formatAlertLocation(alert.location) }}</span>
          </article>
          <article v-if="!routeAlerts.length" class="alert-row">
            <strong>Disconnected lane in 200m</strong>
            <span>Swanston Street</span>
          </article>
          <article v-if="!routeAlerts.length" class="alert-row">
            <strong>High traffic exposure near crossing</strong>
            <span>Flinders Street</span>
          </article>
        </div>
      </div>
    </section>
  </section>
</template>
