from __future__ import annotations

import pytest

from mac_mini_core.logs import (
    LogFetchError,
    UnsupportedWorkloadKindError,
    fetch_workload_logs,
)
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import HostRow, WorkloadRow


def _host() -> HostRow:
    return HostRow(
        id="mac-mini",
        display_name="Mac Mini",
        tailscale_host="mac-mini",
        ssh_user="greg",
        ssh_key_path="~/.ssh/id",
        os="darwin",
        last_seen=None,
    )


def _workload(kind: str = "docker", name: str = "nginx") -> WorkloadRow:
    return WorkloadRow(
        id=f"{kind}:mac-mini:{name}",
        host_id="mac-mini",
        kind=kind,
        name=name,
        monitored=True,
        pinned=False,
        status="running",
        severity="green",
        severity_reason=None,
        last_seen=None,
        metadata={},
    )


# AC-8.1
def test_ac_8_1_docker_logs_command() -> None:
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_LOGS, (("n", 100), ("name", "nginx"))): SshResult(
                stdout="log line\n",
                stderr="",
                exit_code=0,
            ),
        }
    )
    text = fetch_workload_logs(_workload(), _host(), executor, tail=100)
    assert text == "log line\n"
    assert "docker logs --tail 100 nginx" in executor.history[0].rendered


def test_ac_8_4_cron_unsupported() -> None:
    with pytest.raises(UnsupportedWorkloadKindError):
        fetch_workload_logs(
            _workload(kind="cron", name="backup.sh"),
            _host(),
            FakeSshExecutor(),
        )


def test_ac_8_5_ssh_failure_raises() -> None:
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.DOCKER_LOGS, (("n", 200), ("name", "nginx"))): SshResult(
                stdout="",
                stderr="permission denied",
                exit_code=1,
            ),
        }
    )
    with pytest.raises(LogFetchError, match="docker logs failed"):
        fetch_workload_logs(_workload(), _host(), executor)


def test_systemd_logs_via_journalctl() -> None:
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.JOURNALCTL_UNIT, (("n", 200), ("unit", "nginx.service"))): SshResult(
                stdout="May 20 systemd[1]: Started nginx.\n",
                stderr="",
                exit_code=0,
            ),
        }
    )
    text = fetch_workload_logs(
        _workload(kind="systemd", name="nginx.service"),
        _host(),
        executor,
    )
    assert "Started nginx" in text


def test_launchd_logs_via_log_show() -> None:
    log_output = (
        "2026-05-20 com.example.myservice: started\n"
        "2026-05-20 kernel: something else\n"
        "2026-05-20 com.example.myservice: healthy\n"
    )
    executor = FakeSshExecutor(
        responses={
            (CommandTemplate.LOG_SHOW_LAST, (("duration", "30m"),)): SshResult(
                stdout=log_output,
                stderr="",
                exit_code=0,
            ),
        }
    )
    text = fetch_workload_logs(
        _workload(kind="launchd", name="com.example.myservice"),
        _host(),
        executor,
    )
    assert "com.example.myservice" in text
    assert "kernel" not in text
