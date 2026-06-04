"""Business logic for the Garmin (faked) ingestion path.

This is the channel by which wearable-derived data enters the system: daily
wellness metrics (``daily_metrics``) and on-watch session RPE
(``session_feedbacks`` with ``source == garmin_watch``). Ingesting daily metrics
also (re)computes the illness *watch hint* for each affected day and reflects it
onto the corresponding ``illness_flags`` row.
"""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_metric import DailyMetric
from app.models.enums import FeedbackSource
from app.models.session_feedback import SessionFeedback
from app.schemas.garmin import GarminDaily, GarminSessionFeedback
from app.services import illness_service

_DAILY_FIELDS = (
    "sleep_score",
    "sleep_duration_min",
    "sleep_onset",
    "sleep_wake",
    "hrv_rmssd",
    "hrv_status",
    "rhr",
    "stress",
    "body_battery",
    "resp_rate",
    "training_readiness",
    "vo2max",
    "source",
)


def ingest_daily(db: Session, user_id: str, rows: list[GarminDaily]) -> tuple[int, int]:
    """UPSERT daily metrics, then refresh the watch-hint for each ingested day.

    Returns ``(daily_upserted, illness_flags_set)`` where ``illness_flags_set``
    counts the days whose ``watch_hint_triggered`` ended up ``True``. The hint is
    computed only after every row is persisted, so days within the same batch
    contribute to one another's rolling baseline.
    """

    for row in rows:
        existing = db.scalar(
            select(DailyMetric).where(DailyMetric.user_id == user_id, DailyMetric.date == row.date)
        )
        if existing is not None:
            for field in _DAILY_FIELDS:
                setattr(existing, field, getattr(row, field))
        else:
            db.add(DailyMetric(user_id=user_id, date=row.date, **row.model_dump(exclude={"date"})))
    db.commit()

    flags_set = 0
    for day in {row.date for row in rows}:
        hint = illness_service.compute_hint(db, user_id, day)
        if illness_service.set_watch_hint(db, user_id, day, hint.triggered):
            flags_set += 1

    return len(rows), flags_set


def ingest_session_feedback(db: Session, user_id: str, rows: list[GarminSessionFeedback]) -> int:
    """UPSERT on-watch session feedback by ``(user_id, activity_id)``.

    ``source`` is always forced to ``garmin_watch``. Returns the row count.
    """

    for row in rows:
        reported_at = row.reported_at or datetime.now(UTC)
        existing = db.scalar(
            select(SessionFeedback).where(
                SessionFeedback.user_id == user_id,
                SessionFeedback.activity_id == row.activity_id,
            )
        )
        if existing is not None:
            existing.rpe = row.rpe
            existing.affect = row.affect
            existing.source = FeedbackSource.GARMIN_WATCH
            existing.reported_at = reported_at
        else:
            db.add(
                SessionFeedback(
                    user_id=user_id,
                    activity_id=row.activity_id,
                    rpe=row.rpe,
                    affect=row.affect,
                    source=FeedbackSource.GARMIN_WATCH,
                    reported_at=reported_at,
                )
            )
    db.commit()
    return len(rows)


def list_daily(
    db: Session,
    user_id: str,
    *,
    date_from: date_ | None,
    date_to: date_ | None,
    limit: int,
    offset: int,
) -> list[DailyMetric]:
    """List the user's daily metrics, newest first, within an optional window."""

    stmt = select(DailyMetric).where(DailyMetric.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(DailyMetric.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyMetric.date <= date_to)
    stmt = stmt.order_by(DailyMetric.date.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())
