"""Integration tests for the illness flag routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

TODAY = datetime.now(UTC).date().isoformat()


def _illness(date: str = TODAY, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"date": date, "symptoms": ["sore_throat"]}
    body.update(overrides)
    return body


def test_post_illness_happy(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post("/api/illness", json=_illness(), headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["symptoms"] == ["sore_throat"]
    assert body["confirmed_by_user"] is True
    assert body["watch_hint_triggered"] is False


def test_post_illness_requires_auth(client: TestClient) -> None:
    assert client.post("/api/illness", json=_illness()).status_code == 401


def test_post_illness_invalid_symptom(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/illness", json=_illness(symptoms=["not_a_symptom"]), headers=auth_headers
    )
    assert resp.status_code == 422


def test_post_illness_empty_symptoms(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post("/api/illness", json=_illness(symptoms=[]), headers=auth_headers)
    assert resp.status_code == 422


def test_get_illness_returns_created(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/illness", json=_illness(), headers=auth_headers)
    rows = client.get("/api/illness", headers=auth_headers).json()
    assert len(rows) == 1
    assert rows[0]["date"] == TODAY


def test_illness_upsert_same_date(client: TestClient, auth_headers: dict[str, str]) -> None:
    first = client.post(
        "/api/illness", json=_illness(symptoms=["sore_throat"]), headers=auth_headers
    )
    assert first.status_code == 201
    second = client.post(
        "/api/illness",
        json=_illness(symptoms=["fever", "cough"]),
        headers=auth_headers,
    )
    assert second.status_code == 200  # update, not create
    assert second.json()["symptoms"] == ["fever", "cough"]
    assert second.json()["id"] == first.json()["id"]
    rows = client.get("/api/illness", headers=auth_headers).json()
    assert len(rows) == 1


def test_illness_user_isolation(
    client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]
) -> None:
    client.post("/api/illness", json=_illness(), headers=auth_headers)
    assert client.get("/api/illness", headers=other_auth_headers).json() == []


def test_illness_pagination_and_window(client: TestClient, auth_headers: dict[str, str]) -> None:
    for day in range(1, 6):
        client.post("/api/illness", json=_illness(date=f"2026-05-0{day}"), headers=auth_headers)
    page = client.get("/api/illness?limit=2&offset=0", headers=auth_headers).json()
    assert len(page) == 2
    assert page[0]["date"] == "2026-05-05"  # newest first
    window = client.get("/api/illness?from=2026-05-02&to=2026-05-03", headers=auth_headers)
    assert [r["date"] for r in window.json()] == ["2026-05-03", "2026-05-02"]
