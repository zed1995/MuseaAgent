from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request) -> dict[str, str | bool]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "debug_search_enabled": settings.retrieval.enable_debug_endpoint,
    }
