# RideSmart Web

Vue 3 frontend scaffold for the RideSmart cycling decision-support web app.

## Tech Stack

- Vue 3
- Vite
- Vue Router

## Setup

```bash
npm install
npm run dev
```

Create a local `.env` file when the backend is available:

```bash
VITE_API_BASE_URL=https://ridesmart-71t5.onrender.com
VITE_MAPBOX_ACCESS_TOKEN=pk.your_mapbox_public_token
VITE_MAPBOX_STYLE=mapbox://styles/mapbox/streets-v12
```

## Current Screens

- Map workspace with route evaluation, recommendations, alerts, and heatmap mode
- Smart issue reporting
- User profile and contribution badges

## Backend Contract

The API client is prepared for:

- `POST /api/feasibility/evaluate`
- `POST /api/routing/recommend`

Map coordinates from the backend should be kept as WGS84 latitude/longitude pairs.
The Mapbox component converts them to longitude/latitude before rendering.
Address suggestions use the Mapbox Geocoding API through the same public Mapbox token.
