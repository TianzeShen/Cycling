<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import MapboxMap from '../components/map/MapboxMap.vue'
import RouteCard from '../components/RouteCard.vue'
import ScorePanel from '../components/ScorePanel.vue'
import {
  defaultCoordinates,
  getAllReports,
  getMelbourneSa2Heatmap,
  recommendRoute,
  reverseMapboxPlace,
  searchMapboxPlaces,
} from '../services/api'

const router = useRouter()

const mapModes = {
  routeInput: 'routeInput',
  routeAnalysis: 'routeAnalysis',
  heatmapPanel: 'heatmapPanel',
  heatmapMapOnly: 'heatmapMapOnly',
}

const mapStateKey = 'ridesmart_map_view_state'

function readSavedMapState() {
  try {
    return JSON.parse(sessionStorage.getItem(mapStateKey) || 'null')
  } catch (error) {
    return null
  }
}

function isCoordinatePair(value) {
  return Array.isArray(value) && value.length >= 2 && value.every((item) => Number.isFinite(Number(item)))
}

const savedMapState = readSavedMapState()
const shouldRestoreMapState = Boolean(
  savedMapState &&
    (savedMapState.routeOptions?.length ||
      savedMapState.result ||
      savedMapState.routeGeometry ||
      savedMapState.destination ||
      savedMapState.hasDestinationCoordinate),
)

const mode = ref(shouldRestoreMapState ? savedMapState.mode || mapModes.routeInput : mapModes.routeInput)
const start = ref(shouldRestoreMapState ? savedMapState.start || '' : '')
const destination = ref(shouldRestoreMapState ? savedMapState.destination || '' : '')
const startCoordinate = ref(
  shouldRestoreMapState && isCoordinatePair(savedMapState.startCoordinate)
    ? savedMapState.startCoordinate
    : [defaultCoordinates.start_lat, defaultCoordinates.start_lng],
)
const endCoordinate = ref(
  shouldRestoreMapState && isCoordinatePair(savedMapState.endCoordinate) ? savedMapState.endCoordinate : null,
)
const hasStartCoordinate = ref(shouldRestoreMapState ? Boolean(savedMapState.hasStartCoordinate) : false)
const hasDestinationCoordinate = ref(shouldRestoreMapState ? Boolean(savedMapState.hasDestinationCoordinate) : false)
const isInitialLocationResolved = ref(shouldRestoreMapState ? true : false)
const startSuggestions = ref([])
const destinationSuggestions = ref([])
const activeSearchField = ref(null)
const routeSearchContainer = ref(null)
const mapSidePanel = ref(null)
const analysisStack = ref(null)
const isAnalysisHighlighted = ref(false)
const isMobileAnalysisExpanded = ref(false)
const mobileAnalysisDragStartY = ref(null)
const mobileAnalysisDragOffset = ref(0)
const isMobileAnalysisDragging = ref(false)
const hasMobileAnalysisDragged = ref(false)
const shouldIgnoreAnalysisToggleClick = ref(false)
let analysisHighlightTimer = null
let publicReportsRefreshTimer = null
const searchTimers = {
  start: null,
  destination: null,
}
const isLoading = ref(false)
const isSearching = ref(false)
const errorMessage = ref('')
const result = ref(shouldRestoreMapState ? savedMapState.result || null : null)
const isAnalysisVisible = ref(shouldRestoreMapState ? Boolean(savedMapState.isAnalysisVisible) : false)
const routeAlerts = ref(shouldRestoreMapState && Array.isArray(savedMapState.routeAlerts) ? savedMapState.routeAlerts : [])
const routeAlertsStatusMessage = ref(shouldRestoreMapState ? savedMapState.routeAlertsStatusMessage || '' : '')
const routeOptions = ref(
  shouldRestoreMapState && Array.isArray(savedMapState.routeOptions) ? savedMapState.routeOptions : [],
)
const activeRouteIndex = ref(shouldRestoreMapState ? Number(savedMapState.activeRouteIndex) || 0 : 0)
const routeGeometry = ref(shouldRestoreMapState ? savedMapState.routeGeometry || null : null)
const gapPoints = ref(
  shouldRestoreMapState && Array.isArray(savedMapState.gapPoints) ? savedMapState.gapPoints : [],
)
const routeSegments = ref(
  shouldRestoreMapState && Array.isArray(savedMapState.routeSegments) ? savedMapState.routeSegments : [],
)
const heatmapRegions = ref([])
const activeHeatmapRegion = ref(null)
const isHeatmapLoading = ref(false)
const heatmapError = ref('')
const locationStatus = ref(
  shouldRestoreMapState ? savedMapState.locationStatus || 'Route restored from this tab.' : 'Locating your current position...',
)
const currentLocationLabel = ref(shouldRestoreMapState ? savedMapState.currentLocationLabel || '' : '')
const publicReports = ref([])
const tripStatus = ref('idle')
const tripStartedAt = ref(null)
const tripElapsedSeconds = ref(0)
const tripLiveLocation = ref(null)
const tripProgressIndex = ref(-1)
const isTripOffRoute = ref(false)
const isRecalculatingTrip = ref(false)
const tripHadOffRouteEvent = ref(false)
let tripTimer = null
let tripWatchId = null

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

function getSegmentMidpoint(segment) {
  const coordinates = Array.isArray(segment?.coordinates) ? segment.coordinates : []

  if (!coordinates.length) {
    return null
  }

  const midpoint = coordinates[Math.floor((coordinates.length - 1) / 2)]

  if (!Array.isArray(midpoint) || midpoint.length < 2) {
    return null
  }

  return midpoint
}

function formatAlertLocation(location) {
  if (!Array.isArray(location)) {
    return ''
  }

  return `${location[0].toFixed(4)}, ${location[1].toFixed(4)}`
}

function normaliseRouteAlerts(routeResponse) {
  const alerts = routeResponse.alerts || []
  const routeGapPoints = Array.isArray(routeResponse.gap_points) ? routeResponse.gap_points : []
  const legacyGapSegments = (routeResponse.route_segments || []).filter((segment) => segment.is_gap)
  const alertGaps = routeGapPoints.length
    ? routeGapPoints
    : routeResponse.route_geometry
      ? []
      : legacyGapSegments
  const gapCount = alertGaps.length

  if (alerts.length) {
    return alerts
  }

  if (gapCount > 0) {
    return alertGaps.map((gap, index) => ({
      level: gap.risk_level || 'Red',
      location: gap.location || getSegmentMidpoint(gap),
      kind: 'gap_point',
      message:
        gapCount === 1
          ? '1 infrastructure gap detected along the route.'
          : `Infrastructure gap ${index + 1} of ${gapCount} detected along the route.`,
    }))
  }

  return []
}

function toFiniteNumber(value) {
  if (value === null || value === undefined || value === '') {
    return null
  }

  const number = Number(value)

  return Number.isFinite(number) ? number : null
}

