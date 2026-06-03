"""Niggle and niggle-report routes (all scoped to the authenticated user)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.niggle import Niggle, NiggleReport
from app.models.user import User
from app.routes._pagination import PaginationDep
from app.schemas.niggle import (
    NiggleCreate,
    NiggleOut,
    NigglePatch,
    NiggleWithReportsOut,
    ReportCreate,
    ReportOut,
)
from app.services import niggle_service
from app.services.niggle_service import NiggleClosedError

router = APIRouter(prefix="/api/niggles", tags=["niggles"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Niggle not found")


@router.post("", response_model=NiggleWithReportsOut, status_code=status.HTTP_201_CREATED)
def create_niggle(payload: NiggleCreate, current_user: CurrentUser, db: DbSession) -> Niggle:
    """Open a niggle, optionally with a first report embedded in the response."""

    return niggle_service.create_niggle(db, current_user.id, payload)


@router.get("", response_model=list[NiggleOut])
def list_niggles(
    current_user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    active: Annotated[bool, Query(description="Keep only open niggles.")] = False,
) -> list[Niggle]:
    """List niggles (without reports), newest first."""

    return niggle_service.list_niggles(
        db,
        current_user.id,
        active=active,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{niggle_id}", response_model=NiggleWithReportsOut)
def get_niggle(niggle_id: str, current_user: CurrentUser, db: DbSession) -> Niggle:
    """Return a niggle with its reports (date ascending), or ``404`` if not yours."""

    niggle = niggle_service.get_owned(db, current_user.id, niggle_id)
    if niggle is None:
        raise _NOT_FOUND
    return niggle


@router.patch("/{niggle_id}", response_model=NiggleWithReportsOut)
def patch_niggle(
    niggle_id: str, payload: NigglePatch, current_user: CurrentUser, db: DbSession
) -> Niggle:
    """Update ``closed_at`` / ``structure`` / ``notes``. ``region``/``side`` are immutable."""

    niggle = niggle_service.get_owned(db, current_user.id, niggle_id)
    if niggle is None:
        raise _NOT_FOUND
    return niggle_service.patch_niggle(db, niggle, payload)


@router.post(
    "/{niggle_id}/reports",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
)
def add_report(
    niggle_id: str, payload: ReportCreate, current_user: CurrentUser, db: DbSession
) -> NiggleReport:
    """Append a report to an open niggle (``404`` if not yours, ``409`` if closed)."""

    niggle = niggle_service.get_owned(db, current_user.id, niggle_id)
    if niggle is None:
        raise _NOT_FOUND
    try:
        return niggle_service.add_report(db, niggle, payload)
    except NiggleClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot add a report to a closed niggle",
        ) from exc
