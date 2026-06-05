"""CoachAgentEngine: parsing the live contract and handling failures (via respx)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

import httpx
import pytest
import respx

from app.engines.coach_agent import CoachAgentEngine
from app.engines.errors import (
    EngineAuthError,
    EngineBadRequest,
    EngineNotFound,
    EngineUpstreamError,
)
from app.engines.schemas import SessionFeedbackPayload, WellnessDailyPayload

_BASE = "https://coach.test"
_DAY = date(2026, 6, 4)

_STATE_JSON = {
    "date": "2026-06-04",
    "fitness": 64.2,
    "fatigue": 9.1,
    "form": 14.1,
    "acwr": 1.05,
    "load_7d": 412.0,
    "load_28d": 1583.0,
    "trend_form_7d": 3.2,
    "readiness_hint": "neutral",
}


def _engine() -> CoachAgentEngine:
    # backoff_base=0 keeps retry tests instant.
    return CoachAgentEngine(_BASE, "secret-key", max_retries=2, backoff_base=0.0)


@respx.mock
async def test_get_state_parses_and_sends_bearer() -> None:
    route = respx.get(f"{_BASE}/api/v1/engine/state").mock(
        return_value=httpx.Response(200, json=_STATE_JSON)
    )
    engine = _engine()
    state = await engine.get_state(_DAY)
    await engine.aclose()

    assert state.fitness == pytest.approx(64.2)
    assert state.readiness_hint == "neutral"
    assert route.calls.last.request.headers["authorization"] == "Bearer secret-key"
    assert route.calls.last.request.url.params["date"] == "2026-06-04"


@respx.mock
async def test_get_timeseries_parses() -> None:
    body = {
        "date_from": "2026-06-01",
        "date_to": "2026-06-03",
        "series": {
            "form": [{"date": "2026-06-01", "value": 1.0}, {"date": "2026-06-02", "value": None}]
        },
    }
    route = respx.get(f"{_BASE}/api/v1/engine/timeseries").mock(
        return_value=httpx.Response(200, json=body)
    )
    engine = _engine()
    ts = await engine.get_timeseries(date(2026, 6, 1), date(2026, 6, 3), ["form"])
    await engine.aclose()

    assert ts.series["form"][1].value is None
    assert route.calls.last.request.url.params["metrics"] == "form"


@respx.mock
async def test_get_activities_parses() -> None:
    body = [
        {
            "id": "a1",
            "date": "2026-06-04",
            "type": "tempo",
            "duration_s": 3600,
            "distance_m": 14200.0,
            "trimp": 92.5,
            "hr_tss": 78.0,
            "elevation_gain_m": 120.0,
        }
    ]
    respx.get(f"{_BASE}/api/v1/activities").mock(return_value=httpx.Response(200, json=body))
    engine = _engine()
    acts = await engine.get_activities(date(2026, 6, 1), _DAY, limit=10)
    await engine.aclose()

    assert len(acts) == 1
    assert acts[0].id == "a1"


@respx.mock
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, EngineAuthError),
        (400, EngineBadRequest),
        (404, EngineNotFound),
        (403, EngineBadRequest),  # other 4xx → bad request
    ],
)
async def test_client_errors_map_to_exceptions(status: int, expected: type[Exception]) -> None:
    route = respx.get(f"{_BASE}/api/v1/engine/state").mock(
        return_value=httpx.Response(status, json={"error": "x", "message": "nope"})
    )
    engine = _engine()
    with pytest.raises(expected):
        await engine.get_state(_DAY)
    await engine.aclose()
    assert route.call_count == 1  # 4xx is not retried


@respx.mock
async def test_5xx_retried_then_upstream_error() -> None:
    route = respx.get(f"{_BASE}/api/v1/engine/state").mock(
        return_value=httpx.Response(503, json={"message": "down"})
    )
    engine = _engine()  # max_retries=2 → 3 attempts
    with pytest.raises(EngineUpstreamError):
        await engine.get_state(_DAY)
    await engine.aclose()
    assert route.call_count == 3


@respx.mock
async def test_timeout_retried_then_upstream_error() -> None:
    route = respx.get(f"{_BASE}/api/v1/engine/state").mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )
    engine = _engine()
    with pytest.raises(EngineUpstreamError):
        await engine.get_state(_DAY)
    await engine.aclose()
    assert route.call_count == 3


@respx.mock
async def test_success_after_retry() -> None:
    route = respx.get(f"{_BASE}/api/v1/engine/state").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json=_STATE_JSON)]
    )
    engine = _engine()
    state = await engine.get_state(_DAY)
    await engine.aclose()

    assert state.fitness == pytest.approx(64.2)
    assert route.call_count == 2


# --- writes -----------------------------------------------------------------

_WELLNESS = WellnessDailyPayload(
    date=_DAY, form_vs_normal=1, motivation=4, fatigue=2, active_niggles=3
)
_FEEDBACK = SessionFeedbackPayload(
    activity_id="a1",
    rpe=7,
    affect="strong",
    reported_at=datetime(2026, 6, 4, 18, 30, tzinfo=UTC),
)


@respx.mock
async def test_push_wellness_posts_contract_with_bearer() -> None:
    route = respx.post(f"{_BASE}/api/v1/wellness/daily").mock(return_value=httpx.Response(200))
    engine = _engine()
    outcome = await engine.push_wellness_daily(_WELLNESS)
    await engine.aclose()

    assert outcome == "sent"
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer secret-key"
    assert json.loads(request.content) == {
        "date": "2026-06-04",
        "form_vs_normal": 1,
        "motivation": 4,
        "fatigue": 2,
        "active_niggles": 3,
    }


@respx.mock
async def test_push_feedback_posts_contract() -> None:
    route = respx.post(f"{_BASE}/api/v1/feedback/session").mock(return_value=httpx.Response(201))
    engine = _engine()
    outcome = await engine.push_session_feedback(_FEEDBACK)
    await engine.aclose()

    assert outcome == "sent"
    assert json.loads(route.calls.last.request.content) == {
        "activity_id": "a1",
        "rpe": 7,
        "affect": "strong",
        "reported_at": "2026-06-04T18:30:00Z",
    }


@respx.mock
async def test_push_5xx_retried_then_upstream_error() -> None:
    route = respx.post(f"{_BASE}/api/v1/wellness/daily").mock(
        return_value=httpx.Response(503, json={"message": "down"})
    )
    engine = _engine()  # max_retries=2 → 3 attempts
    with pytest.raises(EngineUpstreamError):
        await engine.push_wellness_daily(_WELLNESS)
    await engine.aclose()
    assert route.call_count == 3


@respx.mock
async def test_push_timeout_retried_then_upstream_error() -> None:
    route = respx.post(f"{_BASE}/api/v1/wellness/daily").mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )
    engine = _engine()
    with pytest.raises(EngineUpstreamError):
        await engine.push_wellness_daily(_WELLNESS)
    await engine.aclose()
    assert route.call_count == 3


@respx.mock
async def test_push_401_maps_to_auth_error_and_fails_fast() -> None:
    route = respx.post(f"{_BASE}/api/v1/wellness/daily").mock(
        return_value=httpx.Response(401, json={"message": "nope"})
    )
    engine = _engine()
    with pytest.raises(EngineAuthError):
        await engine.push_wellness_daily(_WELLNESS)
    await engine.aclose()
    assert route.call_count == 1  # 4xx is not retried
