from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.router import api_router
from backend.core.config import Settings, get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    from backend.services.indexing.cold_start import run_cold_start

    run_cold_start()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=_lifespan,
    )
    app.state.settings = app_settings
    app.include_router(api_router, prefix=app_settings.api_prefix)
    return app
