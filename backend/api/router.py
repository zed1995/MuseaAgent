from fastapi import APIRouter

from backend.api.routes.health import router as health_router
from backend.api.routes.internal_ingestion import router as internal_ingestion_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(internal_ingestion_router)
