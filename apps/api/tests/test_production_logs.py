from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mac_mini_api.main import create_production_app
from mac_mini_core.config import AppConfig, HostConfig, load_config
from mac_mini_core.store import WorkloadStore
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.worker.audit import AuditPass

FIXTURES = Path(__file__).resolve().parents[3] / "packages" / "core" / "tests" / "fixtures" / "docker"

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


def test_production_app_serves_logs(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_CONFIG_YAML)
    db_path = tmp_path / "fleet.db"
    monkeypatch.setenv("DASHBOARD_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_PATH", str(db_path))

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

    config = load_config(config_path)
    store = WorkloadStore.open(str(db_path))
    AuditPass().run(config, store, lambda _h: ps_exec)
    store.close()

    monkeypatch.setattr(
        "mac_mini_api.main.create_executor_factory",
        lambda _cfg: factory,
    )

    app = create_production_app()
    client = TestClient(app)
    response = client.get("/api/workloads/docker:mac-mini:nginx/logs")
    assert response.status_code == 200
    assert response.text == "hello from container\n"
    app.state.store.close()
