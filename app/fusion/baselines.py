"""Pure rolling-baseline helpers shared across the fusion rules.

These mirror the formulas in :mod:`app.synth.generator` (``_rolling_z`` /
``_acwr``) so the brain reasons on the same statistics that generated the data.
Everything here is a pure function on already-fetched lists — no IO, no DB.
"""

from __future__ import annotations

from statistics import fmean, pstdev

from app.fusion.thresholds import (
    ACUTE_WINDOW,
    CHRONIC_WINDOW,
    ROLL_LONG,
    ROLL_MIN_OBS,
    Z_CLAMP,
)


def rolling_mean_std(
    values: list[float], *, min_obs: int = ROLL_MIN_OBS
) -> tuple[float, float] | None:
    """Return ``(mean, population_std)`` of ``values`` or ``None`` before warmup.

    The caller is responsible for slicing the causal window (e.g. excluding the
    current day) before handing the values in.
    """

    if len(values) < min_obs:
        return None
    return fmean(values), pstdev(values)


def zscore(value: float, mean: float, std: float, *, clamp: float = Z_CLAMP) -> float:
    """Clamped z-score; ``0.0`` when the baseline has no spread."""

    if std < 1e-9:
        return 0.0
    return max(-clamp, min(clamp, (value - mean) / std))


def rolling_z(
    values: list[float],
    t: int,
    *,
    window: int = ROLL_LONG,
    min_obs: int = ROLL_MIN_OBS,
) -> float | None:
    """Clamped rolling z-score of ``values[t]`` over the trailing ``window``.

    Returns ``None`` before warmup (fewer than ``min_obs`` points up to ``t``).
    The window is inclusive of ``t`` — same convention as the generator's
    ``_rolling_z`` — so this scores "how unusual is today against recent normal".
    """

    if not 0 <= t < len(values):
        return None
    win = values[max(0, t - window + 1) : t + 1]
    if len(win) < min_obs:
        return None
    return zscore(values[t], fmean(win), pstdev(win))


def acwr_from_loads(loads: list[float], t: int) -> float | None:
    """Acute:chronic workload ratio at index ``t`` (locked 7d/28d formula)."""

    if t < ACUTE_WINDOW - 1 or t >= len(loads):
        return None
    acute = fmean(loads[max(0, t - ACUTE_WINDOW + 1) : t + 1])
    chronic = fmean(loads[max(0, t - CHRONIC_WINDOW + 1) : t + 1])
    if chronic == 0.0:
        return None
    return acute / chronic
