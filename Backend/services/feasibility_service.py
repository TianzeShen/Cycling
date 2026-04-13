from math import asin, cos, radians, sin, sqrt
from typing import TypedDict

try:
    from Backend.database import fetch_one, fetch_scalar
    from Backend.schemas import FeasibilityExplanation, FeasibilityRequest, FeasibilityResponse
except ModuleNotFoundError:
    from database import fetch_one, fetch_scalar
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


class RouteContext(TypedDict):
    road_count: int
    lane_count: int
    continuous_lane_count: int
    gap_count: int
    cyclist_crash_count: int
    avg_danger_score: float
    max_danger_score: float


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
    route_context = fetch_route_context(request)
    use_database_context = has_route_context_data(route_context)
    components = build_score_components(request, distance_km, route_context)
    score = calculate_feasibility_score(components)
    warning_message = build_warning_message(score, distance_km)
    explanations = build_explanations(
        distance_km,
        score,
        components,
        route_context,
        use_database_context,
    )

    return FeasibilityResponse(
        score=score,
        is_supported_area=True,
        warning_message=warning_message,
        explanations=explanations,
    )


def is_supported_coordinate(latitude: float, longitude: float) -> bool:
    if has_spatial_network_data():
        query = """
            SELECT (
                EXISTS (
                    SELECT 1
                    FROM ridesmart.road_segment rs
                    WHERE ST_DWithin(
                        rs.geom::geography,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                        3000
                    )
                )
                OR EXISTS (
                    SELECT 1
                    FROM ridesmart.cycling_lane cl
                    WHERE ST_DWithin(
                        cl.geom::geography,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                        3000
                    )
                )
            ) AS is_supported
        """
        row = fetch_one(query, {"lat": latitude, "lng": longitude})
        if row is not None:
            return bool(row["is_supported"])

    return (
        MELBOURNE_BOUNDS["min_lat"] <= latitude <= MELBOURNE_BOUNDS["max_lat"]
        and MELBOURNE_BOUNDS["min_lng"] <= longitude <= MELBOURNE_BOUNDS["max_lng"]
    )


def has_spatial_network_data() -> bool:
    query = """
        SELECT (
            (SELECT COUNT(*) FROM ridesmart.road_segment)
            + (SELECT COUNT(*) FROM ridesmart.cycling_lane)
        ) > 0
    """
    try:
        return bool(fetch_scalar(query))
    except Exception:
        return False


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


def fetch_route_context(request: FeasibilityRequest) -> RouteContext | None:
    query = """
        WITH route_line AS (
            SELECT ST_SetSRID(
                ST_MakeLine(
                    ST_MakePoint(:start_lng, :start_lat),
                    ST_MakePoint(:end_lng, :end_lat)
                ),
                4326
            ) AS geom
        ),
        lane_stats AS (
            SELECT
                COUNT(*) AS lane_count,
                COUNT(*) FILTER (WHERE cl.is_continuous) AS continuous_lane_count
            FROM ridesmart.cycling_lane cl, route_line r
            WHERE ST_DWithin(cl.geom::geography, r.geom::geography, 120)
        ),
        road_stats AS (
            SELECT
                COUNT(*) AS road_count,
                COALESCE(AVG(rs.danger_score), 0) AS avg_danger_score,
                COALESCE(MAX(rs.danger_score), 0) AS max_danger_score
            FROM ridesmart.road_segment rs, route_line r
            WHERE ST_DWithin(rs.geom::geography, r.geom::geography, 120)
        ),
        gap_stats AS (
            SELECT COUNT(*) AS gap_count
            FROM ridesmart.lane_gap lg, route_line r
            WHERE ST_DWithin(lg.geom::geography, r.geom::geography, 120)
        ),
        crash_stats AS (
            SELECT COUNT(*) AS cyclist_crash_count
            FROM ridesmart.crash_record cr, route_line r
            WHERE cr.involves_cyclist = TRUE
              AND cr.geom IS NOT NULL
              AND ST_DWithin(cr.geom::geography, r.geom::geography, 120)
        )
        SELECT
            road_stats.road_count,
            lane_stats.lane_count,
            lane_stats.continuous_lane_count,
            gap_stats.gap_count,
            crash_stats.cyclist_crash_count,
            road_stats.avg_danger_score,
            road_stats.max_danger_score
        FROM lane_stats, road_stats, gap_stats, crash_stats
    """
    try:
        row = fetch_one(
            query,
            {
                "start_lat": request.start_lat,
                "start_lng": request.start_lng,
                "end_lat": request.end_lat,
                "end_lng": request.end_lng,
            },
        )
    except Exception:
        return None

    return row if row is not None else None


def has_route_context_data(route_context: RouteContext | None) -> bool:
    if route_context is None:
        return False
    return (
        route_context["road_count"] > 0
        or route_context["lane_count"] > 0
        or route_context["gap_count"] > 0
        or route_context["cyclist_crash_count"] > 0
    )


