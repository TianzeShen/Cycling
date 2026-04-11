from math import asin, cos, radians, sin, sqrt
from typing import TypedDict

try:
    from Backend.schemas import FeasibilityExplanation, FeasibilityRequest, FeasibilityResponse
except ModuleNotFoundError:
    from schemas import FeasibilityExplanation, FeasibilityRequest, FeasibilityResponse


MELBOURNE_BOUNDS = {
    "min_lat": -38.60,
    "max_lat": -37.20,
    "min_lng": 144.30,
    "max_lng": 145.60,
}

UNSUPPORTED_AREA_MESSAGE = (
    "Selected coordinates are outside the currently supported Melbourne area."
)
MELBOURNE_CBD = (-37.8136, 144.9631)


class ScoreComponents(TypedDict):
    distance_score: int
    infrastructure_score: int
    traffic_score: int
    safety_score: int


def evaluate_feasibility(request: FeasibilityRequest) -> FeasibilityResponse:
    start_supported = is_supported_coordinate(request.start_lat, request.start_lng)
    end_supported = is_supported_coordinate(request.end_lat, request.end_lng)

    if not start_supported or not end_supported:
        return FeasibilityResponse(
            score=None,
            is_supported_area=False,
            warning_message=UNSUPPORTED_AREA_MESSAGE,
            explanations=[
                FeasibilityExplanation(
                    factor="Journey is outside the supported Melbourne service area",
                    impact="High",
                )
            ],
        )

    distance_km = calculate_distance_km(
        request.start_lat,
        request.start_lng,
        request.end_lat,
        request.end_lng,
    )
    components = build_score_components(request, distance_km)
    score = calculate_feasibility_score(components)
    warning_message = build_warning_message(score, distance_km)
    explanations = build_explanations(distance_km, score, components)

    return FeasibilityResponse(
        score=score,
        is_supported_area=True,
        warning_message=warning_message,
        explanations=explanations,
    )


def is_supported_coordinate(latitude: float, longitude: float) -> bool:
    return (
        MELBOURNE_BOUNDS["min_lat"] <= latitude <= MELBOURNE_BOUNDS["max_lat"]
        and MELBOURNE_BOUNDS["min_lng"] <= longitude <= MELBOURNE_BOUNDS["max_lng"]
    )


def calculate_distance_km(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
) -> float:
    earth_radius_km = 6371.0
    delta_lat = radians(end_lat - start_lat)
    delta_lng = radians(end_lng - start_lng)
    start_lat_rad = radians(start_lat)
    end_lat_rad = radians(end_lat)

    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(start_lat_rad) * cos(end_lat_rad) * sin(delta_lng / 2) ** 2
    )
    arc = 2 * asin(sqrt(haversine))
    return earth_radius_km * arc


def build_score_components(
    request: FeasibilityRequest, distance_km: float
) -> ScoreComponents:
    midpoint_lat = (request.start_lat + request.end_lat) / 2
    midpoint_lng = (request.start_lng + request.end_lng) / 2

    # `cbd_distance_km` is only a temporary mock value for the current stage.
    # We use distance from Melbourne CBD as a simple proxy until real
    # database-backed infrastructure and traffic data are available.
    cbd_distance_km = calculate_distance_km(
        midpoint_lat,
        midpoint_lng,
        MELBOURNE_CBD[0],
        MELBOURNE_CBD[1],
    )

    return {
        # Distance score estimates how practical the trip length is for cycling.
        "distance_score": score_distance(distance_km),
        # Infrastructure score estimates lane continuity and riding support.
        "infrastructure_score": score_estimated_infrastructure(cbd_distance_km),
        # Traffic score estimates likely motor traffic exposure.
        "traffic_score": score_estimated_traffic(cbd_distance_km),
        # Safety score estimates overall riding safety for the trip.
        "safety_score": score_safety(distance_km),
    }


def calculate_feasibility_score(components: ScoreComponents) -> int:
    weighted_score = (
        components["distance_score"] * 0.25
        + components["infrastructure_score"] * 0.25
        + components["traffic_score"] * 0.25
        + components["safety_score"] * 0.25
    )
    return max(0, min(100, round(weighted_score)))


