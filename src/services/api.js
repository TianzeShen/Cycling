const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://ridesmart-71t5.onrender.com'
const MAPBOX_ACCESS_TOKEN = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN
const RIDESMART_USER_ID_KEY = 'ridesmart_user_id'
const RIDESMART_USERNAME_KEY = 'ridesmart_username'
const RIDESMART_IS_REGISTERED_KEY = 'ridesmart_is_registered'
const RIDESMART_AUTH_UPDATED_EVENT = 'ridesmart-auth-updated'
const RIDESMART_REPORT_LIKES_KEY = 'ridesmart_report_likes'
const RIDESMART_REPORT_LIKE_SESSIONS_KEY = 'ridesmart_report_like_sessions'

const defaultCoordinates = {
  start_lat: -37.8136,
  start_lng: 144.9631,
  end_lat: -37.911,
  end_lng: 145.134,
}

const SEARCHBOX_TYPES = 'poi,address,street,place,locality,neighborhood'
const GEOCODING_TYPES = 'poi,address,place,locality,neighborhood'
const FOCUSED_SEARCHBOX_TYPES = 'poi,address,place,locality,neighborhood'

function normaliseSearchText(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function levenshteinDistance(source, target) {
  if (!source.length) {
    return target.length
  }

  if (!target.length) {
    return source.length
  }

  const previousRow = Array.from({ length: target.length + 1 }, (_, index) => index)

  for (let row = 1; row <= source.length; row += 1) {
    let previousDiagonal = previousRow[0]
    previousRow[0] = row

    for (let column = 1; column <= target.length; column += 1) {
      const temp = previousRow[column]
      const substitutionCost = source[row - 1] === target[column - 1] ? 0 : 1

      previousRow[column] = Math.min(
        previousRow[column] + 1,
        previousRow[column - 1] + 1,
        previousDiagonal + substitutionCost,
      )

      previousDiagonal = temp
    }
  }

  return previousRow[target.length]
}

function scoreSuggestionMatch(query, suggestion) {
  const normalisedQuery = normaliseSearchText(query)
  const labelText = normaliseSearchText(suggestion.label)
  const addressText = normaliseSearchText(suggestion.address)
  const combinedText = [labelText, addressText].filter(Boolean).join(' ')

  if (!normalisedQuery || !combinedText) {
    return 0
  }

  let score = 0

  if (labelText === normalisedQuery) {
    score += 160
  } else if (combinedText === normalisedQuery) {
    score += 140
  }

  if (labelText.startsWith(normalisedQuery)) {
    score += 120
  }

  if (combinedText.startsWith(normalisedQuery)) {
    score += 95
  }

  if (labelText.includes(normalisedQuery)) {
    score += 80
  }

  if (combinedText.includes(normalisedQuery)) {
    score += 60
  }

  const queryTokens = normalisedQuery.split(' ').filter(Boolean)
  const labelTokens = labelText.split(' ').filter(Boolean)
  const combinedTokens = combinedText.split(' ').filter(Boolean)
  const queryLength = normalisedQuery.length
  const labelLength = labelText.length
  const combinedLength = combinedText.length

  const exactTokenMatches = queryTokens.filter((token, index) => labelTokens[index] === token).length
  score += exactTokenMatches * 35

  const sequentialPrefixMatches = queryTokens.reduce((count, token, index) => {
    const labelToken = labelTokens[index] || ''
    return token && labelToken.startsWith(token) ? count + 1 : count
  }, 0)
  score += sequentialPrefixMatches * 40

  const sharedPrefixLength = (() => {
    const limit = Math.min(queryLength, labelLength)
    let index = 0

    while (index < limit && normalisedQuery[index] === labelText[index]) {
      index += 1
    }

    return index
  })()

  score += sharedPrefixLength * 8

  const missingLabelTokens = Math.max(queryTokens.length - sequentialPrefixMatches, 0)
  score -= missingLabelTokens * 45

  if (queryLength > labelLength && sequentialPrefixMatches < queryTokens.length) {
    score -= (queryLength - labelLength) * 10
  }

  if (queryLength > combinedLength) {
    score -= (queryLength - combinedLength) * 4
  }

  queryTokens.forEach((token, index) => {
    const labelToken = labelTokens[index] || ''
    const combinedToken = combinedTokens[index] || ''

    if (labelToken === token) {
      score += 28
      return
    }

    if (labelToken.startsWith(token) || token.startsWith(labelToken)) {
      score += 22
      return
    }

    if (combinedToken === token) {
      score += 18
      return
    }

    if (combinedToken.startsWith(token) || token.startsWith(combinedToken)) {
      score += 12
    }
  })

  const queryTail = queryTokens[queryTokens.length - 1] || ''
  const labelTail = labelTokens[queryTokens.length - 1] || labelTokens[labelTokens.length - 1] || ''

  if (queryTail && labelTail) {
    const tailDistance = levenshteinDistance(queryTail, labelTail)

    if (tailDistance === 1) {
      score += 36
    } else if (tailDistance === 2) {
      score += 18
    }
  }

  const labelDistance = levenshteinDistance(normalisedQuery, labelText)
  const combinedDistance = levenshteinDistance(normalisedQuery, combinedText)
  const bestDistance = Math.min(labelDistance, combinedDistance)
  const normalisedDistance = queryLength ? bestDistance / queryLength : bestDistance

  if (normalisedDistance <= 0.15) {
    score += 90
  } else if (normalisedDistance <= 0.3) {
    score += 40
  }

  if (bestDistance <= 2) {
    score += 42 - bestDistance * 10
  } else if (bestDistance <= 4) {
    score += 12 - (bestDistance - 3) * 4
  } else {
    score -= bestDistance * 3
  }

  if (suggestion.type === 'poi') {
    score += 20
  }

  if (queryTokens.length > 1 && labelTokens.length === 1 && labelTokens[0] === queryTokens[0]) {
    score -= 120
  }

  return score
}

async function postJson(path, body) {
  return sendJson('POST', path, body)
}

async function patchJson(path, body) {
  return sendJson('PATCH', path, body)
}

async function sendJson(method, path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let errorDetail = ''

    try {
      const contentType = response.headers.get('content-type') || ''

      if (contentType.includes('application/json')) {
        const data = await response.json()
        errorDetail =
          data.detail ||
          data.message ||
          data.error ||
          (Array.isArray(data.errors) ? data.errors.join(', ') : '')
      } else {
        errorDetail = (await response.text()).trim()
      }
    } catch {
      errorDetail = ''
    }

    const error = new Error(errorDetail || `Request failed with status ${response.status}`)
    error.status = response.status
    error.detail = errorDetail
    throw error
  }

  return response.json()
}

