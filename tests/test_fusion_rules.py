"""Pure fusion rules: fire/no-fire, direction, threshold edges."""

from __future__ import annotations

import pytest

from app.fusion.rules import (
    divergence_subj_obj,
    illness_hint,
    mini_test_trend,
    niggle_escalation,
    niggle_load_correlation,
    wellness_divergence,
)
from app.services.illness_service import WatchHint

# A baseline with real spread (mean 48, pstdev 2.0) for the band rules.
_BAND_BASELINE = [45.0, 46.0, 47.0, 48.0, 49.0, 50.0, 51.0]


# --- divergence (the anchor signal) ------------------------------------------
def test_divergence_not_triggered_on_missing_input() -> None:
    s = divergence_subj_obj(None, 1.0)
    assert not s.triggered and s.severity == 0.0


def test_divergence_flags_subjective_optimism() -> None:
    # Felt much better (z=2) than measured form (z=-1): the dangerous gap.
    s = divergence_subj_obj(2.0, -1.0)
    assert s.triggered
    assert s.direction == "subj_optimistic"
    assert s.delta == pytest.approx(3.0)
    assert s.severity > 0.0


def test_divergence_captures_pessimistic_direction() -> None:
    s = divergence_subj_obj(-2.0, 1.0)
    assert s.triggered and s.direction == "subj_pessimistic"


def test_divergence_below_threshold_not_triggered() -> None:
    s = divergence_subj_obj(0.5, 0.0)  # |Δ| = 0.5 < DIVERGENCE_SIGMA
    assert not s.triggered


# --- niggle escalation -------------------------------------------------------
def test_escalation_needs_minimum_reports() -> None:
    assert not niggle_escalation([1.0, 2.0]).triggered


def test_escalation_flags_rising_trend() -> None:
    s = niggle_escalation([1.0, 2.0, 3.0, 4.0])  # slope = 1.0 > 0.5
    assert s.triggered and s.delta == pytest.approx(1.0) and s.direction == "up"


def test_escalation_stable_not_flagged() -> None:
    assert not niggle_escalation([3.0, 3.0, 3.0, 3.0]).triggered


def test_escalation_only_uses_recent_reports() -> None:
    # An early jump then a flat last-5 window must not trigger.
    assert not niggle_escalation([0.0, 10.0, 5.0, 5.0, 5.0, 5.0, 5.0]).triggered


# --- niggle x load -----------------------------------------------------------
def test_niggle_load_no_data_not_triggered() -> None:
    assert not niggle_load_correlation(None).triggered


def test_niggle_load_flags_spike() -> None:
    s = niggle_load_correlation(1.5)  # peak ACWR > 1.3
    assert s.triggered and s.value == 1.5 and s.direction == "up"


def test_niggle_load_below_spike_not_triggered() -> None:
    assert not niggle_load_correlation(1.2).triggered


def test_niggle_load_boundary_is_strict() -> None:
    assert not niggle_load_correlation(1.3).triggered


# --- wellness divergence -----------------------------------------------------
def test_wellness_insufficient_baseline_not_triggered() -> None:
    s = wellness_divergence(40.0, [50.0] * 6, bad_direction="low", label="HRV")
    assert not s.triggered


def test_wellness_low_metric_flagged() -> None:
    s = wellness_divergence(44.0, _BAND_BASELINE, bad_direction="low", label="HRV")
    assert s.triggered and s.direction == "down"


def test_wellness_high_value_not_flagged_when_low_is_bad() -> None:
    s = wellness_divergence(60.0, _BAND_BASELINE, bad_direction="low", label="HRV")
    assert not s.triggered


def test_wellness_high_metric_flagged_for_rhr() -> None:
    s = wellness_divergence(52.0, _BAND_BASELINE, bad_direction="high", label="RHR")
    assert s.triggered and s.direction == "up"


def test_wellness_band_edge_triggers_with_zero_severity() -> None:
    # z = -1.0 sits exactly on the band edge: triggered, but severity floors at 0.
    s = wellness_divergence(46.0, _BAND_BASELINE, bad_direction="low", label="HRV")
    assert s.triggered and s.severity == 0.0


# --- mini-test trend (direction per kind) ------------------------------------
def test_mini_test_jump_drop_flagged() -> None:
    s = mini_test_trend(20.0, _BAND_BASELINE, kind="jump")
    assert s.triggered and s.direction == "down"


def test_mini_test_reaction_slowdown_flagged() -> None:
    s = mini_test_trend(60.0, _BAND_BASELINE, kind="reaction")
    assert s.triggered and s.direction == "up"


def test_mini_test_reaction_speedup_not_flagged() -> None:
    s = mini_test_trend(40.0, _BAND_BASELINE, kind="reaction")
    assert not s.triggered


# --- illness hint delegation -------------------------------------------------
def test_illness_hint_translates_triggered_watch_hint() -> None:
    wh = WatchHint(
        triggered=True, hrv_delta=-5.0, rhr_delta=4.0, resp_delta=2.0, baseline_window_days=14
    )
    s = illness_hint(wh)
    assert s.triggered and s.severity == 1.0
    assert any("HRV" in e for e in s.evidence)


def test_illness_hint_passive_when_not_triggered() -> None:
    wh = WatchHint(
        triggered=False, hrv_delta=None, rhr_delta=None, resp_delta=None, baseline_window_days=3
    )
    s = illness_hint(wh)
    assert not s.triggered and s.severity == 0.0
