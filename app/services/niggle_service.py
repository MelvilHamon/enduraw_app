"""Business logic for niggles and their reports."""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.niggle import Niggle, NiggleReport
from app.schemas.niggle import NiggleCreate, NigglePatch, ReportCreate


class NiggleClosedError(Exception):
    """Raised when adding a report to an already-closed niggle."""


def _today() -> date_:
    return datetime.now(UTC).date()


def _build_report(niggle_id: str, payload: ReportCreate) -> NiggleReport:
    return NiggleReport(
        niggle_id=niggle_id,
        date=payload.date or _today(),
        intensity=payload.intensity,
        pain_type=payload.pain_type,
        mechanical_pattern=payload.mechanical_pattern,
        timing=payload.timing,
        is_new_or_recurrent=payload.is_new_or_recurrent,
        linked_activity_id=payload.linked_activity_id,
        notes=payload.notes,
    )


def create_niggle(db: Session, user_id: str, payload: NiggleCreate) -> Niggle:
    """Open a niggle, optionally with a first report, in one transaction."""

    niggle = Niggle(
        user_id=user_id,
        opened_at=payload.opened_at or _today(),
        region=payload.region,
        side=payload.side,
        structure=payload.structure,
        notes=payload.notes,
    )
    db.add(niggle)
    db.flush()  # assign niggle.id before attaching the report
    if payload.initial_report is not None:
        db.add(_build_report(niggle.id, payload.initial_report))
    db.commit()
    db.refresh(niggle)
    return niggle


def get_owned(db: Session, user_id: str, niggle_id: str) -> Niggle | None:
    """Return the niggle only if it belongs to ``user_id`` (else ``None``)."""

    return db.scalar(select(Niggle).where(Niggle.id == niggle_id, Niggle.user_id == user_id))


def list_niggles(
    db: Session, user_id: str, *, active: bool, limit: int, offset: int
) -> list[Niggle]:
    """List the user's niggles, newest first. ``active`` keeps only open ones."""

    stmt = select(Niggle).where(Niggle.user_id == user_id)
    if active:
        stmt = stmt.where(Niggle.closed_at.is_(None))
    stmt = stmt.order_by(Niggle.opened_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def patch_niggle(db: Session, niggle: Niggle, payload: NigglePatch) -> Niggle:
    """Apply the provided fields (region/side are not patchable by construction)."""

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(niggle, field, value)
    db.commit()
    db.refresh(niggle)
    return niggle


def add_report(db: Session, niggle: Niggle, payload: ReportCreate) -> NiggleReport:
    """Append a report to an open niggle, or raise on a closed one."""

    if niggle.closed_at is not None:
        raise NiggleClosedError(niggle.id)
    report = _build_report(niggle.id, payload)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
