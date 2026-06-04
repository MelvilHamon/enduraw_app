"""The read-only engine port (a structural Protocol).

Both :class:`~app.engines.mock.MockEngine` and
:class:`~app.engines.coach_agent.CoachAgentEngine` satisfy this Protocol, so the
rest of the app depends on ``EnginePort`` rather than a concrete backend. Writes
(syncing app data back to CoachAgent) are a later step and live elsewhere.
"""

from __future__ import annotations

from datetime import date as date_
from typing import Protocol, runtime_checkable

from app.engines.schemas import EngineActivity, EngineState, EngineTimeseries


@runtime_checkable
class EnginePort(Protocol):
    """Read-only access to a training engine's state, timeseries and activities."""

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
