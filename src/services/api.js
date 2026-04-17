const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const defaultCoordinates = {
  start_lat: -37.8136,
  start_lng: 144.9631,
  end_lat: -37.82,
  end_lng: 144.97,
}

async function postJson(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  return response.json()
}

export async function evaluateFeasibility(payload = defaultCoordinates) {
  return postJson('/api/feasibility/evaluate', payload)
}

export async function recommendRoute(payload = defaultCoordinates) {
  return postJson('/api/routing/recommend', payload)
}

export { defaultCoordinates }
