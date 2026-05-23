import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.router import api_router
from backend.core.config import Settings, get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    from backend.services.indexing.cold_start import run_cold_start

    # run_cold_start()
    yield


def _configure_logging() -> None:
    retrieval_logger = logging.getLogger("backend.services.retrieval")
    retrieval_logger.setLevel(logging.INFO)
    if not retrieval_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        retrieval_logger.addHandler(handler)
        retrieval_logger.propagate = False


def create_app(settings: Settings | None = None) -> FastAPI:
    _configure_logging()
    app_settings = settings or get_settings()
    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=_lifespan,
    )
    app.state.settings = app_settings
    app.include_router(api_router, prefix=app_settings.api_prefix)
    return app
