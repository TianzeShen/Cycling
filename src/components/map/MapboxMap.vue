<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { pointToFeature, toMapboxLngLat } from '../../utils/mapCoordinates'
import {
  getReportLikeSession,
  getReportLikes,
  incrementReportLikes,
  saveReportLikeSession,
} from '../../services/api'

const props = defineProps({
  mode: {
    type: String,
    default: 'route',
  },
  routeGeometry: {
    type: Object,
    default: null,
  },
  routeOptions: {
    type: Array,
    default: () => [],
  },
  activeRouteIndex: {
    type: Number,
    default: 0,
  },
  gapPoints: {
    type: Array,
    default: () => [],
  },
  routeSegments: {
    type: Array,
    default: () => [],
  },
  heatmapRegions: {
    type: Array,
    default: () => [],
  },
  alerts: {
    type: Array,
    default: () => [],
  },
  startPoint: {
    type: Array,
    default: () => [-37.8136, 144.9631],
  },
  endPoint: {
    type: Array,
    default: null,
  },
  reports: {
    type: Array,
    default: () => [],
  },
  showReportMarkers: {
    type: Boolean,
    default: true,
  },
  autoGeolocate: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['location-found', 'heatmap-region-hover', 'report-location', 'route-selected'])

const mapContainer = ref(null)
const map = ref(null)
const mapReady = ref(false)
const geolocate = ref(null)
const reportMenu = ref(null)
const activeReportPopup = ref(null)
const reportLikeBursts = ref([])
const REPORT_LIKE_WINDOW_MS = 5000
let reportLikeTimer = null
let longPressTimer = null
let longPressPoint = null
let heatmapHoverFrame = null
let pendingHeatmapHoverFeature = null
let lastHeatmapHoverCode = null
const token = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN
const mapStyle = import.meta.env.VITE_MAPBOX_STYLE || 'mapbox://styles/mapbox/streets-v12'
const useRasterBaseMap = import.meta.env.VITE_MAPBOX_RASTER_BASE !== 'false'
const MELBOURNE_BOUNDS = [
  [144.4, -38.3],
  [145.6, -37.4],
]
const heatmapRegionBounds = new WeakMap()
const GAP_MARKER_IMAGE_ID = 'gap-marker'

const hasToken = computed(() => Boolean(token) && token.startsWith('pk.'))

function clearLongPressTimer() {
  if (longPressTimer) {
    window.clearTimeout(longPressTimer)
    longPressTimer = null
  }

  longPressPoint = null
}

function clearPendingHeatmapHover() {
  if (heatmapHoverFrame) {
    window.cancelAnimationFrame(heatmapHoverFrame)
    heatmapHoverFrame = null
  }

  pendingHeatmapHoverFeature = null
}

function clearReportLikeTimer() {
  if (reportLikeTimer) {
    window.clearInterval(reportLikeTimer)
    reportLikeTimer = null
  }
}

function setMapMovingClass(isMoving) {
  document.body.classList.toggle('map-is-moving', isMoving)
}

function showReportMenuFromMapEvent(event) {
  reportMenu.value = {
    x: event.point.x,
    y: event.point.y,
    lat: event.lngLat.lat,
    lng: event.lngLat.lng,
  }
}

function handleRouteOptionClick(event) {
  const feature = event.features?.[0]
  const routeIndex = Number(feature?.properties?.routeIndex)

  if (!Number.isInteger(routeIndex)) {
    return
  }

  reportMenu.value = null
  emit('route-selected', routeIndex)
}

function emptyCollection() {
  return {
    type: 'FeatureCollection',
    features: [],
  }
}

function getBaseMapStyle() {
  if (!useRasterBaseMap) {
    return mapStyle
  }

  const styleId = mapStyle.startsWith('mapbox://styles/mapbox/')
    ? mapStyle.replace('mapbox://styles/mapbox/', '')
    : 'streets-v12'
  const encodedToken = encodeURIComponent(token)

  return {
    version: 8,
    glyphs: `https://api.mapbox.com/fonts/v1/mapbox/{fontstack}/{range}.pbf?access_token=${encodedToken}`,
    sources: {
      'mapbox-raster-basemap': {
        type: 'raster',
        tiles: [
          `https://api.mapbox.com/styles/v1/mapbox/${styleId}/tiles/512/{z}/{x}/{y}?access_token=${encodedToken}`,
        ],
        tileSize: 512,
        attribution:
          '&copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      },
    },
    layers: [
      {
        id: 'mapbox-raster-basemap',
        type: 'raster',
        source: 'mapbox-raster-basemap',
        paint: {
          'raster-fade-duration': 0,
        },
      },
    ],
  }
}

function getMainRouteCollection() {
  if (props.routeGeometry?.type === 'LineString' && Array.isArray(props.routeGeometry.coordinates)) {
    return {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {},
          geometry: props.routeGeometry,
        },
      ],
    }
  }

  return emptyCollection()
}

