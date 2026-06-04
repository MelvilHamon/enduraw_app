"""Engine factory: mode switch and live-mode config validation."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.engines.coach_agent import CoachAgentEngine
from app.engines.errors import EngineConfigError
from app.engines.factory import get_engine
from app.engines.mock import MockEngine
from app.models.user import User


def _user() -> User:
    return User(id="user-1", email="a@example.com", hashed_password="x")


def test_mock_mode_returns_mock_engine() -> None:
    settings = Settings(ENGINE_MODE="mock", MOCK_ENGINE_DIR="/tmp/snaps")
    engine = get_engine(_user(), settings)
    assert isinstance(engine, MockEngine)


def test_live_mode_returns_coach_agent_engine() -> None:
    settings = Settings(
        ENGINE_MODE="live",
        COACHAGENT_BASE_URL="https://coach.test",
        COACHAGENT_API_KEY="secret",
    )
    engine = get_engine(_user(), settings)
    assert isinstance(engine, CoachAgentEngine)


@pytest.mark.parametrize(
    "overrides",
    [
        {"COACHAGENT_BASE_URL": "https://coach.test"},  # missing key
        {"COACHAGENT_API_KEY": "secret"},  # missing URL
        {},  # missing both
    ],
)
def test_live_mode_missing_config_raises(overrides: dict[str, str]) -> None:
    settings = Settings(ENGINE_MODE="live", **overrides)
    with pytest.raises(EngineConfigError):
        get_engine(_user(), settings)
