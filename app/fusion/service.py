"""Async orchestration: fetch everything, run the rules, assemble the read.

This is the only layer in ``app.fusion`` that does IO. It joins the engine
(:class:`~app.engines.port.EnginePort`), the synced Garmin metrics, subjective
check-ins, niggles and mini-tests, computes the rolling baselines, runs the pure
rules and hands the resulting signals to :mod:`app.fusion.readiness`.

DB access is the project's synchronous ``Session``; the functions are ``async``
only because the engine port is (step-6 contract). Sync DB calls inside an async
function are intentional and match ``engine_dependency``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.errors import EngineError
from app.engines.port import EnginePort
from app.engines.schemas import TIMESERIES_METRICS, EnginePoint, EngineState, EngineTimeseries
from app.fusion import rules
from app.fusion.baselines import rolling_mean_std, rolling_z
from app.fusion.readiness import DailyRead, build_readiness, composite_score
from app.fusion.signals import Signal, SignalKey
from app.fusion.thresholds import ACWR_SPIKE, NIGGLE_LOAD_WINDOW_H, ROLL_LONG, ROLL_SHORT
from app.models.daily_checkin import DailyCheckin
from app.models.daily_metric import DailyMetric
from app.models.enums import MiniTestType
from app.models.mini_test import MiniTest
from app.models.niggle import Niggle
from app.models.user import User
from app.services import illness_service

_LOAD_WINDOW_DAYS = NIGGLE_LOAD_WINDOW_H // 24


# --------------------------------------------------------------------------- #
# DB fetch helpers (synchronous, user-scoped)                                  #
# --------------------------------------------------------------------------- #
def _checkins(db: Session, user_id: str, day: date_, lookback: int) -> list[DailyCheckin]:
    stmt = (
        select(DailyCheckin)
        .where(
            DailyCheckin.user_id == user_id,
            DailyCheckin.date >= day - timedelta(days=lookback),
            DailyCheckin.date <= day,
        )
        .order_by(DailyCheckin.date)
    )
    return list(db.scalars(stmt).all())


def _metrics(db: Session, user_id: str, day: date_, lookback: int) -> list[DailyMetric]:
    stmt = (
        select(DailyMetric)
        .where(
            DailyMetric.user_id == user_id,
            DailyMetric.date >= day - timedelta(days=lookback),
            DailyMetric.date <= day,
        )
        .order_by(DailyMetric.date)
    )
    return list(db.scalars(stmt).all())


def _mini_tests(db: Session, user_id: str, kind: MiniTestType, day: date_) -> list[MiniTest]:
    stmt = (
        select(MiniTest)
        .where(MiniTest.user_id == user_id, MiniTest.type == kind, MiniTest.date <= day)
        .order_by(MiniTest.date)
    )
    return list(db.scalars(stmt).all())


def _active_niggles(db: Session, user_id: str, day: date_) -> list[Niggle]:
    stmt = (
        select(Niggle)
        .where(
            Niggle.user_id == user_id,
            Niggle.opened_at <= day,
            Niggle.closed_at.is_(None),
        )
        .order_by(Niggle.opened_at)
    )
    return list(db.scalars(stmt).all())


# --------------------------------------------------------------------------- #
# Engine fetch helpers (async, fail-soft)                                       #
# --------------------------------------------------------------------------- #
async def _state(engine: EnginePort, day: date_) -> EngineState | None:
    try:
        return await engine.get_state(day)
    except EngineError:
        return None


async def _timeseries(
    engine: EnginePort, date_from: date_, date_to: date_, metrics: list[str]
) -> EngineTimeseries | None:
    if not metrics or date_to < date_from:
        return None
    try:
        return await engine.get_timeseries(date_from, date_to, metrics)
    except EngineError:
        return None


def _values(ts: EngineTimeseries | None, metric: str) -> list[float]:
    if ts is None:
        return []
    return [p.value for p in ts.series.get(metric, []) if p.value is not None]


def _aggregate(key: SignalKey, signals: list[Signal]) -> Signal:
    """Collapse per-item signals into one: the worst triggered, else the loudest."""

    if not signals:
        return Signal(key=key, triggered=False, severity=0.0, explanation="No data.")
    triggered = [s for s in signals if s.triggered]
    return max(triggered or signals, key=lambda s: s.severity)


# --------------------------------------------------------------------------- #
# Daily read                                                                   #
# --------------------------------------------------------------------------- #
async def compute_daily_read(db: Session, user: User, day: date_, engine: EnginePort) -> DailyRead:
    """Join every input for ``day`` into the athlete's readiness read."""

    engine_state = await _state(engine, day)

    divergence = await _divergence_signal(db, user.id, day, engine, engine_state)
    illness = rules.illness_hint(illness_service.compute_hint(db, user.id, day))
    wellness = _wellness_signal(db, user.id, day)
    mini_test = _mini_test_signal(db, user.id, day)
    escalation, niggle_load, max_intensity = await _niggle_signals(
        db, user.id, day, engine, engine_state
    )

    signals = [divergence, illness, escalation, niggle_load, wellness, mini_test]
    score = composite_score(signals)
    readiness = build_readiness(signals, score, max_niggle_intensity=max_intensity)
    return DailyRead(
        date=day,
        engine_state=engine_state,
        composite_score=score,
        readiness=readiness,
        signals=signals,
    )


