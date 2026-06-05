"""Unit tests for the write-only sync service (mode-agnostic, per-row isolation)."""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.engines.errors import EngineUpstreamError
from app.engines.schemas import PushOutcome, SessionFeedbackPayload, WellnessDailyPayload
from app.models.daily_checkin import DailyCheckin
from app.models.enums import Affect, BodyRegion, FeedbackSource, Side
from app.models.niggle import Niggle
from app.models.session_feedback import SessionFeedback
from app.models.user import User
from app.services import sync_service

_DAY = date_(2026, 6, 4)


class FakeEngine:
    """Stand-in EnginePort recording pushes; configurable outcome / failures."""

    def __init__(self, outcome: PushOutcome = "sent", fail_on: set[object] | None = None) -> None:
        self._outcome = outcome
        self._fail_on = fail_on or set()
        self.wellness: list[WellnessDailyPayload] = []
        self.feedback: list[SessionFeedbackPayload] = []

    async def push_wellness_daily(self, payload: WellnessDailyPayload) -> PushOutcome:
        if payload.date in self._fail_on:
            raise EngineUpstreamError("boom")
        self.wellness.append(payload)
        return self._outcome

    async def push_session_feedback(self, payload: SessionFeedbackPayload) -> PushOutcome:
        if payload.activity_id in self._fail_on:
            raise EngineUpstreamError("boom")
        self.feedback.append(payload)
        return self._outcome


def _user(db: Session, email: str = "athlete@example.com") -> User:
    user = User(email=email, hashed_password="x")
    db.add(user)
    db.commit()
    return user


def _checkin(db: Session, user: User, day: date_ = _DAY) -> DailyCheckin:
    checkin = DailyCheckin(
        user_id=user.id,
        date=day,
        form_vs_normal=1,
        motivation=4,
        fatigue=2,
        reported_at=datetime.now(UTC),
    )
    db.add(checkin)
    db.commit()
    return checkin


def _feedback(db: Session, user: User, activity_id: str = "a1") -> SessionFeedback:
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


def _niggle(db: Session, user: User, opened: date_, closed: date_ | None) -> None:
    db.add(
        Niggle(
            user_id=user.id,
            opened_at=opened,
            closed_at=closed,
            region=BodyRegion.KNEE_ANTERIOR,
            side=Side.LEFT,
        )
    )
    db.commit()


# --- sync_checkin / sync_feedback flag handling -----------------------------


async def test_sync_checkin_sets_flags_on_sent(db_session: Session) -> None:
    user = _user(db_session)
    checkin = _checkin(db_session, user)

    outcome = await sync_service.sync_checkin(db_session, user, checkin, FakeEngine("sent"))

    assert outcome == "sent"
    assert checkin.synced_to_coachagent is True
    assert checkin.synced_at is not None


async def test_sync_checkin_skipped_leaves_flags(db_session: Session) -> None:
    user = _user(db_session)
    checkin = _checkin(db_session, user)

    outcome = await sync_service.sync_checkin(db_session, user, checkin, FakeEngine("skipped"))

    assert outcome == "skipped"
    assert checkin.synced_to_coachagent is False
    assert checkin.synced_at is None


async def test_sync_checkin_error_leaves_flags_false(db_session: Session) -> None:
    user = _user(db_session)
    checkin = _checkin(db_session, user)
    engine = FakeEngine(fail_on={_DAY})

    with pytest.raises(EngineUpstreamError):
        await sync_service.sync_checkin(db_session, user, checkin, engine)

    assert checkin.synced_to_coachagent is False
    assert checkin.synced_at is None


async def test_sync_feedback_sets_flags_and_payload(db_session: Session) -> None:
    user = _user(db_session)
    feedback = _feedback(db_session, user)
    engine = FakeEngine("sent")

    await sync_service.sync_feedback(db_session, user, feedback, engine)

    assert feedback.synced_to_coachagent is True
    assert engine.feedback[0].activity_id == "a1"
    assert engine.feedback[0].affect == "strong"


# --- active_niggles_count boundaries ----------------------------------------


