package com.cycling.cyclewise.data.model

data class RoutingResponse(
    val routeSegments: List<RouteSegment>,
    val alerts: List<RouteAlert>
)

data class RouteSegment(
    val coordinates: List<RouteCoordinate>,
    val riskLevel: String,
    val isGap: Boolean
)

data class RouteCoordinate(
    val lat: Double,
    val lng: Double
)

data class RouteAlert(
    val location: RouteCoordinate,
    val message: String
)

fun RouteCoordinate.midpointTo(other: RouteCoordinate): RouteCoordinate {
    return RouteCoordinate(
        lat = (lat + other.lat) / 2.0,
        lng = (lng + other.lng) / 2.0
    )
}
