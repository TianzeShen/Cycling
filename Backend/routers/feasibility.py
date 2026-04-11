from fastapi import APIRouter

try:
    from Backend.schemas import FeasibilityRequest, FeasibilityResponse
    from Backend.services.feasibility_service import evaluate_feasibility
except ModuleNotFoundError:
    from schemas import FeasibilityRequest, FeasibilityResponse
    from services.feasibility_service import evaluate_feasibility


router = APIRouter(prefix="/api/feasibility", tags=["feasibility"])


@router.post("/evaluate", response_model=FeasibilityResponse, summary="Evaluate trip feasibility")
def evaluate_trip_feasibility(payload: FeasibilityRequest) -> FeasibilityResponse:
    # Router stays thin and delegates business rules to the service layer.
    return evaluate_feasibility(payload)
