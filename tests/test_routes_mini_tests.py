"""Integration tests for the mini-test routes (discriminated union)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

JUMP = {"type": "jump", "flight_time_ms": 480, "height_cm": 28.3}
REACTION = {"type": "reaction", "mean_rt_ms": 250.0, "sd_rt_ms": 30.0, "n_taps": 20}


def _payload(data: dict[str, Any], date: str = "2026-06-04") -> dict[str, Any]:
    return {"date": date, "reported_at": f"{date}T07:30:00Z", "data": data}


def test_post_jump_happy(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post("/api/mini-tests", json=_payload(JUMP), headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "jump"
    assert body["data"] == {"flight_time_ms": 480, "height_cm": 28.3}


def test_post_reaction_happy(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post("/api/mini-tests", json=_payload(REACTION), headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["type"] == "reaction"
    assert resp.json()["data"]["n_taps"] == 20


def test_post_mini_test_requires_auth(client: TestClient) -> None:
    assert client.post("/api/mini-tests", json=_payload(JUMP)).status_code == 401


def test_discriminator_catches_mismatched_payload(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # type=jump but a reaction payload -> jump fields missing -> 422.
    bad = {"type": "jump", "mean_rt_ms": 250.0, "sd_rt_ms": 30.0, "n_taps": 20}
    resp = client.post("/api/mini-tests", json=_payload(bad), headers=auth_headers)
    assert resp.status_code == 422


def test_unknown_type_is_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    bad = {"type": "sprint", "value": 1}
    resp = client.post("/api/mini-tests", json=_payload(bad), headers=auth_headers)
    assert resp.status_code == 422


def test_negative_value_is_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    bad = {"type": "jump", "flight_time_ms": -1, "height_cm": 10.0}
    resp = client.post("/api/mini-tests", json=_payload(bad), headers=auth_headers)
    assert resp.status_code == 422


def test_get_returns_created(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/mini-tests", json=_payload(JUMP), headers=auth_headers)
    rows = client.get("/api/mini-tests", headers=auth_headers).json()
    assert len(rows) == 1
    assert rows[0]["type"] == "jump"


def test_type_filter(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/mini-tests", json=_payload(JUMP), headers=auth_headers)
    client.post("/api/mini-tests", json=_payload(REACTION), headers=auth_headers)
    jumps = client.get("/api/mini-tests?type=jump", headers=auth_headers).json()
    assert [r["type"] for r in jumps] == ["jump"]


def test_mini_test_user_isolation(
    client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]
) -> None:
    client.post("/api/mini-tests", json=_payload(JUMP), headers=auth_headers)
    assert client.get("/api/mini-tests", headers=other_auth_headers).json() == []


def test_mini_test_pagination(client: TestClient, auth_headers: dict[str, str]) -> None:
    for day in range(1, 6):
        client.post(
            "/api/mini-tests", json=_payload(JUMP, date=f"2026-05-0{day}"), headers=auth_headers
        )
    page = client.get("/api/mini-tests?limit=2&offset=0", headers=auth_headers).json()
    assert len(page) == 2
    assert page[0]["date"] == "2026-05-05"  # newest first
    page2 = client.get("/api/mini-tests?limit=2&offset=2", headers=auth_headers).json()
    assert page2[0]["date"] == "2026-05-03"
