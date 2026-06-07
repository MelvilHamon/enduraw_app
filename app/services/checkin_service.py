"""Business logic for daily checkins (upsert by ``(user_id, date)``)."""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_checkin import DailyCheckin
from app.schemas.checkin import CheckinCreate


def upsert_checkin(db: Session, user_id: str, payload: CheckinCreate) -> tuple[DailyCheckin, bool]:
    """Create or update the checkin for ``(user_id, payload.date)``.

    Returns ``(checkin, created)`` where ``created`` is ``True`` on insert.
    """

    existing = db.scalar(
        select(DailyCheckin).where(
            DailyCheckin.user_id == user_id,
            DailyCheckin.date == payload.date,
        )
    )
    if existing is not None:
        existing.form_vs_normal = payload.form_vs_normal
        existing.motivation = payload.motivation
        existing.fatigue = payload.fatigue
        existing.stress = payload.stress
        existing.reported_at = datetime.now(UTC)
        # The row changed: re-arm it for sync so the edit reaches CoachAgent.
        existing.synced_to_coachagent = False
        existing.synced_at = None
        db.commit()
        db.refresh(existing)
        return existing, False

    checkin = DailyCheckin(
        user_id=user_id,
        date=payload.date,
        form_vs_normal=payload.form_vs_normal,
        motivation=payload.motivation,
        fatigue=payload.fatigue,
        stress=payload.stress,
        reported_at=datetime.now(UTC),
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin, True


def get_today(db: Session, user_id: str) -> DailyCheckin | None:
    """Return today's checkin for the user, or ``None`` if not done yet."""

    today = datetime.now(UTC).date()
    return db.scalar(
        select(DailyCheckin).where(
            DailyCheckin.user_id == user_id,
            DailyCheckin.date == today,
        )
    )


def list_checkins(
    db: Session,
    user_id: str,
    *,
    date_from: date_ | None,
    date_to: date_ | None,
    limit: int,
    offset: int,
) -> list[DailyCheckin]:
    """Return the user's checkins, newest first, within an optional date window."""

    stmt = select(DailyCheckin).where(DailyCheckin.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(DailyCheckin.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyCheckin.date <= date_to)
    stmt = stmt.order_by(DailyCheckin.date.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
