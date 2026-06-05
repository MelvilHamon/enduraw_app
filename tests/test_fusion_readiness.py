"""Pure readiness: composite weighting, top-2 selection, reco branches."""

from __future__ import annotations

from app.fusion.readiness import (
    Reco,
    build_readiness,
    composite_score,
    recommend,
    top_2_signals,
)
from app.fusion.signals import Signal, SignalDirection, SignalKey
from app.fusion.thresholds import (
    ESCALATION_STRONG_SLOPE,
    NIGGLE_HIGH_INTENSITY,
    SCORE_REST,
)


def _sig(
    key: SignalKey,
    *,
    triggered: bool = True,
    severity: float = 0.5,
    delta: float | None = None,
    direction: SignalDirection | None = None,
    explanation: str = "",
) -> Signal:
    return Signal(
        key=key,
        triggered=triggered,
        severity=severity,
        delta=delta,
        direction=direction,
        explanation=explanation,
    )


def test_composite_score_zero_without_signals() -> None:
    assert composite_score([]) == 0.0


def test_composite_weights_divergence_strongest() -> None:
    div = composite_score([_sig("divergence_subj_obj", severity=1.0)])
    mini = composite_score([_sig("mini_test_trend", severity=1.0)])
    assert div > mini


def test_top_2_picks_highest_severity_triggered() -> None:
    sigs = [
        _sig("divergence_subj_obj", severity=0.2),
        _sig("illness_hint", severity=0.9),
        _sig("wellness_divergence", severity=0.5),
        _sig("mini_test_trend", triggered=False, severity=0.0),
    ]
    top = top_2_signals(sigs)
    assert [s.key for s in top] == ["illness_hint", "wellness_divergence"]


def test_reco_consult_physio_on_strong_escalation() -> None:
    esc = _sig("niggle_escalation", severity=1.0, delta=ESCALATION_STRONG_SLOPE)
    assert recommend([esc], 0.2) == Reco.CONSULT_PHYSIO


def test_reco_consult_physio_on_load_plus_high_intensity() -> None:
    nl = _sig("niggle_load_correlation", severity=0.5)
    reco = recommend([nl], 0.2, max_niggle_intensity=float(NIGGLE_HIGH_INTENSITY))
    assert reco == Reco.CONSULT_PHYSIO


def test_reco_rest_on_illness() -> None:
    assert recommend([_sig("illness_hint", severity=1.0)], 0.1) == Reco.REST


def test_reco_rest_on_high_score() -> None:
    assert recommend([_sig("wellness_divergence", severity=1.0)], SCORE_REST) == Reco.REST


def test_reco_rest_on_severe_optimistic_divergence() -> None:
    div = _sig("divergence_subj_obj", severity=0.6, direction="subj_optimistic")
    assert recommend([div], 0.2) == Reco.REST


def test_reco_lighten_on_moderate_divergence() -> None:
    div = _sig("divergence_subj_obj", severity=0.3, direction="subj_pessimistic")
    assert recommend([div], 0.2) == Reco.LIGHTEN


def test_reco_train_when_clear() -> None:
    assert recommend([], 0.0) == Reco.TRAIN_AS_PLANNED


def test_build_readiness_explains_with_top_signal() -> None:
    div = _sig(
        "divergence_subj_obj", severity=0.3, direction="subj_pessimistic", explanation="felt off"
    )
    r = build_readiness([div], 0.2)
    assert r.reco == Reco.LIGHTEN and "felt off" in r.explanation
