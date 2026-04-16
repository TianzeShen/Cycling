package com.cycling.cyclewise.data.api

import com.cycling.cyclewise.data.mock.MockCyclingData
import com.cycling.cyclewise.data.model.FeasibilityExplanation
import com.cycling.cyclewise.data.model.FeasibilityRequest
import com.cycling.cyclewise.data.model.FeasibilityResponse
import com.cycling.cyclewise.data.model.HeatmapRegion
import com.cycling.cyclewise.data.model.MelbourneSa2HeatmapResponse
import com.cycling.cyclewise.data.model.RouteAlert
import com.cycling.cyclewise.data.model.RouteCoordinate
import com.cycling.cyclewise.data.model.RouteSegment
import com.cycling.cyclewise.data.model.RoutingResponse
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URI
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

object CyclingApiClient {
    private const val BASE_URL = "https://ridesmart-71t5.onrender.com"
    private const val USE_MOCK_API = false

    suspend fun evaluateFeasibility(request: FeasibilityRequest): FeasibilityResponse =
        withContext(Dispatchers.IO) {
            if (USE_MOCK_API) return@withContext MockCyclingData.feasibilityResponse(request)
            val response = postJson("/api/feasibility/evaluate", request.toJson())
            parseFeasibility(response)
        }

    suspend fun recommendRoute(request: FeasibilityRequest): RoutingResponse =
        withContext(Dispatchers.IO) {
            if (USE_MOCK_API) return@withContext MockCyclingData.routingResponse(request)
            val response = postJson("/api/routing/recommend", request.toJson())
            parseRouting(response)
        }

    suspend fun getMelbourneSa2Heatmap(): MelbourneSa2HeatmapResponse =
        withContext(Dispatchers.IO) {
            if (USE_MOCK_API) return@withContext MockCyclingData.melbourneSa2HeatmapResponse()
            val response = getJson("/api/heatmap/melbourne-sa2")
            parseMelbourneSa2Heatmap(response)
        }

    private fun getJson(path: String): JSONObject {
        val url = URI("$BASE_URL$path").toURL()
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 30_000
            readTimeout = 300_000
            setRequestProperty("Accept", "application/json")
        }

