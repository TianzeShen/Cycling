from fastapi import APIRouter

try:
    from Backend.schemas import RoutingRequest, RoutingResponse
    from Backend.services.routing_service import recommend_route
except ModuleNotFoundError:
    from schemas import RoutingRequest, RoutingResponse
    from services.routing_service import recommend_route


router = APIRouter(prefix="/api/routing", tags=["routing"])


@router.post("/recommend", response_model=RoutingResponse, summary="Recommend a gap-aware route")
def recommend_gap_aware_route(payload: RoutingRequest) -> RoutingResponse:
    # Router stays thin and delegates route shaping to the service layer.
    return recommend_route(payload)
