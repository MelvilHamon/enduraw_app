"""Pydantic schemas for neuromuscular mini-tests (discriminated on ``type``)."""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MiniTestType
from app.models.mini_test import MiniTest


class JumpData(BaseModel):
    """Counter-movement jump result."""

    type: Literal["jump"]
    flight_time_ms: int = Field(ge=0, description="Flight time in milliseconds.")
    height_cm: float = Field(ge=0, description="Estimated jump height in centimetres.")


class ReactionData(BaseModel):
    """Reaction-time (tap) test result."""

    type: Literal["reaction"]
    mean_rt_ms: float = Field(ge=0, description="Mean reaction time in milliseconds.")
    sd_rt_ms: float = Field(ge=0, description="Reaction-time standard deviation (ms).")
    n_taps: int = Field(ge=0, description="Number of taps recorded.")


MiniTestData = Annotated[JumpData | ReactionData, Field(discriminator="type")]


class MiniTestCreate(BaseModel):
    """Request body for a mini-test. ``data`` is discriminated by its ``type``."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-06-04",
                "reported_at": "2026-06-04T07:30:00Z",
                "data": {"type": "jump", "flight_time_ms": 480, "height_cm": 28.3},
            }
        }
    )

    date: date_ = Field(description="Calendar day of the test (ISO YYYY-MM-DD).")
    reported_at: datetime = Field(description="When the result was recorded.")
    data: MiniTestData


class MiniTestOut(BaseModel):
    """A persisted mini-test. ``data`` carries the type-specific payload."""

    id: str
    date: date_
    reported_at: datetime
    type: MiniTestType
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, mt: MiniTest) -> MiniTestOut:
        return cls(
            id=mt.id,
            date=mt.date,
            reported_at=mt.reported_at,
            type=mt.type,
            data=mt.payload,
            created_at=mt.created_at,
            updated_at=mt.updated_at,
        )
