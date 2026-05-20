from __future__ import annotations

from pathlib import Path

from mac_mini_api.main import (
    _default_static_dir,
    _default_store,
    _repo_root,
    create_production_app,
)


def test_create_production_app(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(tmp_path / "fleet.db"))
    app = create_production_app()
    assert app.title == "Mac Mini Dashboard"
    store = app.state.store
    assert store is not None
    store.close()


def test_default_store_opens_database(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(tmp_path / "fleet.db"))
    store = _default_store()
    try:
        assert store.count_workloads() == 0
    finally:
        store.close()


def test_default_static_dir_from_env(tmp_path, monkeypatch) -> None:
    ui = tmp_path / "ui"
    ui.mkdir()
    monkeypatch.setenv("DASHBOARD_STATIC_DIR", str(ui))
    assert _default_static_dir() == ui


def test_default_static_dir_missing_env_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_STATIC_DIR", str(tmp_path / "nope"))
    assert _default_static_dir() is None


def test_repo_root_points_at_workspace() -> None:
    root = _repo_root()
    assert (root / "packages" / "core").is_dir()
