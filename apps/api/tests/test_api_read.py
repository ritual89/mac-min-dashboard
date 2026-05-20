from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mac_mini_api.app import create_app
from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import WorkloadStore
from mac_mini_core.worker.audit import AuditPass

FIXTURES = Path(__file__).resolve().parents[3] / "packages" / "core" / "tests" / "fixtures" / "docker"


@pytest.fixture
def seeded_store(tmp_path: Path) -> WorkloadStore:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    config = AppConfig(
        hosts=[
            HostConfig(
                id="mac-mini",
                display_name="Mac Mini",
                tailscale_host="mac-mini",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id_ed25519",
                os=HostOS.DARWIN,
            )
        ],
        promote=PromoteRulesConfig(allowlist=[], port_denylist=[]),
    )
    stdout = (FIXTURES / "ps_standalone.jsonl").read_text()
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=stdout, stderr="", exit_code=0),
        }
    )

    def factory(host: HostConfig) -> FakeSshExecutor:
        return executor

    AuditPass().run(config, store, factory)
    store.ensure_host(config.hosts[0])
    return store


@pytest.fixture
def client(seeded_store: WorkloadStore) -> TestClient:
    app = create_app(store=seeded_store)
    return TestClient(app)


# AC-7.1
def test_ac_7_1_list_hosts(client: TestClient) -> None:
    response = client.get("/api/hosts")
    assert response.status_code == 200
    hosts = response.json()
    assert len(hosts) >= 1
    mac = next(h for h in hosts if h["id"] == "mac-mini")
    assert mac["display_name"] == "Mac Mini"
    assert mac["last_seen"] is not None


# AC-7.2
def test_ac_7_2_filter_monitored(client: TestClient) -> None:
    monitored = client.get("/api/workloads", params={"monitored": True}).json()
    assert len(monitored) == 1
    assert monitored[0]["id"] == "docker:mac-mini:nginx"

    unmonitored = client.get("/api/workloads", params={"monitored": False}).json()
    assert unmonitored == []


# AC-7.3
def test_ac_7_3_filter_host_id(client: TestClient) -> None:
    rows = client.get("/api/workloads", params={"host_id": "mac-mini"}).json()
    assert len(rows) == 1
    assert all(r["host_id"] == "mac-mini" for r in rows)

    empty = client.get("/api/workloads", params={"host_id": "missing-host"}).json()
    assert empty == []


# AC-7.4
def test_ac_7_4_filter_severity(client: TestClient, seeded_store: WorkloadStore) -> None:
    seeded_store.apply_poll_update(
        "docker:mac-mini:nginx",
        None,
        restart_loop_threshold=5,
    )
    orange = client.get("/api/workloads", params={"severity": "orange"}).json()
    assert len(orange) == 1
    assert orange[0]["severity"] == "orange"


# AC-7.5
def test_ac_7_5_workload_not_found(client: TestClient) -> None:
    response = client.get("/api/workloads/docker:missing:svc")
    assert response.status_code == 404


# AC-7.6
def test_ac_7_6_audit_lists_unmonitored(client: TestClient, seeded_store: WorkloadStore) -> None:
    seeded_store.conn.execute(
        "UPDATE workloads SET monitored = 0 WHERE id = ?",
        ("docker:mac-mini:nginx",),
    )
    seeded_store.conn.commit()
    audit = client.get("/api/audit").json()
    assert len(audit) == 1
    assert audit[0]["monitored"] is False


def test_create_app_without_store_raises() -> None:
    app = create_app(store=None)
    client = TestClient(app)
    with pytest.raises(RuntimeError, match="store not configured"):
        client.get("/api/hosts")


def test_get_workload_detail(client: TestClient) -> None:
    response = client.get("/api/workloads/docker:mac-mini:nginx")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "nginx"
    assert body["kind"] == "docker"
    assert "image" in body["metadata"]