        try {
            val statusCode = connection.responseCode
            val stream = if (statusCode in 200..299) {
                connection.inputStream
            } else {
                connection.errorStream
            }
            val responseText = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (statusCode !in 200..299) {
                throw IllegalStateException(
                    "Request failed with HTTP $statusCode: ${responseText.ifBlank { "No error body" }}"
                )
            }
            return JSONObject(responseText)
        } finally {
            connection.disconnect()
        }
    }

    private fun postJson(path: String, body: JSONObject): JSONObject {
        val url = URI("$BASE_URL$path").toURL()
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 30_000
            readTimeout = 300_000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }

        try {
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(body.toString())
            }
            val statusCode = connection.responseCode
            val stream = if (statusCode in 200..299) {
                connection.inputStream
            } else {
                connection.errorStream
            }
            val responseText = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (statusCode !in 200..299) {
                throw IllegalStateException(
                    "Request failed with HTTP $statusCode: ${responseText.ifBlank { "No error body" }}"
                )
            }
            return JSONObject(responseText)
        } finally {
            connection.disconnect()
        }
    }

    private fun FeasibilityRequest.toJson(): JSONObject {
        return JSONObject()
            .put("start_lat", startLat)
            .put("start_lng", startLng)
            .put("end_lat", endLat)
            .put("end_lng", endLng)
    }

    private fun parseFeasibility(json: JSONObject): FeasibilityResponse {
        val explanationsJson = json.optJSONArray("explanations")
        val explanations = buildList {
            if (explanationsJson != null) {
                for (index in 0 until explanationsJson.length()) {
                    val item = explanationsJson.getJSONObject(index)
                    add(
                        FeasibilityExplanation(
                            factor = item.optString("factor", "Unknown factor"),
                            impact = item.optString("impact", "Unknown")
                        )
                    )
                }
            }
        }

        return FeasibilityResponse(
            score = json.optInt("score", 0),
            isSupportedArea = json.optBoolean("is_supported_area", false),
            warningMessage = json.optString("warning_message").ifBlank { null },
            explanations = explanations
        )
    }

    private fun parseRouting(json: JSONObject): RoutingResponse {
        val segmentsJson = json.optJSONArray("route_segments")
        val segments = buildList {
            if (segmentsJson != null) {
                for (index in 0 until segmentsJson.length()) {
                    val item = segmentsJson.getJSONObject(index)
                    val coordinatesJson = item.getJSONArray("coordinates")
                    val coordinates = buildList {
                        for (coordinateIndex in 0 until coordinatesJson.length()) {
                            val point = coordinatesJson.getJSONArray(coordinateIndex)
                            add(
                                RouteCoordinate(
                                    lat = point.getDouble(0),
                                    lng = point.getDouble(1)
                                )
                            )
                        }
                    }
                    add(
                        RouteSegment(
                            coordinates = coordinates,
                            riskLevel = item.optString("risk_level", "Green"),
                            isGap = item.optBoolean("is_gap", false)
                        )
                    )
                }
            }
        }

        val alertsJson = json.optJSONArray("alerts")
        val alerts = buildList {
            if (alertsJson != null) {
                for (index in 0 until alertsJson.length()) {
                    val item = alertsJson.getJSONObject(index)
                    val location = item.getJSONArray("location")
                    add(
                        RouteAlert(
                            location = RouteCoordinate(
                                lat = location.getDouble(0),
                                lng = location.getDouble(1)
                            ),
                            message = item.optString("message", "Route alert")
                        )
                    )
                }
            }
        }

        return RoutingResponse(routeSegments = segments, alerts = alerts)
    }

    private fun parseMelbourneSa2Heatmap(json: JSONObject): MelbourneSa2HeatmapResponse {
        val regionsJson = json.optJSONArray("regions")
        val regions = buildList {
            if (regionsJson != null) {
                for (index in 0 until regionsJson.length()) {
                    val item = regionsJson.getJSONObject(index)
                    add(
                        HeatmapRegion(
                            sa2Code = item.optString("sa2_code", "Unknown"),
                            suburbName = item.optString("suburb_name", "Unknown suburb"),
                            score = item.optInt("score", 0),
                            riskLevel = item.optString("risk_level", "Green"),
                            intensity = item.optInt("intensity", item.optInt("score", 0)),
                            workingPopulationRatio = item.optDouble("working_population_ratio", 0.0),
                            shortCommutePct = item.optDouble("short_commute_pct", 0.0),
                            zeroCarHouseholdPct = item.optDouble("zero_car_household_pct", 0.0),
                            geometry = parseGeometry(item.opt("geometry"))
                        )
                    )
                }
            }
        }

        return MelbourneSa2HeatmapResponse(
            regions = regions,
            statusMessage = json.optString("status_message").ifBlank { null }
        )
    }

    private fun parseGeometry(rawGeometry: Any?): List<List<RouteCoordinate>> {
        if (rawGeometry !is JSONObject) return emptyList()
        return when (rawGeometry.optString("type").lowercase()) {
            "polygon" -> parsePolygon(rawGeometry.optJSONArray("coordinates"))
            "multipolygon" -> {
                val polygonsJson = rawGeometry.optJSONArray("coordinates") ?: return emptyList()
                buildList {
                    for (polygonIndex in 0 until polygonsJson.length()) {
                        addAll(parsePolygon(polygonsJson.optJSONArray(polygonIndex)))
                    }
                }
            }
            else -> emptyList()
        }
    }

    private fun parsePolygon(ringsJson: JSONArray?): List<List<RouteCoordinate>> {
        if (ringsJson == null) return emptyList()
        return buildList {
            for (ringIndex in 0 until ringsJson.length()) {
                val ringJson = ringsJson.optJSONArray(ringIndex) ?: continue
                val ring = buildList {
                    for (pointIndex in 0 until ringJson.length()) {
                        val point = ringJson.optJSONArray(pointIndex) ?: continue
                        if (point.length() >= 2) {
                            add(
                                RouteCoordinate(
                                    lat = point.optDouble(1),
                                    lng = point.optDouble(0)
                                )
                            )
                        }
                    }
                }
                if (ring.size >= 3) {
                    add(ring)
                }
            }
        }
    }
}
