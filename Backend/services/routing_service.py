import json
import logging
import os
from time import perf_counter
from urllib.error import URLError
from urllib.request import urlopen

try:
    from Backend.database import fetch_all, fetch_one, fetch_scalar
    from Backend.schemas import (
        HeatmapZone,
        RouteSegment,
        RoutingAlert,
        RoutingRequest,
        RoutingResponse,
    )
except ModuleNotFoundError:
    from database import fetch_all, fetch_one, fetch_scalar
    from schemas import (
        HeatmapZone,
        RouteSegment,
        RoutingAlert,
        RoutingRequest,
        RoutingResponse,
    )


OSRM_BASE_URL = os.getenv("RIDESMART_OSRM_URL", "https://router.project-osrm.org")
OSRM_PRIMARY_PROFILE = os.getenv("RIDESMART_OSRM_PROFILE", "bike")
OSRM_FALLBACK_PROFILE = os.getenv("RIDESMART_OSRM_FALLBACK_PROFILE", "driving")
OSRM_TIMEOUT_SECONDS = float(os.getenv("RIDESMART_OSRM_TIMEOUT", "6"))
logger = logging.getLogger(__name__)


def recommend_route(request: RoutingRequest) -> RoutingResponse:
    total_start = perf_counter()

    osrm_start = perf_counter()
    route_points = fetch_osrm_route_points(request)
    logger.info("routing.osrm_lookup_ms=%.1f", (perf_counter() - osrm_start) * 1000)

    if route_points:
        build_start = perf_counter()
        segments = build_route_segments(route_points)
        logger.info(
            "routing.segment_build_from_osrm_ms=%.1f",
            (perf_counter() - build_start) * 1000,
        )
    else:
        db_start = perf_counter()
        segments = fetch_route_segments_from_db(request)
        logger.info(
            "routing.db_route_lookup_ms=%.1f",
            (perf_counter() - db_start) * 1000,
        )
        if not segments:
            fallback_start = perf_counter()
            route_points = interpolate_route_points(request)
            segments = build_route_segments(route_points)
            logger.info(
                "routing.fallback_route_build_ms=%.1f",
                (perf_counter() - fallback_start) * 1000,
            )

    try:
        alerts_start = perf_counter()
        alerts = build_route_alerts(segments)
        logger.info(
            "routing.alerts_build_ms=%.1f",
            (perf_counter() - alerts_start) * 1000,
        )
        alerts_status_message = None
    except Exception:
        alerts = []
        alerts_status_message = (
            "Safety alerts are temporarily unavailable. Please review route colors carefully."
        )

    try:
        heatmap_start = perf_counter()
        heatmap_zones = build_heatmap_zones(segments)
        logger.info(
            "routing.heatmap_build_ms=%.1f",
            (perf_counter() - heatmap_start) * 1000,
        )
        heatmap_status_message = None
    except Exception:
        heatmap_zones = []
        heatmap_status_message = (
            "Safety heatmap is temporarily unavailable. Please rely on route segment colors."
        )

    logger.info(
        "routing.total_ms=%.1f segments=%d alerts=%d heatmap_zones=%d",
        (perf_counter() - total_start) * 1000,
        len(segments),
        len(alerts),
        len(heatmap_zones),
    )

    return RoutingResponse(
        route_segments=segments,
        alerts=alerts,
        alerts_status_message=alerts_status_message,
        heatmap_zones=heatmap_zones,
        heatmap_status_message=heatmap_status_message,
    )


def fetch_osrm_route_points(request: RoutingRequest) -> list[tuple[float, float]]:
    route_points = request_osrm_route(request, OSRM_PRIMARY_PROFILE)
    if route_points:
        return route_points
    if OSRM_FALLBACK_PROFILE == OSRM_PRIMARY_PROFILE:
        return []
    return request_osrm_route(request, OSRM_FALLBACK_PROFILE)


def request_osrm_route(
    request: RoutingRequest, profile: str
) -> list[tuple[float, float]]:
    coordinates = (
        f"{request.start_lng},{request.start_lat};{request.end_lng},{request.end_lat}"
    )
    url = (
        f"{OSRM_BASE_URL.rstrip('/')}/route/v1/{profile}/{coordinates}"
        "?overview=full&geometries=geojson&steps=false"
    )

    try:
        with urlopen(url, timeout=OSRM_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError):
        return []

    routes = payload.get("routes", [])
    if not routes:
        return []

    geometry = routes[0].get("geometry", {})
    coordinates_data = geometry.get("coordinates", [])
    route_points = [
        (float(coordinate[1]), float(coordinate[0]))
        for coordinate in coordinates_data
        if len(coordinate) >= 2
    ]
    return compress_route_points(route_points)


def compress_route_points(
    route_points: list[tuple[float, float]], max_points: int = 12
) -> list[tuple[float, float]]:
    if len(route_points) <= max_points:
        return route_points

    compressed = [route_points[0]]
    for index in range(1, max_points - 1):
        source_index = round(index * (len(route_points) - 1) / (max_points - 1))
        compressed.append(route_points[source_index])
    compressed.append(route_points[-1])
    return compressed


