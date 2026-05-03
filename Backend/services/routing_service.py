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
        RouteSegment,
        RoutingAlert,
        RoutingOption,
        RoutingRequest,
        RoutingResponse,
    )
    from Backend.services.feasibility_service import evaluate_feasibility_for_route_points
except ModuleNotFoundError:
    from database import fetch_all, fetch_scalar
    from schemas import (
        RouteSegment,
        RoutingAlert,
        RoutingOption,
        RoutingRequest,
        RoutingResponse,
    )
    from services.feasibility_service import evaluate_feasibility_for_route_points


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
ROUTE_ANALYSIS_MAX_POINTS = 35
GAP_POINT_THRESHOLD_M = 17.5
MIN_CONSECUTIVE_GAP_HITS = 1
GAP_SEGMENT_COOLDOWN_M = 80


class RoutingGenerationError(Exception):
    pass


def build_route_lookup_result(
    routes: list[dict] | None = None,
) -> dict:
    return {
        "routes": routes or [],
    }


def route_label(route_index: int) -> str:
    if route_index == 0:
        return "Recommended"
    return f"Alternative {route_index}"


def calculate_route_safety_score(
    route_segments: list[RouteSegment],
    gap_segments: list[RouteSegment],
    alerts: list[RoutingAlert],
) -> int:
    total_segments = max(1, len(route_segments))
    gap_count = len(gap_segments)
    gap_ratio = gap_count / total_segments
    gap_penalty = gap_ratio * 70
    count_penalty = min(gap_count * 8, 24)
    alert_penalty = min(len(alerts) * 2, 6)
    raw_score = 100 - gap_penalty - count_penalty - alert_penalty
    return max(0, min(100, round(raw_score)))


def assign_route_option_labels(route_options: list[RoutingOption]) -> None:
    if not route_options:
        return

    if len(route_options) == 1:
        route_options[0].label = "Recommended"
        return

    fastest_index = min(
        range(len(route_options)),
        key=lambda index: (
            route_options[index].duration_min
            if route_options[index].duration_min is not None
            else float("inf"),
            route_options[index].distance_km
            if route_options[index].distance_km is not None
            else float("inf"),
            index,
        ),
    )

    safest_index = max(
        range(len(route_options)),
        key=lambda index: (
            route_options[index].score
            if route_options[index].score is not None
            else -1,
            -(
                route_options[index].duration_min
                if route_options[index].duration_min is not None
                else float("inf")
            ),
            -(
                route_options[index].distance_km
                if route_options[index].distance_km is not None
                else float("inf")
            ),
        ),
    )
    if fastest_index == safest_index:
        route_options[fastest_index].label = "Safest & Fastest"
        for index in range(len(route_options)):
            if index != fastest_index:
                route_options[index].label = "Not Recommended"
        return

    route_options[fastest_index].label = "Fastest"
    route_options[safest_index].label = "Safest"

    remaining_indices = [
        index for index in range(len(route_options))
        if index not in {fastest_index, safest_index}
    ]
    if len(remaining_indices) == 1:
        route_options[remaining_indices[0]].label = "Balanced"
        return

    for index in remaining_indices:
        route_options[index].label = "Balanced"