function readFirstNumber(source, keys) {
  if (!source) {
    return null
  }

  for (const key of keys) {
    const value = toFiniteNumber(source[key])

    if (value !== null) {
      return value
    }
  }

  return null
}

function sumSegmentMetric(segments, keys, divisor = 1) {
  const values = (Array.isArray(segments) ? segments : [])
    .map((segment) => readFirstNumber(segment, keys))
    .filter((value) => value !== null)

  if (!values.length) {
    return null
  }

  return values.reduce((total, value) => total + value, 0) / divisor
}

function resolveDistanceKm(route, fallback = null) {
  return (
    readFirstNumber(route, ['distance_km', 'distanceKm', 'distance']) ??
    readFirstNumber(fallback, ['distance_km', 'distanceKm', 'distance']) ??
    sumSegmentMetric(route?.route_segments, ['distance_km', 'distanceKm', 'distance']) ??
    sumSegmentMetric(route?.route_segments, ['distance_m', 'distanceMeters'], 1000)
  )
}

function resolveDurationMin(route, fallback = null) {
  return (
    readFirstNumber(route, ['duration_min', 'durationMin', 'duration']) ??
    readFirstNumber(fallback, ['duration_min', 'durationMin', 'duration']) ??
    sumSegmentMetric(route?.route_segments, ['duration_min', 'durationMin', 'duration']) ??
    sumSegmentMetric(route?.route_segments, ['duration_s', 'durationSeconds'], 60)
  )
}

function resolveRouteScore(route, fallback = null) {
  return (
    readFirstNumber(route, ['score']) ??
    readFirstNumber(fallback, ['score'])
  )
}

function normaliseRouteOptions(routeResponse) {
  const options = Array.isArray(routeResponse?.route_options) ? routeResponse.route_options : []

  if (options.length) {
    return options.map((option, index) => {
      const route = {
        ...option,
        id: `${option.provider || 'route'}-${option.label || index}-${index}`,
        label: option.label || `Route ${index + 1}`,
        route_geometry: option.route_geometry || (index === 0 ? routeResponse.route_geometry : null) || null,
        gap_points: Array.isArray(option.gap_points)
          ? option.gap_points
          : index === 0 && Array.isArray(routeResponse.gap_points)
            ? routeResponse.gap_points
            : [],
        route_segments: Array.isArray(option.route_segments)
          ? option.route_segments
          : index === 0 && Array.isArray(routeResponse.route_segments)
            ? routeResponse.route_segments
            : [],
        alerts: Array.isArray(option.alerts)
          ? option.alerts
          : index === 0 && Array.isArray(routeResponse.alerts)
            ? routeResponse.alerts
            : [],
        score: resolveRouteScore(option, index === 0 ? routeResponse : null),
        warning_message: option.warning_message || (index === 0 ? routeResponse.warning_message : '') || '',
        explanations: Array.isArray(option.explanations)
          ? option.explanations
          : index === 0 && Array.isArray(routeResponse.explanations)
            ? routeResponse.explanations
            : [],
        is_supported_area: option.is_supported_area ?? (index === 0 ? routeResponse.is_supported_area : null) ?? null,
      }

      return {
        ...route,
        distance_km: resolveDistanceKm(route, routeResponse),
        duration_min: resolveDurationMin(route, routeResponse),
      }
    })
  }

  if (
    routeResponse?.route_geometry ||
    (Array.isArray(routeResponse?.gap_points) && routeResponse.gap_points.length) ||
    (Array.isArray(routeResponse?.route_segments) && routeResponse.route_segments.length)
  ) {
    const route = {
      id: 'recommended-legacy',
      label: 'Recommended',
      provider: routeResponse.provider || 'mapbox',
      route_geometry: routeResponse.route_geometry || null,
      gap_points: Array.isArray(routeResponse.gap_points) ? routeResponse.gap_points : [],
      route_segments: Array.isArray(routeResponse.route_segments) ? routeResponse.route_segments : [],
      alerts: routeResponse.alerts || [],
      score: resolveRouteScore(routeResponse),
      warning_message: routeResponse.warning_message || '',
      explanations: Array.isArray(routeResponse.explanations) ? routeResponse.explanations : [],
      is_supported_area: routeResponse.is_supported_area ?? null,
    }

    return [
      {
        ...route,
        distance_km: resolveDistanceKm(route, routeResponse),
        duration_min: resolveDurationMin(route, routeResponse),
      },
    ]
  }

  return []
}

function formatDistance(distanceKm) {
  const value = toFiniteNumber(distanceKm)

  if (value === null) {
    return 'Distance pending'
  }

  return `${value.toFixed(value >= 10 ? 1 : 2)} km`
}

function formatDuration(durationMin) {
  const value = toFiniteNumber(durationMin)

  if (value === null) {
    return 'Time pending'
  }

  return `${Math.round(value)} min`
}

function formatRouteScore(score) {
  const value = toFiniteNumber(score)

  if (value === null) {
    return 'Score pending'
  }

  return `Score ${Math.round(value)}`
}

function radians(value) {
  return (value * Math.PI) / 180
}

