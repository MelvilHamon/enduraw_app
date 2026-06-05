"""Manual sync route: flush the user's unsynced subjective data to the engine."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.engines.factory import EngineDep
from app.models.user import User
from app.schemas.sync import SyncResultOut
from app.services import sync_service

router = APIRouter(prefix="/api/sync", tags=["sync"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/coachagent", response_model=SyncResultOut)
async def sync_coachagent(
    current_user: CurrentUser, db: DbSession, engine: EngineDep
) -> SyncResultOut:
    """Push every unsynced checkin + feedback to the engine, returning the counts.

    Real in ``live`` mode; a no-op (all counts ``0``) in standalone.
    """

    result = await sync_service.flush_user(db, current_user, engine)
    return SyncResultOut.from_result(result)
