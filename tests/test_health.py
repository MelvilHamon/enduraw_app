"""Tests for the health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import __version__


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": __version__}
