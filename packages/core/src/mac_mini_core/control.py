from __future__ import annotations

from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import SshExecutor
from mac_mini_core.store import WorkloadRow

_RESTART_MAP: dict[str, tuple[CommandTemplate, str]] = {
    "docker": (CommandTemplate.DOCKER_RESTART, "name"),
    "compose": (CommandTemplate.DOCKER_RESTART, "name"),
    "systemd": (CommandTemplate.SYSTEMCTL_RESTART, "unit"),
    "launchd": (CommandTemplate.LAUNCHCTL_KICKSTART, "label"),
}

_STOP_MAP: dict[str, tuple[CommandTemplate, str]] = {
    "docker": (CommandTemplate.DOCKER_STOP, "name"),
    "compose": (CommandTemplate.DOCKER_STOP, "name"),
    "systemd": (CommandTemplate.SYSTEMCTL_STOP, "unit"),
}


class UnsupportedControlError(Exception):
    pass


class ControlCommandError(Exception):
    pass


def restart_workload(workload: WorkloadRow, executor: SshExecutor) -> str:
    entry = _RESTART_MAP.get(workload.kind)
    if entry is None:
        msg = f"restart not supported for kind {workload.kind!r}"
        raise UnsupportedControlError(msg)
    template, param_name = entry
    result = executor.execute(template, **{param_name: workload.name})
    if result.exit_code != 0:
        msg = f"restart failed: {result.stderr.strip()}"
        raise ControlCommandError(msg)
    return result.stdout


def stop_workload(workload: WorkloadRow, executor: SshExecutor) -> str:
    entry = _STOP_MAP.get(workload.kind)
    if entry is None:
        msg = f"stop not supported for kind {workload.kind!r}"
        raise UnsupportedControlError(msg)
    template, param_name = entry
    result = executor.execute(template, **{param_name: workload.name})
    if result.exit_code != 0:
        msg = f"stop failed: {result.stderr.strip()}"
        raise ControlCommandError(msg)
    return result.stdout
