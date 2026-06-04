"""Engine abstraction: a read-only port over a training engine (CoachAgent).

``MockEngine`` serves the standalone synthetic data; ``CoachAgentEngine`` talks
to the live REST API; ``get_engine`` picks one from settings. Everything else
depends on :class:`EnginePort`, never a concrete backend.
"""

from __future__ import annotations

from app.engines.coach_agent import CoachAgentEngine
from app.engines.errors import (
    EngineAuthError,
    EngineBadRequest,
    EngineConfigError,
    EngineError,
    EngineNotFound,
    EngineUpstreamError,
)
from app.engines.factory import EngineDep, get_engine
from app.engines.mock import MockEngine
from app.engines.port import EnginePort
from app.engines.schemas import (
    EngineActivity,
    EnginePoint,
    EngineState,
    EngineTimeseries,
    ReadinessHint,
    compute_readiness_hint,
)

__all__ = [
    "CoachAgentEngine",
    "EngineActivity",
    "EngineAuthError",
    "EngineBadRequest",
    "EngineConfigError",
    "EngineDep",
    "EngineError",
    "EngineNotFound",
    "EnginePoint",
    "EnginePort",
    "EngineState",
    "EngineTimeseries",
    "EngineUpstreamError",
    "MockEngine",
    "ReadinessHint",
    "compute_readiness_hint",
    "get_engine",
]
