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


def _app_client(tmp_path: Path) -> TestClient:
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
    ps_out = (FIXTURES / "ps_standalone.jsonl").read_text()
    ps_exec = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=ps_out, stderr="", exit_code=0),
        }
    )
    logs_exec = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_LOGS, (("n", 200), ("name", "nginx"))): SshResult(
                stdout="hello from container\n",
                stderr="",
                exit_code=0,
            ),
        }
    )

    def factory(host: HostConfig) -> FakeSshExecutor:
        return logs_exec if host.id == "mac-mini" else ps_exec

    AuditPass().run(config, store, lambda h: ps_exec)
    app = create_app(store=store, config=config, executor_factory=factory)
    return TestClient(app)


# AC-8.2
def test_ac_8_2_logs_endpoint_returns_plain_text(tmp_path: Path) -> None:
    client = _app_client(tmp_path)
    response = client.get("/api/workloads/docker:mac-mini:nginx/logs")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "hello from container\n"


# AC-8.3
def test_ac_8_3_logs_not_found(tmp_path: Path) -> None:
    client = _app_client(tmp_path)
    response = client.get("/api/workloads/docker:missing:svc/logs")
    assert response.status_code == 404


# AC-8.4
def test_ac_8_4_logs_unsupported_kind(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    config = AppConfig(
        hosts=[
            HostConfig(
                id="mac-mini",
                display_name="Mac Mini",
                tailscale_host="mac-mini",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id",
                os=HostOS.LINUX,
            )
        ]
    )
    store.ensure_host(config.hosts[0])
    store.conn.execute(
        """
        INSERT INTO workloads (id, host_id, kind, name, monitored, pinned, metadata_json)
        VALUES ('cron:mac-mini:abc123', 'mac-mini', 'cron', '*/5 * * * * backup.sh', 1, 0, '{}')
        """
    )
    store.conn.execute(
        """
        INSERT INTO workload_state (workload_id, last_seen, status, severity, restart_count_1h)
        VALUES ('cron:mac-mini:abc123', '2020-01-01T00:00:00+00:00', 'scheduled', 'green', 0)
        """
    )
    store.conn.commit()
    app = create_app(
        store=store,
        config=config,
        executor_factory=lambda _h: FakeSshExecutor(),
    )
    client = TestClient(app)
    response = client.get("/api/workloads/cron:mac-mini:abc123/logs")
    assert response.status_code == 400


# AC-8.5
def test_ac_8_5_logs_ssh_failure_502(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    config = AppConfig(
        hosts=[
            HostConfig(
                id="mac-mini",
                display_name="Mac Mini",
                tailscale_host="mac-mini",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id",
                os=HostOS.LINUX,
            )
        ],
    )
    ps_out = (FIXTURES / "ps_standalone.jsonl").read_text()
    ps_exec = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=ps_out, stderr="", exit_code=0),
        }
    )
    AuditPass().run(config, store, lambda _h: ps_exec)

    fail_logs = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_LOGS, (("n", 200), ("name", "nginx"))): SshResult(
                stdout="",
                stderr="boom",
                exit_code=1,
            ),
        }
    )
    app = create_app(
        store=store,
        config=config,
        executor_factory=lambda _h: fail_logs,
    )
    response = TestClient(app).get("/api/workloads/docker:mac-mini:nginx/logs")
    assert response.status_code == 502


def test_logs_resolves_host_after_scanning_prior_hosts(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    config = AppConfig(
        hosts=[
            HostConfig(
                id="other",
                display_name="Other",
                tailscale_host="other",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id",
                os=HostOS.LINUX,
            ),
            HostConfig(
                id="mac-mini",
                display_name="Mac Mini",
                tailscale_host="mac-mini",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id_ed25519",
                os=HostOS.DARWIN,
            ),
        ],
        promote=PromoteRulesConfig(allowlist=[], port_denylist=[]),
    )
    ps_out = (FIXTURES / "ps_standalone.jsonl").read_text()
    ps_exec = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=ps_out, stderr="", exit_code=0),
        }
    )
    logs_exec = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_LOGS, (("n", 200), ("name", "nginx"))): SshResult(
                stdout="ok\n",
                stderr="",
                exit_code=0,
            ),
        }
    )
    AuditPass().run(config, store, lambda _h: ps_exec)
    app = create_app(
        store=store,
        config=config,
        executor_factory=lambda host: logs_exec if host.id == "mac-mini" else ps_exec,
    )
    response = TestClient(app).get("/api/workloads/docker:mac-mini:nginx/logs")
    assert response.status_code == 200
    assert response.text == "ok\n"
