"""Pydantic schemas for the daily checkin resource."""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckinCreate(BaseModel):
    """Request body to record (and upsert) a daily readiness checkin."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-06-04",
                "form_vs_normal": 1,
                "motivation": 1,
                "fatigue": 2,
                "stress": -1,
            }
        }
    )

    date: date_ = Field(description="Calendar day the checkin refers to (ISO YYYY-MM-DD).")
    form_vs_normal: int = Field(
        ge=-2,
        le=2,
        description="Subjective form vs a normal day, -2 (much worse) to +2 (much better).",
    )
    motivation: int = Field(
        ge=-2,
        le=2,
        description="Motivation vs a normal day, -2 (much lower) to +2 (much higher).",
    )
    fatigue: int = Field(ge=1, le=5, description="Perceived fatigue, 1 (fresh) to 5 (exhausted).")
    stress: int | None = Field(
        default=None,
        ge=-2,
        le=2,
        description="Optional subjective stress vs a normal day, -2 (much less) to +2 (much more).",
    )


class CheckinOut(BaseModel):
    """A persisted daily checkin."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    date: date_
    form_vs_normal: int
    motivation: int
    fatigue: int
    stress: int | None
    reported_at: datetime
    created_at: datetime
    updated_at: datetime
