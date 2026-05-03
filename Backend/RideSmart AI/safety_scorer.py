from math import isfinite


INFRA_QUALITY = {
    "protected": 1.0,
    "shared_path": 0.9,
    "painted": 0.45,
    "informal": 0.15,
}

LANE_WEIGHT = 0.35
AADT_WEIGHT = 0.25
SPEED_WEIGHT = 0.20
DISTANCE_WEIGHT = 0.20
BASE_SCORE_OFFSET = 12.0

GAP_PENALTY_BY_COUNT = {
    0: 0,
    1: 8,
    2: 14,
    3: 20,
    4: 25,
}
MAX_GAP_PENALTY = 30
HIGH_CRASH_SEGMENT_THRESHOLD = 30
MAX_CRASH_PENALTY = 15


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def normalise_aadt(avg_aadt: float | None) -> float:
    if avg_aadt is None or not isfinite(avg_aadt):
        return 0.5
    return clamp(1.0 - (avg_aadt / 40000.0), 0.0, 1.0)


def normalise_speed(avg_speed_zone: float | None) -> float:
    if avg_speed_zone is None or not isfinite(avg_speed_zone):
        return 0.5
    return clamp(1.0 - ((avg_speed_zone - 30.0) / 50.0), 0.0, 1.0)


def normalise_distance(distance_km: float) -> float:
    return clamp(1.0 - (distance_km / 20.0), 0.0, 1.0)


def gap_penalty(gap_count: int) -> int:
    if gap_count in GAP_PENALTY_BY_COUNT:
        return GAP_PENALTY_BY_COUNT[gap_count]
    return MAX_GAP_PENALTY


def crash_penalty(high_crash_segment_count: int) -> int:
    return min(max(0, 3 * int(high_crash_segment_count)), MAX_CRASH_PENALTY)


def compute_safety_score(
    bike_lane_quality: float,
    avg_aadt: float | None,
    avg_speed_zone: float | None,
    distance_km: float,
    gap_count: int,
    high_crash_segment_count: int,
) -> dict:
    lane_score = clamp(bike_lane_quality, 0.0, 1.0)
    aadt_score = normalise_aadt(avg_aadt)
    speed_score = normalise_speed(avg_speed_zone)
    distance_score = normalise_distance(distance_km)

    composite = (
        (LANE_WEIGHT * lane_score)
        + (AADT_WEIGHT * aadt_score)
        + (SPEED_WEIGHT * speed_score)
        + (DISTANCE_WEIGHT * distance_score)
    )
    base_score = round(clamp((composite * 100) + BASE_SCORE_OFFSET, 0.0, 100.0), 1)

    applied_gap_penalty = gap_penalty(gap_count)
    applied_crash_penalty = crash_penalty(high_crash_segment_count)
    final_score = round(
        clamp(base_score - applied_gap_penalty - applied_crash_penalty, 0.0, 100.0),
        1,
    )

    risk_label = (
        "Low Risk"
        if final_score >= 70
        else ("Moderate Risk" if final_score >= 45 else "High Risk")
    )

    return {
        "score": final_score,
        "risk_label": risk_label,
        "breakdown": {
            "bike_lane_score": round(lane_score * 100, 1),
            "traffic_score": round(aadt_score * 100, 1),
            "speed_score": round(speed_score * 100, 1),
            "distance_score": round(distance_score * 100, 1),
            "base_score": base_score,
            "gap_penalty": applied_gap_penalty,
            "crash_penalty": applied_crash_penalty,
        },
    }
