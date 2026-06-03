"""Business logic for session feedback (upsert by ``(user_id, activity_id)``)."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import FeedbackSource
from app.models.session_feedback import SessionFeedback
from app.schemas.feedback import SessionFeedbackCreate


def _start_of(day: date_) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def upsert_feedback(
    db: Session, user_id: str, payload: SessionFeedbackCreate
) -> tuple[SessionFeedback, bool]:
    """Create or update feedback for ``(user_id, activity_id)``.

    ``source`` is always forced to ``app_manual`` in this step. Returns
    ``(feedback, created)``.
    """

    reported_at = payload.reported_at or datetime.now(UTC)
    existing = db.scalar(
        select(SessionFeedback).where(
            SessionFeedback.user_id == user_id,
            SessionFeedback.activity_id == payload.activity_id,
        )
    )
    if existing is not None:
        existing.rpe = payload.rpe
        existing.affect = payload.affect
        existing.source = FeedbackSource.APP_MANUAL
        existing.reported_at = reported_at
        db.commit()
        db.refresh(existing)
        return existing, False

    feedback = SessionFeedback(
        user_id=user_id,
        activity_id=payload.activity_id,
        rpe=payload.rpe,
        affect=payload.affect,
        source=FeedbackSource.APP_MANUAL,
        reported_at=reported_at,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback, True


def list_feedback(
    db: Session,
    user_id: str,
    *,
    activity_id: str | None,
    date_from: date_ | None,
    date_to: date_ | None,
    limit: int,
    offset: int,
) -> list[SessionFeedback]:
    """List the user's feedback, newest first, filtered by activity or date window."""

    stmt = select(SessionFeedback).where(SessionFeedback.user_id == user_id)
    if activity_id is not None:
        stmt = stmt.where(SessionFeedback.activity_id == activity_id)
    if date_from is not None:
        stmt = stmt.where(SessionFeedback.reported_at >= _start_of(date_from))
    if date_to is not None:
        stmt = stmt.where(SessionFeedback.reported_at < _start_of(date_to + timedelta(days=1)))
    stmt = stmt.order_by(SessionFeedback.reported_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
