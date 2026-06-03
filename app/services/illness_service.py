"""Business logic for illness flags (upsert by ``(user_id, date)``)."""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.illness_flag import IllnessFlag
from app.schemas.illness import IllnessCreate


def upsert_illness(db: Session, user_id: str, payload: IllnessCreate) -> tuple[IllnessFlag, bool]:
    """Create or update the illness flag for ``(user_id, date)``.

    The athlete is posting it, so ``confirmed_by_user`` is always ``True`` and
    ``watch_hint_triggered`` stays ``False`` (set by ingestion in a later step).
    Returns ``(flag, created)``.
    """

    day = payload.date or datetime.now(UTC).date()
    symptoms = [symptom.value for symptom in payload.symptoms]
    existing = db.scalar(
        select(IllnessFlag).where(
            IllnessFlag.user_id == user_id,
            IllnessFlag.date == day,
        )
    )
    if existing is not None:
        existing.symptoms = symptoms
        existing.notes = payload.notes
        existing.confirmed_by_user = True
        db.commit()
        db.refresh(existing)
        return existing, False

    flag = IllnessFlag(
        user_id=user_id,
        date=day,
        symptoms=symptoms,
        notes=payload.notes,
        confirmed_by_user=True,
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag, True


def list_illness(
    db: Session,
    user_id: str,
    *,
    date_from: date_ | None,
    date_to: date_ | None,
    limit: int,
    offset: int,
) -> list[IllnessFlag]:
    """List the user's illness flags, newest first, within an optional date window."""

    stmt = select(IllnessFlag).where(IllnessFlag.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(IllnessFlag.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(IllnessFlag.date <= date_to)
    stmt = stmt.order_by(IllnessFlag.date.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
