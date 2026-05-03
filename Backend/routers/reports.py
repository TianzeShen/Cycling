from fastapi import APIRouter

try:
    from Backend.schemas import ReportCreateRequest, ReportListResponse, ReportResponse
    from Backend.services.report_service import create_report, list_reports_for_user
except ModuleNotFoundError:
    from schemas import ReportCreateRequest, ReportListResponse, ReportResponse
    from services.report_service import create_report, list_reports_for_user


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, summary="Create a new user gap report")
def create_user_report(payload: ReportCreateRequest) -> ReportResponse:
    return create_report(payload)


@router.get("", response_model=ReportListResponse, summary="List reports for a user")
def get_reports_for_user(user_id: str) -> ReportListResponse:
    return list_reports_for_user(user_id)
