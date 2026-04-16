def compute_feasibility_score(features):

    distance_km = features.get("distance_km", 0)
    protected_lane_pct = features.get("protected_lane_pct", 0)
    no_infra_pct = features.get("no_infra_pct", 0)
    gap_count = features.get("gap_count", 0)
    high_traffic_pct = features.get("high_traffic_pct", 0)

    # Penalties
    distance_penalty = distance_km * 3
    gap_penalty = gap_count * 8
    traffic_penalty = high_traffic_pct * 0.25
    no_infra_penalty = no_infra_pct * 0.25

    # Bonus
    protected_lane_bonus = protected_lane_pct * 0.20

    score = (
        100
        - distance_penalty
        - gap_penalty
        - traffic_penalty
        - no_infra_penalty
        + protected_lane_bonus
    )

    score = round(max(0, min(100, score)))

    if score >= 75:
        label = "High feasibility"
    elif score >= 45:
        label = "Moderate feasibility"
    else:
        label = "Low feasibility"

    return {
        "score": score,
        "label": label
    }