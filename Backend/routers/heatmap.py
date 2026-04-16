from fastapi import APIRouter

try:
    from Backend.schemas import MelbourneHeatmapResponse
    from Backend.services.heatmap_service import get_melbourne_heatmap
except ModuleNotFoundError:
    from schemas import MelbourneHeatmapResponse
    from services.heatmap_service import get_melbourne_heatmap


router = APIRouter(prefix="/api/heatmap", tags=["heatmap"])


@router.get(
    "/melbourne-sa2",
    response_model=MelbourneHeatmapResponse,
    summary="Get precomputed Melbourne SA2 cycling heatmap data",
)
def get_melbourne_sa2_heatmap() -> MelbourneHeatmapResponse:
    return get_melbourne_heatmap()
