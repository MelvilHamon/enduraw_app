"""Shared pagination dependency for the list endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass
class Pagination:
    """A validated ``limit`` / ``offset`` pair."""

    limit: int
    offset: int


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Max rows to return.")] = (
        DEFAULT_LIMIT
    ),
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]