def build_warning_message(score: int, distance_km: float) -> str | None:
    if score < 50:
        return (
            f"Preliminary feasibility is low for this {distance_km:.1f} km trip. "
            "Please review the route carefully before cycling."
        )
    return None


def build_explanations(
    distance_km: float,
    score: int,
    components: ScoreComponents,
) -> list[FeasibilityExplanation]:
    explanations = [
        explanation_for_distance(distance_km, components["distance_score"]),
        explanation_from_component(
            "Estimated lane continuity",
            components["infrastructure_score"],
        ),
        explanation_from_component(
            "Estimated traffic exposure",
            components["traffic_score"],
        ),
        explanation_from_component(
            "Estimated overall riding safety",
            components["safety_score"],
        ),
    ]

    if score < 50:
        explanations.append(
            FeasibilityExplanation(
                factor="The combined score indicates this journey may be difficult or unsafe",
                impact="High",
            )
        )
    else:
        explanations.append(
            FeasibilityExplanation(
                factor="The combined score indicates cycling is reasonably practical for this trip",
                impact="Low",
            )
        )

    top_explanations = prioritise_explanations(explanations)
    if not top_explanations:
        return default_explanations(score, distance_km)
    return top_explanations


def score_distance(distance_km: float) -> int:
    if distance_km <= 2:
        return 100
    if distance_km <= 5:
        return 75
    if distance_km <= 8:
        return 50
    if distance_km <= 12:
        return 25
    return 0


def score_estimated_infrastructure(cbd_distance_km: float) -> int:
    if cbd_distance_km <= 5:
        return 100
    if cbd_distance_km <= 12:
        return 75
    if cbd_distance_km <= 20:
        return 50
    if cbd_distance_km <= 30:
        return 25
    return 0


def score_estimated_traffic(cbd_distance_km: float) -> int:
    if cbd_distance_km <= 2:
        return 0
    if cbd_distance_km <= 5:
        return 25
    if cbd_distance_km <= 8:
        return 50
    if cbd_distance_km <= 12:
        return 75
    return 100


def score_safety(distance_km: float) -> int:
    if distance_km <= 3:
        return 100
    if distance_km <= 7:
        return 75
    if distance_km <= 12:
        return 50
    if distance_km <= 20:
        return 25
    return 0


def explanation_from_component(label: str, component_score: int) -> FeasibilityExplanation:
    if component_score >= 75:
        impact = "Low"
        factor = f"{label} is supporting the cycling feasibility score"
    elif component_score >= 50:
        impact = "Medium"
        factor = f"{label} has a moderate influence on this trip"
    else:
        impact = "High"
        factor = f"{label} is reducing the cycling feasibility score"

    return FeasibilityExplanation(factor=factor, impact=impact)


def explanation_for_distance(distance_km: float, component_score: int) -> FeasibilityExplanation:
    if component_score >= 75:
        impact = "Low"
        factor = f"The trip distance of {distance_km:.1f} km is manageable for cycling"
    elif component_score >= 50:
        impact = "Medium"
        factor = f"The trip distance of {distance_km:.1f} km has a moderate effect on feasibility"
    else:
        impact = "High"
        factor = f"The trip distance of {distance_km:.1f} km is reducing feasibility"

    return FeasibilityExplanation(factor=factor, impact=impact)


def default_explanations(score: int, distance_km: float) -> list[FeasibilityExplanation]:
    if score < 50:
        return [
            FeasibilityExplanation(
                factor=f"The trip distance of {distance_km:.1f} km appears challenging for cycling",
                impact="High",
            )
        ]
    return [
        FeasibilityExplanation(
            factor=f"The trip distance of {distance_km:.1f} km appears reasonable for cycling",
            impact="Low",
        )
    ]


def prioritise_explanations(
    explanations: list[FeasibilityExplanation],
) -> list[FeasibilityExplanation]:
    priority = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(explanations, key=lambda item: priority[item.impact])[:3]
