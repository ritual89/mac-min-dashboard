from __future__ import annotations

import hashlib

from mac_mini_core.config import HostConfig
from mac_mini_core.models import WorkloadKind, WorkloadSnapshot
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import SshExecutor


def _hash_line(line: str) -> str:
    return hashlib.sha256(line.encode()).hexdigest()[:12]


def parse_crontab_output(host_id: str, stdout: str) -> list[WorkloadSnapshot]:
    snapshots: list[WorkloadSnapshot] = []
    for line in stdout.strip().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        line_hash = _hash_line(stripped)
        snapshots.append(
            WorkloadSnapshot(
                workload_id=f"cron:{host_id}:{line_hash}",
                host_id=host_id,
                kind=WorkloadKind.CRON,
                name=stripped,
                status="scheduled",
            )
        )
    return snapshots


class CronScanner:
    def discover(self, host: HostConfig, executor: SshExecutor) -> list[WorkloadSnapshot]:
        result = executor.execute(CommandTemplate.CRONTAB_LIST)
        return parse_crontab_output(host.id, result.stdout)
