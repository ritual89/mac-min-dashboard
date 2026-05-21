from __future__ import annotations

from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.ssh.executor import SshExecutor
from mac_mini_core.store import HostRow, WorkloadRow

_LOGGABLE_KINDS = frozenset({"docker", "compose", "launchd", "systemd"})


class LogsError(Exception):
    """Base logs error."""


class UnsupportedWorkloadKindError(LogsError):
    """Raised when workload kind cannot produce logs."""


class LogFetchError(LogsError):
    """Raised when SSH log command fails."""


def _tail_to_duration(tail: int) -> str:
    """Map a line-count hint to a macOS `log show --last` duration string."""
    if tail <= 50:
        return "5m"
    if tail <= 200:
        return "30m"
    return "1h"


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

    if workload.kind in ("docker", "compose"):
        result = executor.execute(
            CommandTemplate.DOCKER_LOGS,
            name=workload.name,
            n=tail,
        )
        if result.exit_code != 0:
            msg = f"docker logs failed: {result.stderr.strip()}"
            raise LogFetchError(msg)
        return result.stdout

    if workload.kind == "systemd":
        result = executor.execute(
            CommandTemplate.JOURNALCTL_UNIT,
            unit=workload.name,
            n=tail,
        )
        if result.exit_code != 0:
            msg = f"journalctl failed: {result.stderr.strip()}"
            raise LogFetchError(msg)
        return result.stdout

    # launchd — use macOS unified log, grep by process/subsystem name
    duration = _tail_to_duration(tail)
    result = executor.execute(
        CommandTemplate.LOG_SHOW_LAST,
        duration=duration,
    )
    if result.exit_code != 0:
        msg = f"log show failed: {result.stderr.strip()}"
        raise LogFetchError(msg)
    # Filter to lines mentioning the launchd label
    lines = [
        line for line in result.stdout.splitlines()
        if workload.name in line
    ]
    return "\n".join(lines[-tail:])
