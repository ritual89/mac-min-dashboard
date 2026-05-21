from __future__ import annotations

import pytest

from mac_mini_core.control import (
    ControlCommandError,
    UnsupportedControlError,
    restart_workload,
    stop_workload,
)
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import FakeSshExecutor, SshResult
from mac_mini_core.store import WorkloadRow


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


def _executor(template: CommandTemplate, param_name: str, name: str, exit_code: int = 0) -> FakeSshExecutor:
    return FakeSshExecutor(
        responses={
            (template, ((param_name, name),)): SshResult(
                stdout="ok\n", stderr="" if exit_code == 0 else "error", exit_code=exit_code,
            ),
        }
    )


# AC-15.1
def test_ac_15_1_restart_docker() -> None:
    executor = _executor(CommandTemplate.DOCKER_RESTART, "name", "nginx")
    result = restart_workload(_workload("docker", "nginx"), executor)
    assert result == "ok\n"
    assert executor.history[0].template is CommandTemplate.DOCKER_RESTART


# AC-15.2
def test_ac_15_2_stop_docker() -> None:
    executor = _executor(CommandTemplate.DOCKER_STOP, "name", "nginx")
    result = stop_workload(_workload("docker", "nginx"), executor)
    assert result == "ok\n"
    assert executor.history[0].template is CommandTemplate.DOCKER_STOP


# AC-15.6
def test_ac_15_6_restart_systemd() -> None:
    executor = _executor(CommandTemplate.SYSTEMCTL_RESTART, "unit", "myapp.service")
    result = restart_workload(_workload("systemd", "myapp.service"), executor)
    assert result == "ok\n"
    assert executor.history[0].template is CommandTemplate.SYSTEMCTL_RESTART


# AC-15.7
def test_ac_15_7_restart_launchd() -> None:
    executor = _executor(CommandTemplate.LAUNCHCTL_KICKSTART, "label", "com.my.svc")
    result = restart_workload(_workload("launchd", "com.my.svc"), executor)
    assert result == "ok\n"
    assert executor.history[0].template is CommandTemplate.LAUNCHCTL_KICKSTART


# AC-15.8
def test_ac_15_8_stop_launchd_unsupported() -> None:
    executor = FakeSshExecutor()
    with pytest.raises(UnsupportedControlError, match="stop not supported"):
        stop_workload(_workload("launchd", "com.my.svc"), executor)


# AC-15.9
def test_ac_15_9_restart_ssh_failure() -> None:
    executor = _executor(CommandTemplate.DOCKER_RESTART, "name", "nginx", exit_code=1)
    with pytest.raises(ControlCommandError, match="restart failed"):
        restart_workload(_workload("docker", "nginx"), executor)


def test_restart_compose_uses_docker_restart() -> None:
    executor = _executor(CommandTemplate.DOCKER_RESTART, "name", "api")
    restart_workload(_workload("compose", "api"), executor)
    assert executor.history[0].template is CommandTemplate.DOCKER_RESTART


def test_stop_compose_uses_docker_stop() -> None:
    executor = _executor(CommandTemplate.DOCKER_STOP, "name", "api")
    stop_workload(_workload("compose", "api"), executor)
    assert executor.history[0].template is CommandTemplate.DOCKER_STOP


def test_stop_systemd() -> None:
    executor = _executor(CommandTemplate.SYSTEMCTL_STOP, "unit", "myapp.service")
    stop_workload(_workload("systemd", "myapp.service"), executor)
    assert executor.history[0].template is CommandTemplate.SYSTEMCTL_STOP


def test_restart_unsupported_kind() -> None:
    executor = FakeSshExecutor()
    with pytest.raises(UnsupportedControlError, match="restart not supported"):
        restart_workload(_workload("cron", "job1"), executor)


def test_stop_unsupported_kind() -> None:
    executor = FakeSshExecutor()
    with pytest.raises(UnsupportedControlError, match="stop not supported"):
        stop_workload(_workload("cron", "job1"), executor)


def test_stop_ssh_failure() -> None:
    executor = _executor(CommandTemplate.DOCKER_STOP, "name", "nginx", exit_code=1)
    with pytest.raises(ControlCommandError, match="stop failed"):
        stop_workload(_workload("docker", "nginx"), executor)
