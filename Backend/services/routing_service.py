import json
import logging
import os
from math import cos, radians
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from Backend.database import fetch_all, fetch_scalar
    from Backend.schemas import (
        HeatmapZone,
        RouteSegment,
        RoutingAlert,
        RoutingRequest,
        RoutingResponse,
    )
except ModuleNotFoundError:
    from database import fetch_all, fetch_scalar
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
OSRM_TIMEOUT_SECONDS = float(os.getenv("RIDESMART_OSRM_TIMEOUT", "8"))
USE_OSRM_ROUTING = os.getenv("RIDESMART_USE_OSRM", "false").lower() == "true"
MAPBOX_BASE_URL = os.getenv("RIDESMART_MAPBOX_URL", "https://api.mapbox.com")
MAPBOX_PROFILE = os.getenv("RIDESMART_MAPBOX_PROFILE", "mapbox/cycling")
MAPBOX_ACCESS_TOKEN = (
    os.getenv("RIDESMART_MAPBOX_ACCESS_TOKEN")
    or os.getenv("MAPBOX_ACCESS_TOKEN")
    or os.getenv("VITE_MAPBOX_ACCESS_TOKEN")
    or ""
)
MAPBOX_TIMEOUT_SECONDS = float(os.getenv("RIDESMART_MAPBOX_TIMEOUT", "8"))
USE_MAPBOX_ROUTING = os.getenv("RIDESMART_USE_MAPBOX", "true").lower() == "true"
ORS_BASE_URL = os.getenv("RIDESMART_ORS_URL", "https://api.openrouteservice.org")
ORS_PROFILE = os.getenv("RIDESMART_ORS_PROFILE", "cycling-regular")
ORS_API_KEY = os.getenv("RIDESMART_ORS_API_KEY", "")
ORS_TIMEOUT_SECONDS = float(os.getenv("RIDESMART_ORS_TIMEOUT", "12"))
USE_ORS_ROUTING = os.getenv("RIDESMART_USE_ORS", "false").lower() == "true"
logger = logging.getLogger("uvicorn.error")
ROUTING_DEBUG_SIGNATURE = "routing-signature-2026-04-28-v1"


