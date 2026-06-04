"""Typed output dataclasses for the synthetic data generator.

These map 1:1 onto the ORM models (``app/models``) and the step-5 ingestion
payload. The module is named ``dataset`` — not ``models`` — to avoid any
collision with ``app.models`` (the DB layer). Nothing here touches the database:
the generator produces these structures purely in memory.

All dataclasses are ``frozen`` and use tuples for their collections so a whole
:class:`SyntheticDataset` is deeply immutable and structurally comparable — this
is what the determinism tests rely on (``generate(p, seed) == generate(p, seed)``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_
from datetime import datetime
from typing import Any

from app.models.enums import (
    Affect,
    BodyRegion,
    HrvStatus,
    IllnessSymptom,
    MechanicalPattern,
    MiniTestType,
    PainType,
    Side,
    Timing,
)

# ``is_new_or_recurrent`` mirrors the string stored on ``NiggleReport``.
IsNewOrRecurrent = str  # "new" | "recurrent" | "unknown"

# Latent niggle archetype label (debug / persona alignment only — not persisted).
NiggleArchetype = str  # "tendinopathy" | "bone_stress" | "muscle" | "ligament"


@dataclass(frozen=True)
class SyntheticSession:
    """A faked CoachAgent training activity.

    There is no ``Session`` ORM table — sessions are external CoachAgent
    activities referenced elsewhere by ``activity_id``. The RPE/affect fields
    feed the step-5 ``SessionFeedback`` ingestion; ``rpe_filled_on_watch``
    decides its ``source`` (``garmin_watch`` vs ``app_manual``). When RPE was
    not captured, ``rpe`` is ``None`` and no feedback row is written in step 5.
    """

    activity_id: str
    date: date_
    session_type: str
    duration_s: int
    distance_m: float
    elevation_gain_m: float
    trimp: float
    hr_tss: float
    rpe: int | None
    affect: Affect | None
    rpe_filled_on_watch: bool


@dataclass(frozen=True)
class SyntheticDailyMetric:
    """A faked Garmin daily wellness snapshot (one per day).

    Every numeric field respects the step-2.1 CHECK bounds on ``daily_metrics``:
    ``sleep_score``/``stress``/``body_battery``/``training_readiness`` in
    ``0..100``; the rest ``>= 0``.
    """

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
    source: str = "garmin_faked"


@dataclass(frozen=True)
class SyntheticCheckin:
    """A subjective daily check-in (the three taps)."""

    date: date_
    form_vs_normal: int  # -2..2
    motivation: int  # 1..5
    fatigue: int  # 1..5
    reported_at: datetime


@dataclass(frozen=True)
class SyntheticMiniTest:
    """A neuromuscular mini-test result.

    ``payload`` matches the discriminated shape validated in step 3:
    jump → ``{"flight_time_ms": int, "height_cm": float}``;
    reaction → ``{"mean_rt_ms": float, "sd_rt_ms": float, "n_taps": int}``.
    """

    date: date_
    reported_at: datetime
    type: MiniTestType
    payload: dict[str, Any]


@dataclass(frozen=True)
class SyntheticNiggleReport:
    """One trajectory update event on a niggle."""

    date: date_
    intensity: int  # 0..10
    pain_type: PainType | None
    mechanical_pattern: MechanicalPattern | None
    timing: Timing | None
    is_new_or_recurrent: IsNewOrRecurrent
    linked_activity_id: str | None
    notes: str | None = None


@dataclass(frozen=True)
class SyntheticNiggle:
    """An open/closed nagging complaint with its multi-report trajectory.

    ``archetype`` is the latent injury family that fixed the niggle's coherent
    ``(region, side, pain_type, mechanical_pattern, timing)`` — exposed for debug
    and persona alignment, never persisted.
    """

    opened_at: date_
    closed_at: date_ | None
    region: BodyRegion
    side: Side
    structure: str | None
    archetype: NiggleArchetype
    reports: tuple[SyntheticNiggleReport, ...]


@dataclass(frozen=True)
class SyntheticIllnessEpisode:
    """A latent illness episode degrading the wellness signal.

    The generator exposes episodes (with their symptoms) but never creates
    ``illness_flags`` — that is a later step.
    """

    start: date_
    end: date_
    symptoms: tuple[IllnessSymptom, ...]  # 2..4 values


@dataclass(frozen=True)
class LatentState:
    """The latent truth behind the emissions — debug only, never persisted.

    All sequences are aligned on ``dates`` (one entry per calendar day). ``acwr``
    is ``None`` until 7 days of history exist or while ``chronic == 0``.
    """

    dates: tuple[date_, ...]
    daily_load: tuple[float, ...]
    fitness: tuple[float, ...]
    fatigue: tuple[float, ...]
    form: tuple[float, ...]
    acwr: tuple[float | None, ...]


@dataclass(frozen=True)
class SyntheticDataset:
    """The full in-memory history of one synthetic athlete."""

    persona_name: str
    trait_vector: dict[str, float]
    seed: int
    sessions: tuple[SyntheticSession, ...]
    daily_metrics: tuple[SyntheticDailyMetric, ...]
    checkins: tuple[SyntheticCheckin, ...]
    mini_tests: tuple[SyntheticMiniTest, ...]
    niggles: tuple[SyntheticNiggle, ...]
    illness_episodes: tuple[SyntheticIllnessEpisode, ...]
    latent: LatentState
