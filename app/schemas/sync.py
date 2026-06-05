"""Pydantic response schema for the sync route.

Maps the internal :class:`~app.services.sync_service.SyncResult` dataclass into a
JSON-serialisable shape, mirroring ``SignalOut.from_signal``.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.services.sync_service import SyncResult


class SyncResultOut(BaseModel):
    """How many checkins / feedbacks were pushed, plus any per-row errors."""

    wellness_synced: int
    feedback_synced: int
    errors: list[str]

    @classmethod
    def from_result(cls, result: SyncResult) -> SyncResultOut:
        return cls(
            wellness_synced=result.wellness_synced,
            feedback_synced=result.feedback_synced,
            errors=list(result.errors),
        )
