"""Pure readiness assembly: signals → composite score, top signals, reco.

No IO here either — :func:`compute_daily_read` in the service feeds these the
finished list of :class:`~app.fusion.signals.Signal` objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_
from enum import Enum

from app.engines.schemas import EngineState
from app.fusion.signals import Signal, SignalKey
from app.fusion.thresholds import (
    COMPOSITE_WEIGHTS,
    ESCALATION_STRONG_SLOPE,
    NIGGLE_HIGH_INTENSITY,
    SCORE_LIGHTEN,
    SCORE_REST,
)

# Severity at/above which a subj-optimistic divergence is "strong" enough to rest.
_DIVERGENCE_REST_SEVERITY = 0.5


class Reco(str, Enum):
    """The day's training recommendation (never a medical diagnosis)."""

    TRAIN_AS_PLANNED = "train_as_planned"
    LIGHTEN = "lighten"
    REST = "rest"
    CONSULT_PHYSIO = "consult_physio"


@dataclass(frozen=True)
class Readiness:
    """The headline verdict: what to do and the two reasons why."""

    reco: Reco
    top_2: list[Signal]
    explanation: str


@dataclass(frozen=True)
class DailyRead:
    """The full daily readiness read returned by the fusion service."""

    date: date_
    engine_state: EngineState | None
    composite_score: float
    readiness: Readiness
    signals: list[Signal]


def composite_score(signals: list[Signal]) -> float:
    """Weighted mean of signal severities on a 0..1 scale (higher == worse).

    Normalized by the *total* configured weight, so a single fired signal yields
    a proportionate (not maxed-out) score.
    """

    total_weight = sum(COMPOSITE_WEIGHTS.values())
    if total_weight == 0.0:
        return 0.0
    weighted = sum(COMPOSITE_WEIGHTS.get(s.key, 0.0) * s.severity for s in signals)
    return weighted / total_weight


def top_2_signals(signals: list[Signal]) -> list[Signal]:
    """The two triggered signals with the highest severity (the "why")."""

    triggered = [s for s in signals if s.triggered]
    triggered.sort(key=lambda s: s.severity, reverse=True)
    return triggered[:2]


def _by_key(signals: list[Signal]) -> dict[SignalKey, Signal]:
    return {s.key: s for s in signals if s.triggered}


_REASON_PREFIX = {
    Reco.CONSULT_PHYSIO: "Worth discussing with a physio —",
    Reco.REST: "Back off and rest today —",
    Reco.LIGHTEN: "Ease up a bit today —",
    Reco.TRAIN_AS_PLANNED: "Good to train as planned.",
}


def recommend(
    signals: list[Signal],
    score: float,
    *,
    max_niggle_intensity: float | None = None,
) -> Reco:
    """Map the fired signals (and composite score) onto a recommendation.

    Priority: an injury that needs a physio first, then systemic rest, then a
    lighter day, else train as planned.
    """

    fired = _by_key(signals)
    escalation = fired.get("niggle_escalation")
    nload = fired.get("niggle_load_correlation")
    divergence = fired.get("divergence_subj_obj")

    strong_escalation = (
        escalation is not None
        and escalation.delta is not None
        and escalation.delta >= ESCALATION_STRONG_SLOPE
    )
    load_plus_intensity = (
        nload is not None
        and max_niggle_intensity is not None
        and max_niggle_intensity >= NIGGLE_HIGH_INTENSITY
    )
    if strong_escalation or load_plus_intensity:
        return Reco.CONSULT_PHYSIO

    severe_optimistic_gap = (
        divergence is not None
        and divergence.direction == "subj_optimistic"
        and divergence.severity >= _DIVERGENCE_REST_SEVERITY
    )
    if "illness_hint" in fired or score >= SCORE_REST or severe_optimistic_gap:
        return Reco.REST

    if score >= SCORE_LIGHTEN or divergence is not None or "wellness_divergence" in fired or nload:
        return Reco.LIGHTEN

    return Reco.TRAIN_AS_PLANNED


def _explain(reco: Reco, top: list[Signal]) -> str:
    if reco is Reco.TRAIN_AS_PLANNED or not top:
        return _REASON_PREFIX[Reco.TRAIN_AS_PLANNED]
    return f"{_REASON_PREFIX[reco]} {top[0].explanation}"


def build_readiness(
    signals: list[Signal], score: float, *, max_niggle_intensity: float | None = None
) -> Readiness:
    """Assemble the headline :class:`Readiness` from the fired signals."""

    reco = recommend(signals, score, max_niggle_intensity=max_niggle_intensity)
    top = top_2_signals(signals)
    return Readiness(reco=reco, top_2=top, explanation=_explain(reco, top))