def recommend_route(request: RoutingRequest) -> RoutingResponse:
    total_start = perf_counter()
    logger.warning("routing.started")

    external_start = perf_counter()
    route_points = fetch_external_route_points(request)
    logger.warning(
        "routing.external_lookup_ms=%.1f", (perf_counter() - external_start) * 1000
    )

    if route_points:
        build_start = perf_counter()
        segments = build_route_segments(route_points)
        logger.warning(
            "routing.segment_build_from_external_ms=%.1f",
            (perf_counter() - build_start) * 1000,
        )
    else:
        db_start = perf_counter()
        segments = fetch_route_segments_from_db(request)
        logger.warning(
            "routing.db_route_lookup_ms=%.1f",
            (perf_counter() - db_start) * 1000,
        )
        if not segments:
            fallback_start = perf_counter()
            route_points = interpolate_route_points(request)
            segments = build_route_segments(route_points)
            logger.warning(
                "routing.fallback_route_build_ms=%.1f",
                (perf_counter() - fallback_start) * 1000,
            )

    try:
        alerts_start = perf_counter()
        alerts = build_route_alerts(segments)
        logger.warning(
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
        logger.warning(
            "routing.heatmap_build_ms=%.1f",
            (perf_counter() - heatmap_start) * 1000,
        )
        heatmap_status_message = None
    except Exception:
        heatmap_zones = []
        heatmap_status_message = (
            "Safety heatmap is temporarily unavailable. Please rely on route segment colors."
        )

    logger.warning(
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
        debug_signature=ROUTING_DEBUG_SIGNATURE,
    )


def calculate_gap_segment_count_for_request(request: RoutingRequest) -> int:
    segments = build_route_segments_for_request(request)
    return sum(1 for segment in segments if segment.is_gap)


def build_route_segments_for_request(request: RoutingRequest) -> list[RouteSegment]:
    route_points = fetch_external_route_points(request)
    if route_points:
        return build_route_segments(route_points)

    segments = fetch_route_segments_from_db(request)
    if segments:
        return segments

    return build_route_segments(interpolate_route_points(request))


def fetch_external_route_points(request: RoutingRequest) -> list[tuple[float, float]]:
    route_points = fetch_mapbox_route_points(request)
    if route_points:
        return route_points

    route_points = fetch_osrm_route_points(request)
    if route_points:
        return route_points
    return fetch_ors_route_points(request)


def fetch_mapbox_route_points(request: RoutingRequest) -> list[tuple[float, float]]:
    if not USE_MAPBOX_ROUTING:
        logger.warning("routing.mapbox_disabled=true")
        return []
    if not MAPBOX_ACCESS_TOKEN:
        logger.warning("routing.mapbox_missing_access_token=true")
        return []

    route_points = request_mapbox_route(request, MAPBOX_PROFILE)
    if route_points:
        logger.warning("routing.external_provider=mapbox profile=%s", MAPBOX_PROFILE)
    return route_points


def request_mapbox_route(
    request: RoutingRequest, profile: str
) -> list[tuple[float, float]]:
    coordinates = (
        f"{request.start_lng},{request.start_lat};{request.end_lng},{request.end_lat}"
    )
    query = urlencode(
        {
            "access_token": MAPBOX_ACCESS_TOKEN,
            "geometries": "geojson",
            "overview": "full",
            "steps": "false",
        }
    )
    url = f"{MAPBOX_BASE_URL.rstrip('/')}/directions/v5/{profile}/{coordinates}?{query}"

    try:
        with urlopen(url, timeout=MAPBOX_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.warning("routing.mapbox_http_error_code=%s", exc.code)
        return []
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


def fetch_osrm_route_points(request: RoutingRequest) -> list[tuple[float, float]]:
    if not USE_OSRM_ROUTING:
        logger.warning("routing.osrm_disabled=true")
        return []

    route_points = request_osrm_route(request, OSRM_PRIMARY_PROFILE)
    if route_points:
        logger.warning("routing.external_provider=osrm profile=%s", OSRM_PRIMARY_PROFILE)
        return route_points

    if OSRM_FALLBACK_PROFILE == OSRM_PRIMARY_PROFILE:
        return []

    route_points = request_osrm_route(request, OSRM_FALLBACK_PROFILE)
    if route_points:
        logger.warning("routing.external_provider=osrm profile=%s", OSRM_FALLBACK_PROFILE)
    return route_points


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


def fetch_ors_route_points(request: RoutingRequest) -> list[tuple[float, float]]:
    if not USE_ORS_ROUTING:
        logger.warning("routing.ors_disabled=true")
        return []
    if not ORS_API_KEY:
        logger.warning("routing.ors_missing_api_key=true")
        return []
    logger.warning("routing.external_provider=ors profile=%s", ORS_PROFILE)
    return request_ors_route(request, ORS_PROFILE)


def request_ors_route(
    request: RoutingRequest, profile: str
) -> list[tuple[float, float]]:
    url = f"{ORS_BASE_URL.rstrip('/')}/v2/directions/{profile}/geojson"
    post_body = {
        "coordinates": [
            [request.start_lng, request.start_lat],
            [request.end_lng, request.end_lat],
        ]
    }
    request_bytes = json.dumps(post_body).encode("utf-8")
    ors_request = Request(
        url=url,
        data=request_bytes,
        headers={
            "Authorization": ORS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json, application/geo+json",
        },
        method="POST",
    )

    try:
        with urlopen(ors_request, timeout=ORS_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.warning("routing.ors_http_error_code=%s", exc.code)
        return []
    except (URLError, TimeoutError, ValueError):
        return []

    features = payload.get("features", [])
    if not features:
        return []

    geometry = features[0].get("geometry", {})
    coordinates_data = geometry.get("coordinates", [])
    route_points = [
        (float(coordinate[1]), float(coordinate[0]))
        for coordinate in coordinates_data
        if len(coordinate) >= 2
    ]
    return compress_route_points(route_points)


def compress_route_points(
    route_points: list[tuple[float, float]], max_points: int = 60
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


def has_cycling_lane_data() -> bool:
    query = "SELECT COUNT(*) > 0 FROM ridesmart.cycling_lane"
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
            ST_Y(ST_StartPoint(rs.geom)) AS start_lat,
            ST_X(ST_StartPoint(rs.geom)) AS start_lng,
            ST_Y(ST_EndPoint(rs.geom)) AS end_lat,
            ST_X(ST_EndPoint(rs.geom)) AS end_lng,
            EXISTS (
                SELECT 1
                FROM ridesmart.cycling_lane cl
                WHERE ST_DWithin(cl.geom::geography, rs.geom::geography, 50)
                  AND cl.lane_type = 'protected'
            )
            AND EXISTS (
                SELECT 1
                FROM ridesmart.cycling_lane cl
                WHERE ST_DWithin(cl.geom::geography, rs.geom::geography, 50)
                  AND cl.lane_type = 'informal'
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
                risk_level=segment_risk_level(is_gap),
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
    lane_type_geometries = fetch_lane_type_geometries_near_route(route_points)
    segments: list[RouteSegment] = []
    for index in range(len(route_points) - 1):
        start = route_points[index]
        end = route_points[index + 1]
        is_gap = detect_gap(index, start, end, lane_type_geometries)
        segments.append(
            RouteSegment(
                coordinates=[
                    [round(start[0], 6), round(start[1], 6)],
                    [round(end[0], 6), round(end[1], 6)],
                ],
                risk_level=segment_risk_level(is_gap),
                is_gap=is_gap,
            )
        )
    return segments


def fetch_lane_type_geometries_near_route(
    route_points: list[tuple[float, float]]
) -> dict[str, list[list[tuple[float, float]]]]:
    if not has_cycling_lane_data() or len(route_points) < 2:
        return {"high_quality": [], "informal": []}

    route_coordinates = ",".join(
        f"{lng} {lat}" for lat, lng in route_points
    )

    query = """
        WITH route_line AS (
            SELECT ST_SetSRID(
                ST_GeomFromText(:route_wkt),
                4326
            ) AS geom
        )
        SELECT
            cl.lane_type::text AS lane_type,
            ST_AsGeoJSON(cl.geom) AS geom_json
        FROM ridesmart.cycling_lane cl, route_line r
        WHERE cl.lane_type IN ('protected', 'shared_path', 'informal')
          AND ST_DWithin(cl.geom::geography, r.geom::geography, 120)
    """

    try:
        rows = fetch_all(query, {"route_wkt": f"LINESTRING({route_coordinates})"})
    except Exception:
        return {"high_quality": [], "informal": []}

    lane_geometries = {"high_quality": [], "informal": []}
    for row in rows:
        lane_type = str(row.get("lane_type", "")).strip().lower()
        if lane_type in {"protected", "shared_path"}:
            target_group = "high_quality"
        elif lane_type == "informal":
            target_group = "informal"
        else:
            continue
        geom_json = row.get("geom_json")
        if not geom_json:
            continue
        try:
            geometry = json.loads(geom_json)
        except ValueError:
            continue
        coordinates = geometry.get("coordinates", [])
        lane_points = [
            (float(point[1]), float(point[0]))
            for point in coordinates
            if len(point) >= 2
        ]
        if lane_points:
            lane_geometries[target_group].append(lane_points)
    return lane_geometries


def detect_gap(
    segment_index: int,
    start: tuple[float, float],
    end: tuple[float, float],
    lane_type_geometries: dict[str, list[list[tuple[float, float]]]],
) -> bool:
    protected_lanes = lane_type_geometries.get("high_quality", [])
    informal_lanes = lane_type_geometries.get("informal", [])
    if not protected_lanes or not informal_lanes:
        return False

    sampled_points = sample_segment_points(start, end)
    for segment_point in sampled_points:
        near_protected = any(
            polyline_is_near_point(lane_geometry, segment_point, threshold_m=35)
            for lane_geometry in protected_lanes
        )
        if not near_protected:
            continue

        if any(
            polyline_is_near_point(lane_geometry, segment_point, threshold_m=35)
            for lane_geometry in informal_lanes
        ):
            return True
    return False


def sample_segment_points(
    start: tuple[float, float], end: tuple[float, float]
) -> list[tuple[float, float]]:
    segment_length_m = max(1.0, distance_m(start, end))
    sample_count = max(3, min(25, int(segment_length_m // 20) + 2))
    return [
        (
            start[0] + (end[0] - start[0]) * (index / (sample_count - 1)),
            start[1] + (end[1] - start[1]) * (index / (sample_count - 1)),
        )
        for index in range(sample_count)
    ]


def polyline_is_near_point(
    polyline: list[tuple[float, float]],
    point: tuple[float, float],
    threshold_m: float,
) -> bool:
    if not polyline:
        return False

    for polyline_point in polyline:
        if distance_m(point, polyline_point) <= threshold_m:
            return True
    return False


def distance_m(
    point_a: tuple[float, float],
    point_b: tuple[float, float],
) -> float:
    average_latitude = (point_a[0] + point_b[0]) / 2
    lat_scale = 111_320.0
    lng_scale = 111_320.0 * max(0.1, abs(cos(radians(average_latitude))))

    delta_lat_m = (point_a[0] - point_b[0]) * lat_scale
    delta_lng_m = (point_a[1] - point_b[1]) * lng_scale
    return (delta_lat_m**2 + delta_lng_m**2) ** 0.5


def segment_risk_level(is_gap: bool) -> str:
    # Routing now focuses on lane continuity only: gap segments are red, others stay green.
    if is_gap:
        return "Red"
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
