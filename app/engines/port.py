"""The engine port (a structural Protocol).

Both :class:`~app.engines.mock.MockEngine` and
:class:`~app.engines.coach_agent.CoachAgentEngine` satisfy this Protocol, so the
rest of the app depends on ``EnginePort`` rather than a concrete backend. The
reads return the engine's truth; the ``push_*`` writes send the app's subjective
data back (live) or no-op (mock), reporting a :data:`PushOutcome` either way.
"""

from __future__ import annotations

from datetime import date as date_
from typing import Protocol, runtime_checkable

from app.engines.schemas import (
    EngineActivity,
    EngineState,
    EngineTimeseries,
    PushOutcome,
    SessionFeedbackPayload,
    WellnessDailyPayload,
)


@runtime_checkable
class EnginePort(Protocol):
    """Read the engine's state and push the app's subjective data back."""

    async def get_state(self, day: date_) -> EngineState:
        """Return the engine state for ``day`` (raises ``EngineNotFound`` if absent)."""
        ...

    async def get_timeseries(
        self, date_from: date_, date_to: date_, metrics: list[str]
    ) -> EngineTimeseries:
        """Return the requested ``metrics`` over ``[date_from, date_to]``."""
        ...

    async def get_activities(
        self, date_from: date_, date_to: date_, limit: int = 50
    ) -> list[EngineActivity]:
        """Return up to ``limit`` activities in ``[date_from, date_to]``, newest first."""
        ...

    async def push_wellness_daily(self, payload: WellnessDailyPayload) -> PushOutcome:
        """Upsert the day's subjective wellness; raises on upstream failure."""
        ...

    async def push_session_feedback(self, payload: SessionFeedbackPayload) -> PushOutcome:
        """Upsert post-session RPE/affect for an activity; raises on upstream failure."""
        ...
