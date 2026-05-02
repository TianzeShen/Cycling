from math import asin, cos, radians, sin, sqrt
from typing import Any, TypedDict

try:
    from Backend.database import fetch_one, fetch_scalar
    from Backend.schemas import (
        FeasibilityExplanation,
        FeasibilityRequest,
        FeasibilityResponse,
    )
    from Backend.services.ridesmart_ai_adapter import (
        compute_feasibility_score,
        detect_route_risk,
        generate_explanations,
    )
except ModuleNotFoundError:
    from database import fetch_one, fetch_scalar
    from schemas import (
        FeasibilityExplanation,
        FeasibilityRequest,
        FeasibilityResponse,
    )
    from services.ridesmart_ai_adapter import (
        compute_feasibility_score,
        detect_route_risk,
        generate_explanations,
    )


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


class RouteContext(TypedDict):
    road_count: int
    lane_count: int
    continuous_lane_count: int
    protected_lane_count: int
    gap_count: int
    cyclist_crash_count: int
    avg_danger_score: float
    max_danger_score: float
    avg_speed_limit_kmh: float
    high_traffic_road_count: int


class FeasibilityFeatures(TypedDict):
    distance_km: float
    protected_lane_pct: float
    no_infra_pct: float
    gap_count: int
    high_traffic_pct: float
    avg_speed_limit: float


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
    features = build_feasibility_features(
        request,
        distance_km,
        route_context,
    )

    score_result = compute_feasibility_score(features)
    risk_result = detect_route_risk(features)
    score = int(score_result["score"])

    warning_message = build_warning_message(score_result, risk_result)
    explanations = build_explanations(features, score_result, risk_result)

    return FeasibilityResponse(
        score=score,
        is_supported_area=True,
        warning_message=warning_message,
        explanations=explanations,
    )


def evaluate_feasibility_for_route_points(
    route_points: list[tuple[float, float]],
) -> FeasibilityResponse:
    if len(route_points) < 2:
        return FeasibilityResponse(
            score=None,
            is_supported_area=False,
            warning_message="Route geometry is unavailable for feasibility analysis.",
            explanations=[],
        )

    start_lat, start_lng = route_points[0]
    end_lat, end_lng = route_points[-1]
    start_supported = is_supported_coordinate(start_lat, start_lng)
    end_supported = is_supported_coordinate(end_lat, end_lng)

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

    distance_km = calculate_route_points_distance_km(route_points)
    route_context = fetch_route_context_for_route_points(route_points)
    fallback_request = FeasibilityRequest(
        start_lat=start_lat,
        start_lng=start_lng,
        end_lat=end_lat,
        end_lng=end_lng,
    )
    features = build_feasibility_features(
        fallback_request,
        distance_km,
        route_context,
        use_context_gap_count=True,
    )

    score_result = compute_feasibility_score(features)
    risk_result = detect_route_risk(features)
    score = int(score_result["score"])
    warning_message = build_warning_message(score_result, risk_result)
    explanations = build_explanations(features, score_result, risk_result)

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


