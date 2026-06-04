"""Select and build the engine backend from settings (+ FastAPI wiring)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.auth.deps import get_current_user
from app.config import Settings, get_settings
from app.engines.coach_agent import CoachAgentEngine
from app.engines.errors import EngineConfigError
from app.engines.mock import MockEngine
from app.engines.port import EnginePort
from app.models.user import User


def get_engine(user: User, settings: Settings) -> EnginePort:
    """Return the engine for ``user`` per ``settings.ENGINE_MODE``.

    ``mock`` serves the user's local snapshot; ``live`` talks to CoachAgent and
    requires both ``COACHAGENT_BASE_URL`` and ``COACHAGENT_API_KEY`` (else
    :class:`~app.engines.errors.EngineConfigError`).
    """

    if settings.ENGINE_MODE == "mock":
        return MockEngine(user.id, settings.MOCK_ENGINE_DIR)

    if not settings.COACHAGENT_BASE_URL or not settings.COACHAGENT_API_KEY:
        raise EngineConfigError(
            "ENGINE_MODE=live requires COACHAGENT_BASE_URL and COACHAGENT_API_KEY."
        )
    return CoachAgentEngine(
        base_url=settings.COACHAGENT_BASE_URL,
        api_key=settings.COACHAGENT_API_KEY,
        timeout_s=settings.COACHAGENT_TIMEOUT_S,
        max_retries=settings.COACHAGENT_MAX_RETRIES,
    )


async def engine_dependency(
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[EnginePort]:
    """FastAPI dependency yielding a per-request engine, closing it afterwards."""

    engine = get_engine(current_user, settings)
    try:
        yield engine
    finally:
        aclose = getattr(engine, "aclose", None)
        if aclose is not None:
            await aclose()


EngineDep = Annotated[EnginePort, Depends(engine_dependency)]
