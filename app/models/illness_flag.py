"""The ``IllnessFlag`` ORM model — illness symptom flags, one row per athlete/day."""

from __future__ import annotations

from datetime import date as date_

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin, _uuid


class IllnessFlag(Base, TimestampMixin):
    """A daily illness flag for one athlete.

    ``symptoms`` is a JSON ``list[str]`` whose values correspond to
    :class:`app.models.enums.IllnessSymptom` members.
    """

    __tablename__ = "illness_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    symptoms: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    watch_hint_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_illness_flags_user_date"),
        Index("ix_illness_flags_user_id_date", "user_id", text("date DESC")),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<IllnessFlag id={self.id!r} user_id={self.user_id!r} date={self.date!r}>"
