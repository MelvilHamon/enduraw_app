"""The ``DailyMetric`` ORM model — faked Garmin wellness, one row per athlete/day."""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import HrvStatus
from app.models.mixins import TimestampMixin, _uuid, str_enum


class DailyMetric(Base, TimestampMixin):
    """A daily wellness snapshot (mocked Garmin data) for one athlete.

    Score-like integer columns (``sleep_score``, ``stress``, ``body_battery``,
    ``training_readiness``) are conceptually bounded to ``0..100``. These ranges
    are not enforced with CHECK constraints at this step — validation lands
    Pydantic-side in step 3.
    """

    __tablename__ = "daily_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    sleep_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_onset: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sleep_wake: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hrv_rmssd: Mapped[float | None] = mapped_column(Float, nullable=True)
    hrv_status: Mapped[HrvStatus | None] = mapped_column(str_enum(HrvStatus), nullable=True)
    rhr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_battery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resp_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_readiness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vo2max: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="garmin_faked", nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_metrics_user_date"),
        Index("ix_daily_metrics_user_id_date", "user_id", text("date DESC")),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<DailyMetric id={self.id!r} user_id={self.user_id!r} date={self.date!r}>"
