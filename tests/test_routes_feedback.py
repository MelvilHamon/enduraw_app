"""Integration tests for the session feedback routes."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _feedback(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"activity_id": "act_1", "rpe": 7, "affect": "neutral"}
    body.update(overrides)
    return body


def test_post_feedback_happy(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post("/api/feedback/session", json=_feedback(), headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["activity_id"] == "act_1"
    assert body["source"] == "app_manual"  # forced server-side


def test_post_feedback_ignores_client_source(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/feedback/session",
        json=_feedback(source="garmin_watch"),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["source"] == "app_manual"


def test_post_feedback_requires_auth(client: TestClient) -> None:
    assert client.post("/api/feedback/session", json=_feedback()).status_code == 401


def test_post_feedback_validation(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert (
        client.post(
            "/api/feedback/session", json=_feedback(rpe=11), headers=auth_headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/feedback/session", json=_feedback(affect="meh"), headers=auth_headers
        ).status_code
        == 422
    )


def test_get_feedback_returns_created(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/feedback/session", json=_feedback(), headers=auth_headers)
    rows = client.get("/api/feedback/session", headers=auth_headers).json()
    assert len(rows) == 1
    assert rows[0]["rpe"] == 7


def test_feedback_upsert_same_activity(client: TestClient, auth_headers: dict[str, str]) -> None:
    first = client.post("/api/feedback/session", json=_feedback(rpe=7), headers=auth_headers)
    assert first.status_code == 201
    second = client.post("/api/feedback/session", json=_feedback(rpe=3), headers=auth_headers)
    assert second.status_code == 200  # update, not create
    assert second.json()["rpe"] == 3
    assert second.json()["id"] == first.json()["id"]
    rows = client.get("/api/feedback/session", headers=auth_headers).json()
    assert len(rows) == 1


def test_feedback_activity_filter(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/feedback/session", json=_feedback(activity_id="act_1"), headers=auth_headers)
    client.post("/api/feedback/session", json=_feedback(activity_id="act_2"), headers=auth_headers)
    rows = client.get("/api/feedback/session?activity_id=act_2", headers=auth_headers).json()
    assert [r["activity_id"] for r in rows] == ["act_2"]


def test_feedback_user_isolation(
    client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]
) -> None:
    client.post("/api/feedback/session", json=_feedback(), headers=auth_headers)
    assert client.get("/api/feedback/session", headers=other_auth_headers).json() == []


def test_feedback_pagination(client: TestClient, auth_headers: dict[str, str]) -> None:
    for i in range(5):
        client.post(
            "/api/feedback/session", json=_feedback(activity_id=f"act_{i}"), headers=auth_headers
        )
    page = client.get("/api/feedback/session?limit=2&offset=0", headers=auth_headers).json()
    assert len(page) == 2
    page2 = client.get("/api/feedback/session?limit=2&offset=2", headers=auth_headers).json()
    assert len(page2) == 2
    assert {r["id"] for r in page}.isdisjoint({r["id"] for r in page2})
