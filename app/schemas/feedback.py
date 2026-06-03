"""Pydantic schemas for post-session feedback (RPE + affect)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Affect, FeedbackSource


class SessionFeedbackCreate(BaseModel):
    """Request body to record (and upsert) feedback for one activity."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "activity_id": "act_12345",
                "rpe": 7,
                "affect": "neutral",
                "reported_at": "2026-06-04T18:05:00Z",
            }
        }
    )

    activity_id: str = Field(
        max_length=64, description="CoachAgent activity reference this feedback is for."
    )
    rpe: int = Field(ge=1, le=10, description="Rate of perceived exertion, 1 (easy) to 10 (max).")
    affect: Affect = Field(description="Post-session affect: weak, neutral or strong.")
    reported_at: datetime | None = Field(
        default=None, description="When the feedback was given; defaults to now."
    )


class SessionFeedbackOut(BaseModel):
    """A persisted session feedback entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    activity_id: str
    rpe: int
    affect: Affect
    source: FeedbackSource
    reported_at: datetime
    created_at: datetime
    updated_at: datetime