def has_routing_data() -> bool:
    query = "SELECT COUNT(*) > 0 FROM ridesmart.road_segment"
    try:
        return bool(fetch_scalar(query))
    except Exception:
        return False


def fetch_route_segments_from_db(request: RoutingRequest) -> list[RouteSegment]:
    if not has_routing_data():
        return []

    query = """
        WITH route_line AS (
            SELECT ST_SetSRID(
                ST_MakeLine(
                    ST_MakePoint(:start_lng, :start_lat),
                    ST_MakePoint(:end_lng, :end_lat)
                ),
                4326
            ) AS geom
        )
        SELECT
            rs.segment_id::text AS segment_id,
            COALESCE(rs.danger_score, 0) AS danger_score,
            ST_Y(ST_StartPoint(rs.geom)) AS start_lat,
            ST_X(ST_StartPoint(rs.geom)) AS start_lng,
            ST_Y(ST_EndPoint(rs.geom)) AS end_lat,
            ST_X(ST_EndPoint(rs.geom)) AS end_lng,
            EXISTS (
                SELECT 1
                FROM ridesmart.cycling_lane cl
                WHERE ST_DWithin(cl.geom::geography, rs.geom::geography, 40)
                  AND COALESCE(cl.is_continuous, false) = false
            ) AS has_gap
        FROM ridesmart.road_segment rs, route_line r
        WHERE ST_DWithin(rs.geom::geography, r.geom::geography, 150)
        ORDER BY ST_Distance(
            ST_StartPoint(rs.geom)::geography,
            ST_StartPoint(r.geom)::geography
        )
        LIMIT 8
    """

    try:
        rows = fetch_all(
            query,
            {
                "start_lat": request.start_lat,
                "start_lng": request.start_lng,
                "end_lat": request.end_lat,
                "end_lng": request.end_lng,
            },
        )
    except Exception:
        return []

    segments: list[RouteSegment] = []
    for row in rows:
        is_gap = bool(row["has_gap"])
        segments.append(
            RouteSegment(
                coordinates=[
                    [round(row["start_lat"], 6), round(row["start_lng"], 6)],
                    [round(row["end_lat"], 6), round(row["end_lng"], 6)],
                ],
                risk_level=segment_risk_level(
                    risk_level_from_danger_score(float(row["danger_score"])),
                    is_gap,
                ),
                is_gap=is_gap,
            )
        )
    return segments


def interpolate_route_points(request: RoutingRequest) -> list[tuple[float, float]]:
    # This is only the final fallback when OSRM and database-backed routing are unavailable.
    return [
        (request.start_lat, request.start_lng),
        (
            request.start_lat + (request.end_lat - request.start_lat) * 0.33,
            request.start_lng + (request.end_lng - request.start_lng) * 0.33,
        ),
        (
            request.start_lat + (request.end_lat - request.start_lat) * 0.66,
            request.start_lng + (request.end_lng - request.start_lng) * 0.66,
        ),
        (request.end_lat, request.end_lng),
    ]


def build_route_segments(route_points: list[tuple[float, float]]) -> list[RouteSegment]:
    segments: list[RouteSegment] = []
    for index in range(len(route_points) - 1):
        start = route_points[index]
        end = route_points[index + 1]
        estimated_risk_level = estimate_segment_risk(start, end, index)
        is_gap = detect_gap(start, end, index, estimated_risk_level)
        segments.append(
            RouteSegment(
                coordinates=[
                    [round(start[0], 6), round(start[1], 6)],
                    [round(end[0], 6), round(end[1], 6)],
                ],
                risk_level=segment_risk_level(estimated_risk_level, is_gap),
                is_gap=is_gap,
            )
        )
    return segments


def estimate_segment_risk(
    start: tuple[float, float], end: tuple[float, float], segment_index: int
) -> str:
    db_risk_level = fetch_segment_risk_from_db(start, end)
    if db_risk_level:
        return db_risk_level

    # Simple fallback pattern when nearby segment data is missing.
    if segment_index == 1:
        return "Red"
    if segment_index == 0:
        return "Yellow"
    return "Green"


def fetch_segment_risk_from_db(
    start: tuple[float, float], end: tuple[float, float]
) -> str | None:
    if not has_routing_data():
        return None

    query = """
        WITH candidate_segment AS (
            SELECT ST_SetSRID(
                ST_MakeLine(
                    ST_MakePoint(:start_lng, :start_lat),
                    ST_MakePoint(:end_lng, :end_lat)
                ),
                4326
            ) AS geom
        )
        SELECT AVG(COALESCE(rs.danger_score, 0)) AS average_danger_score
        FROM ridesmart.road_segment rs, candidate_segment c
        WHERE ST_DWithin(rs.geom::geography, c.geom::geography, 60)
    """

    row = fetch_one_safe(
        query,
        {
            "start_lat": start[0],
            "start_lng": start[1],
            "end_lat": end[0],
            "end_lng": end[1],
        },
    )
    if not row or row["average_danger_score"] is None:
        return None
    return risk_level_from_danger_score(float(row["average_danger_score"]))


