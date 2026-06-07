"""The synthetic athlete simulation.

A single seeded :class:`numpy.random.Generator` drives the whole pipeline so two
calls with the same ``(persona, seed, days, end_date)`` produce byte-for-byte
identical datasets. The stages, in order (this order *is* the determinism
contract):

1. calendar → training impulses (periodised 3:1 microcycle) and ``daily_load``;
2. latent Banister state (fitness τ=42, fatigue τ=7) + ACWR (locked formula);
3. rolling 28-day z-scores of fatigue/form;
4. illness episodes (inhomogeneous-enough Poisson over the window);
5. daily Garmin-like metric emissions (+ illness degradation), clamped to the
   step-2.1 CHECK bounds;
6. niggles — inhomogeneous-Poisson onset + multi-report escalation/resolution;
7. subjective check-ins (the subj↔obj divergence lives here);
8. mini-tests (jump / reaction);
9. per-session RPE/affect feedback.

Nothing here writes to the database — it returns an in-memory
:class:`~app.synth.dataset.SyntheticDataset`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from statistics import fmean, pstdev
from typing import TypeVar

import numpy as np

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
from app.synth.dataset import (
    LatentState,
    SyntheticCheckin,
    SyntheticDailyMetric,
    SyntheticDataset,
    SyntheticIllnessEpisode,
    SyntheticMiniTest,
    SyntheticNiggle,
    SyntheticNiggleReport,
    SyntheticSession,
)
from app.synth.personas import TraitVector, sample_trait_vector

_T = TypeVar("_T")

# --- Tunable constants ------------------------------------------------------

# Burn-in days simulated before the output window so the slow fitness impulse
# (τ=42) and the 28-day rolling baselines are warmed by the window's first day.
_BURN_IN = 120

FITNESS_TAU = 42.0
FATIGUE_TAU = 7.0
# Fatigue weighting for the freshness signal: ``form = fitness - K_FAT·fatigue``.
# The raw impulse-sum ``fitness - fatigue`` is monotonically large-positive (the
# slow τ=42 term dwarfs τ=7), so it can never reproduce the "negative form under
# overload" the divergence requires. Weighting fatigue near τ_fit/τ_fat (≈6) puts
# baseline freshness near zero and lets acute spikes push it negative — the
# Banister/TSB behaviour. (The ACWR formula below is untouched.)
_FATIGUE_WEIGHT = 5.5
ACUTE_WINDOW = 7
CHRONIC_WINDOW = 28
ROLL_WINDOW = 28
ROLL_MIN_PERIODS = 7
Z_CLAMP = 3.0
HRV_STATUS_Z = 0.75

# Weekly template (weekday index 0=Mon .. 6=Sun) → session type on a build week.
_WEEKLY_TEMPLATE: dict[int, str] = {
    0: "rest",
    1: "intervals",
    2: "easy",
    3: "tempo",
    4: "rest",
    5: "long",
    6: "recovery",
}
# Fraction of the weekly TRIMP target carried by each session type (sums to 1.0).
_TYPE_FRACTION: dict[str, float] = {
    "intervals": 0.20,
    "easy": 0.12,
    "tempo": 0.18,
    "long": 0.35,
    "recovery": 0.15,
}
# TRIMP per training minute (sets duration); m travelled per minute (sets distance).
_TYPE_INTENSITY: dict[str, float] = {
    "intervals": 1.6,
    "tempo": 1.3,
    "easy": 0.8,
    "long": 0.9,
    "recovery": 0.6,
}
_TYPE_SPEED: dict[str, float] = {
    "intervals": 240.0,
    "tempo": 235.0,
    "easy": 185.0,
    "long": 200.0,
    "recovery": 165.0,
}
_RECOVERY_WEEK_SCALE = 0.55
# Per-session overload spike applied with probability ``load_volatility`` on build
# days. Frequent acute spikes lift a volatile athlete's mean ACWR (the spike
# weighs ~4× more in the 7-day acute window than the 28-day chronic one) without
# a monotonic ramp — so latent ``form`` stays stationary and still dips on
# overload, which is what makes the subj↔obj divergence measurable.
_SPIKE_TRIMP_LO = 1.2
_SPIKE_TRIMP_HI = 1.7
# Gentle volatility-scaled progressive ramp. With the burn-in prefix warming the
# Banister state and the rolling-28d z detrending it, this lifts a volatile
# athlete's mean ACWR (acute persistently above chronic) without biasing form_z.
_LOAD_RAMP = 0.6

# Niggle hazard: λ = base + α·max(0, acwr-1.3) + β·max(0, acute/target - 1).
_HAZARD_ACWR_ALPHA = 0.05
_HAZARD_ACWR_THRESHOLD = 1.3
_HAZARD_LOAD_BETA = 0.012
_MAX_ACTIVE_NIGGLES = 2
# A niggle escalates only under clear overload; otherwise it resolves — this
# gives turnover so higher-hazard personas accumulate more niggles overall.
_NIGGLE_LOAD_THRESHOLD = 1.1

# Subjective check-in weights.
_W_NIGGLE = 0.15
_K_TAP = 0.8
_M_W = 0.7
_CHECKIN_SKIP_PROB = 0.12

_MINITEST_DAILY_PROB = 2.0 / 7.0
_RPE_FILL_PROB = 0.65
_GRAVITY = 9.81


# --- Niggle archetypes ------------------------------------------------------

_REGION_ARCHETYPE: dict[BodyRegion, str] = {
    BodyRegion.ACHILLES: "tendinopathy",
    BodyRegion.KNEE_ANTERIOR: "tendinopathy",
    BodyRegion.IT_BAND: "tendinopathy",
    BodyRegion.SHIN: "bone_stress",
    BodyRegion.FOOT_FORE: "bone_stress",
    BodyRegion.FOOT_MID: "bone_stress",
    BodyRegion.FOOT_HEEL: "bone_stress",
    BodyRegion.CALF: "muscle",
    BodyRegion.HAMSTRING: "muscle",
    BodyRegion.QUAD: "muscle",
    BodyRegion.ANKLE: "ligament",
}


@dataclass(frozen=True)
class _Archetype:
    """Coherent presentation + trajectory behaviour for an injury family."""

    pain_types: tuple[PainType, ...]
    mechanical: tuple[MechanicalPattern, ...]
    timings: tuple[Timing, ...]
    escalation_rate: float
    resolution_rate: float
    load_sensitive: bool


_ARCHETYPES: dict[str, _Archetype] = {
    "tendinopathy": _Archetype(
        pain_types=(PainType.DULL, PainType.BURNING),
        mechanical=(MechanicalPattern.PUSH_OFF, MechanicalPattern.UPHILL),
        timings=(Timing.MORNING_STIFFNESS, Timing.AFTER),
        escalation_rate=0.4,
        resolution_rate=0.5,
        load_sensitive=True,
    ),
    "bone_stress": _Archetype(
        pain_types=(PainType.SHARP, PainType.STABBING),
        mechanical=(MechanicalPattern.IMPACT,),
        timings=(Timing.DURING,),
        escalation_rate=1.0,
        resolution_rate=0.3,
        load_sensitive=True,
    ),
    "muscle": _Archetype(
        pain_types=(PainType.SHARP, PainType.TENSION),
        mechanical=(MechanicalPattern.PUSH_OFF, MechanicalPattern.IMPACT),
        timings=(Timing.DURING,),
        escalation_rate=0.6,
        resolution_rate=1.0,
        load_sensitive=False,
    ),
    "ligament": _Archetype(
        pain_types=(PainType.SHARP,),
        mechanical=(MechanicalPattern.IMPACT,),
        timings=(Timing.DURING,),
        escalation_rate=0.5,
        resolution_rate=0.6,
        load_sensitive=False,
    ),
}

_SIDE_WEIGHTS: tuple[tuple[Side, float], ...] = (
    (Side.LEFT, 0.45),
    (Side.RIGHT, 0.45),
    (Side.BILATERAL, 0.07),
    (Side.CENTER, 0.03),
)


# --- Small numeric helpers --------------------------------------------------


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _clamp_int(value: float, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, round(value))))


def _rolling_z(values: list[float], t: int) -> float:
    """Clamped 28-day rolling z-score of ``values[t]`` (0.0 before warmup)."""

    window = values[max(0, t - ROLL_WINDOW + 1) : t + 1]
    if len(window) < ROLL_MIN_PERIODS:
        return 0.0
    sd = pstdev(window)
    if sd < 1e-9:
        return 0.0
    return _clamp((values[t] - fmean(window)) / sd, -Z_CLAMP, Z_CLAMP)


def _acwr(load: list[float], t: int) -> float | None:
    """Acute:chronic workload ratio — locked formula shared with the engine."""

    if t < ACUTE_WINDOW - 1:  # fewer than 7 days of history
        return None
    acute = fmean(load[max(0, t - ACUTE_WINDOW + 1) : t + 1])
    chronic = fmean(load[max(0, t - CHRONIC_WINDOW + 1) : t + 1])
    if chronic == 0.0:
        return None
    return acute / chronic


def _weighted_choice(
    weights: tuple[tuple[BodyRegion, float], ...] | tuple[tuple[Side, float], ...],
    rng: np.random.Generator,
) -> BodyRegion | Side:
    total = sum(w for _, w in weights)
    r = float(rng.random()) * total
    cumulative = 0.0
    for item, weight in weights:
        cumulative += weight
        if r <= cumulative:
            return item
    return weights[-1][0]


def _pick(options: tuple[_T, ...], rng: np.random.Generator) -> _T:
    return options[int(rng.integers(0, len(options)))]


# --- Internal session draft (mutable until RPE is attached) -----------------


@dataclass
class _SessionDraft:
    activity_id: str
    date: date
    session_type: str
    duration_s: int
    distance_m: float
    elevation_gain_m: float
    trimp: float
    hr_tss: float


# --- Stage 1: calendar → impulses -------------------------------------------


def _build_sessions(
    dates: list[date], traits: TraitVector, seed: int, rng: np.random.Generator
) -> tuple[list[_SessionDraft], list[float]]:
    """Emit training sessions per the periodised template; return drafts + load."""

    daily_load = [0.0] * len(dates)
    drafts: list[_SessionDraft] = []

    # Decide recovery-week status once per week (a skipped recovery → build week).
    week_is_recovery: dict[int, bool] = {}
    for day in dates:
        monday_index = (day.toordinal() - day.weekday()) // 7
        if monday_index in week_is_recovery:
            continue
        recovery = (monday_index % 4) == 3
        if recovery and float(rng.random()) < traits.load_volatility:
            recovery = False  # high volatility → skip the down week, stack volume
        week_is_recovery[monday_index] = recovery

    for t, day in enumerate(dates):
        session_type = _WEEKLY_TEMPLATE[day.weekday()]
        if session_type == "rest":
            continue
        monday_index = (day.toordinal() - day.weekday()) // 7
        recovery_week = week_is_recovery[monday_index]

        trimp = traits.weekly_trimp_target * _TYPE_FRACTION[session_type]
        trimp *= 1.0 + _LOAD_RAMP * traits.load_volatility * (t / max(1, len(dates) - 1))
        trimp *= math.exp(float(rng.normal(0.0, 0.12)))  # multiplicative noise
        if recovery_week:
            trimp *= _RECOVERY_WEEK_SCALE
        elif float(rng.random()) < traits.load_volatility:
            trimp *= float(rng.uniform(_SPIKE_TRIMP_LO, _SPIKE_TRIMP_HI))  # acute overload spike

        duration_min = trimp / _TYPE_INTENSITY[session_type]
        duration_s = int(duration_min * 60)
        distance_m = duration_min * _TYPE_SPEED[session_type] * float(rng.normal(1.0, 0.05))
        distance_m = max(0.0, distance_m)
        elevation = (distance_m / 1000.0) * float(rng.uniform(5.0, 25.0))
        hr_tss = trimp * float(rng.uniform(0.85, 1.05))

        drafts.append(
            _SessionDraft(
                activity_id=f"synth-{seed}-{day.isoformat()}",
                date=day,
                session_type=session_type,
                duration_s=duration_s,
                distance_m=round(distance_m, 1),
                elevation_gain_m=round(elevation, 1),
                trimp=round(trimp, 1),
                hr_tss=round(hr_tss, 1),
            )
        )
        daily_load[t] = trimp

    return drafts, daily_load


# --- Stage 2: Banister latent state -----------------------------------------


def _run_banister(
    daily_load: list[float], fitness_start: float
) -> tuple[list[float], list[float], list[float], list[float | None]]:
    fitness_decay = math.exp(-1.0 / FITNESS_TAU)
    fatigue_decay = math.exp(-1.0 / FATIGUE_TAU)
    # The impulse-sum recurrences below grow to ~load*τ; normalising the *output*
    # by (1 - fitness_decay) brings fitness/fatigue/form back onto the daily-load
    # scale (tens), so form behaves like a TrainingPeaks-style TSB and the engine
    # readiness thresholds (form ±10/15) and the vo2max mapping are meaningful.
    # It is a single scalar factor, so every z-score derived downstream is
    # unchanged — only the reported magnitudes shrink.
    scale = 1.0 - fitness_decay

    fitness: list[float] = []
    fatigue: list[float] = []
    form: list[float] = []
    acwr: list[float | None] = []

    prev_fit = fitness_start
    prev_fat = 0.0
    for t, load in enumerate(daily_load):
        fit = prev_fit * fitness_decay + load
        fat = prev_fat * fatigue_decay + load
        fitness.append(fit * scale)
        fatigue.append(fat * scale)
        form.append((fit - _FATIGUE_WEIGHT * fat) * scale)
        acwr.append(_acwr(daily_load, t))
        prev_fit, prev_fat = fit, fat

    return fitness, fatigue, form, acwr


# --- Stage 4: illness episodes ----------------------------------------------


def _build_illness(
    dates: list[date], traits: TraitVector, rng: np.random.Generator
) -> tuple[list[SyntheticIllnessEpisode], dict[int, SyntheticIllnessEpisode]]:
    n_days = len(dates)
    expected = traits.illness_rate * (n_days / 365.0)
    count = int(rng.poisson(expected))

    episodes: list[SyntheticIllnessEpisode] = []
    day_to_episode: dict[int, SyntheticIllnessEpisode] = {}
    symptoms_all = list(IllnessSymptom)

    for _ in range(count):
        start_idx = int(rng.integers(0, n_days))
        duration = int(rng.integers(3, 8))  # 3..7 days
        end_idx = min(n_days - 1, start_idx + duration - 1)

        n_symptoms = int(rng.integers(2, 5))  # 2..4
        order = list(range(len(symptoms_all)))
        rng.shuffle(order)
        chosen = sorted((symptoms_all[i] for i in order[:n_symptoms]), key=lambda s: s.value)

        episode = SyntheticIllnessEpisode(
            start=dates[start_idx], end=dates[end_idx], symptoms=tuple(chosen)
        )
        episodes.append(episode)
        for idx in range(start_idx, end_idx + 1):
            day_to_episode.setdefault(idx, episode)

    episodes.sort(key=lambda e: e.start)
    return episodes, day_to_episode


# --- Stage 5: daily metric emissions ----------------------------------------


def _emit_daily_metrics(
    dates: list[date],
    traits: TraitVector,
    fitness: list[float],
    form_z: list[float],
    fat_z: list[float],
    ill_days: dict[int, SyntheticIllnessEpisode],
    rng: np.random.Generator,
) -> tuple[list[SyntheticDailyMetric], list[float]]:
    k = traits.fatigue_sensitivity
    hrv_raw: list[float] = []
    sleep_scores: list[float] = []
    rows: list[dict[str, object]] = []

    for t, day in enumerate(dates):
        hrv = max(0.0, traits.hrv_base - 8.0 * k * fat_z[t] + float(rng.normal(0.0, 4.0)))
        rhr = max(0.0, traits.rhr_base + 4.0 * k * fat_z[t] + float(rng.normal(0.0, 2.0)))
        sleep_score = _clamp(
            traits.sleep_base - 6.0 * k * fat_z[t] + float(rng.normal(0.0, 5.0)), 0.0, 100.0
        )
        resp = max(0.0, 14.0 + 0.8 * fat_z[t] + float(rng.normal(0.0, 0.5)))
        body_battery = (
            60.0 - 12.0 * fat_z[t] + (sleep_score - 70.0) * 0.4 + float(rng.normal(0.0, 6.0))
        )
        stress = 35.0 + 10.0 * fat_z[t] + float(rng.normal(0.0, 6.0))
        readiness = (
            60.0
            + 8.0 * form_z[t]
            + (sleep_score - 70.0) * 0.3
            + (hrv - traits.hrv_base) * 0.2
            + float(rng.normal(0.0, 6.0))
        )
        vo2max = max(0.0, 45.0 + fitness[t] * 0.1 + float(rng.normal(0.0, 0.3)))
        duration_min = 360.0 + (sleep_score - 70.0) * 2.0 + float(rng.normal(0.0, 20.0))

        # Illness degradation — must keep HRV↓ + RHR↑ + resp↑ detectable.
        if t in ill_days:
            hrv *= 0.75
            rhr += float(rng.integers(6, 13))
            resp += float(rng.uniform(2.0, 4.0))
            sleep_score = max(0.0, sleep_score - float(rng.integers(20, 36)))
            readiness -= float(rng.integers(15, 31))
            duration_min -= float(rng.uniform(20.0, 60.0))

        hrv_raw.append(hrv)
        sleep_scores.append(sleep_score)

        onset = datetime.combine(day - timedelta(days=1), time(23, 0), tzinfo=UTC) + timedelta(
            minutes=float(rng.normal(0.0, 35.0))
        )
        duration_min = max(0.0, duration_min)
        rows.append(
            {
                "date": day,
                "sleep_score": int(round(sleep_score)),
                "sleep_duration_min": int(round(duration_min)),
                "sleep_onset": onset,
                "sleep_wake": onset + timedelta(minutes=duration_min),
                "hrv_rmssd": round(hrv, 1),
                "rhr": int(round(rhr)),
                "stress": _clamp_int(stress, 0, 100),
                "body_battery": _clamp_int(body_battery, 0, 100),
                "resp_rate": round(resp, 1),
                "training_readiness": _clamp_int(readiness, 0, 100),
                "vo2max": round(vo2max, 1),
            }
        )

    metrics: list[SyntheticDailyMetric] = []
    for t, row in enumerate(rows):
        hrv_z = _rolling_z(hrv_raw, t)
        if hrv_z < -HRV_STATUS_Z:
            status = HrvStatus.LOW
        elif hrv_z > HRV_STATUS_Z:
            status = HrvStatus.HIGH
        else:
            status = HrvStatus.NORMAL
        metrics.append(
            SyntheticDailyMetric(
                date=row["date"],  # type: ignore[arg-type]
                sleep_score=row["sleep_score"],  # type: ignore[arg-type]
                sleep_duration_min=row["sleep_duration_min"],  # type: ignore[arg-type]
                sleep_onset=row["sleep_onset"],  # type: ignore[arg-type]
                sleep_wake=row["sleep_wake"],  # type: ignore[arg-type]
                hrv_rmssd=row["hrv_rmssd"],  # type: ignore[arg-type]
                hrv_status=status,
                rhr=row["rhr"],  # type: ignore[arg-type]
                stress=row["stress"],  # type: ignore[arg-type]
                body_battery=row["body_battery"],  # type: ignore[arg-type]
                resp_rate=row["resp_rate"],  # type: ignore[arg-type]
                training_readiness=row["training_readiness"],  # type: ignore[arg-type]
                vo2max=row["vo2max"],  # type: ignore[arg-type]
            )
        )

    return metrics, sleep_scores


# --- Stage 6: niggles -------------------------------------------------------


def _acute_load_ratio(daily_load: list[float], t: int, weekly_target: float) -> float:
    """Recent acute load relative to the athlete's per-day target (>= 0)."""

    target_daily = max(1e-6, weekly_target / 7.0)
    acute = fmean(daily_load[max(0, t - ACUTE_WINDOW + 1) : t + 1])
    return acute / target_daily


