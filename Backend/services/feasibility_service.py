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
        compute_safety_score,
    )
except ModuleNotFoundError:
    from database import fetch_one, fetch_scalar
    from schemas import (
        FeasibilityExplanation,
        FeasibilityRequest,
        FeasibilityResponse,
    )
    from services.ridesmart_ai_adapter import (
        compute_safety_score,
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
HIGH_CRASH_SEGMENT_THRESHOLD = 30
FEASIBILITY_CONTEXT_MAX_POINTS = 60
LANE_TYPE_SCORES = {
    "protected": 1.0,
    "shared_path": 0.9,
    "painted": 0.45,
    "informal": 0.15,
}


class RouteContext(TypedDict):
    road_count: int
    lane_count: int
    protected_lane_count: int
    shared_path_lane_count: int
    painted_lane_count: int
    informal_lane_count: int
    gap_count: int
    avg_aadt: float | None
    avg_speed_limit_kmh: float | None
    high_crash_segment_count: int


class FeasibilityFeatures(TypedDict):
    distance_km: float
    safe_lane_pct: float
    bike_lane_quality: float
    gap_count: int
    avg_aadt: float | None
    avg_speed_limit: float | None
    high_crash_segment_count: int


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

    score_result = calculate_route_score(features)
    score = int(round(float(score_result["score"])))

    warning_message = build_warning_message(features, score_result)
    explanations = build_explanations(features, score_result)

    return FeasibilityResponse(
        score=score,
        is_supported_area=True,
        warning_message=warning_message,
        explanations=explanations,
    )


def evaluate_feasibility_for_route_points(
    route_points: list[tuple[float, float]],
    distance_km_override: float | None = None,
    gap_count_override: int | None = None,
    context_route_points: list[tuple[float, float]] | None = None,
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
    distance_km = (
        float(distance_km_override)
        if distance_km_override is not None
        else calculate_route_points_distance_km(route_points)
    )
    route_context = fetch_route_context_for_route_points(
        route_points,
        context_route_points=context_route_points,
    )
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
        gap_count_override=gap_count_override,
    )

    score_result = calculate_route_score(features)
    score = int(round(float(score_result["score"])))
    warning_message = build_warning_message(features, score_result)
    explanations = build_explanations(features, score_result)

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


def compress_route_points_for_context(
    route_points: list[tuple[float, float]],
    max_points: int = FEASIBILITY_CONTEXT_MAX_POINTS,
) -> list[tuple[float, float]]:
    if len(route_points) <= max_points:
        return route_points

    if max_points <= 2:
        return [route_points[0], route_points[-1]]

    last_index = len(route_points) - 1
    compressed: list[tuple[float, float]] = []

    for sample_index in range(max_points):
        source_index = round((sample_index / (max_points - 1)) * last_index)
        point = route_points[source_index]
        if compressed and compressed[-1] == point:
            continue
        compressed.append(point)

    if compressed[-1] != route_points[-1]:
        compressed.append(route_points[-1])

    return compressed


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
                COUNT(*) FILTER (WHERE cl.lane_type = 'protected') AS protected_lane_count,
                COUNT(*) FILTER (WHERE cl.lane_type = 'shared_path') AS shared_path_lane_count,
                COUNT(*) FILTER (WHERE cl.lane_type = 'painted') AS painted_lane_count,
                COUNT(*) FILTER (WHERE cl.lane_type = 'informal') AS informal_lane_count
            FROM ridesmart.cycling_lane cl, route_line r
            WHERE ST_DWithin(cl.geom::geography, r.geom::geography, 120)
        ),
        road_stats AS (
            SELECT
                COUNT(*) AS road_count,
                AVG(rs.aadt_volume) FILTER (WHERE rs.aadt_volume IS NOT NULL) AS avg_aadt,
                AVG(rs.speed_limit_kmh) FILTER (WHERE rs.speed_limit_kmh IS NOT NULL) AS avg_speed_limit_kmh,
                COUNT(*) FILTER (
                    WHERE COALESCE(rs.crash_count, 0) >= :high_crash_threshold
                ) AS high_crash_segment_count
            FROM ridesmart.road_segment rs, route_line r
            WHERE ST_DWithin(rs.geom::geography, r.geom::geography, 120)
        ),
        gap_stats AS (
            SELECT COUNT(*) AS explicit_gap_count
            FROM ridesmart.lane_gap lg, route_line r
            WHERE ST_DWithin(lg.geom::geography, r.geom::geography, 120)
        )
        SELECT
            road_stats.road_count,
            lane_stats.lane_count,
            lane_stats.protected_lane_count,
            lane_stats.shared_path_lane_count,
            lane_stats.painted_lane_count,
            lane_stats.informal_lane_count,
            gap_stats.explicit_gap_count AS gap_count,
            road_stats.avg_aadt,
            road_stats.avg_speed_limit_kmh,
            road_stats.high_crash_segment_count
        FROM lane_stats, road_stats, gap_stats
    """
    try:
        row = fetch_one(
            query,
            {
                "start_lat": request.start_lat,
                "start_lng": request.start_lng,
                "end_lat": request.end_lat,
                "end_lng": request.end_lng,
                "high_crash_threshold": HIGH_CRASH_SEGMENT_THRESHOLD,
            },
        )
    except Exception:
        return None

    return row if row is not None else None


def fetch_route_context_for_route_points(
    route_points: list[tuple[float, float]],
    context_route_points: list[tuple[float, float]] | None = None,
) -> RouteContext | None:
    if len(route_points) < 2:
        return None

    route_context_points = (
        context_route_points
        if context_route_points is not None and len(context_route_points) >= 2
        else compress_route_points_for_context(route_points)
    )
    route_coordinates = ",".join(f"{lng} {lat}" for lat, lng in route_context_points)
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
                COUNT(*) FILTER (WHERE cl.lane_type = 'protected') AS protected_lane_count,
                COUNT(*) FILTER (WHERE cl.lane_type = 'shared_path') AS shared_path_lane_count,
                COUNT(*) FILTER (WHERE cl.lane_type = 'painted') AS painted_lane_count,
                COUNT(*) FILTER (WHERE cl.lane_type = 'informal') AS informal_lane_count
            FROM ridesmart.cycling_lane cl, route_line r
            WHERE cl.geom && ST_Expand(r.geom, 0.01)
              AND ST_DWithin(cl.geom::geography, r.geom::geography, 120)
        ),
        road_stats AS (
            SELECT
                COUNT(*) AS road_count,
                AVG(rs.aadt_volume) FILTER (WHERE rs.aadt_volume IS NOT NULL) AS avg_aadt,
                AVG(rs.speed_limit_kmh) FILTER (WHERE rs.speed_limit_kmh IS NOT NULL) AS avg_speed_limit_kmh,
                COUNT(*) FILTER (
                    WHERE COALESCE(rs.crash_count, 0) >= :high_crash_threshold
                ) AS high_crash_segment_count
            FROM ridesmart.road_segment rs, route_line r
            WHERE rs.geom && ST_Expand(r.geom, 0.01)
              AND ST_DWithin(rs.geom::geography, r.geom::geography, 120)
        )
        SELECT
            road_stats.road_count,
            lane_stats.lane_count,
            lane_stats.protected_lane_count,
            lane_stats.shared_path_lane_count,
            lane_stats.painted_lane_count,
            lane_stats.informal_lane_count,
            road_stats.avg_aadt,
            road_stats.avg_speed_limit_kmh,
            road_stats.high_crash_segment_count
        FROM lane_stats, road_stats
    """
    try:
        row = fetch_one(
            query,
            {
                "route_wkt": f"LINESTRING({route_coordinates})",
                "high_crash_threshold": HIGH_CRASH_SEGMENT_THRESHOLD,
            },
        )
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
    gap_count_override: int | None = None,
) -> FeasibilityFeatures:
    if has_route_context_data(route_context) and route_context is not None:
        return build_features_from_context(
            distance_km,
            route_context,
            gap_count_override=gap_count_override,
        )
    return build_estimated_features(request, distance_km)


