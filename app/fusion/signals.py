"""The uniform :class:`Signal` returned by every fusion rule."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Where a signal pushes readiness. For the divergence rule the direction encodes
# *who* is more optimistic — ``subj_optimistic`` (the athlete feels better than
# the engine's form) is the dangerous gap. The wellness/mini-test rules use the
# plain ``up`` / ``down`` of the underlying metric.
SignalDirection = Literal["subj_optimistic", "subj_pessimistic", "up", "down"]

# Stable keys, one per rule, used for weighting and top-signal selection.
SignalKey = Literal[
    "divergence_subj_obj",
    "niggle_escalation",
    "niggle_load_correlation",
    "wellness_divergence",
    "mini_test_trend",
    "illness_hint",
]


@dataclass(frozen=True)
class Signal:
    """One rule's verdict for a day.

    ``severity`` is a 0..1 magnitude (0 when not triggered) used by readiness to
    weight and rank signals. ``value``/``reference``/``delta`` carry the raw
    numbers behind the verdict so the UI can explain it, and ``evidence`` holds
    short human-readable fragments.
    """

    key: SignalKey
    triggered: bool
    severity: float
    value: float | None = None
    reference: float | None = None
    delta: float | None = None
    direction: SignalDirection | None = None
    explanation: str = ""
    evidence: list[str] = field(default_factory=list)
