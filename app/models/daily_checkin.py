"""The ``DailyCheckin`` ORM model — subjective daily self-report."""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin, _uuid


class DailyCheckin(Base, TimestampMixin):
    """A subjective daily check-in (form, motivation, fatigue) for one athlete/day."""

    __tablename__ = "daily_checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    form_vs_normal: Mapped[int] = mapped_column(Integer, nullable=False)
    motivation: Mapped[int] = mapped_column(Integer, nullable=False)
    fatigue: Mapped[int] = mapped_column(Integer, nullable=False)
    # Optional subjective stress vs a normal day, -2..2 (nullable: optional input).
    stress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synced_to_coachagent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "form_vs_normal >= -2 AND form_vs_normal <= 2",
            name="ck_daily_checkins_form_vs_normal",
        ),
        CheckConstraint(
            "motivation >= -2 AND motivation <= 2", name="ck_daily_checkins_motivation"
        ),
        CheckConstraint("fatigue >= 1 AND fatigue <= 5", name="ck_daily_checkins_fatigue"),
        CheckConstraint(
            "stress IS NULL OR (stress >= -2 AND stress <= 2)", name="ck_daily_checkins_stress"
        ),
        UniqueConstraint("user_id", "date", name="uq_daily_checkins_user_date"),
        Index("ix_daily_checkins_user_id_date", "user_id", text("date DESC")),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<DailyCheckin id={self.id!r} user_id={self.user_id!r} date={self.date!r}>"
