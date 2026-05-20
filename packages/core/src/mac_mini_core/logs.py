from __future__ import annotations

from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import SshExecutor
from mac_mini_core.store import HostRow, WorkloadRow

_LOGGABLE_KINDS = frozenset({"docker", "compose"})


class LogsError(Exception):
    """Base logs error."""


class UnsupportedWorkloadKindError(LogsError):
    """Raised when workload kind cannot produce docker logs."""


class LogFetchError(LogsError):
    """Raised when SSH log command fails."""


def fetch_workload_logs(
    workload: WorkloadRow,
    host: HostRow,
    executor: SshExecutor,
    *,
    tail: int = 200,
) -> str:
    del host  # reserved for per-host executor routing at API layer
    if workload.kind not in _LOGGABLE_KINDS:
        msg = f"logs not supported for kind {workload.kind!r}"
        raise UnsupportedWorkloadKindError(msg)

    result = executor.execute(
        CommandTemplate.DOCKER_LOGS,
        name=workload.name,
        n=tail,
    )
    if result.exit_code != 0:
        msg = f"docker logs failed: {result.stderr.strip()}"
        raise LogFetchError(msg)
    return result.stdout
