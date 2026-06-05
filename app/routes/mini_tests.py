"""Mini-test routes (all scoped to the authenticated user)."""

from __future__ import annotations

from datetime import date as date_
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.fusion import service as fusion_service
from app.models.enums import MiniTestType
from app.models.user import User
from app.routes._pagination import PaginationDep
from app.schemas.insights import MiniTestBaselineOut
from app.schemas.mini_test import MiniTestCreate, MiniTestOut
from app.services import mini_test_service

router = APIRouter(prefix="/api/mini-tests", tags=["mini-tests"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=MiniTestOut, status_code=status.HTTP_201_CREATED)
def create_mini_test(
    payload: MiniTestCreate, current_user: CurrentUser, db: DbSession
) -> MiniTestOut:
    """Record a mini-test; the body's ``data.type`` selects the payload schema."""

    mini_test = mini_test_service.create_mini_test(db, current_user.id, payload)
    return MiniTestOut.from_model(mini_test)


@router.get("/baseline", response_model=MiniTestBaselineOut)
def mini_test_baseline(
    current_user: CurrentUser,
    db: DbSession,
    type: Annotated[MiniTestType, Query(description="Which mini-test to baseline.")],
) -> MiniTestBaselineOut:
    """Rolling baseline (mean/std + latest z) for a mini-test type's headline metric."""

    result = fusion_service.mini_test_baseline(db, current_user.id, type)
    return MiniTestBaselineOut.from_result(result)


@router.get("", response_model=list[MiniTestOut])
def list_mini_tests(
    current_user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    type: Annotated[MiniTestType | None, Query(description="Filter by test type.")] = None,
    date_from: Annotated[date_ | None, Query(alias="from")] = None,
    date_to: Annotated[date_ | None, Query(alias="to")] = None,
) -> list[MiniTestOut]:
    """List the user's mini-tests, newest first."""

    rows = mini_test_service.list_mini_tests(
        db,
        current_user.id,
        type_=type,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [MiniTestOut.from_model(row) for row in rows]
