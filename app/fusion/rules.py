"""Pure fusion rules: data in, a :class:`~app.fusion.signals.Signal` out.

Every function here is a pure function of already-fetched values — no DB, no
engine, no clock. That keeps each rule independently testable and the verdicts
explainable. The orchestration that fetches the inputs lives in
:mod:`app.fusion.service`.
"""

from __future__ import annotations

from statistics import fmean
from typing import Literal

from app.fusion.baselines import rolling_mean_std
from app.fusion.signals import Signal, SignalDirection
from app.fusion.thresholds import (
    ACWR_SPIKE,
    DIVERGENCE_SIGMA,
    ESCALATION_MAX_REPORTS,
    ESCALATION_MIN_REPORTS,
    ESCALATION_SLOPE,
    ESCALATION_STRONG_SLOPE,
    MINI_TEST_SIGMA,
    ROLL_SHORT,
    WELLNESS_BAND_SIGMA,
    Z_CLAMP,
)
from app.services.illness_service import WatchHint

MiniTestKind = Literal["jump", "reaction"]
BadDirection = Literal["low", "high"]


def _severity(magnitude: float, threshold: float, ceiling: float) -> float:
    """Normalize how far ``magnitude`` exceeds ``threshold`` into 0..1.

    ``0.0`` at/below the threshold, ``1.0`` at/above the ceiling, linear between.
    """

    if magnitude <= threshold or ceiling <= threshold:
        return 0.0
    return min(1.0, (magnitude - threshold) / (ceiling - threshold))


def _ls_slope(values: list[float]) -> float:
    """Least-squares slope of ``values`` against their index ``0..n-1``."""

    n = len(values)
    xs = list(range(n))
    mx = fmean(xs)
    my = fmean(values)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0.0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, values, strict=True)) / denom


def divergence_subj_obj(z_form_vs_normal: float | None, z_engine_form: float | None) -> Signal:
    """The anchor signal: the gap between *felt* and *measured* form.

    Both inputs are rolling z-scores (subjective ``form_vs_normal`` vs engine
    ``form``). The dangerous case is ``subj_optimistic`` — the athlete feels
    relatively better than the objective form, masking accumulating fatigue.
    """

    if z_form_vs_normal is None or z_engine_form is None:
        return Signal(
            key="divergence_subj_obj",
            triggered=False,
            severity=0.0,
            explanation="Not enough history to compare felt vs measured form.",
        )

    delta = z_form_vs_normal - z_engine_form
    triggered = abs(delta) > DIVERGENCE_SIGMA
    direction: SignalDirection = "subj_optimistic" if delta > 0 else "subj_pessimistic"
    severity = _severity(abs(delta), DIVERGENCE_SIGMA, 2 * Z_CLAMP)
    if direction == "subj_optimistic":
        msg = "Athlete feels better than the engine's form suggests (watch hidden fatigue)."
    else:
        msg = "Athlete feels worse than the engine's form suggests."
    return Signal(
        key="divergence_subj_obj",
        triggered=triggered,
        severity=severity if triggered else 0.0,
        value=z_form_vs_normal,
        reference=z_engine_form,
        delta=delta,
        direction=direction,
        explanation=msg,
        evidence=[f"z(subjective)={z_form_vs_normal:.2f}", f"z(engine form)={z_engine_form:.2f}"],
    )


def niggle_escalation(intensities: list[float], *, label: str = "niggle") -> Signal:
    """Flag a niggle whose recent reports trend upward in intensity.

    ``intensities`` are one niggle's report intensities in chronological order;
    the slope is taken over the last :data:`ESCALATION_MAX_REPORTS`.
    """

    recent = intensities[-ESCALATION_MAX_REPORTS:]
    if len(recent) < ESCALATION_MIN_REPORTS:
        return Signal(
            key="niggle_escalation",
            triggered=False,
            severity=0.0,
            explanation=f"Not enough reports to assess {label} trend.",
        )

    slope = _ls_slope(recent)
    triggered = slope > ESCALATION_SLOPE
    severity = _severity(slope, ESCALATION_SLOPE, ESCALATION_STRONG_SLOPE)
    return Signal(
        key="niggle_escalation",
        triggered=triggered,
        severity=severity if triggered else 0.0,
        value=recent[-1],
        reference=recent[0],
        delta=slope,
        direction="up" if slope > 0 else "down",
        explanation=(
            f"{label} intensity is escalating ({slope:+.2f}/report)."
            if triggered
            else f"{label} intensity is stable."
        ),
        evidence=[f"last {len(recent)} reports: {[round(v, 1) for v in recent]}"],
    )