function distanceBetweenKm(left, right) {
  if (!isCoordinatePair(left) || !isCoordinatePair(right)) {
    return 0
  }

  const [leftLat, leftLng] = left
  const [rightLat, rightLng] = right
  const latDelta = radians(rightLat - leftLat)
  const lngDelta = radians(rightLng - leftLng)
  const a =
    Math.sin(latDelta / 2) ** 2 +
    Math.cos(radians(leftLat)) * Math.cos(radians(rightLat)) * Math.sin(lngDelta / 2) ** 2

  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function bearingBetween(left, right) {
  if (!isCoordinatePair(left) || !isCoordinatePair(right)) {
    return 0
  }

  const [leftLat, leftLng] = left.map(radians)
  const [rightLat, rightLng] = right.map(radians)
  const y = Math.sin(rightLng - leftLng) * Math.cos(rightLat)
  const x =
    Math.cos(leftLat) * Math.sin(rightLat) -
    Math.sin(leftLat) * Math.cos(rightLat) * Math.cos(rightLng - leftLng)

  return (Math.atan2(y, x) * 180) / Math.PI
}

function normaliseTurnAngle(angle) {
  return ((angle + 540) % 360) - 180
}

function getSelectedRouteLatLngCoordinates() {
  return (routeGeometry.value?.coordinates || [])
    .filter((coordinate) => Array.isArray(coordinate) && coordinate.length >= 2)
    .map(([lng, lat]) => [lat, lng])
}

function getNearestRoutePointIndex(location) {
  const coordinates = getSelectedRouteLatLngCoordinates()

  if (!coordinates.length || !isCoordinatePair(location)) {
    return -1
  }

  return coordinates.reduce(
    (nearest, coordinate, index) => {
      const distance = distanceBetweenKm(location, coordinate)
      return distance < nearest.distance ? { distance, index } : nearest
    },
    { distance: Number.POSITIVE_INFINITY, index: -1 },
  ).index
}

function getRemainingDistanceKm(location) {
  const coordinates = getSelectedRouteLatLngCoordinates()
  const nearestIndex = getNearestRoutePointIndex(location)

  if (!coordinates.length || nearestIndex < 0) {
    return selectedRoute.value?.distance_km || 0
  }

  let remainingDistance = distanceBetweenKm(location, coordinates[nearestIndex])

  for (let index = nearestIndex; index < coordinates.length - 1; index += 1) {
    remainingDistance += distanceBetweenKm(coordinates[index], coordinates[index + 1])
  }

  return remainingDistance
}

function getDistanceAlongRouteKm(startIndex, endIndex) {
  const coordinates = getSelectedRouteLatLngCoordinates()

  if (startIndex < 0 || endIndex <= startIndex || !coordinates.length) {
    return 0
  }

  let distance = 0

  for (let index = startIndex; index < endIndex; index += 1) {
    distance += distanceBetweenKm(coordinates[index], coordinates[index + 1])
  }

  return distance
}

function formatTripElapsed(seconds) {
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds % 60
  return `${minutes}:${String(remainder).padStart(2, '0')}`
}

function stopTripTracking() {
  if (tripTimer) {
    window.clearInterval(tripTimer)
    tripTimer = null
  }

  if (tripWatchId !== null) {
    navigator.geolocation?.clearWatch(tripWatchId)
    tripWatchId = null
  }
}

function updateTripLocation(position) {
  const location = [position.coords.latitude, position.coords.longitude]
  tripLiveLocation.value = location
  startCoordinate.value = location
  const nearestIndex = getNearestRoutePointIndex(location)
  const routeCoordinates = getSelectedRouteLatLngCoordinates()
  const nearestDistance =
    nearestIndex >= 0 ? distanceBetweenKm(location, routeCoordinates[nearestIndex]) : Number.POSITIVE_INFINITY

  isTripOffRoute.value = nearestDistance > 0.08
  if (isTripOffRoute.value) {
    tripHadOffRouteEvent.value = true
  }
  tripProgressIndex.value = nearestIndex

  if (endCoordinate.value && distanceBetweenKm(location, endCoordinate.value) <= 0.05) {
    tripStatus.value = 'completed'
    stopTripTracking()
  }
}

function startTrip() {
  if (!selectedRoute.value || !routeGeometry.value || tripStatus.value === 'active') {
    return
  }

  tripStatus.value = 'active'
  tripStartedAt.value = Date.now()
  tripElapsedSeconds.value = 0
  isTripOffRoute.value = false
  tripHadOffRouteEvent.value = false
  isAnalysisVisible.value = false
  mode.value = mapModes.routeAnalysis

  tripTimer = window.setInterval(() => {
    tripElapsedSeconds.value = Math.floor((Date.now() - tripStartedAt.value) / 1000)
  }, 1000)

  if (navigator.geolocation) {
    tripWatchId = navigator.geolocation.watchPosition(updateTripLocation, () => {}, {
      enableHighAccuracy: true,
      maximumAge: 5000,
      timeout: 10000,
    })
  }
}

function endTrip() {
  tripStatus.value = 'completed'
  stopTripTracking()
}

function closeTrip() {
  clearRoutePlan()
}

function exitNavigation() {
  tripStatus.value = 'idle'
  tripStartedAt.value = null
  tripElapsedSeconds.value = 0
  tripLiveLocation.value = null
  tripProgressIndex.value = -1
  isTripOffRoute.value = false
  tripHadOffRouteEvent.value = false
  isAnalysisVisible.value = Boolean(result.value || routeGeometry.value)
  mode.value = mapModes.routeAnalysis
  stopTripTracking()
}

function routeScoreTone(score) {
  const value = toFiniteNumber(score)

  if (value === null) {
    return 'neutral'
  }

  if (value >= 80) {
    return 'green'
  }

  if (value >= 50) {
    return 'yellow'
  }

  return 'red'
}

function setActiveRoute(index) {
  if (!routeOptions.value[index]) {
    return
  }

  activeRouteIndex.value = index
  const route = routeOptions.value[index]
  result.value = route
  routeGeometry.value = route.route_geometry || null
  gapPoints.value = route.gap_points || []
  routeSegments.value = route.route_segments || []
  routeAlerts.value = normaliseRouteAlerts(route)
}

async function revealRouteAnalysis() {
  await nextTick()

  if (!window.matchMedia('(max-width: 620px)').matches || !mapSidePanel.value || !analysisStack.value) {
    return
  }

  mapSidePanel.value.scrollTo({
    top: Math.max(0, analysisStack.value.offsetTop - 8),
    behavior: 'smooth',
  })

  isAnalysisHighlighted.value = true
  window.clearTimeout(analysisHighlightTimer)
  analysisHighlightTimer = window.setTimeout(() => {
    isAnalysisHighlighted.value = false
  }, 1400)
}

function isMobileMapViewport() {
  return typeof window !== 'undefined' && window.matchMedia('(max-width: 620px)').matches
}

function handleMobileAnalysisDragStart(event) {
  if (!isMobileMapViewport()) {
    return
  }

  mobileAnalysisDragStartY.value = event.clientY
  mobileAnalysisDragOffset.value = 0
  isMobileAnalysisDragging.value = true
  hasMobileAnalysisDragged.value = false
  shouldIgnoreAnalysisToggleClick.value = false
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function handleMobileAnalysisDragMove(event) {
  if (mobileAnalysisDragStartY.value === null) {
    return
  }

  const dragDistance = event.clientY - mobileAnalysisDragStartY.value

  mobileAnalysisDragOffset.value = isMobileAnalysisExpanded.value
    ? Math.max(0, dragDistance)
    : Math.min(0, dragDistance)

  if (Math.abs(dragDistance) > 12) {
    hasMobileAnalysisDragged.value = true
  }
}

function finishMobileAnalysisDrag(event) {
  if (mobileAnalysisDragStartY.value === null) {
    return
  }

  const dragDistance = event.clientY - mobileAnalysisDragStartY.value

  if (dragDistance > 48) {
    isMobileAnalysisExpanded.value = false
    shouldIgnoreAnalysisToggleClick.value = true
  } else if (dragDistance < -48) {
    isMobileAnalysisExpanded.value = true
    shouldIgnoreAnalysisToggleClick.value = true
  } else if (hasMobileAnalysisDragged.value) {
    shouldIgnoreAnalysisToggleClick.value = true
  }

  mobileAnalysisDragStartY.value = null
  mobileAnalysisDragOffset.value = 0
  isMobileAnalysisDragging.value = false
  hasMobileAnalysisDragged.value = false
  event.currentTarget.releasePointerCapture?.(event.pointerId)
}

function cancelMobileAnalysisDrag() {
  mobileAnalysisDragStartY.value = null
  mobileAnalysisDragOffset.value = 0
  isMobileAnalysisDragging.value = false
  hasMobileAnalysisDragged.value = false
}

function insightImpactTone(impact) {
  const value = String(impact || '').toLowerCase()

  if (value.includes('high')) {
    return 'high'
  }

  if (value.includes('medium') || value.includes('moderate')) {
    return 'medium'
  }

  if (value.includes('low') || value.includes('good')) {
    return 'low'
  }

  return 'neutral'
}

function handleHeatmapRegionHover(region) {
  activeHeatmapRegion.value = region
}

function formatBackendError(error, fallbackMessage) {
  const detail = String(error?.detail || error?.message || '').trim()

  if (!detail) {
    return fallbackMessage
  }

  if (detail.includes('422') || detail.includes('Request failed with status')) {
    return fallbackMessage
  }

  return detail
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

function closeAddressSuggestions() {
  activeSearchField.value = null
}

function handleDocumentPointerDown(event) {
  const searchElement = routeSearchContainer.value

  if (!searchElement || searchElement.contains(event.target)) {
    return
  }

  closeAddressSuggestions()
}

const isHeatmapMode = computed(
  () => mode.value === mapModes.heatmapPanel || mode.value === mapModes.heatmapMapOnly,
)

const showRouteControls = computed(() => !isHeatmapMode.value && tripStatus.value === 'idle')
const showAnalysis = computed(
  () => mode.value === mapModes.routeAnalysis && isAnalysisVisible.value && tripStatus.value !== 'active',
)
const showHeatmapPanel = computed(() => mode.value === mapModes.heatmapPanel)
const isSidePanelVisible = ref(shouldRestoreMapState ? savedMapState.isSidePanelVisible !== false : true)
const showReportMarkers = ref(shouldRestoreMapState ? savedMapState.showReportMarkers !== false : true)
const showSidePanel = computed(() => isSidePanelVisible.value)
const mapDisplayMode = computed(() => (isHeatmapMode.value ? 'heatmap' : 'route'))
const hasPlannedRoute = computed(() =>
  Boolean(
    result.value ||
      routeOptions.value.length ||
      routeGeometry.value ||
      gapPoints.value.length ||
      routeSegments.value.length ||
      routeAlerts.value.length,
  ),
)

function saveMapState() {
  const state = {
    mode: mode.value,
    start: start.value,
    destination: destination.value,
    startCoordinate: startCoordinate.value,
    endCoordinate: endCoordinate.value,
    hasStartCoordinate: hasStartCoordinate.value,
    hasDestinationCoordinate: hasDestinationCoordinate.value,
    isInitialLocationResolved: isInitialLocationResolved.value,
    locationStatus: locationStatus.value,
    currentLocationLabel: currentLocationLabel.value,
    result: result.value,
    isAnalysisVisible: isAnalysisVisible.value,
    routeAlerts: routeAlerts.value,
    routeAlertsStatusMessage: routeAlertsStatusMessage.value,
    routeOptions: routeOptions.value,
    activeRouteIndex: activeRouteIndex.value,
    routeGeometry: routeGeometry.value,
    gapPoints: gapPoints.value,
    routeSegments: routeSegments.value,
    isSidePanelVisible: isSidePanelVisible.value,
    showReportMarkers: showReportMarkers.value,
  }

  try {
    sessionStorage.setItem(mapStateKey, JSON.stringify(state))
  } catch (error) {
    // Ignore storage failures, for example private browsing quota limits.
  }
}

async function loadMelbourneSa2Heatmap() {
  if (heatmapRegions.value.length || isHeatmapLoading.value) {
    return
  }

  isHeatmapLoading.value = true
  heatmapError.value = ''

  try {
    const response = await getMelbourneSa2Heatmap()
    heatmapRegions.value = response.regions || []
    activeHeatmapRegion.value = null
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
    const routeResult = await recommendRoute(payload)
    routeOptions.value = normaliseRouteOptions(routeResult)
    activeRouteIndex.value = 0
    routeAlertsStatusMessage.value = routeResult.alerts_status_message || ''
    result.value = routeOptions.value[0] || null

    if (routeOptions.value.length) {
      setActiveRoute(0)
    } else {
      routeAlerts.value = []
      routeGeometry.value = null
      gapPoints.value = []
      routeSegments.value = []
    }
  } catch (error) {
    result.value = null
    routeOptions.value = []
    activeRouteIndex.value = 0
    routeAlerts.value = []
    routeAlertsStatusMessage.value = ''
    routeGeometry.value = null
    gapPoints.value = []
    routeSegments.value = []
    errorMessage.value = formatBackendError(error, 'Route generation failed for the selected points.')
  } finally {
    isAnalysisVisible.value = Boolean(
      result.value || routeGeometry.value || gapPoints.value.length || routeSegments.value.length,
    )
    mode.value =
      result.value || routeGeometry.value || gapPoints.value.length || routeSegments.value.length
        ? mapModes.routeAnalysis
        : mapModes.routeInput
    isLoading.value = false

    if (isAnalysisVisible.value) {
      isMobileAnalysisExpanded.value = true
      revealRouteAnalysis()
    }
  }
}

async function recalculateTripRoute() {
  if (!tripLiveLocation.value || !endCoordinate.value || isRecalculatingTrip.value) {
    return
  }

  isRecalculatingTrip.value = true
  errorMessage.value = ''
  startCoordinate.value = tripLiveLocation.value
  hasStartCoordinate.value = true

  try {
    const routeResult = await recommendRoute({
      start_lat: tripLiveLocation.value[0],
      start_lng: tripLiveLocation.value[1],
      end_lat: endCoordinate.value[0],
      end_lng: endCoordinate.value[1],
    })

    routeOptions.value = normaliseRouteOptions(routeResult)
    activeRouteIndex.value = 0
    routeAlertsStatusMessage.value = routeResult.alerts_status_message || ''
    result.value = routeOptions.value[0] || null

    if (routeOptions.value.length) {
      setActiveRoute(0)
      tripProgressIndex.value = 0
      isTripOffRoute.value = false
    }
  } catch (error) {
    errorMessage.value = formatBackendError(error, 'Unable to recalculate the route right now.')
  } finally {
    isRecalculatingTrip.value = false
  }
}

function showRouteMode() {
  mode.value =
    result.value || routeGeometry.value || gapPoints.value.length || routeSegments.value.length
      ? mapModes.routeAnalysis
      : mapModes.routeInput
  isSidePanelVisible.value = true
}

function hideAnalysis() {
  isAnalysisVisible.value = false
  isMobileAnalysisExpanded.value = false
}

function clearRoutePlan() {
  tripStatus.value = 'idle'
  tripStartedAt.value = null
  tripElapsedSeconds.value = 0
  tripLiveLocation.value = null
  tripProgressIndex.value = -1
  isTripOffRoute.value = false
  tripHadOffRouteEvent.value = false
  stopTripTracking()
  result.value = null
  routeOptions.value = []
  activeRouteIndex.value = 0
  routeAlerts.value = []
  routeAlertsStatusMessage.value = ''
  routeGeometry.value = null
  gapPoints.value = []
  routeSegments.value = []
  destination.value = ''
  endCoordinate.value = null
  hasDestinationCoordinate.value = false
  destinationSuggestions.value = []
  activeSearchField.value = null
  isAnalysisVisible.value = false
  isMobileAnalysisExpanded.value = false
  errorMessage.value = ''
  mode.value = mapModes.routeInput
}

function toggleMobileAnalysis() {
  if (shouldIgnoreAnalysisToggleClick.value) {
    shouldIgnoreAnalysisToggleClick.value = false
    return
  }

  isMobileAnalysisExpanded.value = !isMobileAnalysisExpanded.value
}

async function showHeatmapPanelMode() {
  mode.value = mapModes.heatmapPanel
  isSidePanelVisible.value = true
  await loadMelbourneSa2Heatmap()
}

function showHeatmapMapOnlyMode() {
  mode.value = mapModes.heatmapMapOnly
  isSidePanelVisible.value = false
}

function hideSidePanel() {
  isSidePanelVisible.value = false
}

function toggleReportMarkers() {
  showReportMarkers.value = !showReportMarkers.value
}

async function showSidePanelAgain() {
  isSidePanelVisible.value = true

  if (isHeatmapMode.value && !heatmapRegions.value.length) {
    await loadMelbourneSa2Heatmap()
  }
}

async function resolveCurrentLocationLabel() {
  try {
    const place = await reverseMapboxPlace(startCoordinate.value)

    if (place?.label) {
      currentLocationLabel.value =
        place.address && place.address !== place.label ? `${place.label}, ${place.address}` : place.label
    } else {
      currentLocationLabel.value = 'Current location'
    }
  } catch (error) {
    currentLocationLabel.value = 'Current location'
  }
}

function handleLocationFound(location) {
  startCoordinate.value = [location.lat, location.lng]
  start.value = ''
  hasStartCoordinate.value = true
  startSuggestions.value = []
  locationStatus.value = 'Using your current location as the start point.'
}

function requestBrowserLocation(options) {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, options)
  })
}

