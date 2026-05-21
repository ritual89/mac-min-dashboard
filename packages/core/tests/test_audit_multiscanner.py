from __future__ import annotations

from pathlib import Path

from mac_mini_core.config import AppConfig, HostConfig, PromoteRulesConfig
from mac_mini_core.models import HostOS
from mac_mini_core.scanners.cron import CronScanner
from mac_mini_core.scanners.docker import DockerScanner
from mac_mini_core.scanners.launchd import LaunchdScanner
from mac_mini_core.scanners.systemd import SystemdScanner
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import WorkloadStore
from mac_mini_core.worker.audit import AuditPass

DOCKER_FIXTURES = Path(__file__).parent / "fixtures" / "docker"
SYSTEMD_FIXTURES = Path(__file__).parent / "fixtures" / "systemd"
LAUNCHD_FIXTURES = Path(__file__).parent / "fixtures" / "launchd"
CRON_FIXTURES = Path(__file__).parent / "fixtures" / "cron"


def _linux_config() -> AppConfig:
    return AppConfig(
        hosts=[
            HostConfig(
                id="linux-box",
                display_name="Linux Box",
                tailscale_host="linux-box",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id",
                os=HostOS.LINUX,
            )
        ],
        promote=PromoteRulesConfig(allowlist=[], port_denylist=[]),
    )


def _darwin_config() -> AppConfig:
    return AppConfig(
        hosts=[
            HostConfig(
                id="mac-mini",
                display_name="Mac Mini",
                tailscale_host="mac-mini",
                ssh_user="greg",
                ssh_key_path="~/.ssh/id",
                os=HostOS.DARWIN,
            )
        ],
        promote=PromoteRulesConfig(allowlist=[], port_denylist=[]),
    )


def test_linux_host_runs_docker_systemd_cron(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        docker_stdout = (DOCKER_FIXTURES / "ps_standalone.jsonl").read_text()
        systemd_stdout = (SYSTEMD_FIXTURES / "list_units.txt").read_text()
        cron_stdout = (CRON_FIXTURES / "crontab.txt").read_text()

        executor = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=docker_stdout, stderr="", exit_code=0),
                (CommandTemplate.SYSTEMCTL_LIST_UNITS, ()): SshResult(stdout=systemd_stdout, stderr="", exit_code=0),
                (CommandTemplate.CRONTAB_LIST, ()): SshResult(stdout=cron_stdout, stderr="", exit_code=0),
            }
        )

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executor

        audit = AuditPass()
        total = audit.run(_linux_config(), store, factory)
        assert total >= 6  # 1 docker + 3 systemd + 2 cron
    finally:
        store.close()


def test_darwin_host_runs_docker_launchd_cron(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        docker_stdout = (DOCKER_FIXTURES / "ps_standalone.jsonl").read_text()
        launchd_stdout = (LAUNCHD_FIXTURES / "list.txt").read_text()
        cron_stdout = (CRON_FIXTURES / "crontab.txt").read_text()

        executor = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=docker_stdout, stderr="", exit_code=0),
                (CommandTemplate.LAUNCHCTL_LIST, ()): SshResult(stdout=launchd_stdout, stderr="", exit_code=0),
                (CommandTemplate.CRONTAB_LIST, ()): SshResult(stdout=cron_stdout, stderr="", exit_code=0),
            }
        )

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executor

        audit = AuditPass()
        total = audit.run(_darwin_config(), store, factory)
        assert total >= 6  # 1 docker + 3 launchd + 2 cron
    finally:
        store.close()


def test_audit_custom_scanners_dict(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        docker_stdout = (DOCKER_FIXTURES / "ps_standalone.jsonl").read_text()
        executor = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=docker_stdout, stderr="", exit_code=0),
            }
        )

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executor

        audit = AuditPass(scanners={"all": [DockerScanner()], "linux": [], "darwin": []})
        total = audit.run(_darwin_config(), store, factory)
        assert total == 1
    finally:
        store.close()


def test_audit_backward_compat_single_scanner(tmp_path: Path) -> None:
    store = WorkloadStore.open(str(tmp_path / "fleet.db"))
    try:
        docker_stdout = (DOCKER_FIXTURES / "ps_standalone.jsonl").read_text()
        executor = FakeSshExecutor(
            responses={
                (CommandTemplate.DOCKER_PS, ()): SshResult(stdout=docker_stdout, stderr="", exit_code=0),
            }
        )

        def factory(host: HostConfig) -> FakeSshExecutor:
            return executor

        audit = AuditPass(scanner=DockerScanner())
        total = audit.run(_darwin_config(), store, factory)
        assert total == 1
    finally:
        store.close()