async function getJson(path, params = null) {
  const query = params ? `?${params.toString()}` : ''
  const response = await fetch(`${API_BASE_URL}${path}${query}`, {
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  return response.json()
}

function createFallbackUuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16)
    const value = character === 'x' ? random : (random & 0x3) | 0x8

    return value.toString(16)
  })
}

export function getRideSmartUserId() {
  if (typeof window === 'undefined') {
    return ''
  }

  const existingUserId = window.localStorage.getItem(RIDESMART_USER_ID_KEY)

  if (existingUserId) {
    return existingUserId
  }

  const userId = window.crypto?.randomUUID ? window.crypto.randomUUID() : createFallbackUuid()
  window.localStorage.setItem(RIDESMART_USER_ID_KEY, userId)

  return userId
}

export function setRideSmartUserId(userId) {
  if (typeof window === 'undefined' || !userId) {
    return ''
  }

  window.localStorage.setItem(RIDESMART_USER_ID_KEY, userId)

  return userId
}

export function getStoredUsername() {
  if (typeof window === 'undefined') {
    return ''
  }

  return window.localStorage.getItem(RIDESMART_USERNAME_KEY) || ''
}

function saveAuthIdentity(identity) {
  if (typeof window === 'undefined' || !identity) {
    return identity
  }

  if (identity.user_id) {
    setRideSmartUserId(identity.user_id)
  }

  if (identity.username) {
    window.localStorage.setItem(RIDESMART_USERNAME_KEY, identity.username)
  } else {
    window.localStorage.removeItem(RIDESMART_USERNAME_KEY)
  }

  window.localStorage.setItem(RIDESMART_IS_REGISTERED_KEY, identity.is_registered ? 'true' : 'false')
  window.dispatchEvent(new CustomEvent(RIDESMART_AUTH_UPDATED_EVENT, { detail: identity }))

  return identity
}

