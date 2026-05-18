from fastapi import APIRouter, HTTPException

try:
    from Backend.schemas import (
        PublicReportListResponse,
        ReportCreateRequest,
        ReportDeleteResponse,
        ReportLikeRequest,
        ReportLikeResponse,
        ReportListResponse,
        ReportResponse,
        ReportUpdateRequest,
    )
    from Backend.services.report_service import (
        create_report,
        delete_report,
        DuplicateReportError,
        like_report,
        list_all_reports,
        list_reports_for_user,
        ReportAlreadyLikedError,
        update_report,
    )
except ModuleNotFoundError:
    from schemas import (
        PublicReportListResponse,
        ReportCreateRequest,
        ReportDeleteResponse,
        ReportLikeRequest,
        ReportLikeResponse,
        ReportListResponse,
        ReportResponse,
        ReportUpdateRequest,
    )
    from services.report_service import (
        create_report,
        delete_report,
        DuplicateReportError,
        like_report,
        list_all_reports,
        list_reports_for_user,
        ReportAlreadyLikedError,
        update_report,
    )


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, summary="Create a new user gap report")
def create_user_report(payload: ReportCreateRequest) -> ReportResponse:
    try:
        return create_report(payload)
    except DuplicateReportError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=ReportListResponse, summary="List reports for a user")
def get_reports_for_user(user_id: str) -> ReportListResponse:
    return list_reports_for_user(user_id)


@router.get("/all", response_model=PublicReportListResponse, summary="List all visible reports")
def get_all_reports(user_id: str) -> PublicReportListResponse:
    return list_all_reports(user_id)


@router.patch("/{report_id}", response_model=ReportResponse, summary="Update a user report")
def update_user_report(report_id: str, payload: ReportUpdateRequest) -> ReportResponse:
    try:
        return update_report(report_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{report_id}", response_model=ReportDeleteResponse, summary="Delete a user report")
def delete_user_report(report_id: str, user_id: str) -> ReportDeleteResponse:
    try:
        return delete_report(report_id, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{report_id}/like", response_model=ReportLikeResponse, summary="Like a report")
def like_user_report(report_id: str, payload: ReportLikeRequest) -> ReportLikeResponse:
    try:
        return like_report(report_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReportAlreadyLikedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
