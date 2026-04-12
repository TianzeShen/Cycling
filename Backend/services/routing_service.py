try:
    from Backend.schemas import (
        HeatmapZone,
        RouteSegment,
        RoutingAlert,
        RoutingRequest,
        RoutingResponse,
    )
except ModuleNotFoundError:
    from schemas import (
        HeatmapZone,
        RouteSegment,
        RoutingAlert,
        RoutingRequest,
        RoutingResponse,
    )


def recommend_route(request: RoutingRequest) -> RoutingResponse:
    route_points = interpolate_route_points(request)
    segments = build_route_segments(route_points)
    try:
        alerts = build_route_alerts(segments)
        alerts_status_message = None
    except Exception:
        alerts = []
        alerts_status_message = (
            "Safety alerts are temporarily unavailable. Please review route colors carefully."
        )
    try:
        heatmap_zones = build_heatmap_zones(segments)
        heatmap_status_message = None
    except Exception:
        heatmap_zones = []
        heatmap_status_message = (
            "Safety heatmap is temporarily unavailable. Please rely on route segment colors."
        )
    return RoutingResponse(
        route_segments=segments,
        alerts=alerts,
        alerts_status_message=alerts_status_message,
        heatmap_zones=heatmap_zones,
        heatmap_status_message=heatmap_status_message,
    )


def interpolate_route_points(request: RoutingRequest) -> list[tuple[float, float]]:
    # Iteration 1 uses evenly interpolated points as a placeholder route geometry.
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
        risk_level = estimate_segment_risk(index)
        is_gap = detect_gap(index, risk_level)
        segments.append(
            RouteSegment(
                coordinates=[
                    [round(start[0], 6), round(start[1], 6)],
                    [round(end[0], 6), round(end[1], 6)],
                ],
                risk_level=risk_level,
                is_gap=is_gap,
            )
        )
    return segments


def estimate_segment_risk(segment_index: int) -> str:
    # Simple mock pattern until real segment-level datasets are available.
    if segment_index == 1:
        return "Red"
    if segment_index == 0:
        return "Yellow"
    return "Green"


def detect_gap(segment_index: int, risk_level: str) -> bool:
    # Only flag clear gap candidates so we do not create false alerts.
    return segment_index == 1 and risk_level == "Red"


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
