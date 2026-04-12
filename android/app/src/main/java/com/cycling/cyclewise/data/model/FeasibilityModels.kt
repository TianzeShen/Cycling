package com.cycling.cyclewise.data.model

data class FeasibilityRequest(
    val startLat: Double,
    val startLng: Double,
    val endLat: Double,
    val endLng: Double
)

data class FeasibilityResponse(
    val score: Int,
    val isSupportedArea: Boolean,
    val warningMessage: String?,
    val explanations: List<FeasibilityExplanation>
)

data class FeasibilityExplanation(
    val factor: String,
    val impact: String
)
