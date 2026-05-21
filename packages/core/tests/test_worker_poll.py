from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import WorkloadStore
from mac_mini_core.telegram import FakeTelegramNotifier
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


def _executor(
    stdout: str,
    *,
    logs_stdout: str = "",
    inspect_stdout: str = "",
) -> FakeSshExecutor:
    responses: dict[tuple[CommandTemplate, tuple[tuple[str, object], ...]], SshResult] = {
        (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=stdout, stderr="", exit_code=0),
    }
    if logs_stdout:
        responses[(CommandTemplate.DOCKER_LOGS, (("n", 50), ("name", "nginx")))] = SshResult(
            stdout=logs_stdout, stderr="", exit_code=0,
        )
    else:
        responses[(CommandTemplate.DOCKER_LOGS, (("n", 50), ("name", "nginx")))] = SshResult(
            stdout="ok\n", stderr="", exit_code=0,
        )
    if inspect_stdout:
        responses[(CommandTemplate.DOCKER_INSPECT, (("name", "nginx"),))] = SshResult(
            stdout=inspect_stdout, stderr="", exit_code=0,
        )
    else:
        responses[(CommandTemplate.DOCKER_INSPECT, (("name", "nginx"),))] = SshResult(
            stdout='[{"RestartCount": 0}]', stderr="", exit_code=0,
        )
    return FakeSshExecutor(responses=responses)


def _simple_executor(stdout: str) -> FakeSshExecutor:
    return FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=stdout, stderr="", exit_code=0),
        }
    )


def _run_audit_and_poll(
    store: WorkloadStore,
    audit_fixture: str,
    poll_stdout: str,
    *,
    notifier: FakeTelegramNotifier | None = None,
    logs_stdout: str = "",
    inspect_stdout: str = "",
) -> None:
    audit_exec = _simple_executor((FIXTURES / audit_fixture).read_text())

    def audit_factory(host: HostConfig) -> FakeSshExecutor:
        return audit_exec

    AuditPass().run(_config(), store, audit_factory)

    poll_exec = _executor(
        poll_stdout,
        logs_stdout=logs_stdout,
        inspect_stdout=inspect_stdout,
    )

    def poll_factory(host: HostConfig) -> FakeSshExecutor:
        return poll_exec

    PollPass(notifier=notifier).run(_config(), store, poll_factory)


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
        audit_exec = _simple_executor((FIXTURES / "ps_standalone.jsonl").read_text())

        def factory(host: HostConfig) -> FakeSshExecutor:
            return audit_exec

        AuditPass().run(_config(), store, factory)
        store.conn.execute(
            "UPDATE workloads SET monitored = 0 WHERE id = ?",
            ("docker:mac-mini:nginx",),
        )
        store.conn.commit()
        before = store.get_state("docker:mac-mini:nginx")

        empty_exec = _simple_executor("")

        def poll_factory(host: HostConfig) -> FakeSshExecutor:
            return empty_exec

        PollPass().run(_config(), store, poll_factory)
        after = store.get_state("docker:mac-mini:nginx")
        assert after == before
    finally:
        store.close()