function getLocationFailureMessage(error) {
  if (typeof window !== 'undefined' && !window.isSecureContext) {
    return 'Location requires HTTPS or localhost. Using Melbourne Central as a fallback.'
  }

  if (error?.code === error?.PERMISSION_DENIED) {
    return 'Location permission was not granted. Using Melbourne Central as a fallback.'
  }

  if (error?.code === error?.POSITION_UNAVAILABLE) {
    return 'Your device could not provide a location. Using Melbourne Central as a fallback.'
  }

  if (error?.code === error?.TIMEOUT) {
    return 'Location timed out. Using Melbourne Central as a fallback.'
  }

  return 'Current location is unavailable. Using Melbourne Central as a fallback.'
}

async function refineCurrentLocation() {
  try {
    const position = await requestBrowserLocation({
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 25000,
    })

    handleLocationFound({
      lat: position.coords.latitude,
      lng: position.coords.longitude,
    })
    resolveCurrentLocationLabel()
  } catch (error) {
    // The coarse location is already usable; a high-accuracy refresh is a best-effort upgrade.
  }
}

async function loadPublicReports() {
  try {
    const response = await getAllReports()
    publicReports.value = Array.isArray(response.reports) ? response.reports : []
  } catch (error) {
    if (!publicReports.value.length) {
      publicReports.value = []
    }
  }
}

