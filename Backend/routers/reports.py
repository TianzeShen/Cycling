from fastapi import APIRouter, HTTPException

try:
    from Backend.schemas import (
        ReportCreateRequest,
        ReportDeleteResponse,
        ReportListResponse,
        ReportResponse,
        ReportUpdateRequest,
    )
    from Backend.services.report_service import (
        create_report,
        delete_report,
        list_reports_for_user,
        update_report,
    )
except ModuleNotFoundError:
    from schemas import (
        ReportCreateRequest,
        ReportDeleteResponse,
        ReportListResponse,
        ReportResponse,
        ReportUpdateRequest,
    )
    from services.report_service import (
        create_report,
        delete_report,
        list_reports_for_user,
        update_report,
    )


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, summary="Create a new user gap report")
def create_user_report(payload: ReportCreateRequest) -> ReportResponse:
    return create_report(payload)


@router.get("", response_model=ReportListResponse, summary="List reports for a user")
def get_reports_for_user(user_id: str) -> ReportListResponse:
    return list_reports_for_user(user_id)


@router.patch("/{report_id}", response_model=ReportResponse, summary="Update a user report")
def update_user_report(report_id: str, payload: ReportUpdateRequest) -> ReportResponse:
    try:
        return update_report(report_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{report_id}", response_model=ReportDeleteResponse, summary="Delete a user report")
def delete_user_report(report_id: str, user_id: str) -> ReportDeleteResponse:
    try:
        return delete_report(report_id, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