async def _divergence_signal(
    db: Session,
    user_id: str,
    day: date_,
    engine: EnginePort,
    engine_state: EngineState | None,
) -> Signal:
    z_engine: float | None = None
    if engine_state is not None:
        ts = await _timeseries(engine, day - timedelta(days=ROLL_LONG - 1), day, ["form"])
        form_vals = _values(ts, "form")
        if form_vals:
            z_engine = rolling_z(form_vals, len(form_vals) - 1)

    subj_vals = [float(c.form_vs_normal) for c in _checkins(db, user_id, day, ROLL_LONG - 1)]
    z_subj = rolling_z(subj_vals, len(subj_vals) - 1) if subj_vals else None

    return rules.divergence_subj_obj(z_subj, z_engine)


def _wellness_signal(db: Session, user_id: str, day: date_) -> Signal:
    window = _metrics(db, user_id, day, ROLL_SHORT)
    today = window[-1] if window and window[-1].date == day else None
    prior = [m for m in window if m.date < day]

    hrv = rules.wellness_divergence(
        today.hrv_rmssd if today else None,
        [m.hrv_rmssd for m in prior if m.hrv_rmssd is not None],
        bad_direction="low",
        label="HRV",
    )
    sleep = rules.wellness_divergence(
        float(today.sleep_score) if today and today.sleep_score is not None else None,
        [float(m.sleep_score) for m in prior if m.sleep_score is not None],
        bad_direction="low",
        label="sleep",
    )
    rhr = rules.wellness_divergence(
        float(today.rhr) if today and today.rhr is not None else None,
        [float(m.rhr) for m in prior if m.rhr is not None],
        bad_direction="high",
        label="resting HR",
    )
    return _aggregate("wellness_divergence", [hrv, sleep, rhr])


def _mini_test_signal(db: Session, user_id: str, day: date_) -> Signal:
    jumps = _mini_tests(db, user_id, MiniTestType.JUMP, day)
    jump_vals = [float(m.payload["height_cm"]) for m in jumps if "height_cm" in m.payload]
    jump = rules.mini_test_trend(jump_vals[-1] if jump_vals else None, jump_vals[:-1], kind="jump")

    reactions = _mini_tests(db, user_id, MiniTestType.REACTION, day)
    rt_vals = [float(m.payload["mean_rt_ms"]) for m in reactions if "mean_rt_ms" in m.payload]
    reaction = rules.mini_test_trend(
        rt_vals[-1] if rt_vals else None, rt_vals[:-1], kind="reaction"
    )
    return _aggregate("mini_test_trend", [jump, reaction])


async def _niggle_signals(
    db: Session,
    user_id: str,
    day: date_,
    engine: EnginePort,
    engine_state: EngineState | None,
) -> tuple[Signal, Signal, float | None]:
    niggles = _active_niggles(db, user_id, day)
    escalations: list[Signal] = []
    loads: list[Signal] = []
    max_intensity: float | None = None

    for niggle in niggles:
        reports = [r for r in niggle.reports if r.date <= day]
        label = niggle.region.value
        intensities = [float(r.intensity) for r in reports]
        if intensities:
            max_intensity = max(max_intensity or 0.0, intensities[-1])
        escalations.append(rules.niggle_escalation(intensities, label=label))

        peak: float | None = None
        if engine_state is not None:
            ts = await _timeseries(
                engine,
                niggle.opened_at - timedelta(days=_LOAD_WINDOW_DAYS),
                niggle.opened_at,
                ["acwr"],
            )
            acwr_vals = _values(ts, "acwr")
            peak = max(acwr_vals) if acwr_vals else None
        loads.append(rules.niggle_load_correlation(peak, label=label))

    return (
        _aggregate("niggle_escalation", escalations),
        _aggregate("niggle_load_correlation", loads),
        max_intensity,
    )


# --------------------------------------------------------------------------- #
# Timeseries (fused engine + subjective + divergence over time)                #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TimeseriesRead:
    """Fused timeseries: engine metrics + subjective form + divergence Δ."""

    date_from: date_
    date_to: date_
    series: dict[str, list[EnginePoint]]
    form_vs_normal: list[EnginePoint]
    divergence: list[EnginePoint]


def _rolling_z_by_date(points: list[tuple[date_, float]]) -> dict[date_, float]:
    """Rolling z-score at each point, keyed by date (uses the trailing window)."""

    values = [v for _, v in points]
    out: dict[date_, float] = {}
    for i, (day, _) in enumerate(points):
        z = rolling_z(values, i)
        if z is not None:
            out[day] = z
    return out


