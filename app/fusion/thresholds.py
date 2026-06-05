"""Named, tunable thresholds and weights for the fusion layer.

Everything the rules and readiness logic key off lives here so the brain can be
re-calibrated in one place. Windows mirror the engine/synth conventions
(acute 7d, chronic 28d) so the fusion layer speaks the same dialect.
"""

from __future__ import annotations

from app.fusion.signals import SignalKey

# --- Rolling baselines (mirror app/synth/generator) ---------------------------
ROLL_SHORT = 7  # personal "recent" window (wellness band, mini-tests)
ROLL_LONG = 28  # personal "normal" window (z-scores)
ROLL_MIN_OBS = 7  # fewer observations than this -> no baseline (warmup)
Z_CLAMP = 3.0  # clamp z-scores into [-Z_CLAMP, Z_CLAMP]
ACUTE_WINDOW = 7
CHRONIC_WINDOW = 28

# --- Rule trigger thresholds --------------------------------------------------
# Divergence subjective↔objective: flag when the gap between the z-scored
# subjective form and the z-scored engine form exceeds this many sigma.
DIVERGENCE_SIGMA = 1.5

# Niggle escalation: least-squares slope (intensity points per report) over the
# last few reports of an active niggle.
ESCALATION_SLOPE = 0.5
ESCALATION_MIN_REPORTS = 3
ESCALATION_MAX_REPORTS = 5
ESCALATION_STRONG_SLOPE = 1.0  # "strong" escalation -> consult_physio

# Niggle×load: a niggle opened within this many hours after an ACWR spike.
NIGGLE_LOAD_WINDOW_H = 48
ACWR_SPIKE = 1.3

# A niggle report intensity (0..10) at/above this counts as "high intensity".
NIGGLE_HIGH_INTENSITY = 6

# Wellness band: flag a day whose value falls this many sigma outside the
# rolling band of HRV / sleep / RHR.
WELLNESS_BAND_SIGMA = 1.0

# Mini-test trend: flag degradation worse than this many sigma vs the baseline.
MINI_TEST_SIGMA = 1.0

# --- Composite score ----------------------------------------------------------
# Per-signal weights (the divergence is weighted strongest, per the product
# anchor). They need not sum to 1 — the composite normalizes by the total weight.
COMPOSITE_WEIGHTS: dict[SignalKey, float] = {
    "divergence_subj_obj": 0.30,
    "illness_hint": 0.25,
    "niggle_escalation": 0.20,
    "niggle_load_correlation": 0.15,
    "wellness_divergence": 0.15,
    "mini_test_trend": 0.10,
}

# --- Recommendation cutoffs (on the 0..1 composite score) ---------------------
# Higher score == more concerning (it is a weighted sum of severities).
SCORE_REST = 0.6  # at/above -> rest if no stronger reason already fired
SCORE_LIGHTEN = 0.3  # at/above -> lighten
