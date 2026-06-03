"""Illness flag routes (all scoped to the authenticated user)."""

from __future__ import annotations

from datetime import date as date_
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.illness_flag import IllnessFlag
from app.models.user import User
from app.routes._pagination import PaginationDep
from app.schemas.illness import IllnessCreate, IllnessOut
from app.services import illness_service

router = APIRouter(prefix="/api/illness", tags=["illness"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=IllnessOut, status_code=status.HTTP_201_CREATED)
def upsert_illness(
    payload: IllnessCreate,
    current_user: CurrentUser,
    db: DbSession,
    response: Response,
) -> IllnessFlag:
    """Record an illness flag for a day, replacing any existing one.

    Returns ``201`` on first record, ``200`` when an existing entry is updated.
    """

    flag, created = illness_service.upsert_illness(db, current_user.id, payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return flag


@router.get("", response_model=list[IllnessOut])
def list_illness(
    current_user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    date_from: Annotated[date_ | None, Query(alias="from")] = None,
    date_to: Annotated[date_ | None, Query(alias="to")] = None,
) -> list[IllnessFlag]:
    """List the user's illness flags, newest first, within an optional date window."""

    return illness_service.list_illness(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