def _simulate_niggles(
    dates: list[date],
    traits: TraitVector,
    daily_load: list[float],
    acwr: list[float | None],
    activity_by_date: dict[date, str],
    burn: int,
    rng: np.random.Generator,
) -> tuple[list[SyntheticNiggle], list[float]]:
    """Simulate niggles over the output window ``dates[burn:]``.

    ``daily_load`` / ``acwr`` are the *extended* arrays (including the burn-in
    prefix) so the acute/chronic look-back is fully warmed; ``active_intensity``
    is returned indexed against the window (length ``len(dates) - burn``).
    """

    n_days = len(dates)
    n_window = n_days - burn
    niggles: list[SyntheticNiggle] = []
    active_intensity = [0.0] * n_window
    seen_regions: set[BodyRegion] = set()
    # End (ext) indices of niggles still open — caps concurrency.
    open_until: list[int] = []

    region_weights = tuple(traits.zone_bias.items())

    for t in range(burn, n_days):
        open_until = [end for end in open_until if end >= t]
        if len(open_until) >= _MAX_ACTIVE_NIGGLES:
            continue

        acwr_t = acwr[t] or 0.0
        load_ratio = _acute_load_ratio(daily_load, t, traits.weekly_trimp_target)
        hazard = (
            traits.niggle_hazard_base
            + _HAZARD_ACWR_ALPHA * max(0.0, acwr_t - _HAZARD_ACWR_THRESHOLD)
            + _HAZARD_LOAD_BETA * max(0.0, load_ratio - 1.0)
        )
        if float(rng.random()) >= 1.0 - math.exp(-hazard):
            continue

        # Onset: draw region (zone-biased), derive a coherent archetype.
        region = _weighted_choice(region_weights, rng)
        assert isinstance(region, BodyRegion)
        archetype_name = _REGION_ARCHETYPE[region]
        arche = _ARCHETYPES[archetype_name]
        side = _weighted_choice(_SIDE_WEIGHTS, rng)
        assert isinstance(side, Side)
        pain_type = _pick(arche.pain_types, rng)
        mechanical = _pick(arche.mechanical, rng)
        timing = _pick(arche.timings, rng)

        first_kind = "recurrent" if region in seen_regions else "new"
        seen_regions.add(region)

        # Trajectory: a report every 2-4 days until it resolves or the window ends.
        reports: list[SyntheticNiggleReport] = []
        intensity = float(rng.uniform(2.0, 4.0))
        idx = t
        report_dates: list[int] = []
        while idx < n_days:
            ratio = _acute_load_ratio(daily_load, idx, traits.weekly_trimp_target)
            if reports:  # update after the first report
                if ratio >= _NIGGLE_LOAD_THRESHOLD:
                    gain = arche.escalation_rate if arche.load_sensitive else 0.3
                    intensity += gain + float(rng.normal(0.0, 0.5))
                else:
                    intensity -= arche.resolution_rate + float(rng.normal(0.0, 0.5))
                intensity = _clamp(intensity, 0.0, 10.0)

            day = dates[idx]
            linked = (
                activity_by_date.get(day)
                if float(rng.random()) < 0.5 and day in activity_by_date
                else None
            )
            kind = first_kind if not reports else "unknown"
            reports.append(
                SyntheticNiggleReport(
                    date=day,
                    intensity=int(round(intensity)),
                    pain_type=pain_type,
                    mechanical_pattern=mechanical,
                    timing=timing,
                    is_new_or_recurrent=kind,
                    linked_activity_id=linked,
                )
            )
            report_dates.append(idx)
            if intensity <= 0.5 and reports:
                break
            idx += int(rng.integers(2, 5))  # 2..4 days

        closed_idx = report_dates[-1] if intensity <= 0.5 else None
        opened_at = dates[report_dates[0]]
        closed_at = dates[closed_idx] if closed_idx is not None else None

        # Fill the active-intensity step function over the niggle's span (window
        # indices = ext index minus burn-in offset).
        for j, ridx in enumerate(report_dates):
            end = (
                report_dates[j + 1] - 1
                if j + 1 < len(report_dates)
                else (closed_idx if closed_idx is not None else n_days - 1)
            )
            for d in range(ridx, min(end, n_days - 1) + 1):
                w = d - burn
                if 0 <= w < n_window:
                    active_intensity[w] = max(active_intensity[w], reports[j].intensity)

        niggles.append(
            SyntheticNiggle(
                opened_at=opened_at,
                closed_at=closed_at,
                region=region,
                side=side,
                structure=None,
                archetype=archetype_name,
                reports=tuple(reports),
            )
        )
        open_until.append(closed_idx if closed_idx is not None else n_days - 1)
        open_until = [end for end in open_until if end >= t]

    niggles.sort(key=lambda n: n.opened_at)
    return niggles, active_intensity


