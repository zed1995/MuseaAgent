from fastapi import APIRouter

from backend.api.routes.debug_chat import api_router as debug_chat_api_router
from backend.api.routes.health import router as health_router
from backend.api.routes.internal_ingestion import router as internal_ingestion_router
from backend.api.routes.search_agent import router as search_agent_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(internal_ingestion_router)
api_router.include_router(search_agent_router)
api_router.include_router(debug_chat_api_router)
