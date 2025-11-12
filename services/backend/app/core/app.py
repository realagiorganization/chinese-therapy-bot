from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.chat import legacy_router as chat_legacy_router
from app.core.config import get_settings
from app.core.database import init_database


def _configure_logging(level_name: str) -> None:
    """Ensure application logs propagate with the requested verbosity."""
    level = getattr(logging, level_name.upper(), logging.WARNING)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
    root_logger.setLevel(level)


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.database_url:
            await init_database()
        yield

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    app.include_router(chat_legacy_router)

    @app.get("/", tags=["health"])
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "environment": settings.app_env}

    return app