# --- Stage 7: subjective check-ins ------------------------------------------


def _emit_checkins(
    dates: list[date],
    traits: TraitVector,
    form_z: list[float],
    fat_z: list[float],
    sleep_z: list[float],
    active_intensity: list[float],
    rng: np.random.Generator,
) -> list[SyntheticCheckin]:
    checkins: list[SyntheticCheckin] = []
    for t, day in enumerate(dates):
        if float(rng.random()) < _CHECKIN_SKIP_PROB:
            continue
        fvn_raw = (
            traits.subj_form_weight * form_z[t]
            + traits.subj_sleep_weight * sleep_z[t]
            - _W_NIGGLE * active_intensity[t]
            + traits.subj_bias
            + float(rng.normal(0.0, traits.subj_noise))
        )
        form_vs_normal = _clamp_int(fvn_raw, -2, 2)
        fatigue_tap = _clamp_int(
            3.0 + fat_z[t] * _K_TAP + float(rng.normal(0.0, traits.subj_noise)), 1, 5
        )
        # Motivation is reported vs a normal day (signed -2..2), centred on 0.
        motivation = _clamp_int(
            form_z[t] * _M_W + traits.subj_bias + float(rng.normal(0.0, traits.subj_noise)),
            -2,
            2,
        )
        # Optional subjective stress vs normal (-2..2): rises with fatigue, eased
        # by good sleep.
        stress = _clamp_int(
            fat_z[t] * _K_TAP * 0.7
            - sleep_z[t] * 0.4
            + float(rng.normal(0.0, traits.subj_noise)),
            -2,
            2,
        )
        reported_at = datetime.combine(day, time(7, 30), tzinfo=UTC) + timedelta(
            minutes=float(rng.normal(0.0, 25.0))
        )
        checkins.append(
            SyntheticCheckin(
                date=day,
                form_vs_normal=form_vs_normal,
                motivation=motivation,
                fatigue=fatigue_tap,
                stress=stress,
                reported_at=reported_at,
            )
        )
    return checkins


