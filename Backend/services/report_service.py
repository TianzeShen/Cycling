from uuid import uuid4

from sqlalchemy import text

try:
    from Backend.database import fetch_all, fetch_one, get_transaction_connection
    from Backend.schemas import (
        PublicReportListResponse,
        PublicReportResponse,
        ReportCreateRequest,
        ReportDeleteResponse,
        ReportLikeResponse,
        ReportListResponse,
        ReportLikeRequest,
        ReportResponse,
        ReportUpdateRequest,
    )
except ModuleNotFoundError:
    from database import fetch_all, fetch_one, get_transaction_connection
    from schemas import (
        PublicReportListResponse,
        PublicReportResponse,
        ReportCreateRequest,
        ReportDeleteResponse,
        ReportLikeResponse,
        ReportListResponse,
        ReportLikeRequest,
        ReportResponse,
        ReportUpdateRequest,
    )


REPORT_STATUS_PENDING = "pending"
LANE_GAP_TYPE_USER_REPORTED = "user_reported_gap"
DUPLICATE_REPORT_WINDOW_MINUTES = 10
COORDINATE_DUPLICATE_TOLERANCE_METERS = 3.0


class DuplicateReportError(ValueError):
    pass


class ReportAlreadyLikedError(ValueError):
    pass


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
            :issue_type,
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
        ensure_local_uuid_user_exists(connection, payload.user_id)
        reject_duplicate_report(
            connection=connection,
            user_id=payload.user_id,
            issue_type=stored_issue_type,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
        report_row = (
            connection.execute(text(insert_report_query), params).mappings().first()
        )
        if stored_issue_type == "gap":
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


def list_all_reports(user_id: str) -> PublicReportListResponse:
    query = """
        SELECT
            ir.report_id::text AS report_id,
            ir.user_id::text AS user_id,
            ir.segment_id::text AS segment_id,
            ir.issue_type::text AS issue_type,
            ir.status::text AS status,
            ir.lat AS latitude,
            ir.lng AS longitude,
            ir.description,
            ir.reported_at,
            COALESCE(SUM(rl.like_count), 0)::int AS like_count,
            COALESCE(
                BOOL_OR(rl.user_id = CAST(:user_id AS uuid)),
                false
            ) AS liked_by_current_user
        FROM ridesmart.issue_report ir
        LEFT JOIN ridesmart.report_like rl
          ON rl.report_id = ir.report_id
        GROUP BY
            ir.report_id,
            ir.user_id,
            ir.segment_id,
            ir.issue_type,
            ir.status,
            ir.lat,
            ir.lng,
            ir.description,
            ir.reported_at
        ORDER BY ir.reported_at DESC
    """
    rows = fetch_all(query, {"user_id": user_id})
    return PublicReportListResponse(
        reports=[PublicReportResponse(**row) for row in rows]
    )


def update_report(report_id: str, payload: ReportUpdateRequest) -> ReportResponse:
    existing_report = get_owned_report(report_id, payload.user_id)
    if existing_report is None:
        raise LookupError("Report not found for this user.")

    old_issue_type = existing_report["issue_type"]
    old_segment_id = existing_report["segment_id"]
    old_latitude = float(existing_report["latitude"])
    old_longitude = float(existing_report["longitude"])
    old_description = existing_report["description"]
    reported_at = existing_report["reported_at"]

    new_latitude = payload.latitude if payload.latitude is not None else old_latitude
    new_longitude = payload.longitude if payload.longitude is not None else old_longitude
    new_issue_type = (
        normalise_issue_type(payload.issue_type)
        if payload.issue_type is not None
        else old_issue_type
    )
    new_description = (
        payload.description if payload.description is not None else old_description
    )
    new_segment_id = (
        find_nearest_segment_id(new_latitude, new_longitude)
        if (
            payload.latitude is not None
            or payload.longitude is not None
        )
        else old_segment_id
    )

    update_report_query = """
        UPDATE ridesmart.issue_report
        SET
            segment_id = CAST(:segment_id AS uuid),
            issue_type = :issue_type,
            lat = :latitude,
            lng = :longitude,
            geom = ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
            description = :description
        WHERE report_id = CAST(:report_id AS uuid)
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

    params = {
        "report_id": report_id,
        "segment_id": new_segment_id,
        "issue_type": new_issue_type,
        "latitude": new_latitude,
        "longitude": new_longitude,
        "description": new_description,
        "reported_at": reported_at,
        "old_segment_id": old_segment_id,
        "old_latitude": old_latitude,
        "old_longitude": old_longitude,
        "old_description": old_description,
    }

    with get_transaction_connection() as connection:
        reject_duplicate_report(
            connection=connection,
            user_id=payload.user_id,
            issue_type=new_issue_type,
            latitude=new_latitude,
            longitude=new_longitude,
            exclude_report_id=report_id,
        )
        updated_row = (
            connection.execute(text(update_report_query), params).mappings().first()
        )
        sync_lane_gap_for_report_update(
            connection=connection,
            old_issue_type=old_issue_type,
            new_issue_type=new_issue_type,
            reported_at=reported_at,
            old_segment_id=old_segment_id,
            old_latitude=old_latitude,
            old_longitude=old_longitude,
            old_description=old_description,
            new_segment_id=new_segment_id,
            new_latitude=new_latitude,
            new_longitude=new_longitude,
            new_description=new_description,
        )

    if updated_row is None:
        raise RuntimeError("Report update failed.")

    return ReportResponse(**dict(updated_row))


def delete_report(report_id: str, user_id: str) -> ReportDeleteResponse:
    existing_report = get_owned_report(report_id, user_id)
    if existing_report is None:
        raise LookupError("Report not found for this user.")

    with get_transaction_connection() as connection:
        delete_lane_gap_for_report(
            connection=connection,
            reported_at=existing_report["reported_at"],
            segment_id=existing_report["segment_id"],
            latitude=float(existing_report["latitude"]),
            longitude=float(existing_report["longitude"]),
            issue_type=existing_report["issue_type"],
        )
        connection.execute(
            text(
                """
                DELETE FROM ridesmart.issue_report
                WHERE report_id = CAST(:report_id AS uuid)
                """
            ),
            {"report_id": report_id},
        )

    return ReportDeleteResponse(report_id=report_id)


def like_report(report_id: str, payload: ReportLikeRequest) -> ReportLikeResponse:
    with get_transaction_connection() as connection:
        ensure_local_uuid_user_exists(connection, payload.user_id)
        ensure_report_exists(connection, report_id)
        existing_like = connection.execute(
            text(
                """
                SELECT 1
                FROM ridesmart.report_like
                WHERE report_id = CAST(:report_id AS uuid)
                  AND user_id = CAST(:user_id AS uuid)
                LIMIT 1
                """
            ),
            {
                "report_id": report_id,
                "user_id": payload.user_id,
            },
        ).scalar()
        if existing_like:
            raise ReportAlreadyLikedError(
                "This user has already submitted likes for this report."
            )

        connection.execute(
            text(
                """
                INSERT INTO ridesmart.report_like (
                    like_id,
                    report_id,
                    user_id,
                    like_count,
                    liked_at
                )
                VALUES (
                    gen_random_uuid(),
                    CAST(:report_id AS uuid),
                    CAST(:user_id AS uuid),
                    :like_count,
                    NOW()
                )
                """
            ),
            {
                "report_id": report_id,
                "user_id": payload.user_id,
                "like_count": payload.like_count,
            },
        )
        return fetch_report_like_state(
            connection=connection,
            report_id=report_id,
            user_id=payload.user_id,
        )


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
    return key or "other"


def reject_duplicate_report(
    connection,
    user_id: str,
    issue_type: str,
    latitude: float,
    longitude: float,
    exclude_report_id: str | None = None,
) -> None:
    duplicate_query = """
        SELECT
            report_id::text AS report_id
        FROM ridesmart.issue_report
        WHERE user_id = CAST(:user_id AS uuid)
          AND LOWER(issue_type::text) = LOWER(:issue_type)
          AND reported_at >= NOW() - make_interval(mins => :window_minutes)
          AND (
                :exclude_report_id IS NULL
                OR report_id <> CAST(:exclude_report_id AS uuid)
          )
          AND ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                :distance_tolerance_m
          )
        ORDER BY reported_at DESC
        LIMIT 1
    """
    duplicate_row = (
        connection.execute(
            text(duplicate_query),
            {
                "user_id": user_id,
                "issue_type": issue_type,
                "latitude": latitude,
                "longitude": longitude,
                "window_minutes": DUPLICATE_REPORT_WINDOW_MINUTES,
                "distance_tolerance_m": COORDINATE_DUPLICATE_TOLERANCE_METERS,
                "exclude_report_id": exclude_report_id,
            },
        )
        .mappings()
        .first()
    )
    if duplicate_row is not None:
        raise DuplicateReportError(
            "A similar report from this user was already submitted recently."
        )


def ensure_local_uuid_user_exists(connection, user_id: str) -> None:
    exists_query = """
        SELECT 1
        FROM ridesmart.app_user
        WHERE user_id = CAST(:user_id AS uuid)
        LIMIT 1
    """
    exists = connection.execute(text(exists_query), {"user_id": user_id}).scalar()
    if exists:
        return

    insert_query = """
        INSERT INTO ridesmart.app_user (
            user_id,
            full_name,
            email,
            password_hash
        )
        VALUES (
            CAST(:user_id AS uuid),
            :full_name,
            :email,
            :password_hash
        )
    """
    connection.execute(
        text(insert_query),
        {
            "user_id": user_id,
            "full_name": f"Local User {user_id[:8]}",
            "email": f"local-{user_id}@ridesmart.local",
            "password_hash": "localstorage-uuid-placeholder",
        },
    )


def get_owned_report(report_id: str, user_id: str) -> dict | None:
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
        WHERE report_id = CAST(:report_id AS uuid)
          AND user_id = CAST(:user_id AS uuid)
        LIMIT 1
    """
    return fetch_one(query, {"report_id": report_id, "user_id": user_id})


