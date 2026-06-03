"""The ``Niggle`` and ``NiggleReport`` ORM models — persistent-complaint tracking.

A *niggle* is an open/close container for a nagging body complaint; each update
event on its trajectory is recorded as a *niggle report*. The two share a strong
one-to-many relationship, hence they live in the same module.
"""

from __future__ import annotations

from datetime import date as date_

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import BodyRegion, MechanicalPattern, PainType, Side, Timing
from app.models.mixins import TimestampMixin, _uuid, str_enum


class Niggle(Base, TimestampMixin):
    """An open (or closed) nagging body complaint for one athlete."""

    __tablename__ = "niggles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opened_at: Mapped[date_] = mapped_column(Date, nullable=False)
    closed_at: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    region: Mapped[BodyRegion] = mapped_column(str_enum(BodyRegion), nullable=False)
    side: Mapped[Side] = mapped_column(str_enum(Side), nullable=False)
    # Free-text anatomical detail, e.g. "tendon rotulien".
    structure: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reports: Mapped[list[NiggleReport]] = relationship(
        back_populates="niggle",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="NiggleReport.date",
    )

    __table_args__ = (
        Index("ix_niggles_user_id_opened_at", "user_id", text("opened_at DESC")),
        # Supports querying active niggles (closed_at IS NULL) for a user.
        Index("ix_niggles_user_id_closed_at", "user_id", "closed_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Niggle id={self.id!r} region={self.region!r} side={self.side!r}>"


class NiggleReport(Base, TimestampMixin):
    """One trajectory update event for a :class:`Niggle`."""

    __tablename__ = "niggle_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    niggle_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("niggles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    pain_type: Mapped[PainType | None] = mapped_column(str_enum(PainType), nullable=True)
    mechanical_pattern: Mapped[MechanicalPattern | None] = mapped_column(
        str_enum(MechanicalPattern), nullable=True
    )
    timing: Mapped[Timing | None] = mapped_column(str_enum(Timing), nullable=True)
    # "new" | "recurrent" | "unknown".
    is_new_or_recurrent: Mapped[str] = mapped_column(String(20), nullable=False)
    # External CoachAgent activity reference, when the report is tied to a session.
    linked_activity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    niggle: Mapped[Niggle] = relationship(back_populates="reports")

    __table_args__ = (
        CheckConstraint("intensity >= 0 AND intensity <= 10", name="ck_niggle_reports_intensity"),
        Index("ix_niggle_reports_niggle_id_date", "niggle_id", text("date DESC")),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<NiggleReport id={self.id!r} niggle_id={self.niggle_id!r} date={self.date!r}>"
