"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.auth.routes import router as auth_router
from app.config import get_settings
from app.logging_config import configure_logging
from app.routes.checkin import router as checkin_router
from app.routes.feedback import router as feedback_router
from app.routes.garmin import router as garmin_router
from app.routes.health import router as health_router
from app.routes.illness import router as illness_router
from app.routes.insights import router as insights_router
from app.routes.mini_tests import router as mini_tests_router
from app.routes.niggles import router as niggles_router
from app.routes.sync import router as sync_router

logger = logging.getLogger(__name__)

# Built single-page app (frontend/dist), produced by `npm run build`. Served by
# FastAPI in production so the demo runs on a single URL; absent in dev (the Vite
# dev server proxies /api instead).
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

OPENAPI_TAGS = [
    {"name": "health", "description": "Service liveness."},
    {"name": "auth", "description": "Registration, login and current user."},
    {"name": "checkin", "description": "Daily readiness checkins (form, motivation, fatigue)."},
    {"name": "niggles", "description": "Nagging body complaints and their trajectory reports."},
    {"name": "mini-tests", "description": "Neuromuscular micro-tests (jump / reaction)."},
    {"name": "feedback", "description": "Post-session feedback (RPE and affect)."},
    {"name": "illness", "description": "Athlete-confirmed illness flags and symptoms."},
    {"name": "garmin", "description": "Faked Garmin ingestion (daily metrics + on-watch RPE)."},
    {"name": "insights", "description": "Fused readiness: divergence, signals and recommendation."},
    {"name": "sync", "description": "Push the app's subjective data back to CoachAgent."},
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
    app.include_router(mini_tests_router)
    app.include_router(feedback_router)
    app.include_router(illness_router)
    app.include_router(garmin_router)
    app.include_router(insights_router)
    app.include_router(sync_router)

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built SPA when present, with a fallback to ``index.html``.

    Declared after the API routers so ``/api/*``, ``/docs`` and ``/openapi.json``
    keep priority. The catch-all returns hashed build files by name (manifest,
    service worker, icons) and otherwise the SPA shell for client-side routes.
    """

    if not FRONTEND_DIST.is_dir():
        logger.info("No frontend build at %s — API only (dev uses the Vite proxy)", FRONTEND_DIST)
        return

    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = FRONTEND_DIST / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        # Unknown API/doc paths must stay 404 (JSON), not fall back to the shell.
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST):
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