# --- Stage 8: mini-tests ----------------------------------------------------


def _emit_mini_tests(
    dates: list[date], traits: TraitVector, fat_z: list[float], rng: np.random.Generator
) -> list[SyntheticMiniTest]:
    k = traits.fatigue_sensitivity
    tests: list[SyntheticMiniTest] = []
    for t, day in enumerate(dates):
        if float(rng.random()) >= _MINITEST_DAILY_PROB:
            continue
        reported_at = datetime.combine(day, time(18, 0), tzinfo=UTC) + timedelta(
            minutes=float(rng.normal(0.0, 30.0))
        )
        if float(rng.random()) < 0.5:
            flight = max(
                0.0, traits.jump_flight_base - 25.0 * k * fat_z[t] + float(rng.normal(0.0, 12.0))
            )
            flight_ms = int(round(flight))
            height_cm = _GRAVITY * (flight_ms / 1000.0) ** 2 / 8.0 * 100.0
            tests.append(
                SyntheticMiniTest(
                    date=day,
                    reported_at=reported_at,
                    type=MiniTestType.JUMP,
                    payload={"flight_time_ms": flight_ms, "height_cm": round(height_cm, 1)},
                )
            )
        else:
            mean_rt = max(0.0, traits.rt_base + 18.0 * k * fat_z[t] + float(rng.normal(0.0, 8.0)))
            sd_rt = mean_rt * float(rng.uniform(0.12, 0.20))
            tests.append(
                SyntheticMiniTest(
                    date=day,
                    reported_at=reported_at,
                    type=MiniTestType.REACTION,
                    payload={
                        "mean_rt_ms": round(mean_rt, 1),
                        "sd_rt_ms": round(sd_rt, 1),
                        "n_taps": 30,
                    },
                )
            )
    return tests


