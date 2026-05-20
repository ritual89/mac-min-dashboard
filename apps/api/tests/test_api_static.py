from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mac_mini_api.app import create_app
from mac_mini_core.store import WorkloadStore


def test_spa_serves_index(tmp_path: Path) -> None:
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("<html><body>ui</body></html>")
    assets = static / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('ok')")

    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    app = create_app(store=store, static_dir=static)
    client = TestClient(app)

    assert client.get("/").text == "<html><body>ui</body></html>"
    assert client.get("/assets/app.js").status_code == 200


def test_spa_api_path_not_shadowed(tmp_path: Path) -> None:
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("ui")

    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    client = TestClient(create_app(store=store, static_dir=static))
    assert client.get("/api/hosts").status_code == 200
