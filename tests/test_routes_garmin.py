"""Integration tests for the Garmin (faked) ingestion routes + watch-hint."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.synth import generate

BASE = date(2026, 1, 1)


def _daily(day: date, **overrides: Any) -> dict[str, Any]:
    """A normal day's metrics; overrides shape the (de)graded signal."""

    body: dict[str, Any] = {
        "date": day.isoformat(),
        "sleep_score": 80,
        "hrv_rmssd": 60.0,
        "rhr": 48,
        "resp_rate": 14.0,
    }
    body.update(overrides)
    return body


def _baseline_days(n: int) -> list[dict[str, Any]]:
    """``n`` flat, healthy days ending the day before ``BASE + n``."""

    return [_daily(BASE + timedelta(days=i)) for i in range(n)]


# --- daily ingest -----------------------------------------------------------


def test_ingest_daily_upsert_idempotent(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {"daily": _baseline_days(3), "sessions": []}
    first = client.post("/api/garmin/ingest", json=payload, headers=auth_headers)
    assert first.status_code == 200
    assert first.json()["daily_upserted"] == 3
    # Re-ingesting the same batch must not create duplicate rows.
    client.post("/api/garmin/ingest", json=payload, headers=auth_headers)
    rows = client.get("/api/garmin/daily", headers=auth_headers).json()
    assert len(rows) == 3


def test_ingest_daily_default_source(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/garmin/ingest", json={"daily": [_daily(BASE)]}, headers=auth_headers)
    rows = client.get("/api/garmin/daily", headers=auth_headers).json()
    assert rows[0]["source"] == "garmin_faked"


def test_daily_requires_auth(client: TestClient) -> None:
    assert client.get("/api/garmin/daily").status_code == 401
    assert client.post("/api/garmin/ingest", json={"daily": []}).status_code == 401


def test_daily_pagination_and_window(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/garmin/ingest", json={"daily": _baseline_days(5)}, headers=auth_headers)
    page = client.get("/api/garmin/daily?limit=2&offset=0", headers=auth_headers).json()
    assert len(page) == 2
    assert page[0]["date"] == (BASE + timedelta(days=4)).isoformat()  # newest first
    window = client.get(
        f"/api/garmin/daily?from={(BASE + timedelta(days=1)).isoformat()}"
        f"&to={(BASE + timedelta(days=2)).isoformat()}",
        headers=auth_headers,
    ).json()
    assert [r["date"] for r in window] == [
        (BASE + timedelta(days=2)).isoformat(),
        (BASE + timedelta(days=1)).isoformat(),
    ]


def test_daily_user_isolation(
    client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]
) -> None:
    client.post("/api/garmin/ingest", json={"daily": _baseline_days(3)}, headers=auth_headers)
    assert client.get("/api/garmin/daily", headers=other_auth_headers).json() == []


# --- session feedback ingest ------------------------------------------------


def _session(activity_id: str = "act-1", **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"activity_id": activity_id, "rpe": 6, "affect": "neutral"}
    body.update(overrides)
    return body


def test_ingest_session_source_is_watch(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post("/api/garmin/ingest", json={"sessions": [_session()]}, headers=auth_headers)
    assert resp.json()["sessions_upserted"] == 1
    rows = client.get("/api/feedback/session", headers=auth_headers).json()
    assert rows[0]["source"] == "garmin_watch"


def test_ingest_session_upsert_by_activity(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.post("/api/garmin/ingest", json={"sessions": [_session(rpe=4)]}, headers=auth_headers)
    client.post("/api/garmin/ingest", json={"sessions": [_session(rpe=9)]}, headers=auth_headers)
    rows = client.get("/api/feedback/session", headers=auth_headers).json()
    assert len(rows) == 1
    assert rows[0]["rpe"] == 9


# --- watch hint -------------------------------------------------------------


def test_watch_hint_triggers_on_degraded_day(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    sick_day = BASE + timedelta(days=10)
    # 10 flat healthy baseline days, then one clearly degraded day.
    daily = _baseline_days(10) + [_daily(sick_day, hrv_rmssd=40.0, rhr=60, resp_rate=18.0)]
    resp = client.post("/api/garmin/ingest", json={"daily": daily}, headers=auth_headers)
    assert resp.json()["illness_flags_set"] == 1
    hint = client.get(f"/api/illness/hint?date={sick_day.isoformat()}", headers=auth_headers).json()
    assert hint["triggered"] is True
    assert hint["hrv_delta"] < 0 and hint["rhr_delta"] > 0 and hint["resp_delta"] > 0


def test_watch_hint_quiet_on_normal_day(client: TestClient, auth_headers: dict[str, str]) -> None:
    daily = _baseline_days(12)
    resp = client.post("/api/garmin/ingest", json={"daily": daily}, headers=auth_headers)
    assert resp.json()["illness_flags_set"] == 0
    # No flag was created for a quiet day.
    assert client.get("/api/illness", headers=auth_headers).json() == []
    last = (BASE + timedelta(days=11)).isoformat()
    assert (
        client.get(f"/api/illness/hint?date={last}", headers=auth_headers).json()["triggered"]
        is False
    )


def test_watch_hint_no_baseline_means_quiet(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # Only 3 days of history — below the 7-observation minimum, so no trigger
    # even though the last day looks degraded.
    last = _daily(BASE + timedelta(days=2), hrv_rmssd=30.0, rhr=70, resp_rate=20.0)
    daily = _baseline_days(2) + [last]
    resp = client.post("/api/garmin/ingest", json={"daily": daily}, headers=auth_headers)
    assert resp.json()["illness_flags_set"] == 0


def test_watch_hint_preserves_confirmed_flag(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # Athlete confirms an illness first; a later ingest must keep their symptoms.
    sick_day = BASE + timedelta(days=10)
    client.post(
        "/api/illness",
        json={"date": sick_day.isoformat(), "symptoms": ["fever"]},
        headers=auth_headers,
    )
    daily = _baseline_days(10) + [_daily(sick_day, hrv_rmssd=40.0, rhr=60, resp_rate=18.0)]
    client.post("/api/garmin/ingest", json={"daily": daily}, headers=auth_headers)
    rows = client.get("/api/illness", headers=auth_headers).json()
    assert len(rows) == 1
    assert rows[0]["confirmed_by_user"] is True
    assert rows[0]["symptoms"] == ["fever"]
    assert rows[0]["watch_hint_triggered"] is True


def test_watch_hint_matches_synth_illness_episode(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """On a real synth dataset, triggered days intersect the illness episodes."""

    dataset = generate("InjuryProne", seed=7, days=180)
    daily = [
        {
            "date": m.date.isoformat(),
            "hrv_rmssd": m.hrv_rmssd,
            "rhr": m.rhr,
            "resp_rate": m.resp_rate,
            "sleep_score": m.sleep_score,
        }
        for m in dataset.daily_metrics
    ]
    resp = client.post("/api/garmin/ingest", json={"daily": daily}, headers=auth_headers)
    assert resp.json()["illness_flags_set"] > 0

    episode_days = {
        (ep.start + timedelta(days=i)).isoformat()
        for ep in dataset.illness_episodes
        for i in range((ep.end - ep.start).days + 1)
    }
    assert episode_days  # the InjuryProne/seed=7 fixture has at least one episode
    triggered = {
        r["date"]
        for r in client.get("/api/illness?limit=200", headers=auth_headers).json()
        if r["watch_hint_triggered"]
    }
    assert triggered & episode_days
