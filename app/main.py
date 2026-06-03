"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.auth.routes import router as auth_router
from app.config import get_settings
from app.logging_config import configure_logging
from app.routes.checkin import router as checkin_router
from app.routes.health import router as health_router
from app.routes.niggles import router as niggles_router

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "health", "description": "Service liveness."},
    {"name": "auth", "description": "Registration, login and current user."},
    {"name": "checkin", "description": "Daily readiness checkins (form, motivation, fatigue)."},
    {"name": "niggles", "description": "Nagging body complaints and their trajectory reports."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()  # triggers critical settings validation (e.g. JWT secret)
    logger.info(
        "Enduraw Form Tracker starting (version=%s, env=%s, engine=%s)",
        __version__,
        settings.ENV,
        settings.ENGINE_MODE,
    )
    yield
    logger.info("Enduraw Form Tracker shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Enduraw Form Tracker",
        description="API to track and analyse the readiness of endurance athletes.",
        version=__version__,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(checkin_router)
    app.include_router(niggles_router)
    return app


app = create_app()
