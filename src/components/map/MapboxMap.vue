<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { pointToFeature, segmentToGeoJson, toMapboxLngLat } from '../../utils/mapCoordinates'

const props = defineProps({
  mode: {
    type: String,
    default: 'route',
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
  autoGeolocate: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['location-found'])

const mapContainer = ref(null)
const map = ref(null)
const mapReady = ref(false)
const geolocate = ref(null)
const token = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN
const mapStyle = import.meta.env.VITE_MAPBOX_STYLE || 'mapbox://styles/mapbox/streets-v12'

const hasToken = computed(() => Boolean(token) && token.startsWith('pk.'))

function emptyCollection() {
  return {
    type: 'FeatureCollection',
    features: [],
  }
}

function getRouteCollection() {
  return {
    type: 'FeatureCollection',
    features: props.routeSegments.map(segmentToGeoJson),
  }
}

function getReportCollection() {
  return {
    type: 'FeatureCollection',
    features: props.reports.map((report, index) =>
      pointToFeature(
        report.location || [-37.805 + index * 0.007, 144.955 + index * 0.009],
        {
          id: report.id,
          type: report.type,
          area: report.area,
          status: report.status,
          votes: report.votes,
          heatWeight: Math.max(0.25, Math.min(1, report.votes / 50)),
        },
      ),
    ),
  }
}

function getSa2HeatmapCollection() {
  return {
    type: 'FeatureCollection',
    features: props.heatmapRegions
      .filter((region) => region.geometry)
      .map((region) => ({
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
      })),
  }
}

function getAlertCollection() {
  return {
    type: 'FeatureCollection',
    features: props.alerts.map((alert, index) =>
      pointToFeature(alert.location || [-37.815 + index * 0.004, 144.965 + index * 0.003], {
        title: alert.title || alert.message,
        detail: Array.isArray(alert.location) ? alert.location.join(', ') : alert.location || '',
      }),
    ),
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

function updateMarkers() {
  const features = [pointToFeature(props.startPoint, { label: 'Start', kind: 'start' })]

  if (props.endPoint) {
    features.push(pointToFeature(props.endPoint, { label: 'End', kind: 'end' }))
  }

  setSourceData('route-points', {
    type: 'FeatureCollection',
    features,
  })
}

function updateLayers() {
  if (!mapReady.value) {
    return
  }

  const isHeatmap = props.mode === 'heatmap'

  setSourceData('route-segments', getRouteCollection())
  setSourceData('sa2-heatmap-regions', getSa2HeatmapCollection())
  setSourceData('community-reports', getReportCollection())
  setSourceData('route-alerts', getAlertCollection())
  updateMarkers()

  setLayerVisibility('route-segment-lines', !isHeatmap)
  setLayerVisibility('route-points', !isHeatmap)
  setLayerVisibility('route-alerts', !isHeatmap)
  setLayerVisibility('sa2-heatmap-fills', isHeatmap)
  setLayerVisibility('sa2-heatmap-lines', isHeatmap)
  setLayerVisibility('community-heatmap', isHeatmap)
  setLayerVisibility('community-circles', isHeatmap)
}

function addMapSources() {
  map.value.addSource('route-segments', {
    type: 'geojson',
    data: getRouteCollection(),
  })

  map.value.addSource('route-points', {
    type: 'geojson',
    data: emptyCollection(),
  })

  map.value.addSource('sa2-heatmap-regions', {
    type: 'geojson',
    data: getSa2HeatmapCollection(),
  })

  map.value.addSource('route-alerts', {
    type: 'geojson',
    data: getAlertCollection(),
  })

  map.value.addSource('community-reports', {
    type: 'geojson',
    data: getReportCollection(),
  })
}

function addMapLayers() {
  map.value.addLayer({
    id: 'route-segment-lines',
    type: 'line',
    source: 'route-segments',
    paint: {
      'line-width': 7,
      'line-opacity': 0.92,
      'line-color': [
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
    },
  })

  map.value.addLayer({
    id: 'route-points',
    type: 'circle',
    source: 'route-points',
    paint: {
      'circle-radius': 8,
      'circle-color': ['match', ['get', 'kind'], 'start', '#12a594', 'end', '#e85d5d', '#30413d'],
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 3,
    },
  })

  map.value.addLayer({
    id: 'route-alerts',
    type: 'symbol',
    source: 'route-alerts',
    layout: {
      'text-field': '!',
      'text-size': 16,
      'text-allow-overlap': true,
    },
    paint: {
      'text-color': '#ffffff',
      'text-halo-color': '#e85d5d',
      'text-halo-width': 10,
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
      'circle-radius': 7,
      'circle-color': '#e85d5d',
      'circle-opacity': 0.8,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 2,
    },
  })
}

function addMapControls() {
  map.value.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), 'top-right')

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

  map.value.addControl(geolocate.value, 'top-right')
}

onMounted(() => {
  if (!hasToken.value) {
    return
  }

  mapboxgl.accessToken = token

  map.value = new mapboxgl.Map({
    container: mapContainer.value,
    style: mapStyle,
    center: toMapboxLngLat(props.startPoint),
    zoom: 13,
    antialias: false,
    dragRotate: false,
    fadeDuration: 0,
    pitchWithRotate: false,
    renderWorldCopies: false,
    touchPitch: false,
  })

  addMapControls()

  map.value.on('load', () => {
    addMapSources()
    addMapLayers()
    mapReady.value = true
    updateLayers()

    if (props.autoGeolocate) {
      setTimeout(() => {
        geolocate.value?.trigger()
      }, 300)
    }
  })
})

onBeforeUnmount(() => {
  map.value?.remove()
  map.value = null
})

watch(
  () => [
    props.mode,
    props.routeSegments,
    props.heatmapRegions,
    props.alerts,
    props.startPoint,
    props.endPoint,
    props.reports,
  ],
  updateLayers,
  { deep: true },
)

watch(
  () => props.startPoint,
  () => {
    updateMarkers()
  },
  { deep: true },
)
</script>

<template>
  <section class="mapbox-shell">
    <div v-if="hasToken" ref="mapContainer" class="mapbox-container"></div>

    <div v-else class="mapbox-token-empty panel">
      <span class="eyebrow">Mapbox token required</span>
      <h2>Set your Mapbox access token</h2>
      <p>Add <code>VITE_MAPBOX_ACCESS_TOKEN</code> to your local <code>.env</code> file.</p>
    </div>
  </section>
</template>