def build_features_from_context(
    distance_km: float,
    route_context: RouteContext,
    gap_count_override: int | None = None,
) -> FeasibilityFeatures:
    lane_count = route_context["lane_count"]
    safe_lane_count = (
        route_context["protected_lane_count"] + route_context["shared_path_lane_count"]
    )
    safe_lane_pct = percentage(safe_lane_count, lane_count)
    bike_lane_quality = calculate_bike_lane_quality(route_context)

    return {
        "distance_km": round(distance_km, 2),
        "safe_lane_pct": safe_lane_pct,
        "bike_lane_quality": bike_lane_quality,
        "gap_count": (
            int(gap_count_override)
            if gap_count_override is not None
            else build_mock_gap_count(distance_km)
        ),
        "avg_aadt": (
            round(float(route_context["avg_aadt"]), 2)
            if route_context["avg_aadt"] is not None
            else None
        ),
        "avg_speed_limit": (
            round(float(route_context["avg_speed_limit_kmh"]), 2)
            if route_context["avg_speed_limit_kmh"] is not None
            else None
        ),
        "high_crash_segment_count": int(route_context["high_crash_segment_count"]),
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
        safe_lane_pct = 45.0
        bike_lane_quality = 0.75
        avg_aadt = 12000.0
        avg_speed_limit = 40.0
        high_crash_segment_count = 0
    elif cbd_distance_km <= 12:
        safe_lane_pct = 30.0
        bike_lane_quality = 0.55
        avg_aadt = 18000.0
        avg_speed_limit = 50.0
        high_crash_segment_count = 1
    else:
        safe_lane_pct = 15.0
        bike_lane_quality = 0.35
        avg_aadt = 25000.0
        avg_speed_limit = 60.0
        high_crash_segment_count = 2

    return {
        "distance_km": round(distance_km, 2),
        "safe_lane_pct": safe_lane_pct,
        "bike_lane_quality": bike_lane_quality,
        "gap_count": build_mock_gap_count(distance_km),
        "avg_aadt": avg_aadt,
        "avg_speed_limit": avg_speed_limit,
        "high_crash_segment_count": high_crash_segment_count,
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


def calculate_bike_lane_quality(route_context: RouteContext) -> float:
    lane_count = route_context["lane_count"]
    if lane_count <= 0:
        return 0.0

    weighted_total = (
        (route_context["protected_lane_count"] * LANE_TYPE_SCORES["protected"])
        + (route_context["shared_path_lane_count"] * LANE_TYPE_SCORES["shared_path"])
        + (route_context["painted_lane_count"] * LANE_TYPE_SCORES["painted"])
        + (route_context["informal_lane_count"] * LANE_TYPE_SCORES["informal"])
    )
    return round(weighted_total / lane_count, 3)


def calculate_route_score(features: FeasibilityFeatures) -> dict[str, Any]:
    return compute_safety_score(
        bike_lane_quality=features["bike_lane_quality"],
        avg_aadt=features["avg_aadt"],
        avg_speed_zone=features["avg_speed_limit"],
        distance_km=features["distance_km"],
        gap_count=features["gap_count"],
        high_crash_segment_count=features["high_crash_segment_count"],
    )


def build_warning_message(
    features: FeasibilityFeatures,
    score_result: dict[str, Any],
) -> str | None:
    score = int(round(float(score_result["score"])))

    if features["gap_count"] >= 3:
        return "Multiple cycling lane gaps were detected on this route."
    if features["high_crash_segment_count"] >= 2:
        return "This route includes several road segments with elevated crash history."
    if features["avg_speed_limit"] is not None and features["avg_speed_limit"] >= 70:
        return "High-speed road conditions may reduce cycling safety on this route."
    if score < 50:
        return (
            f"Route safety is currently low ({score}/100). "
            "Please review the route carefully before riding."
        )
    return None


def build_explanations(
    features: FeasibilityFeatures,
    score_result: dict[str, Any],
) -> list[FeasibilityExplanation]:
    messages: list[tuple[str, str]] = []

    if features["safe_lane_pct"] >= 45:
        messages.append(
            (
                f"Protected or shared-path infrastructure covers {features['safe_lane_pct']}% of matched cycling lanes.",
                "Low",
            )
        )
    elif features["safe_lane_pct"] <= 20:
        messages.append(
            (
                f"Protected or shared-path coverage is limited at {features['safe_lane_pct']}% of matched cycling lanes.",
                "High",
            )
        )

    if features["gap_count"] > 0:
        messages.append(
            (
                f"This route has {features['gap_count']} detected cycling gap segment(s).",
                "High" if features["gap_count"] >= 2 else "Medium",
            )
        )

    if features["avg_aadt"] is not None:
        if features["avg_aadt"] >= 20000:
            messages.append(
                ("Average nearby traffic volume is high along this route.", "High")
            )
        elif features["avg_aadt"] >= 10000:
            messages.append(
                ("Average nearby traffic volume is moderate along this route.", "Medium")
            )

    if features["avg_speed_limit"] is not None:
        if features["avg_speed_limit"] >= 70:
            messages.append(
                (
                    f"Average nearby speed limits are high at {features['avg_speed_limit']} km/h.",
                    "High",
                )
            )
        elif features["avg_speed_limit"] >= 60:
            messages.append(
                (
                    f"Some nearby road segments have relatively high speed limits around {features['avg_speed_limit']} km/h.",
                    "Medium",
                )
            )

    if features["high_crash_segment_count"] > 0:
        messages.append(
            (
                (
                    f"{features['high_crash_segment_count']} segment(s) on this route have "
                    f"crash counts of {HIGH_CRASH_SEGMENT_THRESHOLD} or more."
                ),
                "High",
            )
        )

    if features["distance_km"] > 12:
        messages.append(
            (
                f"The route distance is {features['distance_km']} km, which may reduce practicality for casual riders.",
                "Medium",
            )
        )

    if not messages:
        messages.append(
            (
                f"The route is rated as {str(score_result.get('risk_label', 'Moderate Risk')).lower()}.",
                "Low",
            )
        )

    explanations: list[FeasibilityExplanation] = []
    seen: set[str] = set()
    for message, impact in messages:
        if message in seen:
            continue
        seen.add(message)
        explanations.append(FeasibilityExplanation(factor=message, impact=impact))
        if len(explanations) >= 4:
            break
    return explanations


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
    return "Medium"
