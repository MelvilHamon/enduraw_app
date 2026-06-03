"""Tests for the authentication flow."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.security import decode_token

VALID = {"email": "athlete@example.com", "password": "supersecret"}


def _register(client: TestClient, **overrides: str) -> object:
    payload = {**VALID, **overrides}
    return client.post("/api/auth/register", json=payload)


def test_register_happy_path(client: TestClient) -> None:
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == VALID["email"]
    assert "id" in body and "created_at" in body
    assert "hashed_password" not in body


def test_register_duplicate_email(client: TestClient) -> None:
    assert _register(client).status_code == 201
    resp = _register(client)
    assert resp.status_code == 409


def test_register_short_password(client: TestClient) -> None:
    resp = _register(client, password="short")
    assert resp.status_code == 422


def test_login_ok_returns_decodable_token(client: TestClient) -> None:
    _register(client)
    resp = client.post("/api/auth/login", json=VALID)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    subject = decode_token(body["access_token"])
    assert subject is not None


def test_login_wrong_password(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        "/api/auth/login",
        json={"email": VALID["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_me_with_token(client: TestClient) -> None:
    _register(client)
    token = client.post("/api/auth/login", json=VALID).json()["access_token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == VALID["email"]


def test_me_without_token(client: TestClient) -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_bogus_token(client: TestClient) -> None:
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