def recommend_route(request: RoutingRequest) -> RoutingResponse:
    total_start = perf_counter()
    logger.warning("routing.started")

    external_start = perf_counter()
    external_route = fetch_external_route_data(request)
    external_routes = external_route["routes"]
    logger.warning("routing.external_route_count=%d", len(external_routes))
    logger.warning(
        "routing.external_lookup_ms=%.1f", (perf_counter() - external_start) * 1000
    )

    route_options: list[RoutingOption] = []
    route_geometry = None
    route_segments: list[RouteSegment] = []
    gap_segments: list[RouteSegment] = []
    alerts: list[RoutingAlert] = []
    distance_km = None
    duration_min = None
    alerts_status_message = None
    score = None
    is_supported_area = True
    warning_message = None
    explanations = []

    if external_routes:
        build_start = perf_counter()
        alerts_start = perf_counter()
        for route_index, route_data in enumerate(external_routes):
            route_build_start = perf_counter()
            try:
                route_points = route_data["route_points"]
                route_distance_km = calculate_route_distance_km(route_points)
                analysis_route_points, source_indices = compress_route_points_with_source_indices(
                    route_points,
                    max_points=ROUTE_ANALYSIS_MAX_POINTS,
                )
                lane_fetch_start = perf_counter()
                lane_type_geometries = fetch_lane_type_geometries_near_route(
                    analysis_route_points
                )
                lane_fetch_ms = (perf_counter() - lane_fetch_start) * 1000

                analysis_segments_start = perf_counter()
                segments = build_route_segments_from_lane_geometries(
                    analysis_route_points,
                    lane_type_geometries=lane_type_geometries,
                )
                analysis_segments_ms = (perf_counter() - analysis_segments_start) * 1000

                gap_segments_start = perf_counter()
                option_gap_segments = build_gap_segments_from_analysis_segments(
                    analysis_segments=segments,
                    full_route_points=route_points,
                    source_indices=source_indices,
                )
                gap_segments_ms = (perf_counter() - gap_segments_start) * 1000

                alerts_only_start = perf_counter()
                option_alerts = build_route_alerts(option_gap_segments)
                alerts_only_ms = (perf_counter() - alerts_only_start) * 1000

                feasibility_start = perf_counter()
                route_feasibility = evaluate_feasibility_for_route_points(
                    route_points,
                    distance_km_override=route_distance_km,
                    gap_count_override=len(option_gap_segments),
                    context_route_points=analysis_route_points,
                )
                feasibility_ms = (perf_counter() - feasibility_start) * 1000
                route_score = route_feasibility.score
                option = RoutingOption(
                    label=route_label(route_index),
                    provider=route_data["provider"],
                    route_geometry=route_points_to_geojson(route_points),
                    route_segments=segments,
                    gap_segments=option_gap_segments,
                    alerts=option_alerts,
                    distance_km=route_distance_km,
                    duration_min=route_data["duration_min"],
                    score=route_score,
                    is_supported_area=route_feasibility.is_supported_area,
                    warning_message=route_feasibility.warning_message,
                    explanations=route_feasibility.explanations,
                )
                route_options.append(option)
                logger.warning(
                    "routing.route_option_built index=%d provider=%s points=%d analysis_points=%d segments=%d gap_segments=%d duration_min=%s score=%s lane_fetch_ms=%.1f analysis_segments_ms=%.1f gap_segments_ms=%.1f alerts_only_ms=%.1f feasibility_ms=%.1f build_ms=%.1f",
                    route_index,
                    route_data["provider"],
                    len(route_points),
                    len(analysis_route_points),
                    len(segments),
                    len(option_gap_segments),
                    str(route_data["duration_min"]),
                    str(route_score),
                    lane_fetch_ms,
                    analysis_segments_ms,
                    gap_segments_ms,
                    alerts_only_ms,
                    feasibility_ms,
                    (perf_counter() - route_build_start) * 1000,
                )
            except Exception as exc:
                logger.exception(
                    "routing.route_option_build_failed index=%d provider=%s error=%s",
                    route_index,
                    route_data.get("provider", "unknown"),
                    exc,
                )

        if route_options:
            assign_route_option_labels(route_options)
            logger.warning(
                "routing.route_options_postprocess_ms=%.1f",
                (perf_counter() - alerts_start) * 1000,
            )

        if route_options:
            primary_option = route_options[0]
            route_geometry = primary_option.route_geometry
            route_segments = primary_option.route_segments
            gap_segments = primary_option.gap_segments
            alerts = primary_option.alerts
            distance_km = primary_option.distance_km
            duration_min = primary_option.duration_min
            score = primary_option.score
            is_supported_area = primary_option.is_supported_area
            warning_message = primary_option.warning_message
            explanations = primary_option.explanations
        else:
            external_routes = []
            logger.warning("routing.external_route_processing_yielded_no_options=true")
        logger.warning(
            "routing.segment_build_from_external_ms=%.1f",
            (perf_counter() - build_start) * 1000,
        )

    external_routing_enabled = (
        USE_MAPBOX_ROUTING or USE_OSRM_ROUTING or USE_ORS_ROUTING
    )
    if external_routing_enabled and not route_options:
        logger.warning("routing.external_routes_unusable_no_db_fallback=true")
        raise RoutingGenerationError(
            "Unable to generate a valid route from the external routing provider."
        )

    if not external_routes and not external_routing_enabled:
        db_start = perf_counter()
        route_segments = fetch_route_segments_from_db(request)
        logger.warning(
            "routing.db_route_lookup_ms=%.1f",
            (perf_counter() - db_start) * 1000,
        )
        if not route_segments:
            fallback_start = perf_counter()
            route_points = interpolate_route_points(request)
            route_segments = build_route_segments(route_points)
            route_geometry = route_points_to_geojson(route_points)
            distance_km = calculate_route_distance_km(route_points)
            logger.warning(
                "routing.fallback_route_build_ms=%.1f",
                (perf_counter() - fallback_start) * 1000,
            )
        else:
            route_geometry = route_geometry_from_segments(route_segments)
            distance_km = calculate_route_distance_from_segments(route_segments)
        gap_segments = [segment for segment in route_segments if segment.is_gap]

        try:
            alerts_start = perf_counter()
            alerts = build_route_alerts(gap_segments)
            logger.warning(
                "routing.alerts_build_ms=%.1f",
                (perf_counter() - alerts_start) * 1000,
            )
        except Exception:
            alerts = []
            alerts_status_message = (
                "Safety alerts are temporarily unavailable. Please review route colors carefully."
            )

        route_options = [
            RoutingOption(
                label="Recommended",
                provider="database-fallback",
                route_geometry=route_geometry,
                route_segments=route_segments,
                gap_segments=gap_segments,
                alerts=alerts,
                distance_km=distance_km,
                duration_min=duration_min,
                score=None,
                is_supported_area=True,
                warning_message=None,
                explanations=[],
            )
        ]

    logger.warning(
        "routing.total_ms=%.1f segments=%d alerts=%d gap_segments=%d route_options=%d",
        (perf_counter() - total_start) * 1000,
        len(route_segments),
        len(alerts),
        len(gap_segments),
        len(route_options),
    )

    return RoutingResponse(
        route_geometry=route_geometry,
        route_segments=route_segments,
        gap_segments=gap_segments,
        alerts=alerts,
        alerts_status_message=alerts_status_message,
        distance_km=distance_km,
        duration_min=duration_min,
        route_options=route_options,
        score=score,
        is_supported_area=is_supported_area,
        warning_message=warning_message,
        explanations=explanations,
        debug_signature=ROUTING_DEBUG_SIGNATURE,
    )


