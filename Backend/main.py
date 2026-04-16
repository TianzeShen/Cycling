from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    # Support running from the repo root: `uvicorn Backend.main:app --reload`
    from Backend.routers.feasibility import router as feasibility_router
    from Backend.routers.heatmap import router as heatmap_router
    from Backend.routers.routing import router as routing_router
    from Backend.services.heatmap_service import warm_melbourne_heatmap_cache
except ModuleNotFoundError:
    # Support running inside the Backend folder: `uvicorn main:app --reload`
    from routers.feasibility import router as feasibility_router
    from routers.heatmap import router as heatmap_router
    from routers.routing import router as routing_router
    from services.heatmap_service import warm_melbourne_heatmap_cache

app = FastAPI(title="Cycling Decision & Navigation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Cycling App API"}


@app.on_event("startup")
def preload_heatmap_cache() -> None:
    warm_melbourne_heatmap_cache()


# Keep API routes grouped under their feature modules.
app.include_router(feasibility_router)
app.include_router(heatmap_router)
app.include_router(routing_router)
