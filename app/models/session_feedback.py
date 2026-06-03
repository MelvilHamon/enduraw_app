"""The ``SessionFeedback`` ORM model — post-session RPE + affect."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from app.models.enums import Affect, FeedbackSource
from app.models.mixins import TimestampMixin, _uuid, str_enum


class SessionFeedback(Base, TimestampMixin):
    """RPE + affect captured after a session, from the watch or the app."""

    __tablename__ = "session_feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # External CoachAgent activity reference.
    activity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rpe: Mapped[int] = mapped_column(Integer, nullable=False)
    affect: Mapped[Affect] = mapped_column(str_enum(Affect), nullable=False)
    source: Mapped[FeedbackSource] = mapped_column(str_enum(FeedbackSource), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synced_to_coachagent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("rpe >= 1 AND rpe <= 10", name="ck_session_feedbacks_rpe"),
        UniqueConstraint("user_id", "activity_id", name="uq_session_feedbacks_user_activity"),
        Index("ix_session_feedbacks_user_id_reported_at", "user_id", text("reported_at DESC")),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<SessionFeedback id={self.id!r} user_id={self.user_id!r} rpe={self.rpe!r}>"