@pytest.mark.parametrize(
    ("opened", "closed", "expected"),
    [
        (date_(2026, 6, 4), None, 1),  # opened == day, still open
        (date_(2026, 6, 3), None, 1),  # opened before, still open
        (date_(2026, 6, 5), None, 0),  # opened after the day
        (date_(2026, 6, 1), date_(2026, 6, 4), 0),  # closed == day → not active
        (date_(2026, 6, 1), date_(2026, 6, 5), 1),  # closed after the day → active
        (date_(2026, 6, 1), date_(2026, 6, 3), 0),  # closed before the day
    ],
)
async def test_active_niggles_count_boundaries(
    db_session: Session, opened: date_, closed: date_ | None, expected: int
) -> None:
    user = _user(db_session)
    _niggle(db_session, user, opened, closed)

    assert sync_service.active_niggles_count(db_session, user.id, _DAY) == expected


async def test_checkin_payload_carries_active_niggles(db_session: Session) -> None:
    user = _user(db_session)
    checkin = _checkin(db_session, user)
    _niggle(db_session, user, date_(2026, 6, 1), None)
    _niggle(db_session, user, date_(2026, 6, 2), date_(2026, 6, 10))
    engine = FakeEngine("sent")

    await sync_service.sync_checkin(db_session, user, checkin, engine)

    assert engine.wellness[0].active_niggles == 2


# --- flush_user -------------------------------------------------------------


async def test_flush_pushes_only_unsynced_and_is_idempotent(db_session: Session) -> None:
    user = _user(db_session)
    _checkin(db_session, user, date_(2026, 6, 3))
    _checkin(db_session, user, date_(2026, 6, 4))
    _feedback(db_session, user, "a1")
    engine = FakeEngine("sent")

    first = await sync_service.flush_user(db_session, user, engine)
    assert (first.wellness_synced, first.feedback_synced, first.errors) == (2, 1, [])

    # Second flush with no changes: nothing left unsynced.
    second = await sync_service.flush_user(db_session, user, FakeEngine("sent"))
    assert (second.wellness_synced, second.feedback_synced) == (0, 0)


async def test_flush_skipped_leaves_backlog(db_session: Session) -> None:
    user = _user(db_session)
    checkin = _checkin(db_session, user)
    engine = FakeEngine("skipped")

    result = await sync_service.flush_user(db_session, user, engine)

    assert result.wellness_synced == 0
    assert checkin.synced_to_coachagent is False
    # Re-flushing still finds the row (true no-op preserves the backlog).
    assert len(engine.wellness) == 1
    again = await sync_service.flush_user(db_session, user, engine)
    assert again.wellness_synced == 0
    assert len(engine.wellness) == 2


async def test_flush_error_isolation(db_session: Session) -> None:
    user = _user(db_session)
    _feedback(db_session, user, "ok-1")
    _feedback(db_session, user, "boom")
    _feedback(db_session, user, "ok-2")
    engine = FakeEngine(fail_on={"boom"})

    result = await sync_service.flush_user(db_session, user, engine)

    assert result.feedback_synced == 2  # the two good rows still went through
    assert len(result.errors) == 1
    assert "boom" in result.errors[0]
    synced = {f.activity_id for f in engine.feedback}
    assert synced == {"ok-1", "ok-2"}


# --- background-task wrapper -------------------------------------------------


async def test_run_checkin_sync_wrapper(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _user(db_session)
    checkin = _checkin(db_session, user)
    checkin_id, user_id = checkin.id, user.id
    engine = FakeEngine("sent")
    # The wrapper opens its own session + engine; point both at the test doubles.
    # It closes the session in its finally, so read the flag back column-wise.
    monkeypatch.setattr(sync_service, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(sync_service, "get_engine", lambda u, s: engine)

    await sync_service.run_checkin_sync(checkin_id, user_id, Settings())

    assert len(engine.wellness) == 1
    db_session.expunge_all()
    synced = db_session.scalar(
        select(DailyCheckin.synced_to_coachagent).where(DailyCheckin.id == checkin_id)
    )
    assert synced is True
