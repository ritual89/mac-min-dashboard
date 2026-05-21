from __future__ import annotations

from mac_mini_core.config import HostConfig
from mac_mini_core.models import WorkloadKind, WorkloadSnapshot
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import SshExecutor


def parse_launchctl_output(host_id: str, stdout: str) -> list[WorkloadSnapshot]:
    snapshots: list[WorkloadSnapshot] = []
    lines = stdout.strip().splitlines()
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        pid_str, _status, label = parts[0], parts[1], parts[2]
        if label == "Label":
            continue
        if label.startswith("com.apple."):
            continue
        has_pid = pid_str.strip() != "-"
        status = "running" if has_pid else "loaded"
        snapshots.append(
            WorkloadSnapshot(
                workload_id=f"launchd:{host_id}:{label}",
                host_id=host_id,
                kind=WorkloadKind.LAUNCHD,
                name=label,
                status=status,
            )
        )
    return snapshots


class LaunchdScanner:
    def discover(self, host: HostConfig, executor: SshExecutor) -> list[WorkloadSnapshot]:
        result = executor.execute(CommandTemplate.LAUNCHCTL_LIST)
        return parse_launchctl_output(host.id, result.stdout)
