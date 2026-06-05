"""Pydantic response schemas for the insights (fusion) routes.

These sit at the API boundary and map the internal fusion dataclasses
(:class:`~app.fusion.signals.Signal`, :class:`~app.fusion.readiness.DailyRead`,
etc.) into JSON-serialisable shapes, mirroring ``MiniTestOut.from_model``.
"""

from __future__ import annotations

from datetime import date as date_

from pydantic import BaseModel

from app.engines.schemas import EnginePoint, EngineState
from app.fusion.readiness import DailyRead, Readiness
from app.fusion.service import (
    CorrelationsRead,
    MiniTestBaseline,
    NiggleCorrelation,
    TimeseriesRead,
)
from app.fusion.signals import Signal


class SignalOut(BaseModel):
    """One rule's verdict, with the numbers behind it."""

    key: str
    triggered: bool
    severity: float
    value: float | None
    reference: float | None
    delta: float | None
    direction: str | None
    explanation: str
    evidence: list[str]

    @classmethod
    def from_signal(cls, s: Signal) -> SignalOut:
        return cls(
            key=s.key,
            triggered=s.triggered,
            severity=s.severity,
            value=s.value,
            reference=s.reference,
            delta=s.delta,
            direction=s.direction,
            explanation=s.explanation,
            evidence=list(s.evidence),
        )


class ReadinessOut(BaseModel):
    """The headline recommendation and the two reasons for it."""

    reco: str
    top_2: list[SignalOut]
    explanation: str

    @classmethod
    def from_readiness(cls, r: Readiness) -> ReadinessOut:
        return cls(
            reco=r.reco.value,
            top_2=[SignalOut.from_signal(s) for s in r.top_2],
            explanation=r.explanation,
        )


class DailyReadOut(BaseModel):
    """The full daily readiness read returned by ``GET /api/insights/today``."""

    date: date_
    engine_state: EngineState | None
    composite_score: float
    readiness: ReadinessOut
    signals: list[SignalOut]

    @classmethod
    def from_read(cls, read: DailyRead) -> DailyReadOut:
        return cls(
            date=read.date,
            engine_state=read.engine_state,
            composite_score=read.composite_score,
            readiness=ReadinessOut.from_readiness(read.readiness),
            signals=[SignalOut.from_signal(s) for s in read.signals],
        )


class TimeseriesOut(BaseModel):
    """Fused engine + subjective + divergence series."""

    date_from: date_
    date_to: date_
    series: dict[str, list[EnginePoint]]
    form_vs_normal: list[EnginePoint]
    divergence: list[EnginePoint]

    @classmethod
    def from_read(cls, read: TimeseriesRead) -> TimeseriesOut:
        return cls(
            date_from=read.date_from,
            date_to=read.date_to,
            series=read.series,
            form_vs_normal=read.form_vs_normal,
            divergence=read.divergence,
        )


class NiggleCorrelationOut(BaseModel):
    """One niggle's link to the acute load around its onset."""

    niggle_id: str
    region: str
    opened_at: date_
    peak_acwr_before_open: float | None
    load_linked: bool

    @classmethod
    def from_item(cls, item: NiggleCorrelation) -> NiggleCorrelationOut:
        return cls(
            niggle_id=item.niggle_id,
            region=item.region,
            opened_at=item.opened_at,
            peak_acwr_before_open=item.peak_acwr_before_open,
            load_linked=item.load_linked,
        )


class CorrelationsOut(BaseModel):
    """Niggle×load summary over a window."""

    date_from: date_
    date_to: date_
    total: int
    load_linked_count: int
    niggles: list[NiggleCorrelationOut]

    @classmethod
    def from_read(cls, read: CorrelationsRead) -> CorrelationsOut:
        return cls(
            date_from=read.date_from,
            date_to=read.date_to,
            total=read.total,
            load_linked_count=read.load_linked_count,
            niggles=[NiggleCorrelationOut.from_item(i) for i in read.niggles],
        )


class MiniTestBaselineOut(BaseModel):
    """Rolling baseline for a mini-test type's headline metric."""

    type: str
    metric: str
    n: int
    mean: float | None
    std: float | None
    latest: float | None
    latest_z: float | None

    @classmethod
    def from_result(cls, b: MiniTestBaseline) -> MiniTestBaselineOut:
        return cls(
            type=b.type,
            metric=b.metric,
            n=b.n,
            mean=b.mean,
            std=b.std,
            latest=b.latest,
            latest_z=b.latest_z,
        )