def ensure_report_exists(connection, report_id: str) -> None:
    exists = connection.execute(
        text(
            """
            SELECT 1
            FROM ridesmart.issue_report
            WHERE report_id = CAST(:report_id AS uuid)
            LIMIT 1
            """
        ),
        {"report_id": report_id},
    ).scalar()
    if not exists:
        raise LookupError("Report not found.")


def fetch_report_like_state(
    connection,
    report_id: str,
    user_id: str,
) -> ReportLikeResponse:
    row = (
        connection.execute(
            text(
                """
                SELECT
                    ir.report_id::text AS report_id,
                    COALESCE(SUM(rl.like_count), 0)::int AS like_count,
                    COALESCE(
                        BOOL_OR(rl.user_id = CAST(:user_id AS uuid)),
                        false
                    ) AS liked_by_current_user
                FROM ridesmart.issue_report ir
                LEFT JOIN ridesmart.report_like rl
                  ON rl.report_id = ir.report_id
                WHERE ir.report_id = CAST(:report_id AS uuid)
                GROUP BY ir.report_id
                """
            ),
            {
                "report_id": report_id,
                "user_id": user_id,
            },
        )
        .mappings()
        .first()
    )
    if row is None:
        raise LookupError("Report not found.")
    return ReportLikeResponse(**dict(row))


