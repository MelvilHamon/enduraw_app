"""Backend-agnostic engine schemas (the shapes returned by every engine).

These describe the *external* training-engine truth (fitness / fatigue / form /
ACWR, the load timeseries and the activity log). The same shapes are produced by
the standalone :class:`~app.engines.mock.MockEngine` and parsed from the live
CoachAgent REST contract by :class:`~app.engines.coach_agent.CoachAgentEngine`,
so downstream code never branches on the backend.
"""

from __future__ import annotations

from datetime import date as date_
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReadinessHint = Literal["low", "neutral", "high"]

# Metrics that :class:`EngineTimeseries` can carry. ``load`` is the per-day
# training impulse; the rest are the Banister/ACWR latent series.
TimeseriesMetric = Literal["fitness", "fatigue", "form", "load", "acwr"]
TIMESERIES_METRICS: frozenset[str] = frozenset({"fitness", "fatigue", "form", "load", "acwr"})

# readiness_hint thresholds (calibrated against the Banister form scale).
_FORM_LOW = -10.0
_FORM_HIGH = 15.0
_ACWR_SWEET_LOW = 0.8
_ACWR_SWEET_HIGH = 1.3


def compute_readiness_hint(form: float, acwr: float | None) -> ReadinessHint:
    """Derive the readiness hint from ``form`` and ``acwr``.

    ``low`` when form is clearly negative; ``high`` only when form is clearly
    positive *and* the acute:chronic ratio sits in the safe band; ``neutral``
    otherwise (including when ``acwr`` is unknown).
    """

    if form < _FORM_LOW:
        return "low"
    if form > _FORM_HIGH and acwr is not None and _ACWR_SWEET_LOW <= acwr <= _ACWR_SWEET_HIGH:
        return "high"
    return "neutral"


class EngineState(BaseModel):
    """The engine's readiness snapshot for a single day."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-06-04",
                "fitness": 64.2,
                "fatigue": 9.1,
                "form": 14.1,
                "acwr": 1.05,
                "load_7d": 412.0,
                "load_28d": 1583.0,
                "trend_form_7d": 3.2,
                "readiness_hint": "neutral",
            }
        }
    )

    date: date_
    fitness: float
    fatigue: float
    form: float
    acwr: float | None
    load_7d: float
    load_28d: float
    trend_form_7d: float | None
    readiness_hint: ReadinessHint


class EnginePoint(BaseModel):
    """One ``(date, value)`` sample of a timeseries metric."""

    date: date_
    value: float | None


class EngineTimeseries(BaseModel):
    """A set of metric timeseries over a date window, keyed by metric name."""

    date_from: date_
    date_to: date_
    series: dict[str, list[EnginePoint]] = Field(default_factory=dict)


class EngineActivity(BaseModel):
    """A single training activity (session) from the engine's activity log."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "synth-7-2026-06-04",
                "date": "2026-06-04",
                "type": "tempo",
                "duration_s": 3600,
                "distance_m": 14200.0,
                "trimp": 92.5,
                "hr_tss": 78.0,
                "elevation_gain_m": 120.0,
            }
        }
    )

    id: str
    date: date_
    type: str
    duration_s: int
    distance_m: float
    trimp: float
    hr_tss: float
    elevation_gain_m: float
