"""Pure baseline helpers: warmup, causality, clamping, ACWR."""

from __future__ import annotations

import pytest

from app.fusion.baselines import acwr_from_loads, rolling_mean_std, rolling_z, zscore


def test_rolling_mean_std_warmup_returns_none() -> None:
    assert rolling_mean_std([1.0] * 6) is None  # fewer than ROLL_MIN_OBS (7)


def test_rolling_mean_std_returns_mean_and_pstdev() -> None:
    assert rolling_mean_std([1.0] * 7) == (1.0, 0.0)


def test_zscore_zero_when_no_spread() -> None:
    assert zscore(5.0, 5.0, 0.0) == 0.0


def test_zscore_is_clamped() -> None:
    assert zscore(100.0, 0.0, 1.0, clamp=3.0) == 3.0
    assert zscore(-100.0, 0.0, 1.0, clamp=3.0) == -3.0


def test_rolling_z_warmup_returns_none() -> None:
    assert rolling_z([1.0, 2.0, 3.0], 2) is None  # fewer than min_obs


def test_rolling_z_detects_recent_outlier() -> None:
    values = [10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 20.0]
    z = rolling_z(values, len(values) - 1)
    assert z is not None and z > 1.0


def test_rolling_z_is_causal_ignores_future() -> None:
    # The spike at index 8 must not affect the z computed at index 7.
    values = [10.0] * 8 + [1000.0]
    assert rolling_z(values, 7) == 0.0


def test_acwr_unit_when_load_constant() -> None:
    assert acwr_from_loads([10.0] * 28, 27) == pytest.approx(1.0)


def test_acwr_none_before_acute_window() -> None:
    assert acwr_from_loads([10.0] * 5, 4) is None