function routeOptionToFeature(route, index) {
  if (route?.route_geometry?.type === 'LineString' && Array.isArray(route.route_geometry.coordinates)) {
    return {
      type: 'Feature',
      properties: {
        label: route.label || `Route ${index + 1}`,
        provider: route.provider || '',
        routeIndex: index,
      },
      geometry: route.route_geometry,
    }
  }

  return null
}

function getAlternativeRouteCollection() {
  return {
    type: 'FeatureCollection',
    features: props.routeOptions
      .map(routeOptionToFeature)
      .filter((feature) => feature && feature.properties.routeIndex !== props.activeRouteIndex),
  }
}

function getGapPointCollection() {
  return {
    type: 'FeatureCollection',
    features: props.gapPoints
      .filter((gap) => Array.isArray(gap?.location))
      .map((gap) =>
        pointToFeature(gap.location, {
          gapType: gap.gap_type || '',
        }),
      ),
  }
}

function addGapMarkerImage() {
  return new Promise((resolve, reject) => {
    if (map.value.hasImage(GAP_MARKER_IMAGE_ID)) {
      resolve()
      return
    }

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
        <path d="M19 2 L36 19 L19 36 L2 19 Z" fill="#f59e0b"/>
        <path d="M19 2 L36 19 L19 36 L2 19 Z" fill="none" stroke="#ffffff" stroke-width="4"/>
        <rect x="17" y="10" width="4" height="13" rx="2" fill="#ffffff"/>
        <circle cx="19" cy="28" r="2.5" fill="#ffffff"/>
      </svg>
    `
    const image = new Image(38, 38)

    image.onload = () => {
      if (!map.value.hasImage(GAP_MARKER_IMAGE_ID)) {
        map.value.addImage(GAP_MARKER_IMAGE_ID, image)
      }
      resolve()
    }
    image.onerror = reject
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
  })
}

function getReportCollection() {
  return {
    type: 'FeatureCollection',
    features: props.reports.map(reportToFeature),
  }
}

function reportToFeature(report, index) {
  const latitude = Number(report.latitude)
  const longitude = Number(report.longitude)
  const location = Number.isFinite(latitude) && Number.isFinite(longitude)
    ? [latitude, longitude]
    : report.location || [-37.805 + index * 0.007, 144.955 + index * 0.009]
  const votes = Number(report.validation_count ?? report.votes ?? 1)

  return pointToFeature(location, {
    id: report.report_id || report.id,
    type: report.issue_type || report.type || 'gap',
    area: report.area || '',
    status: report.status || 'submitted',
    description: report.description || '',
    reportedAt: report.reported_at || '',
    votes,
    heatWeight: Math.max(0.25, Math.min(1, votes / 50)),
  })
}

function heatmapRegionToFeature(region) {
  return {
    type: 'Feature',
    properties: {
      sa2Code: region.sa2_code,
      suburbName: region.suburb_name,
      score: region.score,
      riskLevel: region.risk_level,
      intensity: region.intensity,
      shortCommutePct: region.short_commute_pct,
      zeroCarHouseholdPct: region.zero_car_household_pct,
      workingPopulationRatio: region.working_population_ratio,
    },
    geometry: region.geometry,
  }
}

function extendGeometryBounds(bounds, coordinates) {
  if (!Array.isArray(coordinates)) {
    return bounds
  }

  if (typeof coordinates[0] === 'number' && typeof coordinates[1] === 'number') {
    return {
      west: Math.min(bounds.west, coordinates[0]),
      south: Math.min(bounds.south, coordinates[1]),
      east: Math.max(bounds.east, coordinates[0]),
      north: Math.max(bounds.north, coordinates[1]),
    }
  }

  return coordinates.reduce(extendGeometryBounds, bounds)
}

function getRegionBounds(region) {
  if (!region) {
    return null
  }

  const cachedBounds = heatmapRegionBounds.get(region)

  if (cachedBounds) {
    return cachedBounds
  }

  const bounds = extendGeometryBounds(
    { west: Infinity, south: Infinity, east: -Infinity, north: -Infinity },
    region.geometry?.coordinates,
  )

  if (!Number.isFinite(bounds.west)) {
    return null
  }

  heatmapRegionBounds.set(region, bounds)
  return bounds
}

function getPaddedMapBounds() {
  const bounds = map.value?.getBounds()

  if (!bounds) {
    return null
  }

  const lngPadding = Math.max(0.01, (bounds.getEast() - bounds.getWest()) * 0.45)
  const latPadding = Math.max(0.01, (bounds.getNorth() - bounds.getSouth()) * 0.45)

  return {
    west: bounds.getWest() - lngPadding,
    south: bounds.getSouth() - latPadding,
    east: bounds.getEast() + lngPadding,
    north: bounds.getNorth() + latPadding,
  }
}

function boundsIntersect(a, b) {
  return a.west <= b.east && a.east >= b.west && a.south <= b.north && a.north >= b.south
}

function pointInBounds(feature, bounds) {
  const coordinates = feature.geometry?.coordinates

  return Array.isArray(coordinates) &&
    coordinates[0] >= bounds.west &&
    coordinates[0] <= bounds.east &&
    coordinates[1] >= bounds.south &&
    coordinates[1] <= bounds.north
}

function getSa2HeatmapCollection() {
  const visibleBounds = getPaddedMapBounds()

  return {
    type: 'FeatureCollection',
    features: props.heatmapRegions
      .filter((region) => region.geometry)
      .filter((region) => {
        const regionBounds = getRegionBounds(region)

        return !visibleBounds || (regionBounds && boundsIntersect(regionBounds, visibleBounds))
      })
      .map(heatmapRegionToFeature),
  }
}

function getVisibleReportCollection() {
  const visibleBounds = getPaddedMapBounds()

  return {
    type: 'FeatureCollection',
    features: props.reports
      .map(reportToFeature)
      .filter((feature) => !visibleBounds || pointInBounds(feature, visibleBounds)),
  }
}

function setSourceData(id, data) {
  const source = map.value?.getSource(id)

  if (source) {
    source.setData(data)
  }
}

function setLayerVisibility(id, visible) {
  if (map.value?.getLayer(id)) {
    map.value.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none')
  }
}

function updateRouteData() {
  if (!mapReady.value) {
    return
  }

  setSourceData('route-alternatives', getAlternativeRouteCollection())
  setSourceData('route-main', getMainRouteCollection())
  setSourceData('route-gaps', getGapPointCollection())
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function updateMarkers() {
  if (!mapReady.value) {
    return
  }

  const features = [pointToFeature(props.startPoint, { label: 'Start', kind: 'start' })]

  if (props.endPoint) {
    features.push(pointToFeature(props.endPoint, { label: 'End', kind: 'end' }))
  }

  setSourceData('route-points', {
    type: 'FeatureCollection',
    features,
  })
}

function updateHeatmapData() {
  if (!mapReady.value) {
    return
  }

  if (props.mode !== 'heatmap') {
    setSourceData('sa2-heatmap-regions', emptyCollection())
    setSourceData('community-reports', getVisibleReportCollection())
    return
  }

  setSourceData('sa2-heatmap-regions', getSa2HeatmapCollection())
  setSourceData('community-reports', getVisibleReportCollection())
}

function updateAlertData() {
  if (!mapReady.value) {
    return
  }

}

function collectRouteLngLatCoordinates() {
  if (props.routeOptions.length > 1) {
    return props.routeOptions
      .flatMap((route, index) => routeOptionToFeature(route, index)?.geometry?.coordinates || [])
      .filter((coordinate) => Array.isArray(coordinate) && coordinate.length >= 2)
  }

  if (props.routeGeometry?.type === 'LineString' && Array.isArray(props.routeGeometry.coordinates)) {
    return props.routeGeometry.coordinates.filter((coordinate) => Array.isArray(coordinate) && coordinate.length >= 2)
  }

  return props.gapPoints
    .map((gap) => toMapboxLngLat(gap.location))
    .filter((coordinate) => coordinate && coordinate.length >= 2)
}

function fitToRoute() {
  if (!mapReady.value || props.mode !== 'route') {
    return
  }

  const coordinates = collectRouteLngLatCoordinates()

  if (!coordinates.length) {
    return
  }

  const bounds = coordinates.reduce(
    (routeBounds, coordinate) => routeBounds.extend(coordinate),
    new mapboxgl.LngLatBounds(coordinates[0], coordinates[0]),
  )

  map.value.fitBounds(bounds, {
    padding: {
      top: 96,
      bottom: 96,
      left: 460,
      right: 96,
    },
    maxZoom: 15,
    essential: true,
    duration: 1200,
  })
}

function updateLayerVisibility() {
  if (!mapReady.value) {
    return
  }

  const isHeatmap = props.mode === 'heatmap'
  const showReportMarkers = props.showReportMarkers

  setLayerVisibility('route-alternative-casing', !isHeatmap)
  setLayerVisibility('route-alternative-lines', !isHeatmap)
  setLayerVisibility('route-main-casing', !isHeatmap)
  setLayerVisibility('route-segment-lines', !isHeatmap)
  setLayerVisibility('route-gap-halo', !isHeatmap)
  setLayerVisibility('route-gap-points', !isHeatmap)
  setLayerVisibility('route-points', !isHeatmap)
  setLayerVisibility('route-end-marker', !isHeatmap)
  setLayerVisibility('route-end-core', !isHeatmap)
  setLayerVisibility('sa2-heatmap-fills', isHeatmap)
  setLayerVisibility('sa2-heatmap-lines', isHeatmap)
  setLayerVisibility('community-heatmap', isHeatmap)
  setLayerVisibility('community-report-halo', showReportMarkers)
  setLayerVisibility('community-circles', showReportMarkers)
  setLayerVisibility('community-report-icons', showReportMarkers)
}

function showReportPopup(event) {
  const feature = event.features?.[0]

  if (!feature) {
    return
  }

  const coordinates = feature.geometry.coordinates.slice()
  const properties = feature.properties || {}
  const description = properties.description || 'No description provided.'
  const reportedAt = properties.reportedAt
    ? new Date(properties.reportedAt).toLocaleString()
    : 'Time pending'
  const reportType = properties.type || 'gap'
  const status = properties.status || 'submitted'
  const statusKey = String(properties.status || 'submitted').toLowerCase()
  const statusClass = ['pending', 'validated', 'resolved', 'submitted'].includes(statusKey)
    ? statusKey
    : 'submitted'
  const point = map.value.project(coordinates)
  const reportId = properties.id
  const existingLikeSession = getReportLikeSession(reportId)
  const likeWindowEndsAt = existingLikeSession?.endsAt || null
  const remainingLikeWindow = likeWindowEndsAt ? Math.max(likeWindowEndsAt - Date.now(), 0) : null

  activeReportPopup.value = {
    coordinates,
    description,
    likeProgress:
      remainingLikeWindow === null ? 100 : (remainingLikeWindow / REPORT_LIKE_WINDOW_MS) * 100,
    likeWindowEndsAt,
    likeWindowStarted: Boolean(existingLikeSession),
    likes: getReportLikes(reportId),
    reportId,
    reportedAt,
    reportType,
    status,
    statusClass,
    x: point.x,
    y: point.y,
  }

  if (remainingLikeWindow > 0) {
    startReportLikeTimer()
  }

}

function updateActiveReportPopupPosition() {
  if (!map.value || !activeReportPopup.value) {
    return
  }

  const point = map.value.project(activeReportPopup.value.coordinates)
  activeReportPopup.value = {
    ...activeReportPopup.value,
    x: point.x,
    y: point.y,
  }
}

function startReportLikeTimer() {
  clearReportLikeTimer()

  reportLikeTimer = window.setInterval(() => {
    if (!activeReportPopup.value) {
      clearReportLikeTimer()
      return
    }

    const remaining = Math.max(activeReportPopup.value.likeWindowEndsAt - Date.now(), 0)
    activeReportPopup.value = {
      ...activeReportPopup.value,
      likeProgress: (remaining / REPORT_LIKE_WINDOW_MS) * 100,
    }

    if (remaining <= 0) {
      clearReportLikeTimer()
    }
  }, 50)
}

function likeActiveReport() {
  if (!activeReportPopup.value || activeReportPopup.value.likeProgress <= 0) {
    return
  }

  if (!activeReportPopup.value.likeWindowStarted) {
    const likeWindowEndsAt = Date.now() + REPORT_LIKE_WINDOW_MS
    saveReportLikeSession(activeReportPopup.value.reportId, {
      startedAt: Date.now(),
      endsAt: likeWindowEndsAt,
    })
    activeReportPopup.value = {
      ...activeReportPopup.value,
      likeWindowEndsAt,
      likeWindowStarted: true,
    }
    startReportLikeTimer()
  }

  const likes = incrementReportLikes(activeReportPopup.value.reportId)
  const burstId = `${activeReportPopup.value.reportId}-${Date.now()}-${Math.random()}`
  activeReportPopup.value = {
    ...activeReportPopup.value,
    likes,
  }
  reportLikeBursts.value = [...reportLikeBursts.value, burstId]

  window.setTimeout(() => {
    reportLikeBursts.value = reportLikeBursts.value.filter((id) => id !== burstId)
  }, 700)
}

function emitHeatmapRegionHover(feature) {
  const properties = feature?.properties || {}
  const scoreValue = Number(properties.score)
  const intensityValue = Number(properties.intensity)
  const shortCommuteValue = Number(properties.shortCommutePct)
  const zeroCarValue = Number(properties.zeroCarHouseholdPct)
  const workingPopulationValue = Number(properties.workingPopulationRatio)

  emit('heatmap-region-hover', {
    name: properties.suburbName || 'Selected region',
    riskLevel: properties.riskLevel || 'Unknown',
    score: Number.isFinite(scoreValue) ? Math.round(scoreValue) : null,
    intensity: Number.isFinite(intensityValue) ? Math.round(intensityValue) : null,
    shortCommutePct: Number.isFinite(shortCommuteValue) ? shortCommuteValue : null,
    zeroCarHouseholdPct: Number.isFinite(zeroCarValue) ? zeroCarValue : null,
    workingPopulationRatio: Number.isFinite(workingPopulationValue) ? workingPopulationValue : null,
  })
}

function updateLayers() {
  updateRouteData()
  updateHeatmapData()
  updateAlertData()
  updateMarkers()
  updateLayerVisibility()
}

function addMapSources() {
  map.value.addSource('route-main', {
    type: 'geojson',
    data: getMainRouteCollection(),
    tolerance: 0.8,
  })

  map.value.addSource('route-alternatives', {
    type: 'geojson',
    data: getAlternativeRouteCollection(),
    tolerance: 0.8,
  })

  map.value.addSource('route-gaps', {
    type: 'geojson',
    data: getGapPointCollection(),
    tolerance: 0.8,
  })

  map.value.addSource('route-points', {
    type: 'geojson',
    data: emptyCollection(),
  })

  map.value.addSource('sa2-heatmap-regions', {
    type: 'geojson',
    data: getSa2HeatmapCollection(),
    tolerance: 1.2,
  })

  map.value.addSource('community-reports', {
    type: 'geojson',
    data: getReportCollection(),
  })
}

function addMapLayers() {
  map.value.addLayer({
    id: 'route-alternative-casing',
    type: 'line',
    source: 'route-alternatives',
    paint: {
      'line-width': 8,
      'line-opacity': 0.72,
      'line-color': '#ffffff',
    },
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
  })

  map.value.addLayer({
    id: 'route-alternative-lines',
    type: 'line',
    source: 'route-alternatives',
    paint: {
      'line-width': 5.5,
      'line-opacity': 0.76,
      'line-color': '#6366f1',
    },
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
  })

  map.value.addLayer({
    id: 'route-alternative-hit',
    type: 'line',
    source: 'route-alternatives',
    paint: {
      'line-width': 24,
      'line-opacity': 0.01,
      'line-color': '#ffffff',
    },
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
  })

  map.value.addLayer({
    id: 'route-main-casing',
    type: 'line',
    source: 'route-main',
    paint: {
      'line-width': 11,
      'line-opacity': 0.82,
      'line-color': '#ffffff',
    },
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
  })

  map.value.addLayer({
    id: 'route-segment-lines',
    type: 'line',
    source: 'route-main',
    paint: {
      'line-width': 7.5,
      'line-opacity': 0.96,
      'line-color': '#00b894',
    },
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
  })

  map.value.addLayer({
    id: 'route-gap-halo',
    type: 'circle',
    source: 'route-gaps',
    paint: {
      'circle-radius': 18,
      'circle-color': '#f59e0b',
      'circle-opacity': 0,
    },
  })

  map.value.addLayer({
    id: 'route-gap-points',
    type: 'symbol',
    source: 'route-gaps',
    layout: {
      'icon-image': GAP_MARKER_IMAGE_ID,
      'icon-size': 1,
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
    },
    paint: {
      'icon-opacity': 1,
    },
  })

  map.value.addLayer({
    id: 'route-points',
    type: 'circle',
    source: 'route-points',
    filter: ['==', ['get', 'kind'], 'start'],
    paint: {
      'circle-radius': 10,
      'circle-color': '#ffffff',
      'circle-stroke-color': '#30413d',
      'circle-stroke-width': 2,
    },
  })

  map.value.addLayer({
    id: 'route-end-marker',
    type: 'circle',
    source: 'route-points',
    filter: ['==', ['get', 'kind'], 'end'],
    paint: {
      'circle-radius': 10,
      'circle-color': '#ffffff',
      'circle-stroke-color': '#30413d',
      'circle-stroke-width': 2,
    },
  })

  map.value.addLayer({
    id: 'route-end-core',
    type: 'circle',
    source: 'route-points',
    filter: ['==', ['get', 'kind'], 'end'],
    paint: {
      'circle-radius': 4,
      'circle-color': '#111827',
    },
  })

  map.value.addLayer({
    id: 'sa2-heatmap-fills',
    type: 'fill',
    source: 'sa2-heatmap-regions',
    paint: {
      'fill-color': [
        'match',
        ['get', 'riskLevel'],
        'Red',
        '#e85d5d',
        'Yellow',
        '#ffd166',
        'Green',
        '#12a594',
        '#12a594',
      ],
      'fill-opacity': [
        'interpolate',
        ['linear'],
        ['coalesce', ['get', 'intensity'], ['get', 'score'], 30],
        0,
        0.18,
        50,
        0.42,
        100,
        0.68,
      ],
    },
  })

  map.value.addLayer({
    id: 'sa2-heatmap-lines',
    type: 'line',
    source: 'sa2-heatmap-regions',
    paint: {
      'line-color': '#30413d',
      'line-opacity': 0.28,
      'line-width': 1,
    },
  })

  map.value.on('mousemove', 'sa2-heatmap-fills', (event) => {
    map.value.getCanvas().style.cursor = 'pointer'

    const feature = event.features?.[0]
    const regionCode = feature?.properties?.sa2Code || feature?.properties?.suburbName

    if (!feature || regionCode === lastHeatmapHoverCode) {
      return
    }

    lastHeatmapHoverCode = regionCode
    pendingHeatmapHoverFeature = feature

    if (!heatmapHoverFrame) {
      heatmapHoverFrame = window.requestAnimationFrame(() => {
        heatmapHoverFrame = null
        emitHeatmapRegionHover(pendingHeatmapHoverFeature)
        pendingHeatmapHoverFeature = null
      })
    }
  })

  map.value.on('mouseleave', 'sa2-heatmap-fills', () => {
    map.value.getCanvas().style.cursor = ''
    lastHeatmapHoverCode = null
    clearPendingHeatmapHover()
  })

  map.value.addLayer({
    id: 'community-heatmap',
    type: 'heatmap',
    source: 'community-reports',
    paint: {
      'heatmap-weight': ['get', 'heatWeight'],
      'heatmap-intensity': 1.1,
      'heatmap-radius': 38,
      'heatmap-opacity': 0.78,
      'heatmap-color': [
        'interpolate',
        ['linear'],
        ['heatmap-density'],
        0,
        'rgba(18, 165, 148, 0)',
        0.35,
        '#12a594',
        0.6,
        '#ffd166',
        0.9,
        '#e85d5d',
      ],
    },
  })

  map.value.addLayer({
    id: 'community-circles',
    type: 'circle',
    source: 'community-reports',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10,
        9,
        15,
        13,
      ],
      'circle-color': '#ef4444',
      'circle-opacity': 0.94,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 3,
      'circle-blur': 0,
    },
  })

  map.value.addLayer({
    id: 'community-report-halo',
    type: 'circle',
    source: 'community-reports',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10,
        17,
        15,
        24,
      ],
      'circle-color': '#ef4444',
      'circle-opacity': 0.22,
      'circle-stroke-color': '#ef4444',
      'circle-stroke-opacity': 0.36,
      'circle-stroke-width': 2,
    },
  }, 'community-circles')

  map.value.addLayer({
    id: 'community-report-icons',
    type: 'symbol',
    source: 'community-reports',
    layout: {
      'text-field': '!',
      'text-size': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10,
        14,
        15,
        18,
      ],
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-allow-overlap': true,
      'text-ignore-placement': true,
    },
    paint: {
      'text-color': '#ffffff',
      'text-halo-color': '#b91c1c',
      'text-halo-width': 0.5,
    },
  })

  map.value.on('click', 'community-report-icons', showReportPopup)
  map.value.on('click', 'community-circles', showReportPopup)
  map.value.on('click', 'route-alternative-hit', handleRouteOptionClick)

  map.value.on('mouseenter', 'route-alternative-hit', () => {
    map.value.getCanvas().style.cursor = 'pointer'
  })

  map.value.on('mouseleave', 'route-alternative-hit', () => {
    map.value.getCanvas().style.cursor = ''
  })

  map.value.on('mouseenter', 'community-report-icons', () => {
    map.value.getCanvas().style.cursor = 'pointer'
  })

  map.value.on('mouseleave', 'community-report-icons', () => {
    map.value.getCanvas().style.cursor = ''
  })

  map.value.on('mouseenter', 'community-circles', () => {
    map.value.getCanvas().style.cursor = 'pointer'
  })

  map.value.on('mouseleave', 'community-circles', () => {
    map.value.getCanvas().style.cursor = ''
  })
}

function addMapControls() {
  map.value.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), 'bottom-right')

  geolocate.value = new mapboxgl.GeolocateControl({
    fitBoundsOptions: {
      maxZoom: 15,
    },
    positionOptions: {
      enableHighAccuracy: true,
    },
    showAccuracyCircle: true,
    showUserHeading: true,
    trackUserLocation: false,
  })

  geolocate.value.on('geolocate', (event) => {
    emit('location-found', {
      lat: event.coords.latitude,
      lng: event.coords.longitude,
    })
  })

  map.value.addControl(geolocate.value, 'bottom-right')
}

onMounted(() => {
  if (!hasToken.value) {
    return
  }

  mapboxgl.accessToken = token

  map.value = new mapboxgl.Map({
    container: mapContainer.value,
    style: getBaseMapStyle(),
    projection: 'mercator',
    center: toMapboxLngLat(props.startPoint),
    zoom: 13,
    antialias: false,
    collectResourceTiming: false,
    crossSourceCollisions: false,
    dragRotate: false,
    fadeDuration: 0,
    performanceMetricsCollection: false,
    pitchWithRotate: false,
    refreshExpiredTiles: false,
    renderWorldCopies: false,
    respectPrefersReducedMotion: true,
    touchPitch: false,
    maxBounds: MELBOURNE_BOUNDS,
    minZoom: 9,
    maxZoom: 18,
  })

  addMapControls()

  map.value.on('load', async () => {
    addMapSources()
    await addGapMarkerImage()
    addMapLayers()
    mapReady.value = true
    updateLayers()

    if (props.autoGeolocate) {
      setTimeout(() => {
        geolocate.value?.trigger()
      }, 300)
    }
  })

  map.value.on('contextmenu', (event) => {
    event.preventDefault()
    showReportMenuFromMapEvent(event)
  })

  map.value.on('touchstart', (event) => {
    clearLongPressTimer()
    longPressPoint = event.point
    longPressTimer = window.setTimeout(() => {
      showReportMenuFromMapEvent(event)
      map.value?.getCanvas().blur()
      longPressTimer = null
    }, 650)
  })

  map.value.on('touchmove', (event) => {
    if (!longPressPoint) {
      return
    }

    const movedX = Math.abs(event.point.x - longPressPoint.x)
    const movedY = Math.abs(event.point.y - longPressPoint.y)

    if (movedX > 8 || movedY > 8) {
      clearLongPressTimer()
    }
  })

  map.value.on('touchend', clearLongPressTimer)
  map.value.on('touchcancel', clearLongPressTimer)

  map.value.on('movestart', () => {
    setMapMovingClass(true)
  })

  map.value.on('move', updateActiveReportPopupPosition)

  map.value.on('moveend', () => {
    setMapMovingClass(false)

    if (props.mode === 'heatmap') {
      updateHeatmapData()
    }
  })

  map.value.on('dragstart', () => {
    clearLongPressTimer()
    reportMenu.value = null
    setMapMovingClass(true)
  })

  map.value.on('dragend', () => {
    setMapMovingClass(false)
  })

  map.value.on('click', () => {
    reportMenu.value = null
    activeReportPopup.value = null
    clearReportLikeTimer()
  })
})

onBeforeUnmount(() => {
  clearLongPressTimer()
  clearPendingHeatmapHover()
  clearReportLikeTimer()
  setMapMovingClass(false)
  map.value?.remove()
  map.value = null
})

watch(
  () => props.mode,
  () => {
    updateLayerVisibility()
    updateHeatmapData()
  },
)

watch(
  () => props.routeSegments,
  () => {
    updateRouteData()
    fitToRoute()
  },
  { deep: true },
)

watch(
  () => props.routeGeometry,
  () => {
    updateRouteData()
    fitToRoute()
  },
  { deep: true },
)

watch(
  () => props.routeOptions,
  () => {
    updateRouteData()
    fitToRoute()
  },
  { deep: true },
)

watch(
  () => props.activeRouteIndex,
  updateRouteData,
)

watch(
  () => props.gapPoints,
  () => {
    updateRouteData()
    fitToRoute()
  },
  { deep: true },
)

watch(
  () => props.heatmapRegions,
  updateHeatmapData,
  { deep: true },
)

watch(
  () => props.reports,
  updateHeatmapData,
  { deep: true },
)

watch(
  () => props.showReportMarkers,
  updateLayerVisibility,
)

watch(
  () => props.alerts,
  updateAlertData,
  { deep: true },
)

watch(
  () => [props.startPoint, props.endPoint],
  updateMarkers,
  { deep: true },
)
</script>

<template>
  <section class="mapbox-shell">
    <div v-if="hasToken" ref="mapContainer" class="mapbox-container"></div>

    <div
      v-if="reportMenu"
      class="map-report-menu"
      :style="{ left: `${reportMenu.x}px`, top: `${reportMenu.y}px` }"
    >
      <button
        type="button"
        @click.stop="
          emit('report-location', { latitude: reportMenu.lat, longitude: reportMenu.lng });
          reportMenu = null
        "
      >
        Report gap here
      </button>
    </div>

    <div
      v-if="activeReportPopup"
      class="community-report-overlay"
      :style="{ left: `${activeReportPopup.x}px`, top: `${activeReportPopup.y}px` }"
      @mousedown.stop
      @mouseup.stop
      @click.stop
      @touchstart.stop
      @touchend.stop
    >
      <article class="report-popup-card">
        <header class="report-popup-header">
          <span class="report-popup-kicker">Community report</span>
          <span class="report-status-pill" :class="activeReportPopup.statusClass">
            {{ activeReportPopup.status }}
          </span>
          <button
            type="button"
            class="report-popup-close"
            aria-label="Close report"
            @mousedown.stop.prevent="activeReportPopup = null"
            @touchstart.stop.prevent="activeReportPopup = null"
            @click.stop.prevent="activeReportPopup = null"
          >
            ×
          </button>
        </header>
        <strong class="report-popup-title">{{ activeReportPopup.reportType }} report</strong>
        <p class="report-popup-description">{{ activeReportPopup.description }}</p>
        <footer class="report-popup-meta">
          <span>Reported</span>
          <time>{{ activeReportPopup.reportedAt }}</time>
        </footer>
        <div class="report-like-section">
          <div class="report-like-copy">
            <span>Support window</span>
            <strong>{{ activeReportPopup.likes }} like{{ activeReportPopup.likes === 1 ? '' : 's' }}</strong>
          </div>
          <div class="report-like-progress" aria-hidden="true">
            <span :style="{ width: `${activeReportPopup.likeProgress}%` }"></span>
          </div>
          <button
            type="button"
            class="report-like-button"
            :class="{ 'report-like-button-active': activeReportPopup.likeWindowStarted && activeReportPopup.likeProgress > 0 }"
            :disabled="activeReportPopup.likeProgress <= 0"
            @mousedown.stop.prevent="likeActiveReport"
            @touchstart.stop.prevent="likeActiveReport"
            @click.stop.prevent
          >
            <svg class="report-like-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M10.2 10.2V20H6.8A1.8 1.8 0 0 1 5 18.2v-6.1a1.8 1.8 0 0 1 1.8-1.9h3.4Zm1.7 9.8V10.1l2.3-5a1.8 1.8 0 0 1 3.4.9v3.1h2.5a2 2 0 0 1 1.9 2.5l-1.4 5.6a3.6 3.6 0 0 1-3.5 2.8h-5.2Z"
              />
            </svg>
            {{
              activeReportPopup.likeProgress <= 0
                ? 'Window closed'
                : activeReportPopup.likeWindowStarted
                  ? 'Like +1'
                  : 'Start liking'
            }}
          </button>
          <span
            v-for="burst in reportLikeBursts"
            :key="burst"
            class="report-like-burst"
            aria-hidden="true"
          >
            +1
          </span>
        </div>
      </article>
    </div>

    <div v-if="!hasToken" class="mapbox-token-empty panel">
      <span class="eyebrow">Mapbox token required</span>
      <h2>Set your Mapbox access token</h2>
      <p>Add <code>VITE_MAPBOX_ACCESS_TOKEN</code> to your local <code>.env</code> file.</p>
    </div>
  </section>
</template>
