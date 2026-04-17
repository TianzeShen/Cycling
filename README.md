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
VITE_API_BASE_URL=http://localhost:8000
```

## Current Screens

- Journey feasibility assessment
- Risk-aware route options
- Smart issue reporting
- Community issue validation
- User profile and contribution badges

## Backend Contract

The API client is prepared for:

- `POST /api/feasibility/evaluate`
- `POST /api/routing/recommend`