def build_score_components(
    request: FeasibilityRequest,
    distance_km: float,
    route_context: RouteContext | None,
) -> ScoreComponents:
    midpoint_lat = (request.start_lat + request.end_lat) / 2
    midpoint_lng = (request.start_lng + request.end_lng) / 2

    # `cbd_distance_km` is a temporary proxy used only when real data has
    # not been loaded into ridesmart tables yet.
    cbd_distance_km = calculate_distance_km(
        midpoint_lat,
        midpoint_lng,
        MELBOURNE_CBD[0],
        MELBOURNE_CBD[1],
    )

    if has_route_context_data(route_context):
        return {
            "distance_score": score_distance(distance_km),
            "infrastructure_score": score_infrastructure_from_context(route_context),
            "traffic_score": score_traffic_from_context(route_context),
            "safety_score": score_safety_from_context(route_context),
        }

    return {
        "distance_score": score_distance(distance_km),
        "infrastructure_score": score_estimated_infrastructure(cbd_distance_km),
        "traffic_score": score_estimated_traffic(cbd_distance_km),
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
    route_context: RouteContext | None,
    use_database_context: bool,
) -> list[FeasibilityExplanation]:
    if use_database_context and route_context is not None:
        explanations = [
            explanation_for_distance(distance_km, components["distance_score"]),
            explanation_for_database_infrastructure(route_context, components["infrastructure_score"]),
            explanation_for_database_traffic(route_context, components["traffic_score"]),
            explanation_for_database_safety(route_context, components["safety_score"]),
        ]
    else:
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


def score_infrastructure_from_context(route_context: RouteContext) -> int:
    lane_count = route_context["lane_count"]
    continuous_lane_count = route_context["continuous_lane_count"]
    gap_count = route_context["gap_count"]

    if lane_count == 0 and gap_count > 0:
        return 0
    if lane_count == 0:
        return 25

    continuity_ratio = continuous_lane_count / lane_count
    if gap_count >= 3 or continuity_ratio < 0.25:
        return 0
    if gap_count >= 2 or continuity_ratio < 0.50:
        return 25
    if gap_count >= 1 or continuity_ratio < 0.75:
        return 50
    if continuity_ratio < 0.90:
        return 75
    return 100


def score_traffic_from_context(route_context: RouteContext) -> int:
    avg_danger_score = route_context["avg_danger_score"]
    if avg_danger_score <= 20:
        return 100
    if avg_danger_score <= 40:
        return 75
    if avg_danger_score <= 60:
        return 50
    if avg_danger_score <= 80:
        return 25
    return 0


def score_safety_from_context(route_context: RouteContext) -> int:
    risk_points = 0

    if route_context["gap_count"] >= 2:
        risk_points += 2
    elif route_context["gap_count"] == 1:
        risk_points += 1

    if route_context["cyclist_crash_count"] >= 4:
        risk_points += 2
    elif route_context["cyclist_crash_count"] >= 1:
        risk_points += 1

    if route_context["max_danger_score"] >= 80:
        risk_points += 2
    elif route_context["max_danger_score"] >= 60:
        risk_points += 1

    if risk_points >= 5:
        return 0
    if risk_points == 4:
        return 25
    if risk_points == 3:
        return 50
    if risk_points == 2:
        return 75
    return 100


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


def explanation_for_database_infrastructure(
    route_context: RouteContext,
    component_score: int,
) -> FeasibilityExplanation:
    gap_count = route_context["gap_count"]
    lane_count = route_context["lane_count"]

    if component_score >= 75:
        factor = f"Detected {lane_count} nearby cycling lane segments with strong continuity"
        impact = "Low"
    elif component_score >= 50:
        factor = f"Detected lane continuity is mixed, with {gap_count} route gap areas nearby"
        impact = "Medium"
    else:
        factor = f"Detected {gap_count} gap areas or weak lane continuity along the route"
        impact = "High"

    return FeasibilityExplanation(factor=factor, impact=impact)


def explanation_for_database_traffic(
    route_context: RouteContext,
    component_score: int,
) -> FeasibilityExplanation:
    avg_danger = round(route_context["avg_danger_score"], 1)

    if component_score >= 75:
        factor = f"Nearby road segments show a relatively low danger score ({avg_danger})"
        impact = "Low"
    elif component_score >= 50:
        factor = f"Nearby road segments show a moderate danger score ({avg_danger})"
        impact = "Medium"
    else:
        factor = f"Nearby road segments show a high danger score ({avg_danger})"
        impact = "High"

    return FeasibilityExplanation(factor=factor, impact=impact)


def explanation_for_database_safety(
    route_context: RouteContext,
    component_score: int,
) -> FeasibilityExplanation:
    crash_count = route_context["cyclist_crash_count"]
    gap_count = route_context["gap_count"]

    if component_score >= 75:
        factor = "Few detected safety incidents or gap risks were found near this route"
        impact = "Low"
    elif component_score >= 50:
        factor = (
            f"Detected safety context is mixed with {crash_count} cyclist crash records "
            f"and {gap_count} gap areas nearby"
        )
        impact = "Medium"
    else:
        factor = (
            f"Detected safety risk is elevated with {crash_count} cyclist crash records "
            f"and {gap_count} gap areas nearby"
        )
        impact = "High"

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