def test_poll_sends_telegram_on_severity_transition(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        notifier = FakeTelegramNotifier()
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        _run_audit_and_poll(store, "ps_standalone.jsonl", fixture, notifier=notifier)
        assert len(notifier.sent) == 0

        _run_audit_and_poll(store, "ps_standalone.jsonl", "", notifier=notifier)
        assert len(notifier.sent) == 1
        assert notifier.sent[0]["severity"] == "orange"
        assert notifier.sent[0]["host"] == "mac-mini"
    finally:
        store.close()


def test_poll_respects_notify_orange_off(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        store.update_settings({"notify_orange": False})
        notifier = FakeTelegramNotifier()
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        _run_audit_and_poll(store, "ps_standalone.jsonl", fixture, notifier=notifier)
        _run_audit_and_poll(store, "ps_standalone.jsonl", "", notifier=notifier)
        assert len(notifier.sent) == 0
    finally:
        store.close()


def test_poll_with_log_tail_error_detection(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        error_logs = "ERROR: database connection failed\nFatal crash\n"
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        _run_audit_and_poll(
            store, "ps_standalone.jsonl", fixture, logs_stdout=error_logs,
        )
        _, severity, reason = store.get_state("docker:mac-mini:nginx")
        assert severity == "red"
        assert reason is not None
    finally:
        store.close()


def test_poll_with_restart_count(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        inspect_data = '[{"RestartCount": 10}]'
        _run_audit_and_poll(
            store,
            "ps_standalone.jsonl",
            fixture,
            inspect_stdout=inspect_data,
        )
        _, severity, reason = store.get_state("docker:mac-mini:nginx")
        assert severity == "orange"
        assert reason is not None
    finally:
        store.close()


def test_poll_inspect_parse_failure(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        _run_audit_and_poll(
            store, "ps_standalone.jsonl", fixture, inspect_stdout="not json",
        )
        _, severity, _ = store.get_state("docker:mac-mini:nginx")
        assert severity == "green"
    finally:
        store.close()


def test_poll_inspect_empty_list(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        _run_audit_and_poll(
            store, "ps_standalone.jsonl", fixture, inspect_stdout="[]",
        )
        _, severity, _ = store.get_state("docker:mac-mini:nginx")
        assert severity == "green"
    finally:
        store.close()


def test_poll_log_fetch_exception_handled(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        audit_exec = _simple_executor(fixture)

        def audit_factory(host: HostConfig) -> FakeSshExecutor:
            return audit_exec

        AuditPass().run(_config(), store, audit_factory)

        poll_exec = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=fixture, stderr="", exit_code=0),
                (CommandTemplate.DOCKER_INSPECT, (("name", "nginx"),)): SshResult(
                    stdout='[{"RestartCount": 0}]', stderr="", exit_code=0,
                ),
            }
        )
        poll_exec.failures_before_success[(CommandTemplate.DOCKER_LOGS, (("n", 50), ("name", "nginx")))] = 999

        def poll_factory(host: HostConfig) -> FakeSshExecutor:
            return poll_exec

        PollPass().run(_config(), store, poll_factory)
        _, severity, _ = store.get_state("docker:mac-mini:nginx")
        assert severity == "green"
    finally:
        store.close()


def test_poll_inspect_exception_handled(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        audit_exec = _simple_executor(fixture)

        def audit_factory(host: HostConfig) -> FakeSshExecutor:
            return audit_exec

        AuditPass().run(_config(), store, audit_factory)

        poll_exec = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=fixture, stderr="", exit_code=0),
                (CommandTemplate.DOCKER_LOGS, (("n", 50), ("name", "nginx"))): SshResult(
                    stdout="ok\n", stderr="", exit_code=0,
                ),
            }
        )
        poll_exec.failures_before_success[(CommandTemplate.DOCKER_INSPECT, (("name", "nginx"),))] = 999

        def poll_factory(host: HostConfig) -> FakeSshExecutor:
            return poll_exec

        PollPass().run(_config(), store, poll_factory)
        _, severity, _ = store.get_state("docker:mac-mini:nginx")
        assert severity == "green"
    finally:
        store.close()


def test_poll_log_nonzero_exit_returns_none(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        audit_exec = _simple_executor(fixture)

        def audit_factory(host: HostConfig) -> FakeSshExecutor:
            return audit_exec

        AuditPass().run(_config(), store, audit_factory)

        poll_exec = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=fixture, stderr="", exit_code=0),
                (CommandTemplate.DOCKER_LOGS, (("n", 50), ("name", "nginx"))): SshResult(
                    stdout="", stderr="err", exit_code=1,
                ),
                (CommandTemplate.DOCKER_INSPECT, (("name", "nginx"),)): SshResult(
                    stdout='[{"RestartCount": 0}]', stderr="", exit_code=0,
                ),
            }
        )

        def poll_factory(host: HostConfig) -> FakeSshExecutor:
            return poll_exec

        PollPass().run(_config(), store, poll_factory)
        _, severity, _ = store.get_state("docker:mac-mini:nginx")
        assert severity == "green"
    finally:
        store.close()


def test_poll_inspect_nonzero_exit_returns_zero(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        audit_exec = _simple_executor(fixture)

        def audit_factory(host: HostConfig) -> FakeSshExecutor:
            return audit_exec

        AuditPass().run(_config(), store, audit_factory)

        poll_exec = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=fixture, stderr="", exit_code=0),
                (CommandTemplate.DOCKER_LOGS, (("n", 50), ("name", "nginx"))): SshResult(
                    stdout="ok\n", stderr="", exit_code=0,
                ),
                (CommandTemplate.DOCKER_INSPECT, (("name", "nginx"),)): SshResult(
                    stdout="", stderr="err", exit_code=1,
                ),
            }
        )

        def poll_factory(host: HostConfig) -> FakeSshExecutor:
            return poll_exec

        PollPass().run(_config(), store, poll_factory)
        _, severity, _ = store.get_state("docker:mac-mini:nginx")
        assert severity == "green"
    finally:
        store.close()


def test_poll_non_docker_workload_skips_logs(tmp_path: Path) -> None:
    """Non-docker workloads skip log tail and inspect calls."""
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        from mac_mini_core.models import WorkloadSnapshot, WorkloadKind
        snap = WorkloadSnapshot(
            workload_id="systemd:mac-mini:nginx.service",
            host_id="mac-mini",
            kind=WorkloadKind.SYSTEMD,
            name="nginx.service",
            status="active/running",
        )
        store.ensure_host(_config().hosts[0])
        store.upsert_snapshot(snap, project_roots=[], allowlist=["nginx.service"], port_denylist=[])
        store.pin_workload("systemd:mac-mini:nginx.service")

        poll_exec = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout="", stderr="", exit_code=0),
            }
        )

        def poll_factory(host: HostConfig) -> FakeSshExecutor:
            return poll_exec

        PollPass().run(_config(), store, poll_factory)
    finally:
        store.close()


def test_poll_no_notifier_no_crash(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        fixture = (FIXTURES / "ps_standalone.jsonl").read_text()
        _run_audit_and_poll(store, "ps_standalone.jsonl", fixture, notifier=None)
        _run_audit_and_poll(store, "ps_standalone.jsonl", "", notifier=None)
    finally:
        store.close()
