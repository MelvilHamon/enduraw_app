"""Pydantic schemas for the Garmin (faked) ingestion path.

These mirror the wearable-derived data that enters the system: daily wellness
metrics (``daily_metrics``) and on-watch session RPE (``session_feedbacks`` with
``source == garmin_watch``). The shapes match the generator output in
``app/synth`` so a :class:`~app.synth.dataset.SyntheticDataset` can be ingested
as-is.
"""

from __future__ import annotations

from datetime import date as date_
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Affect, HrvStatus


class GarminDaily(BaseModel):
    """One day of faked Garmin wellness metrics (mirrors ``DailyMetric``)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-06-04",
                "sleep_score": 78,
                "sleep_duration_min": 432,
                "hrv_rmssd": 62.4,
                "hrv_status": "normal",
                "rhr": 48,
                "stress": 31,
                "body_battery": 74,
                "resp_rate": 14.2,
                "training_readiness": 69,
                "vo2max": 58.1,
            }
        }
    )

    date: date_ = Field(description="The day these metrics describe.")
    sleep_score: int | None = Field(default=None, ge=0, le=100)
    sleep_duration_min: int | None = Field(default=None, ge=0)
    sleep_onset: datetime | None = None
    sleep_wake: datetime | None = None
    hrv_rmssd: float | None = Field(default=None, ge=0)
    hrv_status: HrvStatus | None = None
    rhr: int | None = Field(default=None, ge=0)
    stress: int | None = Field(default=None, ge=0, le=100)
    body_battery: int | None = Field(default=None, ge=0, le=100)
    resp_rate: float | None = Field(default=None, ge=0)
    training_readiness: int | None = Field(default=None, ge=0, le=100)
    vo2max: float | None = Field(default=None, ge=0)
    source: str = Field(default="garmin_faked", max_length=32)


class GarminSessionFeedback(BaseModel):
    """On-watch RPE + affect for a CoachAgent activity (source garmin_watch)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "activity_id": "synth-7-2026-06-04",
                "rpe": 6,
                "affect": "neutral",
                "reported_at": "2026-06-04T17:30:00Z",
            }
        }
    )

    activity_id: str = Field(max_length=64, description="CoachAgent activity reference.")
    rpe: int = Field(ge=1, le=10, description="Rate of perceived exertion, 1 (easy) to 10 (max).")
    affect: Affect = Field(description="Post-session affect: weak, neutral or strong.")
    reported_at: datetime | None = Field(
        default=None, description="When the RPE was logged on the watch; defaults to now."
    )


class GarminIngestRequest(BaseModel):
    """A batch of faked Garmin data to ingest for the authenticated athlete."""

    daily: list[GarminDaily] = Field(default_factory=list)
    sessions: list[GarminSessionFeedback] = Field(default_factory=list)


class GarminIngestResponse(BaseModel):
    """Outcome of an ingestion call."""

    daily_upserted: int
    sessions_upserted: int
    illness_flags_set: int


class DailyMetricOut(BaseModel):
    """A persisted daily wellness snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    date: date_
    sleep_score: int | None
    sleep_duration_min: int | None
    sleep_onset: datetime | None
    sleep_wake: datetime | None
    hrv_rmssd: float | None
    hrv_status: HrvStatus | None
    rhr: int | None
    stress: int | None
    body_battery: int | None
    resp_rate: float | None
    training_readiness: int | None
    vo2max: float | None
    source: str
    created_at: datetime
    updated_at: datetime


class IllnessHintOut(BaseModel):
    """The watch-hint computation for one day (vs the athlete's rolling baseline)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "triggered": True,
                "hrv_delta": -18.3,
                "rhr_delta": 9.1,
                "resp_delta": 3.4,
                "baseline_window_days": 14,
            }
        }
    )

    triggered: bool
    hrv_delta: float | None
    rhr_delta: float | None
    resp_delta: float | None
    baseline_window_days: int
