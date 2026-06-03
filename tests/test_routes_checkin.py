"""Integration tests for the daily checkin routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

TODAY = datetime.now(UTC).date().isoformat()


def _checkin(date: str = TODAY, **overrides: int) -> dict[str, object]:
    body: dict[str, object] = {
        "date": date,
        "form_vs_normal": 1,
        "motivation": 4,
        "fatigue": 2,
    }
    body.update(overrides)
    return body


def test_post_checkin_happy_path(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.post("/api/checkin", json=_checkin(), headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["date"] == TODAY
    assert body["form_vs_normal"] == 1
    assert "id" in body and "reported_at" in body


def test_post_checkin_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/checkin", json=_checkin())
    assert resp.status_code == 401


def test_post_checkin_validation_out_of_range(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post("/api/checkin", json=_checkin(form_vs_normal=3), headers=auth_headers)
    assert resp.status_code == 422
    resp = client.post("/api/checkin", json=_checkin(motivation=0), headers=auth_headers)
    assert resp.status_code == 422


def test_get_today_returns_created(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post("/api/checkin", json=_checkin(), headers=auth_headers)
    resp = client.get("/api/checkin/today", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["date"] == TODAY


def test_get_today_404_when_absent(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = client.get("/api/checkin/today", headers=auth_headers)
    assert resp.status_code == 404


def test_post_checkin_upsert_same_date(client: TestClient, auth_headers: dict[str, str]) -> None:
    first = client.post("/api/checkin", json=_checkin(motivation=4), headers=auth_headers)
    assert first.status_code == 201
    second = client.post("/api/checkin", json=_checkin(motivation=2), headers=auth_headers)
    assert second.status_code == 200  # update, not create
    assert second.json()["motivation"] == 2
    assert second.json()["id"] == first.json()["id"]
    # Still exactly one row for that day.
    listing = client.get("/api/checkin", headers=auth_headers).json()
    assert len(listing) == 1


def test_checkin_user_isolation(
    client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]
) -> None:
    client.post("/api/checkin", json=_checkin(), headers=auth_headers)
    # The intruder has no checkin today -> 404, no leak of the other user's data.
    resp = client.get("/api/checkin/today", headers=other_auth_headers)
    assert resp.status_code == 404
    assert client.get("/api/checkin", headers=other_auth_headers).json() == []


def test_checkin_list_pagination(client: TestClient, auth_headers: dict[str, str]) -> None:
    for day in range(1, 6):
        client.post("/api/checkin", json=_checkin(date=f"2026-05-0{day}"), headers=auth_headers)
    page = client.get("/api/checkin?limit=2&offset=0", headers=auth_headers).json()
    assert len(page) == 2
    # Newest first.
    assert page[0]["date"] == "2026-05-05"
    page2 = client.get("/api/checkin?limit=2&offset=2", headers=auth_headers).json()
    assert page2[0]["date"] == "2026-05-03"


def test_checkin_list_date_window(client: TestClient, auth_headers: dict[str, str]) -> None:
    for day in range(1, 6):
        client.post("/api/checkin", json=_checkin(date=f"2026-05-0{day}"), headers=auth_headers)
    resp = client.get("/api/checkin?from=2026-05-02&to=2026-05-04", headers=auth_headers)
    dates = [row["date"] for row in resp.json()]
    assert dates == ["2026-05-04", "2026-05-03", "2026-05-02"]
