"""Daily checkin routes (all scoped to the authenticated user)."""

from __future__ import annotations

from datetime import date as date_
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import Settings, get_settings
from app.db import get_db
from app.models.daily_checkin import DailyCheckin
from app.models.user import User
from app.routes._pagination import PaginationDep
from app.schemas.checkin import CheckinCreate, CheckinOut
from app.services import checkin_service, sync_service

router = APIRouter(prefix="/api/checkin", tags=["checkin"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", response_model=CheckinOut, status_code=status.HTTP_201_CREATED)
def upsert_checkin(
    payload: CheckinCreate,
    current_user: CurrentUser,
    db: DbSession,
    response: Response,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
) -> DailyCheckin:
    """Record the day's checkin, replacing any existing entry for that date.

    Returns ``201`` on first record of the day, ``200`` when an existing entry
    is updated. In live mode the checkin is pushed to CoachAgent in the
    background; in standalone nothing is queued.
    """

    checkin, created = checkin_service.upsert_checkin(db, current_user.id, payload)
    if settings.ENGINE_MODE == "live" and settings.SYNC_ON_WRITE:
        background_tasks.add_task(
            sync_service.run_checkin_sync, checkin.id, current_user.id, settings
        )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return checkin


@router.get("/today", response_model=CheckinOut)
def get_today(current_user: CurrentUser, db: DbSession) -> DailyCheckin:
    """Return today's checkin, or ``404`` if it has not been recorded yet."""

    checkin = checkin_service.get_today(db, current_user.id)
    if checkin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No checkin recorded today"
        )
    return checkin


@router.get("", response_model=list[CheckinOut])
def list_checkins(
    current_user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    date_from: Annotated[date_ | None, Query(alias="from")] = None,
    date_to: Annotated[date_ | None, Query(alias="to")] = None,
) -> list[DailyCheckin]:
    """List the user's checkins, newest first, within an optional date window."""

    return checkin_service.list_checkins(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
