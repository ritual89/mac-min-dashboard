from __future__ import annotations

from mac_mini_core.config import HostConfig
from mac_mini_core.models import WorkloadKind, WorkloadSnapshot
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import SshExecutor


def parse_systemctl_output(host_id: str, stdout: str) -> list[WorkloadSnapshot]:
    snapshots: list[WorkloadSnapshot] = []
    lines = stdout.strip().splitlines()
    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            continue
        unit = parts[0]
        if not unit.endswith(".service"):
            continue
        load_state = parts[1]
        active_state = parts[2]
        sub_state = parts[3]
        if load_state != "loaded":
            continue
        snapshots.append(
            WorkloadSnapshot(
                workload_id=f"systemd:{host_id}:{unit}",
                host_id=host_id,
                kind=WorkloadKind.SYSTEMD,
                name=unit,
                status=f"{active_state}/{sub_state}",
            )
        )
    return snapshots


class SystemdScanner:
    def discover(self, host: HostConfig, executor: SshExecutor) -> list[WorkloadSnapshot]:
        result = executor.execute(CommandTemplate.SYSTEMCTL_LIST_UNITS)
        return parse_systemctl_output(host.id, result.stdout)
