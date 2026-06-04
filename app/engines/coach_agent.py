"""Live engine talking to the external CoachAgent REST API over httpx.

Implements the three read endpoints of the contract, authenticating with a
bearer token. Transient failures (5xx and timeouts / transport errors) are
retried with exponential backoff; everything else is mapped to a typed
:mod:`app.engines.errors` exception so callers stay backend-agnostic.
"""

from __future__ import annotations

import asyncio
from datetime import date as date_
from typing import Any

import httpx

from app.engines.errors import (
    EngineAuthError,
    EngineBadRequest,
    EngineNotFound,
    EngineUpstreamError,
)
from app.engines.schemas import EngineActivity, EngineState, EngineTimeseries

_STATE_PATH = "/api/v1/engine/state"
_TIMESERIES_PATH = "/api/v1/engine/timeseries"
_ACTIVITIES_PATH = "/api/v1/activities"


class CoachAgentEngine:
    """Read-only client for the CoachAgent training engine."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout_s: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout_s),
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""

        await self._client.aclose()

    async def get_state(self, day: date_) -> EngineState:
        payload = await self._get(_STATE_PATH, {"date": day.isoformat()})
        return EngineState.model_validate(payload)

    async def get_timeseries(
        self, date_from: date_, date_to: date_, metrics: list[str]
    ) -> EngineTimeseries:
        payload = await self._get(
            _TIMESERIES_PATH,
            {
                "from": date_from.isoformat(),
                "to": date_to.isoformat(),
                "metrics": ",".join(metrics),
            },
        )
        return EngineTimeseries.model_validate(payload)

    async def get_activities(
        self, date_from: date_, date_to: date_, limit: int = 50
    ) -> list[EngineActivity]:
        payload = await self._get(
            _ACTIVITIES_PATH,
            {"from": date_from.isoformat(), "to": date_to.isoformat(), "limit": limit},
        )
        return [EngineActivity.model_validate(item) for item in payload]

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        """GET ``path`` with retries on transient failures; map errors to exceptions.

        Makes up to ``max_retries`` retries *after* the initial attempt. 5xx and
        timeout / transport errors are retried; 4xx fail fast.
        """

        delay = self._backoff_base
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(path, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                raise EngineUpstreamError(f"CoachAgent request to {path} failed: {exc}") from exc

            if response.status_code >= 500:
                if attempt < self._max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                raise EngineUpstreamError(self._detail(response))

            if response.status_code >= 400:
                self._raise_client_error(response)

            return response.json()

        # Unreachable: the loop either returns or raises on its final iteration.
        raise EngineUpstreamError(f"CoachAgent request to {path} failed: {last_exc}")

    def _raise_client_error(self, response: httpx.Response) -> None:
        detail = self._detail(response)
        if response.status_code == 401:
            raise EngineAuthError(detail)
        if response.status_code == 404:
            raise EngineNotFound(detail)
        raise EngineBadRequest(detail)

    @staticmethod
    def _detail(response: httpx.Response) -> str:
        """Best-effort human-readable detail from a ``{error, message}`` body."""

        try:
            body = response.json()
        except ValueError:
            return f"HTTP {response.status_code}"
        if isinstance(body, dict):
            message = body.get("message") or body.get("error")
            if message:
                return f"HTTP {response.status_code}: {message}"
        return f"HTTP {response.status_code}"
