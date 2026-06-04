"""Tests for the deterministic synthetic data generator (``app.synth``).

These are pure in-memory unit tests — no database, no routes. Population-level
sanity checks average over several seeds (all seeded, so still deterministic) to
avoid single-draw flakiness. A fixed ``end_date`` keeps assertions stable across
calendar days.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from statistics import fmean

import numpy as np
import pytest

from app.synth import (
    PRESETS,
    TRAIT_RANGES,
    SyntheticDataset,
    generate,
    generate_cohort,
    sample_trait_vector,
)
from app.synth.generator import _rolling_z

_END = date(2026, 6, 4)
_DAYS = 180
_SEEDS = range(12)


def _gen(persona: str | object, seed: int, days: int = _DAYS) -> SyntheticDataset:
    return generate(persona, seed=seed, days=days, end_date=_END)  # type: ignore[arg-type]


def _avg(persona: str, metric: Callable[[SyntheticDataset], float]) -> float:
    return fmean(metric(_gen(persona, s)) for s in _SEEDS)


def _mean_acwr(d: SyntheticDataset) -> float:
    vals = [a for a in d.latent.acwr if a is not None]
    return fmean(vals)


def _form_z(d: SyntheticDataset) -> list[float]:
    form = list(d.latent.form)
    return [_rolling_z(form, t) for t in range(len(form))]


def _fat_z(d: SyntheticDataset) -> list[float]:
    fatigue = list(d.latent.fatigue)
    return [_rolling_z(fatigue, t) for t in range(len(fatigue))]


def _divergence(d: SyntheticDataset) -> float:
    """Mean gap between reported form and the objective form z-score."""

    idx = {day: i for i, day in enumerate(d.latent.dates)}
    fz = _form_z(d)
    return fmean(c.form_vs_normal - fz[idx[c.date]] for c in d.checkins)


# --- Determinism ------------------------------------------------------------


def test_same_seed_is_deterministic() -> None:
    assert _gen("OverTrainer", 7) == _gen("OverTrainer", 7)


def test_different_seed_differs() -> None:
    assert _gen("OverTrainer", 7) != _gen("OverTrainer", 8)


def test_cohort_matches_individual_generate() -> None:
    specs = [("Regular", 1), ("PoorSleeper", 2), ("InjuryProne", 3)]
    cohort = generate_cohort(specs, days=_DAYS, end_date=_END)
    assert [c.persona_name for c in cohort] == ["Regular", "PoorSleeper", "InjuryProne"]
    for (name, seed), built in zip(specs, cohort, strict=True):
        assert built == _gen(name, seed)


def test_custom_trait_vector_named_custom() -> None:
    rng = np.random.default_rng(0)
    tv = sample_trait_vector("Regular", rng)
    assert _gen(tv, 5).persona_name == "custom"


def test_unknown_preset_raises() -> None:
    with pytest.raises(ValueError, match="unknown preset"):
        generate("NotAPersona", seed=1, end_date=_END)


# --- Trait sampling ---------------------------------------------------------


def test_sampled_traits_within_ranges() -> None:
    rng = np.random.default_rng(123)
    for name in PRESETS:
        for _ in range(20):
            tv = sample_trait_vector(name, rng)
            for trait, (lo, hi) in TRAIT_RANGES.items():
                value = getattr(tv, trait)
                assert lo <= value <= hi, (name, trait, value)


# --- Shape ------------------------------------------------------------------


@pytest.mark.parametrize("days", [30, 90, 180])
def test_window_shape(days: int) -> None:
    d = _gen("Regular", 1, days=days)
    assert len(d.daily_metrics) == days
    assert len(d.latent.dates) == days
    assert d.latent.dates[-1] == _END
    assert d.latent.dates[0] == _END - timedelta(days=days - 1)


# --- Invariants -------------------------------------------------------------


def test_daily_metric_check_bounds() -> None:
    bounded_0_100 = ("sleep_score", "stress", "body_battery", "training_readiness")
    non_negative = ("sleep_duration_min", "rhr", "hrv_rmssd", "resp_rate", "vo2max")
    for name in PRESETS:
        for s in _SEEDS:
            for m in _gen(name, s).daily_metrics:
                for field in bounded_0_100:
                    value = getattr(m, field)
                    assert value is None or 0 <= value <= 100, (name, field, value)
                for field in non_negative:
                    value = getattr(m, field)
                    assert value is None or value >= 0, (name, field, value)


def test_checkin_bounds() -> None:
    for name in PRESETS:
        for s in _SEEDS:
            for c in _gen(name, s).checkins:
                assert -2 <= c.form_vs_normal <= 2
                assert 1 <= c.motivation <= 5
                assert 1 <= c.fatigue <= 5


def test_niggle_intensity_bounds() -> None:
    for name in PRESETS:
        for s in _SEEDS:
            for n in _gen(name, s).niggles:
                for r in n.reports:
                    assert 0 <= r.intensity <= 10


def test_session_rpe_bounds_and_source_flag() -> None:
    for name in PRESETS:
        for s in _SEEDS:
            for sess in _gen(name, s).sessions:
                if sess.rpe is None:
                    # No RPE captured → never flagged as watch-filled.
                    assert sess.affect is None
                    assert sess.rpe_filled_on_watch is False
                else:
                    assert 1 <= sess.rpe <= 10


def test_series_dates_sorted_and_unique() -> None:
    d = _gen("OverTrainer", 4)
    for series in (d.daily_metrics, d.checkins, d.mini_tests, d.sessions):
        dates = [x.date for x in series]
        assert dates == sorted(dates)
    # Daily series are one-per-day.
    for series in (d.daily_metrics, d.checkins):
        dates = [x.date for x in series]
        assert len(dates) == len(set(dates))


def test_acwr_non_negative_and_recomputable() -> None:
    d = _gen("OverTrainer", 2)
    load = list(d.latent.daily_load)
    for t, got in enumerate(d.latent.acwr):
        if t < 6:
            assert got is None  # fewer than 7 days of history
            continue
        chronic = fmean(load[max(0, t - 27) : t + 1])
        expected = None if chronic == 0 else fmean(load[max(0, t - 6) : t + 1]) / chronic
        if expected is None:
            assert got is None
        else:
            assert got is not None and got >= 0
            assert got == pytest.approx(expected)


# --- Persona sanity ---------------------------------------------------------


def test_overtrainer_acwr_above_regular() -> None:
    assert _avg("OverTrainer", _mean_acwr) > _avg("Regular", _mean_acwr)


def test_poorsleeper_sleep_below_regular() -> None:
    def mean_sleep(d: SyntheticDataset) -> float:
        return fmean(m.sleep_score for m in d.daily_metrics if m.sleep_score is not None)

    assert _avg("PoorSleeper", mean_sleep) < _avg("Regular", mean_sleep)


def test_injuryprone_more_niggles_than_regular() -> None:
    n = lambda d: float(len(d.niggles))  # noqa: E731
    assert _avg("InjuryProne", n) > _avg("Regular", n)


def test_beginner_final_fitness_below_regular() -> None:
    final_fitness = lambda d: d.latent.fitness[-1]  # noqa: E731
    assert _avg("Beginner", final_fitness) < _avg("Regular", final_fitness)


def test_overtrainer_divergence_above_regular() -> None:
    # OverTrainer (optimistic bias, low form weight) reports better form than its
    # objective freshness warrants — a larger subjective↔objective gap.
    assert _avg("OverTrainer", _divergence) > _avg("Regular", _divergence)


# --- Niggle trajectory ------------------------------------------------------


def test_niggle_trajectories_are_multi_report_and_can_escalate() -> None:
    multi = 0
    escalating = 0
    for s in _SEEDS:
        for n in _gen("OverTrainer", s).niggles:
            if len(n.reports) >= 3:
                multi += 1
                if n.reports[-1].intensity > n.reports[0].intensity:
                    escalating += 1
    assert multi >= 3, multi
    assert escalating >= 1, escalating


def test_first_report_marks_new_or_recurrent() -> None:
    # Across all niggles, the first report carries new/recurrent; later reports
    # of the same niggle are trajectory updates ("unknown").
    seen = False
    for s in _SEEDS:
        for n in _gen("InjuryProne", s).niggles:
            assert n.reports[0].is_new_or_recurrent in ("new", "recurrent")
            for r in n.reports[1:]:
                assert r.is_new_or_recurrent == "unknown"
            seen = True
    assert seen


# --- Illness ----------------------------------------------------------------


def test_illness_episode_degrades_signal() -> None:
    for s in range(40):
        d = _gen("PoorSleeper", s)
        if not d.illness_episodes:
            continue
        by_date = {m.date: m for m in d.daily_metrics}
        hrv_base = fmean(m.hrv_rmssd for m in d.daily_metrics if m.hrv_rmssd is not None)
        rhr_base = fmean(m.rhr for m in d.daily_metrics if m.rhr is not None)
        resp_base = fmean(m.resp_rate for m in d.daily_metrics if m.resp_rate is not None)
        episode = d.illness_episodes[0]
        span = (episode.end - episode.start).days + 1
        days = [episode.start + timedelta(days=i) for i in range(span)]
        assert any(
            (m := by_date.get(day)) is not None
            and m.hrv_rmssd is not None
            and m.rhr is not None
            and m.resp_rate is not None
            and m.hrv_rmssd < hrv_base
            and m.rhr > rhr_base
            and m.resp_rate > resp_base
            for day in days
        )
        assert 2 <= len(episode.symptoms) <= 4
        return
    pytest.fail("no illness episode generated across 40 PoorSleeper seeds")


# --- Mini-tests -------------------------------------------------------------


def test_jump_height_decreases_with_fatigue() -> None:
    fatigues: list[float] = []
    heights: list[float] = []
    for s in _SEEDS:
        d = _gen("Regular", s)
        idx = {day: i for i, day in enumerate(d.latent.dates)}
        fz = _fat_z(d)
        for mt in d.mini_tests:
            if mt.type.value == "jump":
                fatigues.append(fz[idx[mt.date]])
                heights.append(float(mt.payload["height_cm"]))
    mean_f = fmean(fatigues)
    mean_h = fmean(heights)
    covariance = sum((f - mean_f) * (h - mean_h) for f, h in zip(fatigues, heights, strict=True))
    assert covariance < 0  # higher fatigue → lower jump height
