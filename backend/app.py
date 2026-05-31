import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy import text

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.router import api_router
from backend.api.routes.debug_chat import page_router as debug_chat_page_router
from backend.core.config import Settings, get_settings
from backend.core.db import create_engine_from_settings, create_session_factory

_DEBUG_STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    from backend.services.indexing.cold_start import run_cold_start

    engine = getattr(app.state, "db_engine", None)
    if engine is not None:
        connection = engine.connect()
        try:
            connection.execute(text("SELECT 1"))
        finally:
            connection.close()

    # run_cold_start()
    yield
    if engine is not None:
        engine.dispose()


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))

    for logger_name, level in [
        ("backend.services.chat_debug", logging.INFO),
        ("backend.services.retrieval", logging.INFO),
        ("backend.services.indexing", logging.INFO),
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        if not logger.handlers:
            logger.addHandler(handler)
            logger.propagate = False


def create_app(settings: Settings | None = None) -> FastAPI:
    _configure_logging()
    app_settings = settings or get_settings()
    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=_lifespan,
    )
    app.state.settings = app_settings
    app.state.db_engine = create_engine_from_settings(app_settings)
    app.state.session_factory = create_session_factory(app.state.db_engine)
    app.mount("/debug-assets", StaticFiles(directory=_DEBUG_STATIC_DIR), name="debug-assets")
    app.include_router(api_router, prefix=app_settings.api_prefix)
    app.include_router(debug_chat_page_router)
    if app_settings.retrieval.enable_debug_endpoint:
        from backend.api.routes.search_debug import router as search_debug_router

        app.include_router(search_debug_router, prefix=app_settings.api_prefix)
    return app
