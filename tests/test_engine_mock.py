"""MockEngine: serving a per-user snapshot from disk."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.engines.errors import EngineBadRequest, EngineNotFound
from app.engines.mock import MockEngine
from app.engines.schemas import SessionFeedbackPayload, WellnessDailyPayload
from app.synth import generate
from app.synth.seeder import seed_user

_END = date(2026, 6, 4)
_DAYS = 120


def _seed(db: Session, engine_dir: Path) -> tuple[str, object]:
    dataset = generate("OverTrainer", seed=7, days=_DAYS, end_date=_END)
    user = seed_user(db, dataset, engine_dir=engine_dir)
    return user.id, dataset


def _write_snapshot(engine_dir: Path, user_id: str, **arrays: object) -> MockEngine:
    """Hand-write a minimal snapshot and return a MockEngine over it."""

    engine_dir.mkdir(parents=True, exist_ok=True)
    (engine_dir / f"{user_id}.json").write_text(json.dumps(arrays), encoding="utf-8")
    return MockEngine(user_id, str(engine_dir))


async def test_get_state_matches_latent(db_session: Session, tmp_path: Path) -> None:
    user_id, dataset = _seed(db_session, tmp_path)
    engine = MockEngine(user_id, str(tmp_path))
    latent = dataset.latent
    i = len(latent.dates) - 1  # the last day always has full history

    state = await engine.get_state(latent.dates[i])

    assert state.fitness == pytest.approx(latent.fitness[i])
    assert state.fatigue == pytest.approx(latent.fatigue[i])
    assert state.form == pytest.approx(latent.form[i])  # Banister form, not fitness - fatigue
    if latent.acwr[i] is None:
        assert state.acwr is None
    else:
        assert state.acwr == pytest.approx(latent.acwr[i])


async def test_load_and_trend_formulas(db_session: Session, tmp_path: Path) -> None:
    user_id, dataset = _seed(db_session, tmp_path)
    engine = MockEngine(user_id, str(tmp_path))
    latent = dataset.latent
    i = len(latent.dates) - 1

    state = await engine.get_state(latent.dates[i])

    assert state.load_7d == pytest.approx(sum(latent.daily_load[i - 6 : i + 1]))
    assert state.load_28d == pytest.approx(sum(latent.daily_load[i - 27 : i + 1]))
    assert state.trend_form_7d == pytest.approx(latent.form[i] - latent.form[i - 7])


async def test_trend_is_none_before_seven_days(tmp_path: Path) -> None:
    dates = [(date(2026, 1, 1) + timedelta(days=d)).isoformat() for d in range(3)]
    engine = _write_snapshot(
        tmp_path,
        "u-short",
        dates=dates,
        daily_load=[10.0, 20.0, 30.0],
        fitness=[1.0, 2.0, 3.0],
        fatigue=[0.0, 0.0, 0.0],
        form=[1.0, 2.0, 3.0],
        acwr=[None, None, None],
        activities=[],
    )
    state = await engine.get_state(date(2026, 1, 3))
    assert state.trend_form_7d is None
    assert state.load_7d == pytest.approx(60.0)  # partial window allowed


@pytest.mark.parametrize(
    ("form", "acwr", "expected"),
    [
        (-10.1, 1.0, "low"),  # just below -10
        (-10.0, 1.0, "neutral"),  # boundary is not "low"
        (15.1, 1.0, "high"),  # above 15 and acwr in band
        (15.0, 1.0, "neutral"),  # boundary is not "high"
        (20.0, 0.8, "high"),  # acwr lower edge of band
        (20.0, 1.3, "high"),  # acwr upper edge of band
        (20.0, 1.31, "neutral"),  # acwr just outside band
        (20.0, None, "neutral"),  # unknown acwr can't be "high"
    ],
)
async def test_readiness_hint_boundaries(
    tmp_path: Path, form: float, acwr: float | None, expected: str
) -> None:
    engine = _write_snapshot(
        tmp_path,
        "u-hint",
        dates=[date(2026, 1, 1).isoformat()],
        daily_load=[0.0],
        fitness=[0.0],
        fatigue=[0.0],
        form=[form],
        acwr=[acwr],
        activities=[],
    )
    state = await engine.get_state(date(2026, 1, 1))
    assert state.readiness_hint == expected


async def test_timeseries_filtered_by_metrics(db_session: Session, tmp_path: Path) -> None:
    user_id, dataset = _seed(db_session, tmp_path)
    engine = MockEngine(user_id, str(tmp_path))
    latent = dataset.latent

    ts = await engine.get_timeseries(latent.dates[0], latent.dates[-1], ["form", "load"])

    assert set(ts.series) == {"form", "load"}
    assert len(ts.series["form"]) == len(latent.dates)
    assert ts.series["load"][0].value == pytest.approx(latent.daily_load[0])


async def test_timeseries_window_slices(db_session: Session, tmp_path: Path) -> None:
    user_id, dataset = _seed(db_session, tmp_path)
    engine = MockEngine(user_id, str(tmp_path))
    latent = dataset.latent
    lo, hi = latent.dates[10], latent.dates[20]

    ts = await engine.get_timeseries(lo, hi, ["fitness"])

    points = ts.series["fitness"]
    assert len(points) == 11
    assert points[0].date == lo
    assert points[-1].date == hi


async def test_timeseries_unknown_metric_raises(db_session: Session, tmp_path: Path) -> None:
    user_id, dataset = _seed(db_session, tmp_path)
    engine = MockEngine(user_id, str(tmp_path))
    with pytest.raises(EngineBadRequest):
        await engine.get_timeseries(dataset.latent.dates[0], dataset.latent.dates[-1], ["bogus"])


async def test_activities_window_and_limit(db_session: Session, tmp_path: Path) -> None:
    user_id, dataset = _seed(db_session, tmp_path)
    engine = MockEngine(user_id, str(tmp_path))

    acts = await engine.get_activities(_END - timedelta(days=30), _END, limit=5)

    assert len(acts) <= 5
    assert acts == sorted(acts, key=lambda a: a.date, reverse=True)  # newest first
    assert all(_END - timedelta(days=30) <= a.date <= _END for a in acts)


async def test_missing_snapshot_raises(tmp_path: Path) -> None:
    engine = MockEngine("nobody", str(tmp_path))
    with pytest.raises(EngineNotFound):
        await engine.get_state(_END)


async def test_out_of_range_date_raises(db_session: Session, tmp_path: Path) -> None:
    user_id, _ = _seed(db_session, tmp_path)
    engine = MockEngine(user_id, str(tmp_path))
    with pytest.raises(EngineNotFound):
        await engine.get_state(_END + timedelta(days=365))


async def test_writes_are_noops_that_skip(tmp_path: Path) -> None:
    # No snapshot needed: writes never touch disk, they just report "skipped".
    engine = MockEngine("nobody", str(tmp_path))
    wellness = WellnessDailyPayload(
        date=_END, form_vs_normal=0, motivation=3, fatigue=3, active_niggles=0
    )
    feedback = SessionFeedbackPayload(
        activity_id="a1", rpe=5, affect="neutral", reported_at=datetime(2026, 6, 4, tzinfo=UTC)
    )

    assert await engine.push_wellness_daily(wellness) == "skipped"
    assert await engine.push_session_feedback(feedback) == "skipped"
