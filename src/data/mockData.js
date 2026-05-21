export const feasibilityResult = {
  score: 85,
  is_supported_area: true,
  warning_message: null,
  explanations: [
    { factor: 'High lane continuity through the central segment', impact: 'High' },
    { factor: 'Low traffic exposure near the destination', impact: 'Medium' },
    { factor: 'Short travel distance supports a practical trip', impact: 'High' },
  ],
}

export const routeOptions = [
  {
    id: 'safe',
    name: 'Safest',
    time: '21 min',
    distance: '4.8 km',
    risk: 18,
    tone: 'green',
    summary: 'Keeps you on connected bike lanes for most of the trip.',
  },
  {
    id: 'balanced',
    name: 'Balanced',
    time: '17 min',
    distance: '4.4 km',
    risk: 31,
    tone: 'yellow',
    summary: 'Saves time while avoiding the most exposed road segments.',
  },
  {
    id: 'fast',
    name: 'Fastest',
    time: '14 min',
    distance: '4.1 km',
    risk: 56,
    tone: 'red',
    summary: 'Includes a short disconnected lane and heavier traffic exposure.',
  },
]

export const alerts = [
  { title: 'Disconnected lane', location: 'Swanston Street', distance: '200 m' },
  { title: 'High traffic exposure', location: 'Flinders Street crossing', distance: '650 m' },
]

export const communityReports = [
  { id: 1, type: 'Lane gap', area: 'Carlton', status: 'Validated', votes: 42 },
  { id: 2, type: 'Unsafe merge', area: 'Docklands', status: 'Pending', votes: 15 },
  { id: 3, type: 'Blocked bike lane', area: 'Southbank', status: 'Validated', votes: 31 },
]

export const badges = [
  { name: 'First Report', detail: 'Submitted your first cycling issue' },
  { name: 'Local Guide', detail: 'Reached 100 safety points' },
  { name: 'Safety Builder', detail: 'Helped improve high-impact routes' },
]
