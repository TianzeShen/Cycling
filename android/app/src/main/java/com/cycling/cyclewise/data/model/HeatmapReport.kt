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
