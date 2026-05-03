from uuid import uuid4

from sqlalchemy import text

try:
    from Backend.database import fetch_all, fetch_one, get_transaction_connection
    from Backend.schemas import (
        ReportCreateRequest,
        ReportListResponse,
        ReportResponse,
    )
except ModuleNotFoundError:
    from database import fetch_all, fetch_one, get_transaction_connection
    from schemas import (
        ReportCreateRequest,
        ReportListResponse,
        ReportResponse,
    )


REPORT_STATUS_PENDING = "pending"
LANE_GAP_TYPE_USER_REPORTED = "user_reported_gap"
ISSUE_TYPE_MAPPING = {
    "gap": "no_lane",
    "no_lane": "no_lane",
    "broken_lane": "broken_lane",
    "pothole": "pothole",
    "debris": "debris",
    "unsafe_crossing": "unsafe_crossing",
    "other": "other",
}


def create_report(payload: ReportCreateRequest) -> ReportResponse:
    report_id = str(uuid4())
    gap_id = str(uuid4())
    segment_id = find_nearest_segment_id(payload.latitude, payload.longitude)
    stored_issue_type = normalise_issue_type(payload.issue_type)

    insert_report_query = """
        INSERT INTO ridesmart.issue_report (
            report_id,
            user_id,
            segment_id,
            issue_type,
            status,
            lat,
            lng,
            geom,
            description,
            ai_impact_score,
            is_duplicate,
            validation_count,
            reported_at,
            resolved_at
        )
        VALUES (
            :report_id,
            CAST(:user_id AS uuid),
            CAST(:segment_id AS uuid),
            CAST(:issue_type AS ridesmart.issue_type_enum),
            CAST(:status AS ridesmart.issue_status_enum),
            :latitude,
            :longitude,
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
            :description,
            NULL,
            false,
            0,
            NOW(),
            NULL
        )
        RETURNING
            report_id::text AS report_id,
            user_id::text AS user_id,
            segment_id::text AS segment_id,
            issue_type::text AS issue_type,
            status::text AS status,
            lat AS latitude,
            lng AS longitude,
            description,
            reported_at
    """

    insert_lane_gap_query = """
        INSERT INTO ridesmart.lane_gap (
            gap_id,
            lane_id,
            segment_id,
            gap_type,
            distance_m,
            risk_note,
            geom,
            detected_at
        )
        VALUES (
            :gap_id,
            NULL,
            CAST(:segment_id AS uuid),
            :gap_type,
            NULL,
            :risk_note,
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
            NOW()
        )
    """

    params = {
        "report_id": report_id,
        "gap_id": gap_id,
        "user_id": payload.user_id,
        "segment_id": segment_id,
        "issue_type": stored_issue_type,
        "status": REPORT_STATUS_PENDING,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "description": payload.description,
        "gap_type": LANE_GAP_TYPE_USER_REPORTED,
        "risk_note": payload.description,
    }

    with get_transaction_connection() as connection:
        report_row = (
            connection.execute(text(insert_report_query), params).mappings().first()
        )
        connection.execute(text(insert_lane_gap_query), params)

    if report_row is None:
        raise RuntimeError("Report creation failed.")

    return ReportResponse(**dict(report_row))


def list_reports_for_user(user_id: str) -> ReportListResponse:
    query = """
        SELECT
            report_id::text AS report_id,
            user_id::text AS user_id,
            segment_id::text AS segment_id,
            issue_type::text AS issue_type,
            status::text AS status,
            lat AS latitude,
            lng AS longitude,
            description,
            reported_at
        FROM ridesmart.issue_report
        WHERE user_id = CAST(:user_id AS uuid)
        ORDER BY reported_at DESC
    """
    rows = fetch_all(query, {"user_id": user_id})
    return ReportListResponse(reports=[ReportResponse(**row) for row in rows])


def find_nearest_segment_id(latitude: float, longitude: float) -> str | None:
    query = """
        WITH selected_point AS (
            SELECT ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) AS geom
        )
        SELECT rs.segment_id::text AS segment_id
        FROM ridesmart.road_segment rs, selected_point p
        WHERE rs.geom && ST_Expand(p.geom, 0.01)
          AND ST_DWithin(rs.geom::geography, p.geom::geography, 100)
        ORDER BY rs.geom <-> p.geom
        LIMIT 1
    """
    row = fetch_one(
        query,
        {
            "latitude": latitude,
            "longitude": longitude,
        },
    )
    return None if row is None else row["segment_id"]


def normalise_issue_type(issue_type: str) -> str:
    key = issue_type.strip().lower()
    return ISSUE_TYPE_MAPPING.get(key, "other")