# --- Stage 9: session RPE/affect --------------------------------------------


def _finalize_sessions(
    drafts: list[_SessionDraft],
    traits: TraitVector,
    index_of: dict[date, int],
    fat_z: list[float],
    form_z: list[float],
    rng: np.random.Generator,
) -> list[SyntheticSession]:
    sessions: list[SyntheticSession] = []
    for draft in drafts:
        t = index_of[draft.date]
        rpe: int | None = None
        affect: Affect | None = None
        on_watch = False
        if float(rng.random()) < _RPE_FILL_PROB:
            rpe = _clamp_int(
                2.0 + 0.012 * draft.trimp + 1.2 * fat_z[t] + float(rng.normal(0.0, 0.8)), 1, 10
            )
            affect_score = form_z[t] + float(rng.normal(0.0, 0.3))
            if affect_score > 0.5:
                affect = Affect.STRONG
            elif affect_score < -0.5:
                affect = Affect.WEAK
            else:
                affect = Affect.NEUTRAL
            on_watch = float(rng.random()) < 0.5
        sessions.append(
            SyntheticSession(
                activity_id=draft.activity_id,
                date=draft.date,
                session_type=draft.session_type,
                duration_s=draft.duration_s,
                distance_m=draft.distance_m,
                elevation_gain_m=draft.elevation_gain_m,
                trimp=draft.trimp,
                hr_tss=draft.hr_tss,
                rpe=rpe,
                affect=affect,
                rpe_filled_on_watch=on_watch,
            )
        )
    return sessions


