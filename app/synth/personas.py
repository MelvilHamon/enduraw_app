"""Athlete population model — continuous trait vectors with named preset anchors.

An athlete is a continuous :class:`TraitVector`. Each named :class:`TraitPreset`
gives a ``(mean, sd)`` per trait; :func:`sample_trait_vector` draws
``Normal(mean, sd)`` and clamps into the trait's range. The presets are
detector-aligned anchors (one per capability exercised downstream); variety comes
from sampling and from combining axes (an athlete can emerge high-load ×
poor-sleep). Categorical traits (``zone_bias``) are fixed weights per preset.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.models.enums import BodyRegion

# Continuous traits and their valid ``(lo, hi)`` ranges. Order is irrelevant; the
# sampler iterates this mapping and clamps each draw into its range.
TRAIT_RANGES: dict[str, tuple[float, float]] = {
    "weekly_trimp_target": (150.0, 600.0),
    "load_volatility": (0.0, 1.0),
    "subj_form_weight": (0.0, 1.0),
    "subj_sleep_weight": (0.0, 1.0),
    "subj_bias": (-1.5, 1.5),
    "subj_noise": (0.2, 1.0),
    "hrv_base": (50.0, 110.0),
    "rhr_base": (38.0, 60.0),
    "sleep_base": (55.0, 95.0),
    "fatigue_sensitivity": (0.5, 2.0),
    "niggle_hazard_base": (0.001, 0.02),
    "fitness_start": (0.0, 60.0),
    "jump_flight_base": (440.0, 580.0),
    "rt_base": (240.0, 340.0),
    "illness_rate": (1.0, 8.0),
}

# sd defaults to this fraction of a trait's range unless a preset overrides it.
DEFAULT_SD_FRACTION = 0.12


@dataclass(frozen=True)
class TraitVector:
    """A concrete, sampled athlete — one value per continuous trait.

    ``zone_bias`` are fixed per-region weights (copied from the preset, not
    sampled) used to pick the :class:`~app.models.enums.BodyRegion` of a niggle.
    """

    weekly_trimp_target: float
    load_volatility: float
    subj_form_weight: float
    subj_sleep_weight: float
    subj_bias: float
    subj_noise: float
    hrv_base: float
    rhr_base: float
    sleep_base: float
    fatigue_sensitivity: float
    niggle_hazard_base: float
    fitness_start: float
    jump_flight_base: float
    rt_base: float
    illness_rate: float
    zone_bias: dict[BodyRegion, float]

    def as_dict(self) -> dict[str, float]:
        """Continuous traits as a flat dict (``zone_bias`` excluded)."""

        return {name: float(getattr(self, name)) for name in TRAIT_RANGES}


@dataclass(frozen=True)
class TraitPreset:
    """A named detector-aligned anchor: a mean per trait + categorical weights."""

    name: str
    means: dict[str, float]
    zone_bias: dict[BodyRegion, float]
    sd_overrides: dict[str, float] = field(default_factory=dict)


# --- Categorical zone-bias weights -----------------------------------------
#
# Runner-biased region weights. The archetype draw (in the generator) keeps only
# regions that belong to an injury family, so every region listed here must be
# reachable by at least one archetype. Weights are relative (normalised at draw).

_RUNNER_ZONE_BASE: dict[BodyRegion, float] = {
    BodyRegion.ACHILLES: 1.0,
    BodyRegion.CALF: 1.0,
    BodyRegion.SHIN: 1.0,
    BodyRegion.KNEE_ANTERIOR: 1.0,
    BodyRegion.IT_BAND: 1.0,
    BodyRegion.FOOT_FORE: 0.7,
    BodyRegion.FOOT_MID: 0.7,
    BodyRegion.FOOT_HEEL: 0.7,
    BodyRegion.HAMSTRING: 1.0,
    BodyRegion.QUAD: 0.6,
    BodyRegion.ANKLE: 0.6,
}


def _zone_bias(multipliers: dict[BodyRegion, float] | None = None) -> dict[BodyRegion, float]:
    """Runner zone weights with optional per-region multipliers applied."""

    weights = dict(_RUNNER_ZONE_BASE)
    for region, factor in (multipliers or {}).items():
        weights[region] = weights[region] * factor
    return weights


# Load-driven overuse focus (bone stress + tendinopathy from too much volume).
_OVERTRAINER_ZONE = _zone_bias(
    {BodyRegion.SHIN: 2.0, BodyRegion.ACHILLES: 1.8, BodyRegion.KNEE_ANTERIOR: 1.6}
)
# Marked overuse-injury bias (tendinopathy / ITBS), sharper than baseline.
_INJURY_PRONE_ZONE = _zone_bias(
    {
        BodyRegion.ACHILLES: 2.2,
        BodyRegion.IT_BAND: 2.0,
        BodyRegion.KNEE_ANTERIOR: 1.8,
        BodyRegion.SHIN: 1.6,
    }
)


PRESETS: dict[str, TraitPreset] = {
    "Regular": TraitPreset(
        name="Regular",
        means={
            "weekly_trimp_target": 350.0,
            "load_volatility": 0.25,
            "subj_form_weight": 0.85,
            "subj_sleep_weight": 0.15,
            "subj_bias": 0.0,
            "subj_noise": 0.35,
            "hrv_base": 80.0,
            "rhr_base": 46.0,
            "sleep_base": 82.0,
            "fatigue_sensitivity": 1.0,
            "niggle_hazard_base": 0.004,
            "fitness_start": 35.0,
            "jump_flight_base": 530.0,
            "rt_base": 270.0,
            "illness_rate": 3.0,
        },
        zone_bias=_zone_bias(),
    ),
    "OverTrainer": TraitPreset(
        name="OverTrainer",
        means={
            "weekly_trimp_target": 520.0,
            "load_volatility": 0.75,
            "subj_form_weight": 0.45,
            "subj_sleep_weight": 0.10,
            "subj_bias": 0.9,
            "subj_noise": 0.55,
            "hrv_base": 75.0,
            "rhr_base": 44.0,
            "sleep_base": 78.0,
            "fatigue_sensitivity": 1.4,
            "niggle_hazard_base": 0.010,
            "fitness_start": 50.0,
            "jump_flight_base": 525.0,
            "rt_base": 275.0,
            "illness_rate": 5.0,
        },
        zone_bias=_OVERTRAINER_ZONE,
    ),
    "PoorSleeper": TraitPreset(
        name="PoorSleeper",
        means={
            "weekly_trimp_target": 360.0,
            "load_volatility": 0.30,
            "subj_form_weight": 0.40,
            "subj_sleep_weight": 0.65,
            "subj_bias": -0.3,
            "subj_noise": 0.55,
            "hrv_base": 70.0,
            "rhr_base": 50.0,
            "sleep_base": 62.0,
            "fatigue_sensitivity": 1.2,
            "niggle_hazard_base": 0.004,
            "fitness_start": 35.0,
            "jump_flight_base": 515.0,
            "rt_base": 285.0,
            "illness_rate": 6.0,
        },
        zone_bias=_zone_bias(),
    ),
    "InjuryProne": TraitPreset(
        name="InjuryProne",
        means={
            "weekly_trimp_target": 340.0,
            "load_volatility": 0.35,
            "subj_form_weight": 0.70,
            "subj_sleep_weight": 0.15,
            "subj_bias": -0.2,
            "subj_noise": 0.45,
            "hrv_base": 78.0,
            "rhr_base": 47.0,
            "sleep_base": 80.0,
            "fatigue_sensitivity": 1.1,
            "niggle_hazard_base": 0.016,
            "fitness_start": 35.0,
            "jump_flight_base": 520.0,
            "rt_base": 275.0,
            "illness_rate": 3.0,
        },
        # Marked bias + wider spread on the region draw.
        zone_bias=_INJURY_PRONE_ZONE,
    ),
    "Beginner": TraitPreset(
        name="Beginner",
        means={
            "weekly_trimp_target": 200.0,
            "load_volatility": 0.45,
            "subj_form_weight": 0.55,
            "subj_sleep_weight": 0.25,
            "subj_bias": -0.4,
            "subj_noise": 0.70,
            "hrv_base": 65.0,
            "rhr_base": 54.0,
            "sleep_base": 75.0,
            "fatigue_sensitivity": 1.5,
            "niggle_hazard_base": 0.008,
            "fitness_start": 15.0,
            "jump_flight_base": 480.0,
            "rt_base": 300.0,
            "illness_rate": 4.0,
        },
        zone_bias=_zone_bias(),
    ),
}


def sample_trait_vector(preset_name: str, rng: np.random.Generator) -> TraitVector:
    """Draw a concrete :class:`TraitVector` from a named preset.

    Each continuous trait is drawn ``Normal(mean, sd)`` — ``sd`` defaulting to
    ``DEFAULT_SD_FRACTION`` of the trait's range — then clamped into range.
    ``zone_bias`` is copied verbatim from the preset (fixed categorical weights).
    """

    try:
        preset = PRESETS[preset_name]
    except KeyError as exc:
        raise ValueError(
            f"unknown preset {preset_name!r}; choose one of {sorted(PRESETS)}"
        ) from exc

    values: dict[str, float] = {}
    for trait, (lo, hi) in TRAIT_RANGES.items():
        mean = preset.means[trait]
        sd = preset.sd_overrides.get(trait, DEFAULT_SD_FRACTION * (hi - lo))
        draw = float(rng.normal(mean, sd))
        values[trait] = min(hi, max(lo, draw))

    return TraitVector(**values, zone_bias=dict(preset.zone_bias))
