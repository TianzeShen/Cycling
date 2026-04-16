def generate_explanations(features):

    reasons = []

    distance_km = features.get("distance_km", 0)
    protected_lane_pct = features.get("protected_lane_pct", 0)
    no_infra_pct = features.get("no_infra_pct", 0)
    gap_count = features.get("gap_count", 0)
    high_traffic_pct = features.get("high_traffic_pct", 0)

    if protected_lane_pct >= 30:
        reasons.append(
            f"{protected_lane_pct}% of this route has protected bike lanes, improving safety."
        )

    if gap_count > 0:
        reasons.append(
            f"This route has {gap_count} disconnected bike lane gap(s)."
        )

    if high_traffic_pct >= 25:
        reasons.append(
            f"{high_traffic_pct}% of the route passes through higher traffic roads."
        )

    if no_infra_pct >= 30:
        reasons.append(
            f"{no_infra_pct}% of the route has no dedicated cycling infrastructure."
        )

    if distance_km > 8:
        reasons.append(
            f"The route distance is {distance_km} km, which may be challenging for casual riders."
        )

    if not reasons:
        reasons.append("This route has generally balanced cycling conditions.")

    return reasons[:3]