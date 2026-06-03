"""Pydantic schemas for niggles and their trajectory reports."""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BodyRegion, MechanicalPattern, PainType, Side, Timing

IsNewOrRecurrent = Literal["new", "recurrent", "unknown"]


class ReportCreate(BaseModel):
    """Request body to record one trajectory update on a niggle."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-06-04",
                "intensity": 4,
                "pain_type": "sharp",
                "mechanical_pattern": "downhill",
                "timing": "during",
                "is_new_or_recurrent": "recurrent",
                "linked_activity_id": "act_12345",
                "notes": "Tightens up on descents.",
            }
        }
    )

    date: date_ | None = Field(default=None, description="Report day; defaults to today.")
    intensity: int = Field(ge=0, le=10, description="Pain intensity, 0 (none) to 10 (worst).")
    pain_type: PainType | None = None
    mechanical_pattern: MechanicalPattern | None = None
    timing: Timing | None = None
    is_new_or_recurrent: IsNewOrRecurrent = Field(
        description="Whether the complaint is new, recurrent, or of unknown history."
    )
    linked_activity_id: str | None = Field(
        default=None, max_length=64, description="Optional CoachAgent activity reference."
    )
    notes: str | None = None


class NiggleCreate(BaseModel):
    """Request body to open a niggle, optionally with a first report."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "region": "knee_anterior",
                "side": "left",
                "structure": "tendon rotulien",
                "notes": "Felt it after the long run.",
                "opened_at": "2026-06-04",
                "initial_report": {
                    "intensity": 3,
                    "is_new_or_recurrent": "new",
                    "timing": "after",
                },
            }
        }
    )

    region: BodyRegion = Field(description="Body region (immutable once created).")
    side: Side = Field(description="Body side (immutable once created).")
    structure: str | None = Field(
        default=None, max_length=100, description="Free-text anatomical detail."
    )
    notes: str | None = None
    opened_at: date_ | None = Field(default=None, description="Open date; defaults to today.")
    initial_report: ReportCreate | None = Field(
        default=None, description="Optional first report, created in the same transaction."
    )


class NigglePatch(BaseModel):
    """Partial update of a niggle. ``region`` / ``side`` are immutable.

    Any extra key (including ``region`` or ``side``) is rejected with ``422``.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"closed_at": "2026-06-20"}},
    )

    closed_at: date_ | None = Field(default=None, description="Close date; ``null`` reopens.")
    structure: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class ReportOut(BaseModel):
    """A persisted niggle report."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    niggle_id: str
    date: date_
    intensity: int
    pain_type: PainType | None
    mechanical_pattern: MechanicalPattern | None
    timing: Timing | None
    is_new_or_recurrent: str
    linked_activity_id: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class NiggleOut(BaseModel):
    """A niggle summary without embedded reports (used in list views)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    opened_at: date_
    closed_at: date_ | None
    region: BodyRegion
    side: Side
    structure: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class NiggleWithReportsOut(NiggleOut):
    """A niggle with its reports embedded (date ascending)."""

    reports: list[ReportOut]