def calculate_gap_segment_count_for_request(request: RoutingRequest) -> int:
    segments = build_route_segments_for_request(request)
    return sum(1 for segment in segments if segment.is_gap)


def build_route_segments_for_request(request: RoutingRequest) -> list[RouteSegment]:
    external_routes = fetch_external_route_data(request)["routes"]
    if external_routes:
        route_points = external_routes[0]["route_points"]
        analysis_route_points, _ = compress_route_points_with_source_indices(
            route_points,
            max_points=ROUTE_ANALYSIS_MAX_POINTS,
        )
        return build_route_segments(analysis_route_points)

    segments = fetch_route_segments_from_db(request)
    if segments:
        return segments

    return build_route_segments(interpolate_route_points(request))


def fetch_external_route_data(request: RoutingRequest) -> dict:
    route_data = fetch_mapbox_route_data(request)
    if route_data["routes"]:
        return route_data

    route_data = fetch_osrm_route_data(request)
    if route_data["routes"]:
        return route_data
    return fetch_ors_route_data(request)


def fetch_mapbox_route_data(request: RoutingRequest) -> dict:
    if not USE_MAPBOX_ROUTING:
        logger.warning("routing.mapbox_disabled=true")
        return build_route_lookup_result()
    if not MAPBOX_ACCESS_TOKEN:
        logger.warning("routing.mapbox_missing_access_token=true")
        return build_route_lookup_result()

    route_data = request_mapbox_route(request, MAPBOX_PROFILE)
    if route_data["routes"]:
        logger.warning("routing.external_provider=mapbox profile=%s", MAPBOX_PROFILE)
    else:
        logger.warning("routing.mapbox_returned_no_routes=true")
    return route_data


