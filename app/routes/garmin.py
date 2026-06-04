"""Garmin (faked) ingestion routes (all scoped to the authenticated user)."""

from __future__ import annotations

from datetime import date as date_
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.daily_metric import DailyMetric
from app.models.user import User
from app.routes._pagination import PaginationDep
from app.schemas.garmin import (
    DailyMetricOut,
    GarminIngestRequest,
    GarminIngestResponse,
)
from app.services import garmin_service

router = APIRouter(prefix="/api/garmin", tags=["garmin"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/ingest", response_model=GarminIngestResponse)
def ingest(
    payload: GarminIngestRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> GarminIngestResponse:
    """Ingest a batch of faked Garmin data (daily metrics + on-watch RPE).

    Daily metrics also refresh the illness watch-hint for each affected day.
    """

    daily_upserted, illness_flags_set = garmin_service.ingest_daily(
        db, current_user.id, payload.daily
    )
    sessions_upserted = garmin_service.ingest_session_feedback(
        db, current_user.id, payload.sessions
    )
    return GarminIngestResponse(
        daily_upserted=daily_upserted,
        sessions_upserted=sessions_upserted,
        illness_flags_set=illness_flags_set,
    )


@router.get("/daily", response_model=list[DailyMetricOut])
def list_daily(
    current_user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    date_from: Annotated[date_ | None, Query(alias="from")] = None,
    date_to: Annotated[date_ | None, Query(alias="to")] = None,
) -> list[DailyMetric]:
    """List the user's daily metrics, newest first, within an optional window."""

    return garmin_service.list_daily(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