function startPublicReportsPolling() {
  window.clearInterval(publicReportsRefreshTimer)
  publicReportsRefreshTimer = window.setInterval(loadPublicReports, 5000)
}

function handleReportLocation(location) {
  router.push({
    name: 'report',
    query: {
      lat: location.latitude.toFixed(6),
      lng: location.longitude.toFixed(6),
    },
  })
}

function handleReportLikeUpdated({ reportId, likeCount, likedByCurrentUser }) {
  publicReports.value = publicReports.value.map((report) => {
    if (report.id === reportId || report.report_id === reportId) {
      return {
        ...report,
        like_count: likeCount,
        likes: likeCount,
        liked_by_current_user: likedByCurrentUser,
      }
    }
    return report
  })
  loadPublicReports()
}

async function useCurrentLocationAsStart() {
  start.value = 'Resolving current address...'
  if (!currentLocationLabel.value) {
    await resolveCurrentLocationLabel()
  }

  start.value = currentLocationLabel.value || 'Current location'
  hasStartCoordinate.value = true
  locationStatus.value = 'Using your current location as the start point.'
}

async function locateUserOnLoad() {
  if (!navigator.geolocation) {
    locationStatus.value = 'Browser location is unavailable. Using Melbourne Central as a fallback.'
    isInitialLocationResolved.value = true
    return
  }

  try {
    const position = await requestBrowserLocation({
      enableHighAccuracy: false,
      maximumAge: 120000,
      timeout: 20000,
    })

    handleLocationFound({
      lat: position.coords.latitude,
      lng: position.coords.longitude,
    })
    resolveCurrentLocationLabel()
    isInitialLocationResolved.value = true
    refineCurrentLocation()
  } catch (error) {
    try {
      const position = await requestBrowserLocation({
        enableHighAccuracy: true,
        maximumAge: 60000,
        timeout: 25000,
      })

      handleLocationFound({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
      })
      resolveCurrentLocationLabel()
    } catch (fallbackError) {
      locationStatus.value = getLocationFailureMessage(fallbackError || error)
    } finally {
      isInitialLocationResolved.value = true
    }
  }
}

watch(
  [
    mode,
    start,
    destination,
    startCoordinate,
    endCoordinate,
    hasStartCoordinate,
    hasDestinationCoordinate,
    isInitialLocationResolved,
    locationStatus,
    currentLocationLabel,
    result,
    isAnalysisVisible,
    routeAlerts,
    routeAlertsStatusMessage,
    routeOptions,
    activeRouteIndex,
    routeGeometry,
    gapPoints,
    routeSegments,
    isSidePanelVisible,
    showReportMarkers,
  ],
  saveMapState,
  { deep: true },
)

onMounted(() => {
  if (!shouldRestoreMapState) {
    locateUserOnLoad()
  }

  loadPublicReports()
  startPublicReportsPolling()
  document.addEventListener('pointerdown', handleDocumentPointerDown)
})

onBeforeUnmount(() => {
  window.clearTimeout(analysisHighlightTimer)
  window.clearInterval(publicReportsRefreshTimer)
  stopTripTracking()
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
})

