try:
    from Backend.schemas import RouteSegment, RoutingAlert, RoutingRequest, RoutingResponse
except ModuleNotFoundError:
    from schemas import RouteSegment, RoutingAlert, RoutingRequest, RoutingResponse


def recommend_route(request: RoutingRequest) -> RoutingResponse:
    route_points = interpolate_route_points(request)
    segments = build_route_segments(route_points)
    alerts = build_gap_alerts(segments)
    return RoutingResponse(route_segments=segments, alerts=alerts)


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


def build_gap_alerts(segments: list[RouteSegment]) -> list[RoutingAlert]:
    alerts: list[RoutingAlert] = []
    for segment in segments:
        if not segment.is_gap:
            continue
        midpoint = midpoint_from_segment(segment.coordinates)
        alerts.append(
            RoutingAlert(
                location=midpoint,
                message="Disconnected bike lane detected ahead",
            )
        )
    return alerts


def midpoint_from_segment(coordinates: list[list[float]]) -> list[float]:
    start, end = coordinates
    return [
        round((start[0] + end[0]) / 2, 6),
        round((start[1] + end[1]) / 2, 6),
    ]
