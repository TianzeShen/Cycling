export function toMapboxLngLat(coordinate) {
  if (!Array.isArray(coordinate) || coordinate.length < 2) {
    return null
  }

  const [lat, lng] = coordinate
  return [lng, lat]
}

export function segmentToGeoJson(segment) {
  return {
    type: 'Feature',
    properties: {
      riskLevel: segment.risk_level || segment.riskLevel || 'Green',
      isGap: Boolean(segment.is_gap || segment.isGap),
    },
    geometry: {
      type: 'LineString',
      coordinates: (segment.coordinates || []).map(toMapboxLngLat).filter(Boolean),
    },
  }
}

export function pointToFeature(coordinate, properties = {}) {
  const lngLat = toMapboxLngLat(coordinate)

  return {
    type: 'Feature',
    properties,
    geometry: {
      type: 'Point',
      coordinates: lngLat || [144.9631, -37.8136],
    },
  }
}
