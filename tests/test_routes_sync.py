"""Sync route: auth, standalone no-op, user scoping, and the live push (respx)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from datetime import date as date_

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.main import app
from app.models.daily_checkin import DailyCheckin
from app.models.enums import Affect, FeedbackSource
from app.models.session_feedback import SessionFeedback
from app.models.user import User
from app.security import create_access_token, hash_password

_DAY = date_(2026, 6, 4)
_HASH = hash_password("supersecret123")


def _user(db: Session, email: str) -> tuple[User, dict[str, str]]:
    user = User(email=email, hashed_password=_HASH)
    db.add(user)
    db.commit()
    token, _ = create_access_token(subject=user.id)
    return user, {"Authorization": f"Bearer {token}"}


def _add_checkin(db: Session, user: User, day: date_ = _DAY) -> DailyCheckin:
    checkin = DailyCheckin(
        user_id=user.id,
        date=day,
        form_vs_normal=1,
        motivation=1,
        fatigue=2,
        reported_at=datetime.now(UTC),
    )
    db.add(checkin)
    db.commit()
    return checkin


def _add_feedback(db: Session, user: User, activity_id: str = "a1") -> SessionFeedback:
    feedback = SessionFeedback(
        user_id=user.id,
        activity_id=activity_id,
        rpe=7,
        affect=Affect.STRONG,
        source=FeedbackSource.APP_MANUAL,
        reported_at=datetime.now(UTC),
    )
    db.add(feedback)
    db.commit()
    return feedback


@pytest.fixture
def live_settings() -> Iterator[None]:
    """Point the engine at a (respx-mocked) live CoachAgent for the test."""

    settings = Settings(
        ENGINE_MODE="live",
        COACHAGENT_BASE_URL="https://coach.test",
        COACHAGENT_API_KEY="secret-key",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    yield
    app.dependency_overrides.pop(get_settings, None)


def test_sync_requires_auth(client: TestClient) -> None:
    assert client.post("/api/sync/coachagent").status_code == 401


def test_sync_standalone_is_noop(
    client: TestClient, db_session: Session, auth_headers: dict[str, str]
) -> None:
    # auth_headers already created the primary athlete; fetch it to attach rows.
    user = db_session.query(User).filter_by(email="athlete@example.com").one()
    checkin = _add_checkin(db_session, user)

    body = client.post("/api/sync/coachagent", headers=auth_headers).json()

    assert body == {"wellness_synced": 0, "feedback_synced": 0, "errors": []}
    db_session.refresh(checkin)
    assert checkin.synced_to_coachagent is False  # backlog preserved


@respx.mock
def test_sync_live_pushes_and_counts(
    client: TestClient, db_session: Session, live_settings: None
) -> None:
    user, headers = _user(db_session, "live@example.com")
    checkin = _add_checkin(db_session, user)
    feedback = _add_feedback(db_session, user)
    respx.post("https://coach.test/api/v1/wellness/daily").mock(return_value=httpx.Response(200))
    respx.post("https://coach.test/api/v1/feedback/session").mock(return_value=httpx.Response(200))

    body = client.post("/api/sync/coachagent", headers=headers).json()

    assert body == {"wellness_synced": 1, "feedback_synced": 1, "errors": []}
    db_session.refresh(checkin)
    db_session.refresh(feedback)
    assert checkin.synced_to_coachagent is True
    assert feedback.synced_to_coachagent is True


@respx.mock
def test_sync_live_is_user_scoped(
    client: TestClient, db_session: Session, live_settings: None
) -> None:
    owner, _ = _user(db_session, "owner@example.com")
    _, intruder_headers = _user(db_session, "intruder@example.com")
    owner_checkin = _add_checkin(db_session, owner)
    respx.post("https://coach.test/api/v1/wellness/daily").mock(return_value=httpx.Response(200))

    body = client.post("/api/sync/coachagent", headers=intruder_headers).json()

    assert body["wellness_synced"] == 0  # intruder has no rows of their own
    db_session.refresh(owner_checkin)
    assert owner_checkin.synced_to_coachagent is False  # owner's row untouched