def niggle_load_correlation(
    peak_acwr_before_open: float | None, *, label: str = "niggle"
) -> Signal:
    """Flag a niggle opened shortly after an acute-load spike.

    ``peak_acwr_before_open`` is the highest ACWR over the
    :data:`NIGGLE_LOAD_WINDOW_H`-hour window ending when the niggle opened.
    """

    if peak_acwr_before_open is None:
        return Signal(
            key="niggle_load_correlation",
            triggered=False,
            severity=0.0,
            explanation="No load data around the niggle onset.",
        )

    triggered = peak_acwr_before_open > ACWR_SPIKE
    severity = _severity(peak_acwr_before_open, ACWR_SPIKE, 2.0)
    return Signal(
        key="niggle_load_correlation",
        triggered=triggered,
        severity=severity if triggered else 0.0,
        value=peak_acwr_before_open,
        reference=ACWR_SPIKE,
        delta=peak_acwr_before_open - ACWR_SPIKE,
        direction="up",
        explanation=(
            f"{label} appeared just after an acute-load spike (ACWR "
            f"{peak_acwr_before_open:.2f})."
            if triggered
            else f"{label} onset not linked to a load spike."
        ),
        evidence=[f"peak ACWR before onset={peak_acwr_before_open:.2f}", f"spike>{ACWR_SPIKE}"],
    )


def wellness_divergence(
    value: float | None,
    baseline_values: list[float],
    *,
    bad_direction: BadDirection,
    label: str,
) -> Signal:
    """Flag a wellness metric (HRV/sleep/RHR) outside its recent rolling band.

    ``baseline_values`` are the trailing :data:`ROLL_SHORT` observations *before*
    today. ``bad_direction`` says which way is concerning (``low`` for HRV/sleep,
    ``high`` for RHR).
    """

    return _band_signal(
        key="wellness_divergence",
        value=value,
        baseline_values=baseline_values,
        bad_direction=bad_direction,
        threshold=WELLNESS_BAND_SIGMA,
        label=label,
    )


def mini_test_trend(
    value: float | None,
    baseline_values: list[float],
    *,
    kind: MiniTestKind,
) -> Signal:
    """Flag neuromuscular degradation vs the rolling mini-test baseline.

    Jump *height* dropping (``low``) or reaction *time* rising (``high``) is the
    concerning direction.
    """

    bad_direction: BadDirection = "low" if kind == "jump" else "high"
    return _band_signal(
        key="mini_test_trend",
        value=value,
        baseline_values=baseline_values,
        bad_direction=bad_direction,
        threshold=MINI_TEST_SIGMA,
        label=f"{kind} mini-test",
    )


def _band_signal(
    *,
    key: Literal["wellness_divergence", "mini_test_trend"],
    value: float | None,
    baseline_values: list[float],
    bad_direction: BadDirection,
    threshold: float,
    label: str,
) -> Signal:
    """Shared rolling-band logic for the wellness and mini-test rules."""

    stats = rolling_mean_std(baseline_values, min_obs=ROLL_SHORT)
    if value is None or stats is None:
        return Signal(
            key=key,
            triggered=False,
            severity=0.0,
            explanation=f"Not enough history for {label}.",
        )

    mean, std = stats
    if std < 1e-9:
        z = 0.0
    else:
        z = (value - mean) / std
    bad = z <= -threshold if bad_direction == "low" else z >= threshold
    severity = _severity(abs(z), threshold, Z_CLAMP)
    direction: SignalDirection = "down" if bad_direction == "low" else "up"
    return Signal(
        key=key,
        triggered=bad,
        severity=severity if bad else 0.0,
        value=value,
        reference=mean,
        delta=value - mean,
        direction=direction,
        explanation=(
            f"{label} is off its recent normal ({z:+.1f}σ)."
            if bad
            else f"{label} is within normal range."
        ),
        evidence=[f"value={value:.1f}", f"baseline μ={mean:.1f}", f"z={z:+.2f}"],
    )


def illness_hint(watch_hint: WatchHint) -> Signal:
    """Adapt the illness watch-hint (HRV↓+RHR↑+resp↑) into a :class:`Signal`.

    The detection logic lives in :func:`app.services.illness_service.compute_hint`
    — this rule only translates its verdict, never recomputes it.
    """

    evidence: list[str] = []
    if watch_hint.hrv_delta is not None:
        evidence.append(f"HRV Δ={watch_hint.hrv_delta:+.1f}")
    if watch_hint.rhr_delta is not None:
        evidence.append(f"RHR Δ={watch_hint.rhr_delta:+.1f}")
    if watch_hint.resp_delta is not None:
        evidence.append(f"resp Δ={watch_hint.resp_delta:+.1f}")
    return Signal(
        key="illness_hint",
        triggered=watch_hint.triggered,
        severity=1.0 if watch_hint.triggered else 0.0,
        explanation=(
            "Physiology looks like early illness (HRV down, RHR & respiration up)."
            if watch_hint.triggered
            else "No illness pattern in the physiology."
        ),
        evidence=evidence,
    )
