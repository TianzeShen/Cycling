from math import asin, cos, radians, sin, sqrt

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
    score = calculate_provisional_score(distance_km)
    warning_message = build_warning_message(score, distance_km)

    return FeasibilityResponse(
        score=score,
        is_supported_area=True,
        warning_message=warning_message,
        explanations=build_explanations(distance_km, score),
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


def calculate_provisional_score(distance_km: float) -> int:
    # Iteration 1 uses a simple heuristic until routing data is integrated.
    base_score = 92
    distance_penalty = min(distance_km * 6, 52)
    score = round(base_score - distance_penalty)
    return max(40, min(95, score))


def build_warning_message(score: int, distance_km: float) -> str | None:
    if score < 50:
        return (
            f"Preliminary feasibility is low for this {distance_km:.1f} km trip. "
            "Please review the route carefully before cycling."
        )
    return None


def build_explanations(
    distance_km: float, score: int
) -> list[FeasibilityExplanation]:
    explanations = [
        FeasibilityExplanation(
            factor=f"Trip distance is approximately {distance_km:.1f} km",
            impact=distance_impact(distance_km),
        ),
        FeasibilityExplanation(
            factor="Both coordinates are within the supported Melbourne area",
            impact="Medium",
        ),
    ]

    if score < 50:
        explanations.append(
            FeasibilityExplanation(
                factor="Longer trips receive a lower provisional safety/practicality score",
                impact="High",
            )
        )
    else:
        explanations.append(
            FeasibilityExplanation(
                factor="This provisional score can be evaluated successfully with valid input",
                impact="Low",
            )
        )

    return explanations


def distance_impact(distance_km: float) -> str:
    if distance_km >= 10:
        return "High"
    if distance_km >= 5:
        return "Medium"
    return "Low"
