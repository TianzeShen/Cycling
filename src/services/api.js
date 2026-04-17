const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://ridesmart-71t5.onrender.com'
const MAPBOX_ACCESS_TOKEN = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN

const defaultCoordinates = {
  start_lat: -37.8136,
  start_lng: 144.9631,
  end_lat: -37.911,
  end_lng: 145.134,
}

async function postJson(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  return response.json()
}

export async function searchMapboxPlaces(query, proximityCoordinate = null) {
  if (!MAPBOX_ACCESS_TOKEN || !MAPBOX_ACCESS_TOKEN.startsWith('pk.') || query.trim().length < 3) {
    return []
  }

  const proximity = Array.isArray(proximityCoordinate)
    ? `${proximityCoordinate[1]},${proximityCoordinate[0]}`
    : '144.9631,-37.8136'

  const params = new URLSearchParams({
    access_token: MAPBOX_ACCESS_TOKEN,
    bbox: '144.4,-38.3,145.6,-37.4',
    country: 'AU',
    language: 'en',
    limit: '8',
    proximity,
    types: 'poi,address,street,place,locality,neighborhood',
  })

  const response = await fetch(
    `https://api.mapbox.com/search/searchbox/v1/forward?q=${encodeURIComponent(query)}&${params.toString()}`,
    {
      headers: {
        Accept: 'application/json',
      },
    },
  )

  if (!response.ok) {
    throw new Error(`Mapbox search failed with status ${response.status}`)
  }

  const data = await response.json()

  const seenResults = new Set()

  return (data.features || [])
    .map((feature) => {
      const name = feature.properties?.name || feature.properties?.full_address || ''
      const address = feature.properties?.full_address || feature.properties?.place_formatted || ''
      const coordinate = [feature.geometry.coordinates[1], feature.geometry.coordinates[0]]
      const dedupeKey = `${name}-${address}-${coordinate.join(',')}`

      return {
        id: feature.properties?.mapbox_id || feature.id || dedupeKey,
        label: name,
        address: address !== name ? address : '',
        type: feature.properties?.feature_type,
        coordinate,
        dedupeKey,
      }
    })
    .filter((result) => {
      if (seenResults.has(result.dedupeKey)) {
        return false
      }

      seenResults.add(result.dedupeKey)
      return true
    })
}

export async function reverseMapboxPlace(coordinate) {
  if (!MAPBOX_ACCESS_TOKEN || !MAPBOX_ACCESS_TOKEN.startsWith('pk.') || !Array.isArray(coordinate)) {
    return null
  }

  const params = new URLSearchParams({
    access_token: MAPBOX_ACCESS_TOKEN,
    language: 'en',
    limit: '1',
    types: 'poi,address',
  })

  const [lat, lng] = coordinate
  const response = await fetch(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?${params.toString()}`,
    {
      headers: {
        Accept: 'application/json',
      },
    },
  )

  if (!response.ok) {
    throw new Error(`Mapbox reverse geocoding failed with status ${response.status}`)
  }

  const data = await response.json()
  const feature = data.features?.[0]

  if (!feature) {
    return null
  }

  return {
    label: feature.text || feature.place_name || 'Current location',
    address: feature.place_name || '',
  }
}

export async function evaluateFeasibility(payload = defaultCoordinates) {
  return postJson('/api/feasibility/evaluate', payload)
}

export async function recommendRoute(payload = defaultCoordinates) {
  return postJson('/api/routing/recommend', payload)
}

export async function getMelbourneSa2Heatmap() {
  const response = await fetch(`${API_BASE_URL}/api/heatmap/melbourne-sa2`, {
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Heatmap request failed with status ${response.status}`)
  }

  return response.json()
}

export { defaultCoordinates }
