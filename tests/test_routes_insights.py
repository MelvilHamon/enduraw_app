"""Insights routes: auth, user isolation, response shapes (ENGINE_MODE=mock)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.main import app
from app.security import create_access_token
from app.synth import generate
from app.synth.seeder import seed_user

_TODAY = datetime.now(UTC).date()


@pytest.fixture
def synth(
    client: TestClient, db_session: Session, tmp_path: Path
) -> Iterator[tuple[dict[str, str], object]]:
    """Seed a synth athlete + snapshot and point the engine at the temp dir."""

    dataset = generate("InjuryProne", seed=7, days=180, end_date=_TODAY)
    user = seed_user(db_session, dataset, engine_dir=tmp_path)
    app.dependency_overrides[get_settings] = lambda: Settings(MOCK_ENGINE_DIR=str(tmp_path))
    token, _ = create_access_token(subject=user.id)
    yield {"Authorization": f"Bearer {token}"}, user
    app.dependency_overrides.pop(get_settings, None)


def test_today_requires_auth(client: TestClient) -> None:
    assert client.get("/api/insights/today").status_code == 401


def test_timeseries_requires_auth(client: TestClient) -> None:
    assert client.get(f"/api/insights/timeseries?from={_TODAY}&to={_TODAY}").status_code == 401


def test_today_shape(client: TestClient, synth: tuple[dict[str, str], object]) -> None:
    headers, _ = synth
    body = client.get("/api/insights/today", headers=headers).json()

    assert body["date"] == _TODAY.isoformat()
    assert {s["key"] for s in body["signals"]} == {
        "divergence_subj_obj",
        "illness_hint",
        "niggle_escalation",
        "niggle_load_correlation",
        "wellness_divergence",
        "mini_test_trend",
    }
    assert 0.0 <= body["composite_score"] <= 1.0
    assert body["readiness"]["reco"] in {
        "train_as_planned",
        "lighten",
        "rest",
        "consult_physio",
    }
    assert len(body["readiness"]["top_2"]) <= 2
    assert body["engine_state"] is not None  # snapshot covers today


def test_timeseries_metrics_filter(
    client: TestClient, synth: tuple[dict[str, str], object]
) -> None:
    headers, _ = synth
    frm = _TODAY - timedelta(days=30)
    resp = client.get(
        f"/api/insights/timeseries?from={frm}&to={_TODAY}&metrics=form", headers=headers
    )
    body = resp.json()
    assert resp.status_code == 200
    assert set(body["series"]) == {"form"}  # only the requested engine metric
    assert "form_vs_normal" in body and "divergence" in body


def test_correlations_shape(client: TestClient, synth: tuple[dict[str, str], object]) -> None:
    headers, _ = synth
    frm = _TODAY - timedelta(days=180)
    body = client.get(f"/api/insights/correlations?from={frm}&to={_TODAY}", headers=headers).json()
    assert body["total"] == len(body["niggles"])
    assert body["load_linked_count"] <= body["total"]


def test_mini_test_baseline(client: TestClient, synth: tuple[dict[str, str], object]) -> None:
    headers, _ = synth
    body = client.get("/api/mini-tests/baseline?type=jump", headers=headers).json()
    assert body["type"] == "jump" and body["metric"] == "height_cm"
    assert body["n"] >= 0


def test_user_isolation(
    client: TestClient, db_session: Session, synth: tuple[dict[str, str], object]
) -> None:
    # A second athlete with no data / no snapshot sees only their own (empty) read.
    other = seed_user(db_session, generate("Regular", seed=99, days=10, end_date=_TODAY))
    token, _ = create_access_token(subject=other.id)
    headers = {"Authorization": f"Bearer {token}"}

    # This user has no engine snapshot in the temp dir, so their engine state is
    # absent — proving they aren't served the InjuryProne athlete's snapshot.
    today = client.get("/api/insights/today", headers=headers)
    assert today.status_code == 200
    assert today.json()["engine_state"] is None
