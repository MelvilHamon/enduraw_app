"""Integration tests for the niggle and niggle-report routes."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _niggle(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"region": "knee_anterior", "side": "left"}
    body.update(overrides)
    return body


def _report(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"intensity": 4, "is_new_or_recurrent": "new"}
    body.update(overrides)
    return body


def _create(client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    resp = client.post("/api/niggles", json=_niggle(**overrides), headers=headers)
    assert resp.status_code == 201
    return resp.json()


def test_post_niggle_without_report(client: TestClient, auth_headers: dict[str, str]) -> None:
    body = _create(client, auth_headers)
    assert body["region"] == "knee_anterior"
    assert body["closed_at"] is None
    assert body["reports"] == []


def test_post_niggle_with_initial_report(client: TestClient, auth_headers: dict[str, str]) -> None:
    body = _create(client, auth_headers, initial_report=_report(intensity=6))
    assert len(body["reports"]) == 1
    assert body["reports"][0]["intensity"] == 6
    assert body["reports"][0]["niggle_id"] == body["id"]


def test_post_niggle_requires_auth(client: TestClient) -> None:
    assert client.post("/api/niggles", json=_niggle()).status_code == 401


def test_post_niggle_validation(client: TestClient, auth_headers: dict[str, str]) -> None:
    # Bad region enum.
    resp = client.post("/api/niggles", json=_niggle(region="elbow"), headers=auth_headers)
    assert resp.status_code == 422
    # Bad report intensity (out of range) in the initial report.
    resp = client.post(
        "/api/niggles",
        json=_niggle(initial_report=_report(intensity=99)),
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_get_niggle_detail_embeds_reports(client: TestClient, auth_headers: dict[str, str]) -> None:
    niggle = _create(client, auth_headers)
    client.post(f"/api/niggles/{niggle['id']}/reports", json=_report(), headers=auth_headers)
    resp = client.get(f"/api/niggles/{niggle['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["reports"]) == 1


def test_get_niggle_unknown_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/api/niggles/does-not-exist", headers=auth_headers).status_code == 404


def test_list_active_filter(client: TestClient, auth_headers: dict[str, str]) -> None:
    open_niggle = _create(client, auth_headers)
    closed_niggle = _create(client, auth_headers, side="right")
    client.patch(
        f"/api/niggles/{closed_niggle['id']}",
        json={"closed_at": "2026-06-20"},
        headers=auth_headers,
    )
    all_ids = {n["id"] for n in client.get("/api/niggles", headers=auth_headers).json()}
    assert all_ids == {open_niggle["id"], closed_niggle["id"]}
    active = client.get("/api/niggles?active=true", headers=auth_headers).json()
    assert [n["id"] for n in active] == [open_niggle["id"]]
    # List view stays light: no embedded reports.
    assert "reports" not in active[0]


def test_niggle_user_isolation(
    client: TestClient, auth_headers: dict[str, str], other_auth_headers: dict[str, str]
) -> None:
    niggle = _create(client, auth_headers)
    # Intruder cannot read it -> 404 (never 403, never leak existence).
    assert client.get(f"/api/niggles/{niggle['id']}", headers=other_auth_headers).status_code == 404
    assert client.get("/api/niggles", headers=other_auth_headers).json() == []
    # Intruder cannot patch or report on it either.
    assert (
        client.patch(
            f"/api/niggles/{niggle['id']}",
            json={"notes": "x"},
            headers=other_auth_headers,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/niggles/{niggle['id']}/reports", json=_report(), headers=other_auth_headers
        ).status_code
        == 404
    )


def test_patch_niggle_happy(client: TestClient, auth_headers: dict[str, str]) -> None:
    niggle = _create(client, auth_headers)
    resp = client.patch(
        f"/api/niggles/{niggle['id']}",
        json={"closed_at": "2026-06-20", "structure": "tendon"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["closed_at"] == "2026-06-20"
    assert resp.json()["structure"] == "tendon"


def test_patch_niggle_region_immutable(client: TestClient, auth_headers: dict[str, str]) -> None:
    niggle = _create(client, auth_headers)
    resp = client.patch(
        f"/api/niggles/{niggle['id']}", json={"region": "calf"}, headers=auth_headers
    )
    assert resp.status_code == 422


def test_post_report_happy(client: TestClient, auth_headers: dict[str, str]) -> None:
    niggle = _create(client, auth_headers)
    resp = client.post(
        f"/api/niggles/{niggle['id']}/reports", json=_report(intensity=7), headers=auth_headers
    )
    assert resp.status_code == 201
    assert resp.json()["intensity"] == 7


def test_post_report_on_closed_niggle_409(client: TestClient, auth_headers: dict[str, str]) -> None:
    niggle = _create(client, auth_headers)
    client.patch(
        f"/api/niggles/{niggle['id']}", json={"closed_at": "2026-06-20"}, headers=auth_headers
    )
    resp = client.post(f"/api/niggles/{niggle['id']}/reports", json=_report(), headers=auth_headers)
    assert resp.status_code == 409


def test_niggle_list_pagination(client: TestClient, auth_headers: dict[str, str]) -> None:
    for _ in range(5):
        _create(client, auth_headers)
    page = client.get("/api/niggles?limit=2&offset=0", headers=auth_headers).json()
    assert len(page) == 2
    page2 = client.get("/api/niggles?limit=2&offset=2", headers=auth_headers).json()
    assert len(page2) == 2
    assert {n["id"] for n in page}.isdisjoint({n["id"] for n in page2})
