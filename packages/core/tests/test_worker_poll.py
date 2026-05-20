from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import WorkloadStore
from mac_mini_core.worker.audit import AuditPass
from mac_mini_core.worker.poll import PollPass

FIXTURES = Path(__file__).parent / "fixtures" / "docker"


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


def _executor(stdout: str) -> FakeSshExecutor:
    return FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=stdout, stderr="", exit_code=0),
        }
    )


def _run_audit_and_poll(
    store: WorkloadStore,
    audit_fixture: str,
    poll_stdout: str,
) -> None:
    audit_exec = _executor((FIXTURES / audit_fixture).read_text())

    def audit_factory(host: HostConfig) -> FakeSshExecutor:
        return audit_exec

    AuditPass().run(_config(), store, audit_factory)

    poll_exec = _executor(poll_stdout)

    def poll_factory(host: HostConfig) -> FakeSshExecutor:
        return poll_exec

    PollPass().run(_config(), store, poll_factory)


# AC-6.6
def test_ac_6_6_poll_sets_green_for_healthy_running(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        _run_audit_and_poll(store, "ps_standalone.jsonl", fixture)
        status, severity, reason = store.get_state("docker:mac-mini:nginx")
        assert status == "running"
        assert severity == "green"
        assert reason is None
    finally:
        store.close()


# AC-6.7
def test_ac_6_7_poll_marks_missing_container_orange(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        _run_audit_and_poll(store, "ps_standalone.jsonl", "")
        status, severity, reason = store.get_state("docker:mac-mini:nginx")
        assert status == "missing"
        assert severity == "orange"
        assert reason == "not found in docker ps"
    finally:
        store.close()


# AC-6.8
def test_ac_6_8_poll_sets_red_for_unhealthy(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        unhealthy = (
            '{"ID":"x","Names":"/nginx","Image":"n:1","State":"running",'
            '"Status":"Up 1 second (unhealthy)","Labels":""}\n'
        )
        _run_audit_and_poll(store, "ps_standalone.jsonl", unhealthy)
        _, severity, reason = store.get_state("docker:mac-mini:nginx")
        assert severity == "red"
        assert reason is not None
        assert "health" in reason
    finally:
        store.close()


# AC-6.9
def test_ac_6_9_poll_skips_unmonitored_workloads(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        audit_exec = _executor((FIXTURES / "ps_standalone.jsonl").read_text())

        def factory(host: HostConfig) -> FakeSshExecutor:
            return audit_exec

        AuditPass().run(_config(), store, factory)
        store.conn.execute(
            "UPDATE workloads SET monitored = 0 WHERE id = ?",
            ("docker:mac-mini:nginx",),
        )
        store.conn.commit()
        before = store.get_state("docker:mac-mini:nginx")

        empty_exec = _executor("")

        def poll_factory(host: HostConfig) -> FakeSshExecutor:
            return empty_exec

        PollPass().run(_config(), store, poll_factory)
        after = store.get_state("docker:mac-mini:nginx")
        assert after == before
    finally:
        store.close()
