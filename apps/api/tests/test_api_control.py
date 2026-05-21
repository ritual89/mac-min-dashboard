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


def _make_client(
    seeded_store: WorkloadStore,
    restart_result: SshResult | None = None,
    stop_result: SshResult | None = None,
) -> TestClient:
    default_ok = SshResult(stdout="ok\n", stderr="", exit_code=0)

    responses: dict[tuple[CommandTemplate, tuple[tuple[str, object], ...]], SshResult] = {}
    responses[(CommandTemplate.DOCKER_RESTART, (("name", "nginx"),))] = restart_result or default_ok
    responses[(CommandTemplate.DOCKER_STOP, (("name", "nginx"),))] = stop_result or default_ok

    executor = FakeSshExecutor(responses=responses)

    def factory(host: HostConfig) -> FakeSshExecutor:
        return executor

    app = create_app(store=seeded_store, config=_config(), executor_factory=factory)
    return TestClient(app)


# AC-15.1
def test_ac_15_1_restart_docker(seeded_store: WorkloadStore) -> None:
    client = _make_client(seeded_store)
    response = client.post("/api/workloads/docker:mac-mini:nginx/restart")
    assert response.status_code == 200
    assert response.json()["status"] == "restarted"


# AC-15.2
def test_ac_15_2_stop_docker_with_confirm(seeded_store: WorkloadStore) -> None:
    client = _make_client(seeded_store)
    response = client.post("/api/workloads/docker:mac-mini:nginx/stop?confirm=1")
    assert response.status_code == 200
    assert response.json()["status"] == "stopped"


# AC-15.3
def test_ac_15_3_stop_without_confirm(seeded_store: WorkloadStore) -> None:
    client = _make_client(seeded_store)
    response = client.post("/api/workloads/docker:mac-mini:nginx/stop")
    assert response.status_code == 400
    assert "confirm" in response.json()["detail"]


# AC-15.4
def test_ac_15_4_restart_unknown_404(seeded_store: WorkloadStore) -> None:
    client = _make_client(seeded_store)
    response = client.post("/api/workloads/docker:missing:svc/restart")
    assert response.status_code == 404


# AC-15.5
def test_ac_15_5_stop_unknown_404(seeded_store: WorkloadStore) -> None:
    client = _make_client(seeded_store)
    response = client.post("/api/workloads/docker:missing:svc/stop?confirm=1")
    assert response.status_code == 404


# AC-15.9
def test_ac_15_9_restart_ssh_failure_502(seeded_store: WorkloadStore) -> None:
    client = _make_client(
        seeded_store,
        restart_result=SshResult(stdout="", stderr="timeout", exit_code=1),
    )
    response = client.post("/api/workloads/docker:mac-mini:nginx/restart")
    assert response.status_code == 502
    assert "restart failed" in response.json()["detail"]


def test_stop_ssh_failure_502(seeded_store: WorkloadStore) -> None:
    client = _make_client(
        seeded_store,
        stop_result=SshResult(stdout="", stderr="timeout", exit_code=1),
    )
    response = client.post("/api/workloads/docker:mac-mini:nginx/stop?confirm=1")
    assert response.status_code == 502
    assert "stop failed" in response.json()["detail"]


def test_restart_no_executor_raises(seeded_store: WorkloadStore) -> None:
    app = create_app(store=seeded_store, config=_config(), executor_factory=None)
    client = TestClient(app)
    with pytest.raises(RuntimeError, match="executor_factory not configured"):
        client.post("/api/workloads/docker:mac-mini:nginx/restart")


def test_stop_no_executor_raises(seeded_store: WorkloadStore) -> None:
    app = create_app(store=seeded_store, config=_config(), executor_factory=None)
    client = TestClient(app)
    with pytest.raises(RuntimeError, match="executor_factory not configured"):
        client.post("/api/workloads/docker:mac-mini:nginx/stop?confirm=1")


def test_restart_unsupported_kind_400(seeded_store: WorkloadStore) -> None:
    seeded_store.conn.execute(
        "UPDATE workloads SET kind = 'cron' WHERE id = ?",
        ("docker:mac-mini:nginx",),
    )
    seeded_store.conn.commit()
    client = _make_client(seeded_store)
    response = client.post("/api/workloads/docker:mac-mini:nginx/restart")
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]


def test_stop_unsupported_kind_400(seeded_store: WorkloadStore) -> None:
    seeded_store.conn.execute(
        "UPDATE workloads SET kind = 'launchd' WHERE id = ?",
        ("docker:mac-mini:nginx",),
    )
    seeded_store.conn.commit()
    client = _make_client(seeded_store)
    response = client.post("/api/workloads/docker:mac-mini:nginx/stop?confirm=1")
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]
