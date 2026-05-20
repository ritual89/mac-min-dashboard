from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import WorkloadStore
from mac_mini_core.worker.audit import AuditPass

FIXTURES = Path(__file__).parent / "fixtures" / "docker"


def _config(*host_ids: str) -> AppConfig:
    return AppConfig(
        hosts=[
            HostConfig(
                id=host_id,
                display_name=host_id,
                tailscale_host=host_id,
                ssh_user="greg",
                ssh_key_path="~/.ssh/id_ed25519",
                os=HostOS.LINUX,
            )
            for host_id in host_ids
        ],
        promote=PromoteRulesConfig(allowlist=[], port_denylist=[]),
    )


def _factory(fixture_name: str) -> dict[str, FakeSshExecutor]:
    stdout = (FIXTURES / fixture_name).read_text()
    result = SshResult(stdout=stdout, stderr="", exit_code=0)
    return {
        "mac-mini": FakeSshExecutor(
            responses={(CommandTemplate.DOCKER_PS, ()): result}
        ),
        "vultr-1": FakeSshExecutor(
            responses={(CommandTemplate.DOCKER_PS, ()): result}
        ),
    }


# AC-6.1
def test_ac_6_1_audit_upserts_workload(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        executors = _factory("ps_standalone.jsonl")

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executors[host.id]

        count = AuditPass().run(_config("mac-mini"), store, factory)
        assert count == 1
        assert store.count_workloads() == 1
    finally:
        store.close()


# AC-6.2
def test_ac_6_2_docker_workload_is_monitored(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        executors = _factory("ps_standalone.jsonl")

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executors[host.id]

        AuditPass().run(_config("mac-mini"), store, factory)
        assert store.get_monitored("docker:mac-mini:nginx")
    finally:
        store.close()


# AC-6.3
def test_ac_6_3_multi_host_audit(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        executors = _factory("ps_standalone.jsonl")

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executors[host.id]

        count = AuditPass().run(_config("mac-mini", "vultr-1"), store, factory)
        assert count == 2
        assert store.count_workloads() == 2
    finally:
        store.close()


# AC-6.4
def test_ac_6_4_audit_upsert_is_idempotent(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        executors = _factory("ps_standalone.jsonl")

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executors[host.id]

        audit = AuditPass()
        audit.run(_config("mac-mini"), store, factory)
        audit.run(_config("mac-mini"), store, factory)
        assert store.count_workloads() == 1
    finally:
        store.close()


# AC-6.5
def test_ac_6_5_compose_workload_monitored(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        executors = _factory("ps_compose.jsonl")

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executors[host.id]

        AuditPass().run(_config("mac-mini"), store, factory)
        assert store.get_monitored("compose:mac-mini:myapp:api")
    finally:
        store.close()
