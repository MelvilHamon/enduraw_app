"""Insights routes: the fused readiness read (all scoped to the auth'd user)."""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as date_
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.engines.factory import EngineDep
from app.fusion import service as fusion_service
from app.models.user import User
from app.schemas.insights import CorrelationsOut, DailyReadOut, TimeseriesOut

router = APIRouter(prefix="/api/insights", tags=["insights"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

# Engine metrics surfaced by the timeseries route when none are requested.
_DEFAULT_METRICS = ["fitness", "fatigue", "form", "acwr"]


def _today() -> date_:
    return datetime.now(UTC).date()


@router.get("/today", response_model=DailyReadOut)
async def today(current_user: CurrentUser, db: DbSession, engine: EngineDep) -> DailyReadOut:
    """The athlete's readiness read for today: signals, composite, recommendation."""

    read = await fusion_service.compute_daily_read(db, current_user, _today(), engine)
    return DailyReadOut.from_read(read)


@router.get("/timeseries", response_model=TimeseriesOut)
async def timeseries(
    current_user: CurrentUser,
    db: DbSession,
    engine: EngineDep,
    date_from: Annotated[date_, Query(alias="from")],
    date_to: Annotated[date_, Query(alias="to")],
    metrics: Annotated[list[str] | None, Query(description="Engine metrics to include.")] = None,
) -> TimeseriesOut:
    """Fused engine + subjective form + divergence Δ over ``[from, to]``."""

    read = await fusion_service.compute_timeseries(
        db, current_user, date_from, date_to, metrics or _DEFAULT_METRICS, engine
    )
    return TimeseriesOut.from_read(read)


@router.get("/correlations", response_model=CorrelationsOut)
async def correlations(
    current_user: CurrentUser,
    db: DbSession,
    engine: EngineDep,
    date_from: Annotated[date_, Query(alias="from")],
    date_to: Annotated[date_, Query(alias="to")],
) -> CorrelationsOut:
    """Niggle×load summary: each niggle opened in the window and its onset ACWR."""

    read = await fusion_service.compute_correlations(db, current_user, date_from, date_to, engine)
    return CorrelationsOut.from_read(read)
