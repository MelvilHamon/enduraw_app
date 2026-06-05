"""Write-only sync of the app's subjective data back to the engine (CoachAgent).

The app owns the subjective truth (daily wellness, post-session RPE/affect) and
niggles; this layer pushes it to the engine so its model can factor it in. Reads
the unsynced rows, pushes each through the :class:`~app.engines.port.EnginePort`
and — only when the engine reports ``sent`` — marks the row synced. Niggles are
not pushed individually: their effect is the ``active_niggles`` counter inside
the wellness payload.

Functions are ``async`` (the engine port is async) but use the existing sync
``Session``, mirroring the step-7 fusion service. They stay backend-agnostic: a
``skipped`` push (standalone / mock) leaves the row unsynced, so a later switch
to live would still flush the backlog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from datetime import date as date_

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import SessionLocal
from app.engines.errors import EngineError
from app.engines.factory import get_engine
from app.engines.port import EnginePort
from app.engines.schemas import PushOutcome, SessionFeedbackPayload, WellnessDailyPayload
from app.models.daily_checkin import DailyCheckin
from app.models.niggle import Niggle
from app.models.session_feedback import SessionFeedback
from app.models.user import User


@dataclass
class SyncResult:
    """Counts of rows actually pushed in a flush, plus per-row error messages."""

    wellness_synced: int = 0
    feedback_synced: int = 0
    errors: list[str] = field(default_factory=list)


def active_niggles_count(db: Session, user_id: str, day: date_) -> int:
    """Number of the user's niggles open on ``day``.

    A niggle counts when it was opened on/before ``day`` and is either still open
    or was closed strictly after ``day``.
    """

    count = db.scalar(
        select(func.count())
        .select_from(Niggle)
        .where(
            Niggle.user_id == user_id,
            Niggle.opened_at <= day,
            or_(Niggle.closed_at.is_(None), Niggle.closed_at > day),
        )
    )
    return count or 0


async def sync_checkin(
    db: Session, user: User, checkin: DailyCheckin, engine: EnginePort
) -> PushOutcome:
    """Push one daily checkin as wellness; mark it synced only when ``sent``."""

    payload = WellnessDailyPayload(
        date=checkin.date,
        form_vs_normal=checkin.form_vs_normal,
        motivation=checkin.motivation,
        fatigue=checkin.fatigue,
        active_niggles=active_niggles_count(db, user.id, checkin.date),
    )
    outcome = await engine.push_wellness_daily(payload)
    if outcome == "sent":
        checkin.synced_to_coachagent = True
        checkin.synced_at = datetime.now(UTC)
        db.commit()
    return outcome


async def sync_feedback(
    db: Session, user: User, feedback: SessionFeedback, engine: EnginePort
) -> PushOutcome:
    """Push one session feedback; mark it synced only when ``sent``."""

    payload = SessionFeedbackPayload(
        activity_id=feedback.activity_id,
        rpe=feedback.rpe,
        affect=feedback.affect.value,
        reported_at=feedback.reported_at,
    )
    outcome = await engine.push_session_feedback(payload)
    if outcome == "sent":
        feedback.synced_to_coachagent = True
        feedback.synced_at = datetime.now(UTC)
        db.commit()
    return outcome


async def flush_user(db: Session, user: User, engine: EnginePort) -> SyncResult:
    """Push every unsynced checkin + feedback for ``user``, isolating failures.

    Idempotent: only rows with ``synced_to_coachagent`` false are queried, so a
    second flush with no changes does nothing. Each row is pushed independently —
    one row's :class:`EngineError` is recorded and the rest still go through.
    """

    result = SyncResult()

    checkins = db.scalars(
        select(DailyCheckin)
        .where(
            DailyCheckin.user_id == user.id,
            DailyCheckin.synced_to_coachagent.is_(False),
        )
        .order_by(DailyCheckin.date)
    ).all()
    for checkin in checkins:
        try:
            if await sync_checkin(db, user, checkin, engine) == "sent":
                result.wellness_synced += 1
        except EngineError as exc:
            result.errors.append(f"checkin {checkin.id}: {exc}")

    feedbacks = db.scalars(
        select(SessionFeedback)
        .where(
            SessionFeedback.user_id == user.id,
            SessionFeedback.synced_to_coachagent.is_(False),
        )
        .order_by(SessionFeedback.reported_at)
    ).all()
    for feedback in feedbacks:
        try:
            if await sync_feedback(db, user, feedback, engine) == "sent":
                result.feedback_synced += 1
        except EngineError as exc:
            result.errors.append(f"feedback {feedback.id}: {exc}")

    return result


async def _close_engine(engine: EnginePort) -> None:
    aclose = getattr(engine, "aclose", None)
    if aclose is not None:
        await aclose()


async def run_checkin_sync(checkin_id: str, user_id: str, settings: Settings) -> None:
    """Background-task wrapper: push one checkin on its own session + engine.

    Best-effort — an :class:`EngineError` leaves the row unsynced, to be retried
    by the next flush. Manages the full lifecycle (session + engine) itself.
    """

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        checkin = db.get(DailyCheckin, checkin_id)
        if user is None or checkin is None or checkin.synced_to_coachagent:
            return
        engine = get_engine(user, settings)
        try:
            await sync_checkin(db, user, checkin, engine)
        except EngineError:
            pass
        finally:
            await _close_engine(engine)
    finally:
        db.close()


async def run_feedback_sync(feedback_id: str, user_id: str, settings: Settings) -> None:
    """Background-task wrapper: push one feedback on its own session + engine."""

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        feedback = db.get(SessionFeedback, feedback_id)
        if user is None or feedback is None or feedback.synced_to_coachagent:
            return
        engine = get_engine(user, settings)
        try:
            await sync_feedback(db, user, feedback, engine)
        except EngineError:
            pass
        finally:
            await _close_engine(engine)
    finally:
        db.close()