def sync_lane_gap_for_report_update(
    connection,
    old_issue_type: str,
    new_issue_type: str,
    reported_at,
    old_segment_id: str | None,
    old_latitude: float,
    old_longitude: float,
    old_description: str | None,
    new_segment_id: str | None,
    new_latitude: float,
    new_longitude: float,
    new_description: str | None,
) -> None:
    if old_issue_type == "gap" and new_issue_type != "gap":
        delete_lane_gap_row(
            connection,
            reported_at,
            old_segment_id,
            old_latitude,
            old_longitude,
        )
        return

    if old_issue_type != "gap" and new_issue_type == "gap":
        connection.execute(
            text(
                """
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
                    gen_random_uuid(),
                    NULL,
                    CAST(:segment_id AS uuid),
                    :gap_type,
                    NULL,
                    :risk_note,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                    :reported_at
                )
                """
            ),
            {
                "segment_id": new_segment_id,
                "gap_type": LANE_GAP_TYPE_USER_REPORTED,
                "risk_note": new_description,
                "longitude": new_longitude,
                "latitude": new_latitude,
                "reported_at": reported_at,
            },
        )
        return

    if old_issue_type == "gap" and new_issue_type == "gap":
        connection.execute(
            text(
                """
                UPDATE ridesmart.lane_gap
                SET
                    segment_id = CAST(:new_segment_id AS uuid),
                    risk_note = :new_description,
                    geom = ST_SetSRID(ST_MakePoint(:new_longitude, :new_latitude), 4326)
                WHERE gap_type = :gap_type
                  AND detected_at = :reported_at
                  AND (
                    (segment_id IS NULL AND CAST(:old_segment_id AS uuid) IS NULL)
                    OR segment_id = CAST(:old_segment_id AS uuid)
                  )
                  AND ST_DWithin(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint(:old_longitude, :old_latitude), 4326)::geography,
                        1
                  )
                """
            ),
            {
                "new_segment_id": new_segment_id,
                "new_description": new_description,
                "new_longitude": new_longitude,
                "new_latitude": new_latitude,
                "gap_type": LANE_GAP_TYPE_USER_REPORTED,
                "reported_at": reported_at,
                "old_segment_id": old_segment_id,
                "old_longitude": old_longitude,
                "old_latitude": old_latitude,
            },
        )


def delete_lane_gap_for_report(
    connection,
    reported_at,
    segment_id: str | None,
    latitude: float,
    longitude: float,
    issue_type: str,
) -> None:
    if issue_type != "gap":
        return
    delete_lane_gap_row(connection, reported_at, segment_id, latitude, longitude)


def delete_lane_gap_row(
    connection,
    reported_at,
    segment_id: str | None,
    latitude: float,
    longitude: float,
) -> None:
    connection.execute(
        text(
            """
            DELETE FROM ridesmart.lane_gap
            WHERE gap_type = :gap_type
              AND detected_at = :reported_at
              AND (
                (segment_id IS NULL AND CAST(:segment_id AS uuid) IS NULL)
                OR segment_id = CAST(:segment_id AS uuid)
              )
              AND ST_DWithin(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                    1
              )
            """
        ),
        {
            "gap_type": LANE_GAP_TYPE_USER_REPORTED,
            "reported_at": reported_at,
            "segment_id": segment_id,
            "longitude": longitude,
            "latitude": latitude,
        },
    )