async def compute_timeseries(
    db: Session,
    user: User,
    date_from: date_,
    date_to: date_,
    metrics: list[str],
    engine: EnginePort,
) -> TimeseriesRead:
    """Build fused series over ``[date_from, date_to]`` for the timeseries route."""

    engine_metrics = [m for m in metrics if m in TIMESERIES_METRICS]
    ts = await _timeseries(engine, date_from, date_to, engine_metrics)
    series = dict(ts.series) if ts is not None else {}

    checkins = _checkins(db, user.id, date_to, (date_to - date_from).days)
    form_vs_normal = [
        EnginePoint(date=c.date, value=float(c.form_vs_normal))
        for c in checkins
        if c.date >= date_from
    ]

    divergence = await _divergence_series(db, user.id, date_from, date_to, engine)
    return TimeseriesRead(
        date_from=date_from,
        date_to=date_to,
        series=series,
        form_vs_normal=form_vs_normal,
        divergence=divergence,
    )


async def _divergence_series(
    db: Session, user_id: str, date_from: date_, date_to: date_, engine: EnginePort
) -> list[EnginePoint]:
    extended = date_from - timedelta(days=ROLL_LONG)
    form_ts = await _timeseries(engine, extended, date_to, ["form"])
    if form_ts is None:
        return []
    form_points = [(p.date, p.value) for p in form_ts.series.get("form", []) if p.value is not None]
    z_engine = _rolling_z_by_date(form_points)

    checkins = _checkins(db, user_id, date_to, (date_to - extended).days)
    z_subj = _rolling_z_by_date([(c.date, float(c.form_vs_normal)) for c in checkins])

    out: list[EnginePoint] = []
    for day in sorted(z_subj.keys() & z_engine.keys()):
        if date_from <= day <= date_to:
            out.append(EnginePoint(date=day, value=z_subj[day] - z_engine[day]))
    return out


# --------------------------------------------------------------------------- #
# Mini-test baseline                                                            #
# --------------------------------------------------------------------------- #
_MINI_TEST_METRIC: dict[MiniTestType, str] = {
    MiniTestType.JUMP: "height_cm",
    MiniTestType.REACTION: "mean_rt_ms",
}


@dataclass(frozen=True)
class MiniTestBaseline:
    """Rolling baseline for one mini-test type's headline metric."""

    type: str
    metric: str
    n: int
    mean: float | None
    std: float | None
    latest: float | None
    latest_z: float | None


def mini_test_baseline(
    db: Session, user_id: str, kind: MiniTestType, day: date_ | None = None
) -> MiniTestBaseline:
    """Rolling mean/std (+ latest z) of a mini-test metric, newest value last."""

    metric = _MINI_TEST_METRIC[kind]
    cutoff = day or date_.max
    rows = _mini_tests(db, user_id, kind, cutoff)
    values = [float(r.payload[metric]) for r in rows if metric in r.payload]

    stats = rolling_mean_std(values)
    latest = values[-1] if values else None
    latest_z = rolling_z(values, len(values) - 1) if values else None
    return MiniTestBaseline(
        type=kind.value,
        metric=metric,
        n=len(values),
        mean=stats[0] if stats else None,
        std=stats[1] if stats else None,
        latest=latest,
        latest_z=latest_z,
    )


# --------------------------------------------------------------------------- #
# Correlations (niggle × load)                                                  #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class NiggleCorrelation:
    """One niggle's relationship to the acute load around its onset."""

    niggle_id: str
    region: str
    opened_at: date_
    peak_acwr_before_open: float | None
    load_linked: bool


@dataclass(frozen=True)
class CorrelationsRead:
    """Summary of niggle×load over a window."""

    date_from: date_
    date_to: date_
    niggles: list[NiggleCorrelation]
    total: int
    load_linked_count: int


async def compute_correlations(
    db: Session, user: User, date_from: date_, date_to: date_, engine: EnginePort
) -> CorrelationsRead:
    """For each niggle opened in the window, was it preceded by a load spike?"""

    stmt = (
        select(Niggle)
        .where(
            Niggle.user_id == user.id,
            Niggle.opened_at >= date_from,
            Niggle.opened_at <= date_to,
        )
        .order_by(Niggle.opened_at)
    )
    niggles = list(db.scalars(stmt).all())

    items: list[NiggleCorrelation] = []
    for niggle in niggles:
        ts = await _timeseries(
            engine,
            niggle.opened_at - timedelta(days=_LOAD_WINDOW_DAYS),
            niggle.opened_at,
            ["acwr"],
        )
        acwr_vals = _values(ts, "acwr")
        peak = max(acwr_vals) if acwr_vals else None
        linked = peak is not None and peak > ACWR_SPIKE
        items.append(
            NiggleCorrelation(
                niggle_id=niggle.id,
                region=niggle.region.value,
                opened_at=niggle.opened_at,
                peak_acwr_before_open=peak,
                load_linked=linked,
            )
        )

    return CorrelationsRead(
        date_from=date_from,
        date_to=date_to,
        niggles=items,
        total=len(items),
        load_linked_count=sum(1 for i in items if i.load_linked),
    )