export function getStoredAuthIdentity() {
  const userId = getRideSmartUserId()

  if (typeof window === 'undefined') {
    return {
      user_id: userId,
      username: null,
      is_registered: false,
      reward_points: 0,
      likes_received_total: 0,
    }
  }

  const username = getStoredUsername()

  return {
    user_id: userId,
    username: username || null,
    is_registered: window.localStorage.getItem(RIDESMART_IS_REGISTERED_KEY) === 'true',
    reward_points: 0,
    likes_received_total: 0,
  }
}

export async function getCurrentAuthIdentity(userId = getRideSmartUserId()) {
  const params = new URLSearchParams({
    user_id: userId,
  })
  const identity = await getJson('/api/auth/me', params)

  return saveAuthIdentity(identity)
}

export async function registerUsername(username) {
  const identity = await postJson('/api/auth/register', {
    user_id: getRideSmartUserId(),
    username,
  })

  return saveAuthIdentity(identity)
}

export async function loginWithUsername(username) {
  const identity = await postJson('/api/auth/login', {
    username,
  })

  return saveAuthIdentity(identity)
}

export function createReport({ latitude, longitude, issueType = 'gap', description = '' }) {
  return postJson('/api/reports', {
    user_id: getRideSmartUserId(),
    latitude,
    longitude,
    issue_type: issueType,
    description,
  })
}

function getStoredReportLikes() {
  if (typeof window === 'undefined') {
    return {}
  }

  try {
    return JSON.parse(window.localStorage.getItem(RIDESMART_REPORT_LIKES_KEY) || '{}')
  } catch {
    return {}
  }
}

function getStoredReportLikeSessions() {
  if (typeof window === 'undefined') {
    return {}
  }

  try {
    return JSON.parse(window.localStorage.getItem(RIDESMART_REPORT_LIKE_SESSIONS_KEY) || '{}')
  } catch {
    return {}
  }
}

export function getReportLikes(reportId) {
  if (!reportId) {
    return null
  }

  const storedLikes = getStoredReportLikes()

  if (!Object.prototype.hasOwnProperty.call(storedLikes, reportId)) {
    return null
  }

  return Number(storedLikes[reportId] || 0)
}

export function setReportLikes(reportId, likesCount) {
  if (!reportId || typeof window === 'undefined') {
    return 0
  }

  const likes = getStoredReportLikes()
  likes[reportId] = Number(likesCount || 0)
  window.localStorage.setItem(RIDESMART_REPORT_LIKES_KEY, JSON.stringify(likes))

  return likes[reportId]
}

export function incrementReportLikes(reportId) {
  if (!reportId || typeof window === 'undefined') {
    return 0
  }

  const likes = getStoredReportLikes()
  const nextLikes = Number(likes[reportId] || 0) + 1
  likes[reportId] = nextLikes
  window.localStorage.setItem(RIDESMART_REPORT_LIKES_KEY, JSON.stringify(likes))

  return nextLikes
}

export function getReportLikeSession(reportId) {
  if (!reportId) {
    return null
  }

  return getStoredReportLikeSessions()[reportId] || null
}

export function saveReportLikeSession(reportId, session) {
  if (!reportId || typeof window === 'undefined') {
    return null
  }

  const sessions = getStoredReportLikeSessions()
  sessions[reportId] = session
  window.localStorage.setItem(RIDESMART_REPORT_LIKE_SESSIONS_KEY, JSON.stringify(sessions))

  return session
}

export function getMyReports() {
  const params = new URLSearchParams({
    user_id: getRideSmartUserId(),
  })

  return getJson('/api/reports', params)
}

export function getAllReports() {
  const params = new URLSearchParams({
    user_id: getRideSmartUserId(),
  })

  return getJson('/api/reports/all', params)
}

