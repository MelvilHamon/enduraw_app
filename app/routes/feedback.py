"""Session feedback routes (all scoped to the authenticated user)."""

from __future__ import annotations

from datetime import date as date_
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models.session_feedback import SessionFeedback
from app.models.user import User
from app.routes._pagination import PaginationDep
from app.schemas.feedback import SessionFeedbackCreate, SessionFeedbackOut
from app.services import feedback_service

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/session", response_model=SessionFeedbackOut, status_code=status.HTTP_201_CREATED)
def upsert_feedback(
    payload: SessionFeedbackCreate,
    current_user: CurrentUser,
    db: DbSession,
    response: Response,
) -> SessionFeedback:
    """Record feedback for an activity, replacing any prior entry for it.

    Returns ``201`` on first record, ``200`` when an existing entry is updated.
    ``source`` is always set to ``app_manual`` server-side.
    """

    feedback, created = feedback_service.upsert_feedback(db, current_user.id, payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return feedback


@router.get("/session", response_model=list[SessionFeedbackOut])
def list_feedback(
    current_user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    activity_id: Annotated[str | None, Query(description="Exact activity filter.")] = None,
    date_from: Annotated[date_ | None, Query(alias="from")] = None,
    date_to: Annotated[date_ | None, Query(alias="to")] = None,
) -> list[SessionFeedback]:
    """List the user's feedback, newest first."""

    return feedback_service.list_feedback(
        db,
        current_user.id,
        activity_id=activity_id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