# --- Public API -------------------------------------------------------------


def generate(
    persona: str | TraitVector,
    seed: int,
    days: int = 180,
    end_date: date | None = None,
) -> SyntheticDataset:
    """Generate one synthetic athlete history, deterministically from ``seed``.

    ``persona`` is either a preset name (sampled into a :class:`TraitVector`) or a
    ready-made :class:`TraitVector`. ``end_date`` defaults to today; the calendar
    spans ``[end_date - days + 1 .. end_date]``.
    """

    if days < 1:
        raise ValueError("days must be >= 1")
    end = end_date or date.today()
    rng = np.random.default_rng(seed)

    if isinstance(persona, str):
        traits = sample_trait_vector(persona, rng)
        persona_name = persona
    else:
        traits = persona
        persona_name = "custom"

    # Simulate over an extended calendar (a burn-in prefix + the output window) so
    # the Banister state and rolling baselines are fully warmed by the window's
    # first day; only the window tail is emitted.
    window_start = end - timedelta(days=days - 1)
    ext_start = window_start - timedelta(days=_BURN_IN)
    ext_len = _BURN_IN + days
    ext_dates = [ext_start + timedelta(days=i) for i in range(ext_len)]
    index_of = {day: i for i, day in enumerate(ext_dates)}
    burn = _BURN_IN
    window_dates = ext_dates[burn:]

    drafts, daily_load = _build_sessions(ext_dates, traits, seed, rng)
    activity_by_date = {d.date: d.activity_id for d in drafts}

    fitness, fatigue, form, acwr = _run_banister(daily_load, traits.fitness_start)
    fat_z = [_rolling_z(fatigue, t) for t in range(ext_len)]
    form_z = [_rolling_z(form, t) for t in range(ext_len)]

    episodes, ill_days = _build_illness(window_dates, traits, rng)
    metrics, sleep_scores = _emit_daily_metrics(
        window_dates, traits, fitness[burn:], form_z[burn:], fat_z[burn:], ill_days, rng
    )
    sleep_z = [_rolling_z(sleep_scores, t) for t in range(days)]

    niggles, active_intensity = _simulate_niggles(
        ext_dates, traits, daily_load, acwr, activity_by_date, burn, rng
    )
    checkins = _emit_checkins(
        window_dates, traits, form_z[burn:], fat_z[burn:], sleep_z, active_intensity, rng
    )
    mini_tests = _emit_mini_tests(window_dates, traits, fat_z[burn:], rng)
    window_drafts = [d for d in drafts if d.date >= window_start]
    sessions = _finalize_sessions(window_drafts, traits, index_of, fat_z, form_z, rng)

    # Latent ACWR is recomputed over the window-sliced load so the debug output is
    # self-consistent (recomputable from ``latent.daily_load`` with the locked
    # formula). The niggle hazard above used the warmed extended-array ACWR.
    window_load = daily_load[burn:]
    latent = LatentState(
        dates=tuple(window_dates),
        daily_load=tuple(window_load),
        fitness=tuple(fitness[burn:]),
        fatigue=tuple(fatigue[burn:]),
        form=tuple(form[burn:]),
        acwr=tuple(_acwr(window_load, t) for t in range(days)),
    )

    return SyntheticDataset(
        persona_name=persona_name,
        trait_vector=traits.as_dict(),
        seed=seed,
        sessions=tuple(sessions),
        daily_metrics=tuple(metrics),
        checkins=tuple(checkins),
        mini_tests=tuple(mini_tests),
        niggles=tuple(niggles),
        illness_episodes=tuple(episodes),
        latent=latent,
    )


def generate_cohort(
    specs: list[tuple[str, int]],
    days: int = 180,
    end_date: date | None = None,
) -> list[SyntheticDataset]:
    """Generate a cohort from ``(preset_name, seed)`` specs.

    Each athlete is fully reproducible from its own seed; reproducibility of the
    whole cohort is therefore guaranteed by the caller's seed choice.
    """

    return [generate(name, seed, days=days, end_date=end_date) for name, seed in specs]
