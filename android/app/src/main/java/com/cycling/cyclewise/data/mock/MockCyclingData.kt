package com.cycling.cyclewise.data.mock

import com.cycling.cyclewise.data.model.FeasibilityExplanation
import com.cycling.cyclewise.data.model.FeasibilityRequest
import com.cycling.cyclewise.data.model.FeasibilityResponse
import com.cycling.cyclewise.data.model.HeatmapReport
import com.cycling.cyclewise.data.model.HeatmapRegion
import com.cycling.cyclewise.data.model.MelbourneSa2HeatmapResponse
import com.cycling.cyclewise.data.model.RiskLevel
import com.cycling.cyclewise.data.model.RouteAlert
import com.cycling.cyclewise.data.model.RouteCoordinate
import com.cycling.cyclewise.data.model.RouteSegment
import com.cycling.cyclewise.data.model.RoutingResponse

object MockCyclingData {
    val heatmapReports = listOf(
        HeatmapReport(
            title = "Missing Bike Lane",
            locationName = "Monash Clayton campus",
            lat = -37.9114,
            lng = 145.1340,
            riskLevel = RiskLevel.High,
            status = "Verified",
            votes = 24,
            timeAgo = "2h ago",
            radiusMeters = 280.0,
            issueCount = 12
        ),
        HeatmapReport(
            title = "Unsafe Crossing",
            locationName = "Wellington Rd",
            lat = -37.9141,
            lng = 145.1308,
            riskLevel = RiskLevel.Medium,
            status = "Verified",
            votes = 18,
            timeAgo = "5h ago",
            radiusMeters = 230.0,
            issueCount = 5
        ),
        HeatmapReport(
            title = "Low Visibility Segment",
            locationName = "Blackburn Rd",
            lat = -37.9084,
            lng = 145.1389,
            riskLevel = RiskLevel.Low,
            status = "Pending",
            votes = 9,
            timeAgo = "1d ago",
            radiusMeters = 190.0,
            issueCount = 3
        )
    )

    fun melbourneSa2HeatmapResponse(): MelbourneSa2HeatmapResponse {
        return MelbourneSa2HeatmapResponse(
            regions = listOf(
                HeatmapRegion(
                    sa2Code = "MEL0001",
                    suburbName = "Clayton",
                    score = 53,
                    riskLevel = "Yellow",
                    intensity = 53,
                    workingPopulationRatio = 1.1721,
                    shortCommutePct = 19.97,
                    zeroCarHouseholdPct = 21.37,
                    geometry = listOf(
                        listOf(
                            RouteCoordinate(-37.9025, 145.1265),
                            RouteCoordinate(-37.9025, 145.1435),
                            RouteCoordinate(-37.9185, 145.1435),
                            RouteCoordinate(-37.9185, 145.1265),
                            RouteCoordinate(-37.9025, 145.1265)
                        )
                    )
                )
            ),
            statusMessage = null
        )
    }

    fun feasibilityResponse(request: FeasibilityRequest): FeasibilityResponse {
        val approximateDistance = kotlin.math.hypot(
            request.endLat - request.startLat,
            request.endLng - request.startLng
        )
        val score = when {
            approximateDistance < 0.03 -> 85
            approximateDistance < 0.08 -> 68
            else -> 45
        }

        return FeasibilityResponse(
            score = score,
            isSupportedArea = true,
            warningMessage = if (score < 50) {
                "This mock route includes long exposure and a disconnected cycling segment."
            } else {
                null
            },
            explanations = listOf(
                FeasibilityExplanation(
                    factor = "Lane continuity",
                    impact = if (score >= 75) "High" else "Medium"
                ),
                FeasibilityExplanation(
                    factor = "Traffic exposure",
                    impact = if (score < 50) "High" else "Medium"
                ),
                FeasibilityExplanation(
                    factor = "Infrastructure gap risk",
                    impact = if (score < 70) "High" else "Low"
                )
            )
        )
    }

    fun routingResponse(request: FeasibilityRequest): RoutingResponse {
        val start = RouteCoordinate(request.startLat, request.startLng)
        val firstMid = RouteCoordinate(
            lat = request.startLat + (request.endLat - request.startLat) * 0.38,
            lng = request.startLng + (request.endLng - request.startLng) * 0.38
        )
        val secondMid = RouteCoordinate(
            lat = request.startLat + (request.endLat - request.startLat) * 0.68,
            lng = request.startLng + (request.endLng - request.startLng) * 0.68
        )
        val end = RouteCoordinate(request.endLat, request.endLng)
        val warningPoint = RouteCoordinate(
            lat = (firstMid.lat + secondMid.lat) / 2.0,
            lng = (firstMid.lng + secondMid.lng) / 2.0
        )
        val gapPoint = RouteCoordinate(
            lat = (secondMid.lat + end.lat) / 2.0,
            lng = (secondMid.lng + end.lng) / 2.0
        )

        return RoutingResponse(
            routeSegments = listOf(
                RouteSegment(
                    coordinates = listOf(start, firstMid),
                    riskLevel = "Green",
                    isGap = false
                ),
                RouteSegment(
                    coordinates = listOf(firstMid, secondMid),
                    riskLevel = "Yellow",
                    isGap = false
                ),
                RouteSegment(
                    coordinates = listOf(secondMid, end),
                    riskLevel = "Red",
                    isGap = true
                )
            ),
            alerts = listOf(
                RouteAlert(
                    location = warningPoint,
                    message = "Mock early warning: moderate traffic exposure ahead"
                ),
                RouteAlert(
                    location = gapPoint,
                    message = "Mock high-risk alert: disconnected lane before destination"
                )
            )
        )
    }
}
