from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mac_mini_api.app import create_app
from mac_mini_core.config import AppConfig, HostConfig
from mac_mini_core.models import HostOS
from mac_mini_core.store import WorkloadStore


def test_logs_requires_executor_factory(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    store.ensure_host(
        HostConfig(
            id="mac-mini",
            display_name="Mac Mini",
            tailscale_host="mac-mini",
            ssh_user="greg",
            ssh_key_path="~/.ssh/id",
            os=HostOS.LINUX,
        )
    )
    store.conn.execute(
        """
        INSERT INTO workloads (id, host_id, kind, name, monitored, pinned, metadata_json)
        VALUES ('docker:mac-mini:nginx', 'mac-mini', 'docker', 'nginx', 1, 0, '{}')
        """
    )
    store.conn.execute(
        """
        INSERT INTO workload_state (workload_id, last_seen, status, severity, restart_count_1h)
        VALUES ('docker:mac-mini:nginx', '2020-01-01T00:00:00+00:00', 'running', 'green', 0)
        """
    )
    store.conn.commit()
    client = TestClient(create_app(store=store, config=AppConfig(hosts=[])))
    with pytest.raises(RuntimeError, match="executor_factory"):
        client.get("/api/workloads/docker:mac-mini:nginx/logs")


def test_logs_host_not_in_config(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    store.ensure_host(
        HostConfig(
            id="mac-mini",
            display_name="Mac Mini",
            tailscale_host="mac-mini",
            ssh_user="greg",
            ssh_key_path="~/.ssh/id",
            os=HostOS.LINUX,
        )
    )
    store.conn.execute(
        """
        INSERT INTO workloads (id, host_id, kind, name, monitored, pinned, metadata_json)
        VALUES ('docker:mac-mini:nginx', 'mac-mini', 'docker', 'nginx', 1, 0, '{}')
        """
    )
    store.conn.execute(
        """
        INSERT INTO workload_state (workload_id, last_seen, status, severity, restart_count_1h)
        VALUES ('docker:mac-mini:nginx', '2020-01-01T00:00:00+00:00', 'running', 'green', 0)
        """
    )
    store.conn.commit()
    client = TestClient(
        create_app(
            store=store,
            config=AppConfig(hosts=[]),
            executor_factory=lambda _h: None,  # type: ignore[arg-type, return-value]
        )
    )
    response = client.get("/api/workloads/docker:mac-mini:nginx/logs")
    assert response.status_code == 404


def test_logs_host_row_missing(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    store.conn.execute(
        """
        INSERT INTO workloads (id, host_id, kind, name, monitored, pinned, metadata_json)
        VALUES ('docker:ghost:nginx', 'ghost', 'docker', 'nginx', 1, 0, '{}')
        """
    )
    store.conn.execute(
        """
        INSERT INTO workload_state (workload_id, last_seen, status, severity, restart_count_1h)
        VALUES ('docker:ghost:nginx', '2020-01-01T00:00:00+00:00', 'running', 'green', 0)
        """
    )
    store.conn.commit()
    config = AppConfig(
        hosts=[
            HostConfig(
                id="ghost",
                display_name="Ghost",
                tailscale_host="ghost",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id",
                os=HostOS.LINUX,
            )
        ]
    )
    client = TestClient(
        create_app(store=store, config=config, executor_factory=lambda _h: None)  # type: ignore[arg-type, return-value]
    )
    response = client.get("/api/workloads/docker:ghost:nginx/logs")
    assert response.status_code == 404
    assert response.json()["detail"] == "host not found"


def test_static_without_assets_dir(tmp_path: Path) -> None:
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("ok")
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    client = TestClient(create_app(store=store, static_dir=static))
    assert client.get("/").text == "ok"


def test_logs_config_not_configured(tmp_path: Path) -> None:
    from mac_mini_core.ssh.executor import FakeSshExecutor

    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    store.ensure_host(
        HostConfig(
            id="mac-mini",
            display_name="Mac Mini",
            tailscale_host="mac-mini",
            ssh_user="greg",
            ssh_key_path="~/.ssh/id",
            os=HostOS.LINUX,
        )
    )
    store.conn.execute(
        """
        INSERT INTO workloads (id, host_id, kind, name, monitored, pinned, metadata_json)
        VALUES ('docker:mac-mini:nginx', 'mac-mini', 'docker', 'nginx', 1, 0, '{}')
        """
    )
    store.conn.execute(
        """
        INSERT INTO workload_state (workload_id, last_seen, status, severity, restart_count_1h)
        VALUES ('docker:mac-mini:nginx', '2020-01-01T00:00:00+00:00', 'running', 'green', 0)
        """
    )
    store.conn.commit()
    client = TestClient(
        create_app(store=store, config=None, executor_factory=lambda _h: FakeSshExecutor())
    )
    with pytest.raises(RuntimeError, match="config not configured"):
        client.get("/api/workloads/docker:mac-mini:nginx/logs")


def test_spa_rejects_unknown_api_path(tmp_path: Path) -> None:
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("ui")
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    client = TestClient(create_app(store=store, static_dir=static))
    response = client.get("/api/unknown-route")
    assert response.status_code == 404


def test_static_index_missing_returns_404(tmp_path: Path) -> None:
    static = tmp_path / "dist"
    static.mkdir()
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    client = TestClient(create_app(store=store, static_dir=static))
    assert client.get("/").status_code == 404
