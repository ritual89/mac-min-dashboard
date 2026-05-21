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


def _config() -> AppConfig:
    return AppConfig(
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


@pytest.fixture
def seeded_store(tmp_path: Path) -> WorkloadStore:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    config = _config()
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
    app = create_app(store=seeded_store, config=_config())
    return TestClient(app)


# AC-14.1
def test_ac_14_1_pin_discovered_workload(client: TestClient, seeded_store: WorkloadStore) -> None:
    seeded_store.conn.execute(
        "UPDATE workloads SET monitored = 0, pinned = 0 WHERE id = ?",
        ("docker:mac-mini:nginx",),
    )
    seeded_store.conn.commit()

    response = client.post("/api/workloads/docker:mac-mini:nginx/pin")
    assert response.status_code == 200

    row = seeded_store.get_workload("docker:mac-mini:nginx")
    assert row is not None
    assert row.pinned is True
    assert row.monitored is True


# AC-14.4
def test_ac_14_4_pin_unknown_returns_404(client: TestClient) -> None:
    response = client.post("/api/workloads/docker:missing:svc/pin")
    assert response.status_code == 404


# AC-14.5
def test_ac_14_5_unpin_unknown_returns_404(client: TestClient) -> None:
    response = client.delete("/api/workloads/docker:missing:svc/pin")
    assert response.status_code == 404


# AC-14.2
def test_ac_14_2_unpin_docker_stays_monitored(client: TestClient, seeded_store: WorkloadStore) -> None:
    seeded_store.pin_workload("docker:mac-mini:nginx")
    response = client.delete("/api/workloads/docker:mac-mini:nginx/pin")
    assert response.status_code == 200

    row = seeded_store.get_workload("docker:mac-mini:nginx")
    assert row is not None
    assert row.pinned is False
    assert row.monitored is True


# AC-14.6
def test_ac_14_6_pin_already_pinned_idempotent(client: TestClient, seeded_store: WorkloadStore) -> None:
    seeded_store.pin_workload("docker:mac-mini:nginx")
    response = client.post("/api/workloads/docker:mac-mini:nginx/pin")
    assert response.status_code == 200