def request_mapbox_route(
    request: RoutingRequest, profile: str
) -> dict:
    coordinates = (
        f"{request.start_lng},{request.start_lat};{request.end_lng},{request.end_lat}"
    )
    query = urlencode(
        {
            "access_token": MAPBOX_ACCESS_TOKEN,
            "geometries": "geojson",
            "overview": "full",
            "steps": "false",
            "alternatives": "true",
        }
    )
    url = f"{MAPBOX_BASE_URL.rstrip('/')}/directions/v5/{profile}/{coordinates}?{query}"

    try:
        with urlopen(url, timeout=MAPBOX_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.warning("routing.mapbox_http_error_code=%s", exc.code)
        return build_route_lookup_result()
    except (URLError, TimeoutError, ValueError) as exc:
        logger.warning("routing.mapbox_request_failed=%s", exc.__class__.__name__)
        return build_route_lookup_result()

    routes = payload.get("routes", [])
    if not routes:
        return build_route_lookup_result()

    built_routes: list[dict] = []
    for route in routes[:3]:
        geometry = route.get("geometry", {})
        coordinates_data = geometry.get("coordinates", [])
        route_points = [
            (float(coordinate[1]), float(coordinate[0]))
            for coordinate in coordinates_data
            if len(coordinate) >= 2
        ]
        if not route_points:
            continue
        duration_seconds = route.get("duration")
        duration_min = (
            round(float(duration_seconds) / 60, 1)
            if duration_seconds is not None
            else None
        )
        built_routes.append(
            {
                "provider": "mapbox",
                "route_points": route_points,
                "duration_min": duration_min,
            }
        )
    return build_route_lookup_result(routes=built_routes)


def fetch_osrm_route_data(request: RoutingRequest) -> dict:
    if not USE_OSRM_ROUTING:
        logger.warning("routing.osrm_disabled=true")
        return build_route_lookup_result()

    route_data = request_osrm_route(request, OSRM_PRIMARY_PROFILE)
    if route_data["routes"]:
        logger.warning("routing.external_provider=osrm profile=%s", OSRM_PRIMARY_PROFILE)
        return route_data
    logger.warning("routing.osrm_primary_returned_no_routes=true")

    if OSRM_FALLBACK_PROFILE == OSRM_PRIMARY_PROFILE:
        return build_route_lookup_result()

    route_data = request_osrm_route(request, OSRM_FALLBACK_PROFILE)
    if route_data["routes"]:
        logger.warning("routing.external_provider=osrm profile=%s", OSRM_FALLBACK_PROFILE)
    else:
        logger.warning("routing.osrm_fallback_returned_no_routes=true")
    return route_data


def request_osrm_route(
    request: RoutingRequest, profile: str
) -> dict:
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
    except (URLError, TimeoutError, ValueError) as exc:
        logger.warning("routing.osrm_request_failed=%s", exc.__class__.__name__)
        return build_route_lookup_result()

    routes = payload.get("routes", [])
    if not routes:
        return build_route_lookup_result()

    primary_route = routes[0]
    geometry = primary_route.get("geometry", {})
    coordinates_data = geometry.get("coordinates", [])
    route_points = [
        (float(coordinate[1]), float(coordinate[0]))
        for coordinate in coordinates_data
        if len(coordinate) >= 2
    ]
    duration_seconds = primary_route.get("duration")
    duration_min = (
        round(float(duration_seconds) / 60, 1)
        if duration_seconds is not None
        else None
    )
    return build_route_lookup_result(
        routes=[
            {
                "provider": "osrm",
                "route_points": compress_route_points(route_points),
                "duration_min": duration_min,
            }
        ]
    )


def fetch_ors_route_data(request: RoutingRequest) -> dict:
    if not USE_ORS_ROUTING:
        logger.warning("routing.ors_disabled=true")
        return build_route_lookup_result()
    if not ORS_API_KEY:
        logger.warning("routing.ors_missing_api_key=true")
        return build_route_lookup_result()
    logger.warning("routing.external_provider=ors profile=%s", ORS_PROFILE)
    return request_ors_route(request, ORS_PROFILE)


def request_ors_route(
    request: RoutingRequest, profile: str
) -> dict:
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
        return build_route_lookup_result()
    except (URLError, TimeoutError, ValueError) as exc:
        logger.warning("routing.ors_request_failed=%s", exc.__class__.__name__)
        return build_route_lookup_result()

    features = payload.get("features", [])
    if not features:
        return build_route_lookup_result()

    feature = features[0]
    geometry = feature.get("geometry", {})
    coordinates_data = geometry.get("coordinates", [])
    route_points = [
        (float(coordinate[1]), float(coordinate[0]))
        for coordinate in coordinates_data
        if len(coordinate) >= 2
    ]
    summary = feature.get("properties", {}).get("summary", {})
    duration_seconds = summary.get("duration")
    duration_min = (
        round(float(duration_seconds) / 60, 1)
        if duration_seconds is not None
        else None
    )
    return build_route_lookup_result(
        routes=[
            {
                "provider": "ors",
                "route_points": compress_route_points(route_points),
                "duration_min": duration_min,
            }
        ]
    )


def compress_route_points(
    route_points: list[tuple[float, float]], max_points: int = 50
) -> list[tuple[float, float]]:
    compressed_points, _ = compress_route_points_with_source_indices(
        route_points,
        max_points=max_points,
    )
    return compressed_points


def compress_route_points_with_source_indices(
    route_points: list[tuple[float, float]],
    max_points: int = 50,
) -> tuple[list[tuple[float, float]], list[int]]:
    if len(route_points) <= max_points:
        return route_points, list(range(len(route_points)))

    source_indices = [0]
    for index in range(1, max_points - 1):
        source_index = round(index * (len(route_points) - 1) / (max_points - 1))
        source_indices.append(source_index)
    source_indices.append(len(route_points) - 1)

    deduplicated_indices: list[int] = []
    for source_index in source_indices:
        if not deduplicated_indices or deduplicated_indices[-1] != source_index:
            deduplicated_indices.append(source_index)

    compressed_points = [route_points[source_index] for source_index in deduplicated_indices]
    return compressed_points, deduplicated_indices


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
    return build_route_segments_from_lane_geometries(
        route_points,
        lane_type_geometries=lane_type_geometries,
    )


def build_route_segments_from_lane_geometries(
    route_points: list[tuple[float, float]],
    lane_type_geometries: dict[str, list[list[tuple[float, float]]]],
) -> list[RouteSegment]:
    segments: list[RouteSegment] = []
    cooldown_remaining_m = 0.0
    for index in range(len(route_points) - 1):
        start = route_points[index]
        end = route_points[index + 1]
        segment_length_m = distance_m(start, end)
        if cooldown_remaining_m > 0:
            is_gap = False
            cooldown_remaining_m = max(0.0, cooldown_remaining_m - segment_length_m)
        else:
            is_gap = detect_gap(index, start, end, lane_type_geometries)
            if is_gap:
                cooldown_remaining_m = GAP_SEGMENT_COOLDOWN_M
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


def build_gap_segments_from_analysis_segments(
    analysis_segments: list[RouteSegment],
    full_route_points: list[tuple[float, float]],
    source_indices: list[int],
) -> list[RouteSegment]:
    gap_segments: list[RouteSegment] = []
    if not analysis_segments or len(full_route_points) < 2:
        return gap_segments

    for segment_index, segment in enumerate(analysis_segments):
        if not segment.is_gap:
            continue
        if segment_index + 1 >= len(source_indices):
            continue

        start_index = source_indices[segment_index]
        end_index = source_indices[segment_index + 1]
        if end_index < start_index:
            start_index, end_index = end_index, start_index

        route_slice = full_route_points[start_index : end_index + 1]
        if len(route_slice) < 2:
            route_slice = [full_route_points[start_index], full_route_points[end_index]]

        gap_segments.append(
            RouteSegment(
                coordinates=[
                    [round(point[0], 6), round(point[1], 6)] for point in route_slice
                ],
                risk_level="Red",
                is_gap=True,
            )
        )
    return gap_segments


def route_points_to_geojson(route_points: list[tuple[float, float]]) -> dict | None:
    if len(route_points) < 2:
        return None
    return {
        "type": "LineString",
        "coordinates": [[point[1], point[0]] for point in route_points],
    }


def route_geometry_from_segments(segments: list[RouteSegment]) -> dict | None:
    route_points: list[list[float]] = []
    for index, segment in enumerate(segments):
        coordinates = segment.coordinates
        if not coordinates:
            continue
        if index == 0:
            route_points.extend([[point[1], point[0]] for point in coordinates])
        else:
            route_points.extend([[point[1], point[0]] for point in coordinates[1:]])
    if len(route_points) < 2:
        return None
    return {"type": "LineString", "coordinates": route_points}


def calculate_route_distance_km(route_points: list[tuple[float, float]]) -> float | None:
    if len(route_points) < 2:
        return None
    distance_km = 0.0
    for index in range(len(route_points) - 1):
        distance_km += distance_m(route_points[index], route_points[index + 1]) / 1000
    return round(distance_km, 2)


def calculate_route_distance_from_segments(segments: list[RouteSegment]) -> float | None:
    if not segments:
        return None
    distance_km = 0.0
    for segment in segments:
        coordinates = segment.coordinates
        if len(coordinates) < 2:
            continue
        start = (coordinates[0][0], coordinates[0][1])
        end = (coordinates[-1][0], coordinates[-1][1])
        distance_km += distance_m(start, end) / 1000
    return round(distance_km, 2)


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
          AND cl.geom && ST_Expand(r.geom, 0.01)
          AND ST_DWithin(cl.geom::geography, r.geom::geography, 20)
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
    consecutive_gap_hits = 0
    for segment_point in sampled_points:
        near_protected = any(
            polyline_is_near_point(
                lane_geometry,
                segment_point,
                threshold_m=GAP_POINT_THRESHOLD_M,
            )
            for lane_geometry in protected_lanes
        )
        if not near_protected:
            consecutive_gap_hits = 0
            continue

        if any(
            polyline_is_near_point(
                lane_geometry,
                segment_point,
                threshold_m=GAP_POINT_THRESHOLD_M,
            )
            for lane_geometry in informal_lanes
        ):
            consecutive_gap_hits += 1
            if consecutive_gap_hits >= MIN_CONSECUTIVE_GAP_HITS:
                return True
            continue

        consecutive_gap_hits = 0
    return False


def sample_segment_points(
    start: tuple[float, float], end: tuple[float, float]
) -> list[tuple[float, float]]:
    segment_length_m = max(1.0, distance_m(start, end))
    sample_count = max(3, min(25, int(segment_length_m // 20) + 2))
    if sample_count <= 2:
        return []
    return [
        (
            start[0] + (end[0] - start[0]) * (index / (sample_count - 1)),
            start[1] + (end[1] - start[1]) * (index / (sample_count - 1)),
        )
        for index in range(1, sample_count - 1)
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
    if not coordinates:
        return [0.0, 0.0]
    if len(coordinates) == 1:
        return [round(coordinates[0][0], 6), round(coordinates[0][1], 6)]

    start = coordinates[0]
    end = coordinates[1]
    return [
        round(start[0] + (end[0] - start[0]) * 0.2, 6),
        round(start[1] + (end[1] - start[1]) * 0.2, 6),
    ]