def detect_gap(
    start: tuple[float, float],
    end: tuple[float, float],
    segment_index: int,
    risk_level: str,
) -> bool:
    gap_flag = fetch_gap_flag_from_db(start, end)
    if gap_flag is not None:
        return gap_flag

    # Only flag a clear gap candidate when no database evidence is available.
    return segment_index == 1 and risk_level == "Red"


def fetch_gap_flag_from_db(start: tuple[float, float], end: tuple[float, float]) -> bool | None:
    if not has_routing_data():
        return None

    query = """
        WITH candidate_segment AS (
            SELECT ST_SetSRID(
                ST_MakeLine(
                    ST_MakePoint(:start_lng, :start_lat),
                    ST_MakePoint(:end_lng, :end_lat)
                ),
                4326
            ) AS geom
        )
        SELECT
            COUNT(*) FILTER (
                WHERE COALESCE(cl.is_continuous, false) = false
            ) AS broken_lane_count,
            COUNT(*) AS matched_lane_count
        FROM ridesmart.cycling_lane cl, candidate_segment c
        WHERE ST_DWithin(cl.geom::geography, c.geom::geography, 40)
    """

    row = fetch_one_safe(
        query,
        {
            "start_lat": start[0],
            "start_lng": start[1],
            "end_lat": end[0],
            "end_lng": end[1],
        },
    )
    if not row or row["matched_lane_count"] == 0:
        return None
    return int(row["broken_lane_count"]) > 0


def fetch_one_safe(query: str, params: dict[str, float]) -> dict | None:
    try:
        return fetch_one(query, params)
    except Exception:
        return None


def segment_risk_level(base_risk_level: str, is_gap: bool) -> str:
    # Any route segment near a non-continuous bike lane should stand out clearly.
    if is_gap:
        return "Red"
    return base_risk_level


def risk_level_from_danger_score(danger_score: float) -> str:
    if danger_score >= 70:
        return "Red"
    if danger_score >= 40:
        return "Yellow"
    return "Green"


def build_route_alerts(segments: list[RouteSegment]) -> list[RoutingAlert]:
    alerts: list[RoutingAlert] = []
    for segment in segments:
        if segment.is_gap:
            alerts.append(
                RoutingAlert(
                    location=alert_position_before_segment(segment.coordinates),
                    level="Red",
                    message="Disconnected bike lane detected ahead. Prepare to slow down or reroute.",
                )
            )
            continue

        if segment.risk_level == "Red":
            alerts.append(
                RoutingAlert(
                    location=alert_position_before_segment(segment.coordinates),
                    level="Red",
                    message="High-risk segment ahead. Use caution before entering this section.",
                )
            )
            continue

        if segment.risk_level == "Yellow":
            alerts.append(
                RoutingAlert(
                    location=alert_position_before_segment(segment.coordinates),
                    level="Yellow",
                    message="Moderate-risk segment ahead. Stay alert and prepare for changing conditions.",
                )
            )
    return alerts


def alert_position_before_segment(coordinates: list[list[float]]) -> list[float]:
    start, end = coordinates
    return [
        round(start[0] + (end[0] - start[0]) * 0.2, 6),
        round(start[1] + (end[1] - start[1]) * 0.2, 6),
    ]


def build_heatmap_zones(segments: list[RouteSegment]) -> list[HeatmapZone]:
    zones = [zone_from_segment(segment) for segment in segments]
    if not zones:
        raise ValueError("No risk data available for heatmap rendering.")
    return merge_overlapping_zones(zones)


def zone_from_segment(segment: RouteSegment) -> HeatmapZone:
    center = midpoint_from_segment(segment.coordinates)
    radius_m = radius_from_risk(segment.risk_level)
    intensity = intensity_from_risk(segment.risk_level, segment.is_gap)
    return HeatmapZone(
        center=center,
        radius_m=radius_m,
        risk_level=segment.risk_level,
        intensity=intensity,
    )


def midpoint_from_segment(coordinates: list[list[float]]) -> list[float]:
    start, end = coordinates
    return [
        round((start[0] + end[0]) / 2, 6),
        round((start[1] + end[1]) / 2, 6),
    ]


def radius_from_risk(risk_level: str) -> int:
    if risk_level == "Red":
        return 180
    if risk_level == "Yellow":
        return 140
    return 100


def intensity_from_risk(risk_level: str, is_gap: bool) -> int:
    if is_gap:
        return 100
    if risk_level == "Red":
        return 90
    if risk_level == "Yellow":
        return 60
    return 30


def merge_overlapping_zones(zones: list[HeatmapZone]) -> list[HeatmapZone]:
    merged: dict[tuple[float, float], HeatmapZone] = {}
    for zone in zones:
        key = (zone.center[0], zone.center[1])
        existing = merged.get(key)
        if existing is None or zone_priority(zone) > zone_priority(existing):
            merged[key] = zone
    return list(merged.values())


def zone_priority(zone: HeatmapZone) -> tuple[int, int]:
    risk_rank = {"Green": 0, "Yellow": 1, "Red": 2}
    return (risk_rank[zone.risk_level], zone.intensity)
