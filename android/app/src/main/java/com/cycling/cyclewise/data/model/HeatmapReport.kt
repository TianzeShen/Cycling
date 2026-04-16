package com.cycling.cyclewise.data.model

data class HeatmapReport(
    val title: String,
    val locationName: String,
    val lat: Double,
    val lng: Double,
    val riskLevel: RiskLevel,
    val status: String,
    val votes: Int,
    val timeAgo: String,
    val radiusMeters: Double,
    val issueCount: Int
)

enum class RiskLevel(val label: String) {
    High("High"),
    Medium("Medium"),
    Low("Low")
}

data class MelbourneSa2HeatmapResponse(
    val regions: List<HeatmapRegion>,
    val statusMessage: String?
)

data class HeatmapRegion(
    val sa2Code: String,
    val suburbName: String,
    val score: Int,
    val riskLevel: String,
    val intensity: Int,
    val workingPopulationRatio: Double,
    val shortCommutePct: Double,
    val zeroCarHouseholdPct: Double,
    val geometry: List<List<RouteCoordinate>>
) {
    val hasGeometry: Boolean
        get() = geometry.isNotEmpty()
}