const displayedGapCount = computed(() =>
  gapPoints.value.length || (routeGeometry.value ? 0 : routeSegments.value.filter((segment) => segment.is_gap).length),
)

const selectedRoute = computed(() => routeOptions.value[activeRouteIndex.value] || null)

const routeOptionCards = computed(() =>
  routeOptions.value.map((route, index) => {
    const gapCount =
      (route.gap_points || []).length ||
      (route.route_geometry ? 0 : (route.route_segments || []).filter((segment) => segment.is_gap).length)

    return {
      ...route,
      index,
      gapCount,
      distanceLabel: formatDistance(route.distance_km),
      durationLabel: formatDuration(route.duration_min),
      scoreLabel: formatRouteScore(route.score),
      tone: routeScoreTone(route.score),
    }
  }),
)

const feasibilityInsights = computed(() =>
  (result.value?.explanations || []).filter((item) => {
    const factor = String(item.factor || '').toLowerCase()

    return !factor.includes('gap') && !factor.includes('disconnected')
  }),
)

const selectedRouteMetrics = computed(() => ({
  distanceLabel: selectedRoute.value ? formatDistance(selectedRoute.value.distance_km) : '',
  durationLabel: selectedRoute.value ? formatDuration(selectedRoute.value.duration_min) : '',
}))

const tripRemainingDistanceKm = computed(() =>
  tripStatus.value === 'active' && tripLiveLocation.value
    ? getRemainingDistanceKm(tripLiveLocation.value)
    : selectedRoute.value?.distance_km || 0,
)

const tripRemainingMinutes = computed(() => {
  const routeDistance = selectedRoute.value?.distance_km || 0
  const routeDuration = selectedRoute.value?.duration_min || 0

  if (!routeDistance || !routeDuration) {
    return 0
  }

  return Math.max(0, (tripRemainingDistanceKm.value / routeDistance) * routeDuration)
})

const tripStatusLabel = computed(() => {
  if (tripStatus.value === 'completed') {
    return 'Trip completed'
  }

  return isTripOffRoute.value ? 'Off route' : 'On route'
})

const nextManeuver = computed(() => {
  if (tripStatus.value !== 'active') {
    return null
  }

  const coordinates = getSelectedRouteLatLngCoordinates()
  const startIndex = Math.max(tripProgressIndex.value, 0)

  if (coordinates.length < 3 || startIndex >= coordinates.length - 2) {
    return {
      label: 'Continue to destination',
      distance: tripRemainingDistanceKm.value,
      tone: 'straight',
    }
  }

  for (let index = Math.max(startIndex + 1, 1); index < coordinates.length - 1; index += 1) {
    const incomingBearing = bearingBetween(coordinates[index - 1], coordinates[index])
    const outgoingBearing = bearingBetween(coordinates[index], coordinates[index + 1])
    const turnAngle = normaliseTurnAngle(outgoingBearing - incomingBearing)

    if (Math.abs(turnAngle) >= 35) {
      return {
        label: turnAngle > 0 ? 'Turn right' : 'Turn left',
        distance: getDistanceAlongRouteKm(startIndex, index),
        tone: turnAngle > 0 ? 'right' : 'left',
      }
    }
  }

  return {
    label: 'Continue straight',
    distance: tripRemainingDistanceKm.value,
    tone: 'straight',
  }
})

const completedTripSummary = computed(() => ({
  duration: formatTripElapsed(tripElapsedSeconds.value),
  distance: selectedRoute.value ? formatDistance(selectedRoute.value.distance_km) : 'Distance pending',
  score: selectedRoute.value ? formatRouteScore(selectedRoute.value.score) : 'Score pending',
  deviation: tripHadOffRouteEvent.value ? 'Route adjusted' : 'Stayed on route',
  warnings:
    displayedGapCount.value > 0
      ? `${displayedGapCount.value} gap${displayedGapCount.value === 1 ? '' : 's'}`
      : `${routeAlerts.value.length} warning${routeAlerts.value.length === 1 ? '' : 's'}`,
}))

const warningCards = computed(() =>
  routeGeometry.value || gapPoints.value.length || routeSegments.value.length
    ? [
          {
            id: 'alerts',
            name: 'Warnings',
            time:
              displayedGapCount.value > 0
              ? `${displayedGapCount.value} gap${displayedGapCount.value === 1 ? '' : 's'} detected`
              : `${routeAlerts.value.length} alert${routeAlerts.value.length === 1 ? '' : 's'}`,
          distance: selectedRoute.value
            ? `${formatDistance(selectedRoute.value.distance_km)} route`
            : 'Live route data',
          risk: displayedGapCount.value > 0 ? displayedGapCount.value : routeAlerts.value.length,
          tone: displayedGapCount.value > 0 || routeAlerts.value.length ? 'yellow' : 'green',
          summary:
            displayedGapCount.value > 0
              ? 'Infrastructure gaps detected along the recommended route.'
              : routeAlerts.value.length
              ? routeAlerts.value[0].message
              : routeAlertsStatusMessage.value || 'No route warning points were returned by the backend.',
        },
      ]
    : [],
)

const isMobileAnalysisRevealing = computed(
  () => isMobileAnalysisDragging.value && !isMobileAnalysisExpanded.value && mobileAnalysisDragOffset.value < 0,
)

function getMobileExpandedAnalysisHeight() {
  if (typeof window === 'undefined') {
    return 490
  }

  return Math.min(window.innerHeight * 0.56, 490)
}

const mobileAnalysisStyle = computed(() => ({
  '--analysis-drag-height': isMobileAnalysisDragging.value
    ? isMobileAnalysisExpanded.value
      ? `${Math.max(35, getMobileExpandedAnalysisHeight() - mobileAnalysisDragOffset.value)}px`
      : `${Math.min(getMobileExpandedAnalysisHeight(), 35 + Math.abs(mobileAnalysisDragOffset.value))}px`
    : undefined,
  '--analysis-drag-progress':
    isMobileAnalysisDragging.value && isMobileAnalysisExpanded.value
      ? Math.min(1, mobileAnalysisDragOffset.value / Math.max(getMobileExpandedAnalysisHeight() - 35, 1))
      : 0,
}))
</script>

