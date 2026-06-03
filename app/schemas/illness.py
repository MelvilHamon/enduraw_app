"""Pydantic schemas for athlete-confirmed illness flags."""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IllnessSymptom


class IllnessCreate(BaseModel):
    """Request body to record (and upsert) an illness flag for a day."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-06-04",
                "symptoms": ["sore_throat", "unusual_fatigue"],
                "notes": "Started last night.",
            }
        }
    )

    date: date_ | None = Field(default=None, description="Day of illness; defaults to today.")
    symptoms: list[IllnessSymptom] = Field(
        min_length=1, description="At least one reported symptom."
    )
    notes: str | None = None


class IllnessOut(BaseModel):
    """A persisted illness flag."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    date: date_
    symptoms: list[IllnessSymptom]
    watch_hint_triggered: bool
    confirmed_by_user: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