def calculate_route_points_distance_km(
    route_points: list[tuple[float, float]],
) -> float:
    if len(route_points) < 2:
        return 0.0

    total_distance_km = 0.0
    for index in range(len(route_points) - 1):
        start = route_points[index]
        end = route_points[index + 1]
        total_distance_km += calculate_distance_km(
            start[0],
            start[1],
            end[0],
            end[1],
        )
    return round(total_distance_km, 2)


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
                COUNT(*) FILTER (WHERE COALESCE(cl.is_continuous, false)) AS continuous_lane_count,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(cl.protection_level, '')) IN ('high', 'medium')
                       OR LOWER(COALESCE(cl.lane_type, '')) LIKE '%protected%'
                       OR LOWER(COALESCE(cl.lane_type, '')) LIKE '%separated%'
                ) AS protected_lane_count,
                COUNT(*) FILTER (WHERE COALESCE(cl.is_continuous, false) = false) AS inferred_gap_count
            FROM ridesmart.cycling_lane cl, route_line r
            WHERE ST_DWithin(cl.geom::geography, r.geom::geography, 120)
        ),
        road_stats AS (
            SELECT
                COUNT(*) AS road_count,
                COALESCE(AVG(rs.danger_score), 0) AS avg_danger_score,
                COALESCE(MAX(rs.danger_score), 0) AS max_danger_score,
                COALESCE(AVG(COALESCE(rs.speed_limit_kmh, 40)), 40) AS avg_speed_limit_kmh,
                COUNT(*) FILTER (
                    WHERE COALESCE(rs.aadt_volume, 0) >= 20000
                       OR COALESCE(rs.danger_score, 0) >= 60
                ) AS high_traffic_road_count
            FROM ridesmart.road_segment rs, route_line r
            WHERE ST_DWithin(rs.geom::geography, r.geom::geography, 120)
        ),
        gap_stats AS (
            SELECT COUNT(*) AS explicit_gap_count
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
            lane_stats.protected_lane_count,
            GREATEST(gap_stats.explicit_gap_count, lane_stats.inferred_gap_count) AS gap_count,
            crash_stats.cyclist_crash_count,
            road_stats.avg_danger_score,
            road_stats.max_danger_score,
            road_stats.avg_speed_limit_kmh,
            road_stats.high_traffic_road_count
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


def fetch_route_context_for_route_points(
    route_points: list[tuple[float, float]],
) -> RouteContext | None:
    if len(route_points) < 2:
        return None

    route_coordinates = ",".join(f"{lng} {lat}" for lat, lng in route_points)
    query = """
        WITH route_line AS (
            SELECT ST_SetSRID(
                ST_GeomFromText(:route_wkt),
                4326
            ) AS geom
        ),
        lane_stats AS (
            SELECT
                COUNT(*) AS lane_count,
                COUNT(*) FILTER (WHERE COALESCE(cl.is_continuous, false)) AS continuous_lane_count,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(cl.protection_level, '')) IN ('high', 'medium')
                       OR LOWER(COALESCE(cl.lane_type, '')) LIKE '%protected%'
                       OR LOWER(COALESCE(cl.lane_type, '')) LIKE '%separated%'
                ) AS protected_lane_count,
                COUNT(*) FILTER (WHERE COALESCE(cl.is_continuous, false) = false) AS inferred_gap_count
            FROM ridesmart.cycling_lane cl, route_line r
            WHERE ST_DWithin(cl.geom::geography, r.geom::geography, 120)
        ),
        road_stats AS (
            SELECT
                COUNT(*) AS road_count,
                COALESCE(AVG(rs.danger_score), 0) AS avg_danger_score,
                COALESCE(MAX(rs.danger_score), 0) AS max_danger_score,
                COALESCE(AVG(COALESCE(rs.speed_limit_kmh, 40)), 40) AS avg_speed_limit_kmh,
                COUNT(*) FILTER (
                    WHERE COALESCE(rs.aadt_volume, 0) >= 20000
                       OR COALESCE(rs.danger_score, 0) >= 60
                ) AS high_traffic_road_count
            FROM ridesmart.road_segment rs, route_line r
            WHERE ST_DWithin(rs.geom::geography, r.geom::geography, 120)
        ),
        gap_stats AS (
            SELECT COUNT(*) AS explicit_gap_count
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
            lane_stats.protected_lane_count,
            GREATEST(gap_stats.explicit_gap_count, lane_stats.inferred_gap_count) AS gap_count,
            crash_stats.cyclist_crash_count,
            road_stats.avg_danger_score,
            road_stats.max_danger_score,
            road_stats.avg_speed_limit_kmh,
            road_stats.high_traffic_road_count
        FROM lane_stats, road_stats, gap_stats, crash_stats
    """
    try:
        row = fetch_one(query, {"route_wkt": f"LINESTRING({route_coordinates})"})
    except Exception:
        return None

    return row if row is not None else None


def has_route_context_data(route_context: RouteContext | None) -> bool:
    if route_context is None:
        return False
    return route_context["road_count"] > 0 or route_context["lane_count"] > 0


def build_feasibility_features(
    request: FeasibilityRequest,
    distance_km: float,
    route_context: RouteContext | None,
    use_context_gap_count: bool = False,
) -> FeasibilityFeatures:
    if has_route_context_data(route_context) and route_context is not None:
        return build_features_from_context(
            distance_km,
            route_context,
            use_context_gap_count=use_context_gap_count,
        )
    return build_estimated_features(request, distance_km)


def build_features_from_context(
    distance_km: float,
    route_context: RouteContext,
    use_context_gap_count: bool = False,
) -> FeasibilityFeatures:
    road_count = max(route_context["road_count"], 1)
    lane_count = route_context["lane_count"]

    protected_lane_pct = percentage(route_context["protected_lane_count"], lane_count)
    lane_coverage_pct = percentage(route_context["continuous_lane_count"], road_count)
    no_infra_pct = round(max(0.0, 100.0 - lane_coverage_pct), 2)
    high_traffic_pct = percentage(route_context["high_traffic_road_count"], road_count)

    return {
        "distance_km": round(distance_km, 2),
        "protected_lane_pct": protected_lane_pct,
        "no_infra_pct": no_infra_pct,
        "gap_count": (
            int(route_context["gap_count"])
            if use_context_gap_count
            else build_mock_gap_count(distance_km)
        ),
        "high_traffic_pct": high_traffic_pct,
        "avg_speed_limit": round(float(route_context["avg_speed_limit_kmh"]), 2),
    }


def build_estimated_features(
    request: FeasibilityRequest,
    distance_km: float,
) -> FeasibilityFeatures:
    midpoint_lat = (request.start_lat + request.end_lat) / 2
    midpoint_lng = (request.start_lng + request.end_lng) / 2

    # `cbd_distance_km` is only a temporary proxy for the early mock stage.
    cbd_distance_km = calculate_distance_km(
        midpoint_lat,
        midpoint_lng,
        MELBOURNE_CBD[0],
        MELBOURNE_CBD[1],
    )

    if cbd_distance_km <= 5:
        protected_lane_pct = 40.0
        no_infra_pct = 20.0
        high_traffic_pct = 15.0
        avg_speed_limit = 40.0
    elif cbd_distance_km <= 12:
        protected_lane_pct = 25.0
        no_infra_pct = 35.0
        high_traffic_pct = 25.0
        avg_speed_limit = 50.0
    else:
        protected_lane_pct = 10.0
        no_infra_pct = 50.0
        high_traffic_pct = 40.0
        avg_speed_limit = 60.0

    return {
        "distance_km": round(distance_km, 2),
        "protected_lane_pct": protected_lane_pct,
        "no_infra_pct": no_infra_pct,
        "gap_count": build_mock_gap_count(distance_km),
        "high_traffic_pct": high_traffic_pct,
        "avg_speed_limit": avg_speed_limit,
    }


def build_mock_gap_count(distance_km: float) -> int:
    if distance_km > 15:
        return 2
    if distance_km > 8:
        return 1
    return 0


def percentage(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 2)


def build_warning_message(
    score_result: dict[str, Any],
    risk_result: dict[str, Any],
) -> str | None:
    score = int(score_result["score"])
    risk_level = str(risk_result.get("risk_level", "Low"))
    alerts = [str(alert) for alert in risk_result.get("alerts", [])]

    if score < 50:
        return (
            f"Cycling feasibility is currently low ({score}/100). "
            "Please review the route carefully before riding."
        )

    if risk_level == "High" and alerts:
        return alerts[0]

    return None


def build_explanations(
    features: FeasibilityFeatures,
    score_result: dict[str, Any],
    risk_result: dict[str, Any],
) -> list[FeasibilityExplanation]:
    reasons = [str(reason) for reason in generate_explanations(features)]
    alerts = [str(alert) for alert in risk_result.get("alerts", [])]

    combined_messages = deduplicate_messages(reasons + alerts)
    if not combined_messages:
        combined_messages = [
            f"The route is rated as {str(score_result.get('label', 'Moderate feasibility')).lower()}."
        ]

    return [
        FeasibilityExplanation(
            factor=message,
            impact=infer_impact_from_message(message, score_result, risk_result),
        )
        for message in combined_messages[:4]
    ]


def deduplicate_messages(messages: list[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for message in messages:
        normalised = message.strip()
        if not normalised:
            continue
        if normalised in seen:
            continue
        seen.add(normalised)
        deduplicated.append(normalised)
    return deduplicated


def infer_impact_from_message(
    message: str,
    score_result: dict[str, Any],
    risk_result: dict[str, Any],
) -> str:
    lowered_message = message.lower()
    risk_level = str(risk_result.get("risk_level", "Low"))
    score = int(score_result["score"])

    high_keywords = [
        "gap",
        "higher traffic",
        "no dedicated",
        "challenging",
        "high-speed",
        "substantial exposure",
    ]
    low_keywords = [
        "improving safety",
        "balanced cycling conditions",
        "helps reduce route risk",
    ]

    if any(keyword in lowered_message for keyword in high_keywords):
        return "High"
    if any(keyword in lowered_message for keyword in low_keywords):
        return "Low"
    if risk_level == "High" or score < 50:
        return "High"
    if risk_level == "Medium" or score < 75:
        return "Medium"
    return "Low"
