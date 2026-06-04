"""Deterministic, seed-driven synthetic athlete data generator.

Produces a full in-memory athlete history (sessions, daily metrics, check-ins,
mini-tests, niggle trajectories, illness episodes) as typed dataclasses that map
1:1 onto the ORM models / the step-5 ingestion payload. No database, no routes.
"""

from __future__ import annotations

from app.synth.dataset import (
    LatentState,
    SyntheticCheckin,
    SyntheticDailyMetric,
    SyntheticDataset,
    SyntheticIllnessEpisode,
    SyntheticMiniTest,
    SyntheticNiggle,
    SyntheticNiggleReport,
    SyntheticSession,
)
from app.synth.generator import generate, generate_cohort
from app.synth.personas import PRESETS, TRAIT_RANGES, TraitPreset, TraitVector, sample_trait_vector

__all__ = [
    "generate",
    "generate_cohort",
    "sample_trait_vector",
    "TraitVector",
    "TraitPreset",
    "PRESETS",
    "TRAIT_RANGES",
    "SyntheticDataset",
    "SyntheticSession",
    "SyntheticDailyMetric",
    "SyntheticCheckin",
    "SyntheticMiniTest",
    "SyntheticNiggle",
    "SyntheticNiggleReport",
    "SyntheticIllnessEpisode",
    "LatentState",
]
