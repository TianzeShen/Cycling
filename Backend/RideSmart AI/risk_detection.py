def detect_route_risk(features):
    """
    Detect overall route risk and produce warning messages.

    Expected input:
    features = {
        "gap_count": int,
        "no_infra_pct": float,
        "high_traffic_pct": float,
        "avg_speed_limit": float,
        "protected_lane_pct": float
    }
    """

    gap_count = features.get("gap_count", 0)
    no_infra_pct = features.get("no_infra_pct", 0)
    high_traffic_pct = features.get("high_traffic_pct", 0)
    avg_speed_limit = features.get("avg_speed_limit", 40)
    protected_lane_pct = features.get("protected_lane_pct", 0)

    alerts = []
    risk_points = 0

    if gap_count >= 2:
        alerts.append("Multiple disconnected bike lane gaps detected.")
        risk_points += 2
    elif gap_count == 1:
        alerts.append("A disconnected bike lane gap is present on this route.")
        risk_points += 1

    if no_infra_pct >= 40:
        alerts.append("A large part of the route has no dedicated cycling infrastructure.")
        risk_points += 2
    elif no_infra_pct >= 20:
        alerts.append("Some parts of the route do not have cycling infrastructure.")
        risk_points += 1

    if high_traffic_pct >= 35:
        alerts.append("This route includes substantial exposure to higher traffic roads.")
        risk_points += 2
    elif high_traffic_pct >= 20:
        alerts.append("This route includes moderate traffic exposure.")
        risk_points += 1

    if avg_speed_limit >= 70:
        alerts.append("High-speed road conditions may reduce cycling safety.")
        risk_points += 2
    elif avg_speed_limit >= 60:
        alerts.append("Some segments are near relatively high-speed roads.")
        risk_points += 1

    if protected_lane_pct >= 40:
        alerts.append("Protected bike lane coverage helps reduce route risk.")
        risk_points -= 1

    if risk_points >= 5:
        risk_level = "High"
    elif risk_points >= 2:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "risk_level": risk_level,
        "alerts": alerts[:4]
    }