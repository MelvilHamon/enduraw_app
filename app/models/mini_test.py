"""The ``MiniTest`` ORM model — neuromuscular micro-tests (jump / reaction)."""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import MiniTestType
from app.models.mixins import TimestampMixin, _uuid, str_enum


class MiniTest(Base, TimestampMixin):
    """A neuromuscular mini-test result for one athlete.

    The shape of ``payload`` depends on ``type``:

    * ``type == "jump"``     → ``{"flight_time_ms": int, "height_cm": float}``
    * ``type == "reaction"`` → ``{"mean_rt_ms": float, "sd_rt_ms": float, "n_taps": int}``

    Typed validation of the payload is performed Pydantic-side in step 3; the ORM
    stores it as opaque JSON.
    """

    __tablename__ = "mini_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[MiniTestType] = mapped_column(str_enum(MiniTestType), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        Index("ix_mini_tests_user_id_type_date", "user_id", "type", text("date DESC")),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<MiniTest id={self.id!r} user_id={self.user_id!r} type={self.type!r}>"
