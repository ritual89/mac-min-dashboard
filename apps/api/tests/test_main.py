from __future__ import annotations

from pathlib import Path

from mac_mini_api.main import (
    _config_path,
    _default_config,
    _default_static_dir,
    _default_store,
    _repo_root,
    create_production_app,
)

_CONFIG_YAML = """\
hosts:
  - id: mac-mini
    display_name: Mac Mini
    tailscale_host: mac-mini
    ssh_user: greg
    ssh_key_path: ~/.ssh/id_ed25519
    os: darwin
promote:
  allowlist: []
  port_denylist: []
"""


def test_create_production_app(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_CONFIG_YAML)
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(tmp_path / "fleet.db"))
    app = create_production_app()
    assert app.title == "Mac Mini Dashboard"
    assert app.state.config is not None
    assert app.state.executor_factory is not None
    store = app.state.store
    assert store is not None
    store.close()


def test_default_config_loads_from_env(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_CONFIG_YAML)
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    config = _default_config()
    assert config.hosts[0].id == "mac-mini"


def test_default_config_missing_file_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    import pytest

    with pytest.raises(FileNotFoundError, match="config not found"):
        _default_config()


def test_config_path_default() -> None:
    assert _config_path().name == "config.yaml"


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