<template>
  <section class="map-view-wrapper">
    <div class="mapbox-shell">
      <MapboxMap
        v-if="isInitialLocationResolved"
        :mode="mapDisplayMode"
        :route-geometry="routeGeometry"
        :route-options="routeOptions"
        :active-route-index="activeRouteIndex"
        :gap-points="gapPoints"
        :route-segments="routeSegments"
        :trip-progress-index="tripProgressIndex"
        :trip-follow-point="tripLiveLocation"
        :heatmap-regions="heatmapRegions"
        :alerts="routeAlerts"
        :start-point="startCoordinate"
        :end-point="endCoordinate"
        :reports="publicReports"
        :show-report-markers="showReportMarkers"
        @location-found="handleLocationFound"
        @heatmap-region-hover="handleHeatmapRegionHover"
        @report-location="handleReportLocation"
        @report-like-updated="handleReportLikeUpdated"
        @route-selected="setActiveRoute"
      />
      <div v-else class="glass-panel locating-panel">
        <h2>Locating...</h2>
        <p>Requesting GPS access</p>
      </div>
    </div>

    <div
      class="floating-controls"
      :class="{ 'floating-controls-stacked': showSidePanel && showAnalysis && routeOptionCards.length }"
      aria-label="Map mode controls"
    >
      <button type="button" :class="{ secondary: isHeatmapMode }" @click="showRouteMode">Route</button>
      <button type="button" :class="{ secondary: !isHeatmapMode }" @click="showHeatmapPanelMode">
        {{ isHeatmapLoading ? 'Loading...' : 'Heatmap' }}
      </button>
      <button
        type="button"
        :class="{ secondary: !showReportMarkers }"
        @click="toggleReportMarkers"
      >
        {{ showReportMarkers ? 'Reports On' : 'Reports Off' }}
      </button>
    </div>

    <transition name="slide-up">
      <section
        v-if="showSidePanel && showAnalysis && routeOptionCards.length"
        class="route-top-strip"
        :class="{ 'with-side-panel': showSidePanel }"
        aria-label="Route options"
      >
        <div class="route-top-header">
          <span>Routes</span>
          <strong>{{ routeOptionCards.length }} options</strong>
        </div>
        <div class="route-top-list">
          <button
            v-for="route in routeOptionCards"
            :key="route.id"
            type="button"
            class="route-option-card route-top-card"
            :class="[
              `route-option-${route.tone}`,
              { active: route.index === activeRouteIndex },
            ]"
            @click="setActiveRoute(route.index)"
          >
            <span class="route-option-rank">{{ route.index + 1 }}</span>
            <span class="route-option-main">
              <span class="route-option-kicker">
                {{ route.index === activeRouteIndex ? 'Selected route' : `Option ${route.index + 1}` }}
              </span>
              <strong>{{ route.label }}</strong>
              <span v-if="route.gapCount" class="route-option-gap">
                {{ route.gapCount }} gap{{ route.gapCount === 1 ? '' : 's' }}
              </span>
            </span>
            <span class="route-option-metrics">
              <strong>{{ route.durationLabel }}</strong>
              <span>{{ route.distanceLabel }}</span>
              <span class="route-option-score">{{ route.scoreLabel }}</span>
            </span>
          </button>
        </div>
      </section>
    </transition>

    <section v-if="selectedRoute && !isHeatmapMode" class="trip-launch-panel glass-panel">
      <template v-if="tripStatus === 'idle'">
        <div>
          <span class="panel-kicker">Ready to ride</span>
          <strong>{{ selectedRoute.label || 'Selected route' }}</strong>
        </div>
        <button type="button" class="primary" @click="startTrip">Start Trip</button>
      </template>

      <template v-else>
        <div class="trip-live-summary">
          <span class="panel-kicker">{{ tripStatusLabel }}</span>
          <strong>{{ formatTripElapsed(tripElapsedSeconds) }}</strong>
        </div>
        <div v-if="nextManeuver" class="trip-maneuver" :class="`trip-maneuver-${nextManeuver.tone}`">
          <span>{{ nextManeuver.label }}</span>
          <strong>{{ formatDistance(nextManeuver.distance) }}</strong>
        </div>
        <div class="trip-live-metrics">
          <span>{{ formatDistance(tripRemainingDistanceKm) }} left</span>
          <span>{{ formatDuration(tripRemainingMinutes) }} left</span>
        </div>
        <button
          v-if="tripStatus === 'active' && isTripOffRoute"
          type="button"
          class="trip-recalculate-btn"
          :disabled="isRecalculatingTrip"
          @click="recalculateTripRoute"
        >
          {{ isRecalculatingTrip ? 'Recalculating...' : 'Recalculate Route' }}
        </button>
        <button v-if="tripStatus === 'active'" type="button" class="secondary" @click="exitNavigation">
          Exit Navigation
        </button>
        <button
          type="button"
          class="secondary"
          @click="tripStatus === 'completed' ? closeTrip() : endTrip()"
        >
          {{ tripStatus === 'completed' ? 'Close Trip' : 'End Trip' }}
        </button>
      </template>
    </section>

    <section v-if="tripStatus === 'completed'" class="trip-summary-card glass-panel">
      <div class="trip-summary-header">
        <span class="panel-kicker">Trip complete</span>
        <strong>{{ completedTripSummary.duration }}</strong>
      </div>
      <div class="trip-summary-grid">
        <div>
          <span>Distance</span>
          <strong>{{ completedTripSummary.distance }}</strong>
        </div>
        <div>
          <span>Safety</span>
          <strong>{{ completedTripSummary.score }}</strong>
        </div>
        <div>
          <span>Journey</span>
          <strong>{{ completedTripSummary.deviation }}</strong>
        </div>
        <div>
          <span>Warnings</span>
          <strong>{{ completedTripSummary.warnings }}</strong>
        </div>
      </div>
    </section>

    <div
      class="map-report-hint"
      :class="{ 'map-report-hint-trip-active': selectedRoute && !isHeatmapMode }"
      aria-label="How to report a map issue"
    >
      <span>Report a hazard</span>
      <p>Desktop: right-click the map. Mobile: long-press a location.</p>
    </div>

    <button
      v-if="!showSidePanel"
      type="button"
      class="side-panel-toggle side-panel-toggle-show"
      @click="showSidePanelAgain"
    >
      Show Panel
    </button>

    <transition name="panel-slide">
      <aside v-if="showSidePanel" ref="mapSidePanel" class="map-side-panel">
        <form
          v-if="showRouteControls"
          class="glass-panel compact-planner"
          :class="{ 'planner-collapsed': hasPlannedRoute }"
          @submit.prevent="evaluateJourney"
        >
        <div class="planner-header">
          <div>
            <h2>Trip Planner</h2>
            <p>Find the safest path.</p>
          </div>
          <div class="planner-header-actions">
            <button
              v-if="hasPlannedRoute"
              type="button"
              class="side-panel-toggle route-clear-btn"
              @click="clearRoutePlan"
            >
              Clear Route
            </button>
            <button type="button" class="side-panel-toggle side-panel-toggle-hide" @click="hideSidePanel">
              Hide
            </button>
          </div>
        </div>

        <div ref="routeSearchContainer" class="route-inputs-group">
          <div class="route-connector">
            <div class="dot origin-dot"></div>
            <div class="line"></div>
            <div class="dot dest-dot"></div>
          </div>

          <div class="inputs-container">
            <div
              class="input-wrapper"
              :class="{ 'input-wrapper-active': activeSearchField === 'start' && startSuggestions.length }"
            >
              <input
                v-model="start"
                type="text"
                placeholder="Current Location"
                autocomplete="off"
                @input="queueAddressSearch('start', start)"
                @focus="activeSearchField = 'start'"
              />
              <button
                v-if="isInitialLocationResolved"
                type="button"
                class="icon-btn locate-btn"
                title="Use current location"
                @click="useCurrentLocationAsStart"
              >
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
                  <polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
                </svg>
              </button>

              <ul v-if="activeSearchField === 'start' && startSuggestions.length" class="suggestion-list">
                <li v-for="suggestion in startSuggestions" :key="suggestion.id">
                  <button type="button" @click="selectSuggestion('start', suggestion)">
                    <span class="suggestion-copy">
                      <span class="suggestion-title">{{ suggestion.label }}</span>
                      <span v-if="suggestion.address" class="suggestion-address">{{ suggestion.address }}</span>
                    </span>
                  </button>
                </li>
              </ul>
            </div>

            <div class="input-divider"></div>

            <div
              class="input-wrapper"
              :class="{
                'input-wrapper-active': activeSearchField === 'destination' && destinationSuggestions.length,
              }"
            >
              <input
                v-model="destination"
                type="text"
                placeholder="Where to?"
                autocomplete="off"
                @input="queueAddressSearch('destination', destination)"
                @focus="activeSearchField = 'destination'"
              />

              <ul
                v-if="activeSearchField === 'destination' && destinationSuggestions.length"
                class="suggestion-list"
              >
                <li v-for="suggestion in destinationSuggestions" :key="suggestion.id">
                  <button type="button" @click="selectSuggestion('destination', suggestion)">
                    <span class="suggestion-copy">
                      <span class="suggestion-title">{{ suggestion.label }}</span>
                      <span v-if="suggestion.address" class="suggestion-address">{{ suggestion.address }}</span>
                    </span>
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <button type="submit" class="primary glow-btn" :class="{ loading: isLoading }" :disabled="isLoading || !isInitialLocationResolved">
          <span v-if="isLoading" class="route-loading-spinner" aria-hidden="true"></span>
          <span>{{ isLoading ? 'Computing route...' : hasPlannedRoute ? 'Update Route' : 'Generate Route' }}</span>
        </button>
        <p v-if="isSearching" class="helper-text">Searching addresses...</p>
        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
      </form>

      <section v-if="showHeatmapPanel" class="glass-panel heatmap-panel">
        <div class="heatmap-panel-header">
          <div class="panel-header-row">
            <div>
              <h2>Safety Layer</h2>
              <p>{{ heatmapRegions.length }} SA2 regions loaded.</p>
            </div>
            <button type="button" class="side-panel-toggle side-panel-toggle-hide" @click="hideSidePanel">
              Hide
            </button>
          </div>
          <p v-if="heatmapError" class="status-text">{{ heatmapError }}</p>
        </div>

        <article class="heatmap-region-card">
          <span class="panel-kicker">Selected Region</span>

          <template v-if="activeHeatmapRegion">
            <div class="heatmap-region-summary">
              <div>
                <h3>{{ activeHeatmapRegion.name }}</h3>
                <p>Move across the heatmap to compare neighbourhood risk signals.</p>
              </div>
              <span class="pill" :class="`pill-${riskTone(activeHeatmapRegion.riskLevel)}`">
                {{ activeHeatmapRegion.riskLevel }}
              </span>
            </div>

            <div class="heatmap-region-metrics">
              <div class="heatmap-metric">
                <span class="metric-label">Score</span>
                <strong>{{ activeHeatmapRegion.score ?? 'N/A' }}</strong>
              </div>
            </div>
          </template>

          <div v-else class="heatmap-region-empty">
            <h3>Move across the map</h3>
            <p>Select an SA2 region on the heatmap to reveal its risk signal and supporting data.</p>
          </div>
        </article>

        <div class="heatmap-panel-grid">
          <div class="heatmap-support-card">
            <span class="panel-kicker">Legend</span>
            <div class="heatmap-legend" aria-label="Heatmap legend">
              <span><i class="legend-critical"></i> Critical</span>
              <span><i class="legend-high"></i> High</span>
              <span><i class="legend-medium"></i> Safe</span>
            </div>
          </div>
        </div>
      </section>

      <transition name="slide-up">
        <div
          v-if="showAnalysis"
          ref="analysisStack"
          class="analysis-stack"
          :style="mobileAnalysisStyle"
          :class="{
            'analysis-stack-highlight': isAnalysisHighlighted,
            'analysis-stack-expanded': isMobileAnalysisExpanded,
            'analysis-stack-dragging': isMobileAnalysisDragging,
            'analysis-stack-revealing': isMobileAnalysisRevealing,
          }"
        >
          <button
            type="button"
            class="analysis-sheet-toggle"
            :aria-expanded="isMobileAnalysisExpanded"
            :aria-label="isMobileAnalysisExpanded ? 'Drag down to minimise route details' : 'Drag up to show route details'"
            @pointerdown="handleMobileAnalysisDragStart"
            @pointermove="handleMobileAnalysisDragMove"
            @pointerup="finishMobileAnalysisDrag"
            @pointercancel="cancelMobileAnalysisDrag"
            @click="toggleMobileAnalysis"
          >
            <span class="analysis-sheet-handle" aria-hidden="true"></span>
            <span>{{ isMobileAnalysisExpanded ? 'Swipe down' : 'Details' }}</span>
          </button>

          <ScorePanel
            v-if="result"
            :result="result"
            :duration-label="selectedRouteMetrics.durationLabel"
            :distance-label="selectedRouteMetrics.distanceLabel"
            @close="hideAnalysis"
          />

          <div v-if="feasibilityInsights.length" class="glass-panel compact-overview analysis-detail-panel">
            <div class="overview-header">
              <h3>Feasibility Insights</h3>
            </div>
            <div class="feasibility-list">
              <article
                v-for="item in feasibilityInsights"
                :key="`${item.factor}-${item.impact}`"
                class="feasibility-card"
                :class="`feasibility-${insightImpactTone(item.impact)}`"
              >
                <div class="feasibility-copy">
                  <h4>{{ item.factor }}</h4>
                  <p>
                    <span class="impact-badge" :class="`impact-${insightImpactTone(item.impact)}`">
                      {{ item.impact }}
                    </span>
                  </p>
                </div>
              </article>
            </div>
          </div>

          <div class="glass-panel compact-overview analysis-detail-panel">
            <div class="overview-header">
              <h3>Warnings</h3>
            </div>
            <div class="route-cards-vertical">
              <RouteCard v-for="route in warningCards" :key="route.id" :route="route" />
            </div>
          </div>

        </div>
      </transition>
      </aside>
    </transition>
  </section>
</template>