export function likeReport(reportId, likeCount = 1) {
  const safeLikeCount = Math.min(Math.max(Number(likeCount) || 1, 1), 100)

  return postJson(`/api/reports/${encodeURIComponent(reportId)}/like`, {
    user_id: getRideSmartUserId(),
    like_count: safeLikeCount,
  })
}

export function updateReport(reportId, { description = '' }) {
  return patchJson(`/api/reports/${encodeURIComponent(reportId)}`, {
    user_id: getRideSmartUserId(),
    issue_type: 'gap',
    description,
  })
}

export async function deleteReport(reportId) {
  const params = new URLSearchParams({
    user_id: getRideSmartUserId(),
  })
  const response = await fetch(`${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}?${params.toString()}`, {
    method: 'DELETE',
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  if (response.status === 204) {
    return null
  }

  const text = await response.text()

  return text ? JSON.parse(text) : null
}

async function fetchMapboxSearchbox(query, params) {
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

  return response.json()
}

async function fetchMapboxGeocoding(query, proximity, limit, types = GEOCODING_TYPES) {
  const params = new URLSearchParams({
    access_token: MAPBOX_ACCESS_TOKEN,
    autocomplete: 'true',
    bbox: '144.4,-38.3,145.6,-37.4',
    country: 'AU',
    fuzzyMatch: 'true',
    language: 'en',
    limit: String(limit),
    types,
  })

  if (proximity) {
    params.set('proximity', proximity)
  }

  const response = await fetch(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?${params.toString()}`,
    {
      headers: {
        Accept: 'application/json',
      },
    },
  )

  if (!response.ok) {
    throw new Error(`Mapbox geocoding failed with status ${response.status}`)
  }

  return response.json()
}

function mapSearchboxFeature(feature) {
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
}

function mapGeocodingFeature(feature) {
  const name = feature.text || feature.place_name || ''
  const address = feature.place_name || ''
  const coordinate = [feature.center[1], feature.center[0]]
  const dedupeKey = `${name}-${address}-${coordinate.join(',')}`

  return {
    id: feature.id || dedupeKey,
    label: name,
    address: address !== name ? address : '',
    type: feature.place_type?.[0] || '',
    coordinate,
    dedupeKey,
  }
}

function readFulfilledJson(result) {
  return result.status === 'fulfilled' ? result.value : { features: [] }
}

function buildSearchQueries(query) {
  const normalisedQuery = normaliseSearchText(query)

  if (!normalisedQuery) {
    return []
  }

  const queries = [normalisedQuery]
  const queryTokens = normalisedQuery.split(' ').filter(Boolean)

  if (queryTokens.length >= 2) {
    const withoutLastToken = queryTokens.slice(0, -1).join(' ')

    if (withoutLastToken.length >= 3 && !queries.includes(withoutLastToken)) {
      queries.push(withoutLastToken)
    }
  }

  return queries
}

function buildSearchStrategies(query, proximity) {
  const normalisedQuery = normaliseSearchText(query)
  const queryTokens = normalisedQuery.split(' ').filter(Boolean)
  const hasMultipleTokens = queryTokens.length >= 2

  return buildSearchQueries(query).flatMap((candidateQuery, index) => {
    const useFocusedSearch = hasMultipleTokens && index === 0
    const strategies = [
      {
        query: candidateQuery,
        source: 'searchbox',
        types: useFocusedSearch ? FOCUSED_SEARCHBOX_TYPES : SEARCHBOX_TYPES,
        proximity: useFocusedSearch ? null : proximity,
      },
      {
        query: candidateQuery,
        source: 'geocoding',
        types: GEOCODING_TYPES,
        proximity: useFocusedSearch ? null : proximity,
      },
    ]

    if (useFocusedSearch) {
      strategies.push({
        query: candidateQuery,
        source: 'searchbox',
        types: SEARCHBOX_TYPES,
        proximity,
      })
    }

    return strategies
  })
}

function candidateMatchesQueryTail(query, suggestion) {
  const queryTokens = normaliseSearchText(query).split(' ').filter(Boolean)

  if (queryTokens.length < 2) {
    return true
  }

  const tailToken = queryTokens[queryTokens.length - 1]
  const suggestionTokens = [
    ...normaliseSearchText(suggestion.label).split(' ').filter(Boolean),
    ...normaliseSearchText(suggestion.address).split(' ').filter(Boolean),
  ]

  return suggestionTokens.some((token) => {
    if (!token || !tailToken) {
      return false
    }

    if (token.startsWith(tailToken) || tailToken.startsWith(token)) {
      return true
    }

    return levenshteinDistance(token, tailToken) <= 2
  })
}

function candidateMatchesAllQueryTokens(query, suggestion) {
  const queryTokens = normaliseSearchText(query).split(' ').filter(Boolean)

  if (queryTokens.length < 2) {
    return true
  }

  const suggestionTokens = [
    ...normaliseSearchText(suggestion.label).split(' ').filter(Boolean),
    ...normaliseSearchText(suggestion.address).split(' ').filter(Boolean),
  ]

  return queryTokens.every((queryToken) =>
    suggestionTokens.some((suggestionToken) => {
      if (!queryToken || !suggestionToken) {
        return false
      }

      if (suggestionToken.startsWith(queryToken) || queryToken.startsWith(suggestionToken)) {
        return true
      }

      return queryToken.length >= 4 && levenshteinDistance(suggestionToken, queryToken) <= 2
    }),
  )
}

export async function searchMapboxPlaces(query, proximityCoordinate = null) {
  if (!MAPBOX_ACCESS_TOKEN || !MAPBOX_ACCESS_TOKEN.startsWith('pk.') || query.trim().length < 3) {
    return []
  }

  const proximity = Array.isArray(proximityCoordinate)
    ? `${proximityCoordinate[1]},${proximityCoordinate[0]}`
    : '144.9631,-37.8136'

  const searchStrategies = buildSearchStrategies(query, proximity)
  const searchTasks = searchStrategies.map((strategy) => {
    const params = new URLSearchParams({
      access_token: MAPBOX_ACCESS_TOKEN,
      bbox: '144.4,-38.3,145.6,-37.4',
      country: 'AU',
      language: 'en',
      limit: '10',
      types: strategy.types,
    })

    if (strategy.proximity) {
      params.set('proximity', strategy.proximity)
    }

    if (strategy.source === 'searchbox') {
      return fetchMapboxSearchbox(strategy.query, params).then((data) => ({
        query: strategy.query,
        source: 'searchbox',
        features: (data.features || []).map(mapSearchboxFeature),
      }))
    }

    return fetchMapboxGeocoding(strategy.query, strategy.proximity, 10, strategy.types).then((data) => ({
      query: strategy.query,
      source: 'geocoding',
      features: (data.features || []).map(mapGeocodingFeature),
    }))
  })
  const settledSearches = await Promise.allSettled(searchTasks)

  const seenResults = new Set()
  const mergedResults = settledSearches.flatMap((result) => {
    const data = readFulfilledJson(result)

    return (data.features || []).map((feature) => ({
      ...feature,
      matchedQuery: data.query || query,
      matchedSource: data.source || '',
    }))
  })

  const allTokenMatchedResults = mergedResults.filter((result) => candidateMatchesAllQueryTokens(query, result))
  const tailMatchedResults = mergedResults.filter((result) => candidateMatchesQueryTail(query, result))
  const rankedCandidates = allTokenMatchedResults.length
    ? allTokenMatchedResults
    : tailMatchedResults.length
    ? tailMatchedResults
    : mergedResults

  return rankedCandidates
    .filter((result) => {
      if (seenResults.has(result.dedupeKey)) {
        return false
      }

      seenResults.add(result.dedupeKey)
      return true
    })
    .map((result, index) => ({
      ...result,
      matchScore: scoreSuggestionMatch(query, result),
      originalIndex: index,
    }))
    .sort((left, right) => {
      if (right.matchScore !== left.matchScore) {
        return right.matchScore - left.matchScore
      }

      return left.originalIndex - right.originalIndex
    })
    .map(({ matchScore, originalIndex, matchedQuery, matchedSource, ...result }) => result)
    .slice(0, 8)
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
