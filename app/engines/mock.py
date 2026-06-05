"""Standalone engine backed by a per-user JSON snapshot on disk.

Serves the same shapes as the live CoachAgent engine from the generator's latent
truth (see :mod:`app.engines.snapshot`). Derived fields not stored in the
snapshot — ``load_7d`` / ``load_28d`` (trailing sums of daily load),
``trend_form_7d`` (7-day form delta) and ``readiness_hint`` — are computed here
with the shared rule, so the mock and live backends agree.
"""

from __future__ import annotations

from datetime import date as date_

from app.engines.errors import EngineBadRequest, EngineNotFound
from app.engines.schemas import (
    TIMESERIES_METRICS,
    EngineActivity,
    EnginePoint,
    EngineState,
    EngineTimeseries,
    PushOutcome,
    SessionFeedbackPayload,
    WellnessDailyPayload,
    compute_readiness_hint,
)
from app.engines.snapshot import EngineSnapshot, load_snapshot

_LOAD_7D_WINDOW = 7
_LOAD_28D_WINDOW = 28
_TREND_LAG = 7


class MockEngine:
    """Read-only engine serving one user's snapshot (lazily loaded and cached)."""

    def __init__(self, user_id: str, base_dir: str) -> None:
        self._user_id = user_id
        self._base_dir = base_dir
        self._snapshot: EngineSnapshot | None = None
        self._index: dict[date_, int] | None = None

    def _load(self) -> EngineSnapshot:
        if self._snapshot is None:
            self._snapshot = load_snapshot(self._base_dir, self._user_id)
            self._index = {day: i for i, day in enumerate(self._snapshot.dates)}
        return self._snapshot

    def _index_of(self, day: date_) -> int:
        self._load()
        assert self._index is not None  # set by _load
        idx = self._index.get(day)
        if idx is None:
            raise EngineNotFound(f"No engine state for {day.isoformat()} (user {self._user_id!r})")
        return idx

    async def get_state(self, day: date_) -> EngineState:
        snap = self._load()
        i = self._index_of(day)

        form = snap.form[i]
        acwr = snap.acwr[i]
        load_7d = sum(snap.daily_load[max(0, i - _LOAD_7D_WINDOW + 1) : i + 1])
        load_28d = sum(snap.daily_load[max(0, i - _LOAD_28D_WINDOW + 1) : i + 1])
        trend_form_7d = form - snap.form[i - _TREND_LAG] if i >= _TREND_LAG else None

        return EngineState(
            date=day,
            fitness=snap.fitness[i],
            fatigue=snap.fatigue[i],
            form=form,
            acwr=acwr,
            load_7d=load_7d,
            load_28d=load_28d,
            trend_form_7d=trend_form_7d,
            readiness_hint=compute_readiness_hint(form, acwr),
        )

    async def get_timeseries(
        self, date_from: date_, date_to: date_, metrics: list[str]
    ) -> EngineTimeseries:
        unknown = [m for m in metrics if m not in TIMESERIES_METRICS]
        if unknown:
            raise EngineBadRequest(f"Unknown timeseries metric(s): {', '.join(sorted(unknown))}")

        snap = self._load()
        columns: dict[str, list[float | None]] = {
            "fitness": list(snap.fitness),
            "fatigue": list(snap.fatigue),
            "form": list(snap.form),
            "load": list(snap.daily_load),
            "acwr": list(snap.acwr),
        }
        window = [(i, day) for i, day in enumerate(snap.dates) if date_from <= day <= date_to]
        series = {
            metric: [EnginePoint(date=day, value=columns[metric][i]) for i, day in window]
            for metric in metrics
        }
        return EngineTimeseries(date_from=date_from, date_to=date_to, series=series)

    async def get_activities(
        self, date_from: date_, date_to: date_, limit: int = 50
    ) -> list[EngineActivity]:
        snap = self._load()
        in_window = [
            a for a in snap.activities if date_from <= date_.fromisoformat(a["date"]) <= date_to
        ]
        in_window.sort(key=lambda a: a["date"], reverse=True)
        return [EngineActivity.model_validate(a) for a in in_window[:limit]]

    async def push_wellness_daily(self, payload: WellnessDailyPayload) -> PushOutcome:
        # Standalone has no CoachAgent to receive writes: a true no-op.
        return "skipped"

    async def push_session_feedback(self, payload: SessionFeedbackPayload) -> PushOutcome:
        return "skipped"
