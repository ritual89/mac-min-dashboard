from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mac_mini_api.app import create_app
from mac_mini_core.store import WorkloadStore


@pytest.fixture
def store(tmp_path: Path) -> WorkloadStore:
    return WorkloadStore.open(str(tmp_path / "fleet.db"))


@pytest.fixture
def client(store: WorkloadStore) -> TestClient:
    app = create_app(store=store)
    return TestClient(app)


# AC-16.1
def test_ac_16_1_get_default_settings(client: TestClient) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["notify_orange"] is True
    assert body["notify_red"] is True


# AC-16.2
def test_ac_16_2_patch_updates_single_key(client: TestClient) -> None:
    response = client.patch("/api/settings", json={"notify_orange": False})
    assert response.status_code == 200

    settings = client.get("/api/settings").json()
    assert settings["notify_orange"] is False
    assert settings["notify_red"] is True


# AC-16.3
def test_ac_16_3_patch_unknown_key_400(client: TestClient) -> None:
    response = client.patch("/api/settings", json={"bogus_key": True})
    assert response.status_code == 400
    assert "unknown" in response.json()["detail"]


# AC-16.4
def test_ac_16_4_patch_empty_body_200(client: TestClient) -> None:
    response = client.patch("/api/settings", json={})
    assert response.status_code == 200
