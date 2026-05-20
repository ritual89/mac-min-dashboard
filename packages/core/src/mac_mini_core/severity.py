from __future__ import annotations

import re
from dataclasses import dataclass

from mac_mini_core.models import Severity

_LOG_ERROR_PATTERNS = (
    re.compile(r"ERROR", re.IGNORECASE),
    re.compile(r"Traceback"),
    re.compile(r"panic", re.IGNORECASE),
)

_STOPPED_STATUSES = frozenset({"exited", "stopped", "dead", "failed", "inactive"})


@dataclass(frozen=True)
class SeverityInput:
    status: str
    docker_health: str | None = None
    log_tail: str = ""
    http_probe_configured: bool = False
    http_probe_ok: bool | None = None
    expected_running: bool = True
    restart_count_1h: int = 0
    restart_loop_threshold: int = 5


@dataclass(frozen=True)
class SeverityResult:
    severity: Severity
    reason: str | None = None


def _log_indicates_error(log_tail: str) -> bool:
    if not log_tail:
        return False
    return any(pattern.search(log_tail) for pattern in _LOG_ERROR_PATTERNS)


def evaluate_severity(data: SeverityInput) -> SeverityResult:
    if data.docker_health == "unhealthy":
        return SeverityResult(severity=Severity.RED, reason="docker health unhealthy")

    if data.http_probe_configured and data.http_probe_ok is False:
        return SeverityResult(severity=Severity.RED, reason="http probe failed")

    if _log_indicates_error(data.log_tail):
        return SeverityResult(severity=Severity.RED, reason="error pattern in logs")

    if data.expected_running and data.status.lower() in _STOPPED_STATUSES:
        return SeverityResult(severity=Severity.ORANGE, reason="expected running but stopped")

    if data.restart_count_1h > data.restart_loop_threshold:
        return SeverityResult(
            severity=Severity.ORANGE,
            reason=f"restart loop ({data.restart_count_1h}/hour)",
        )

    return SeverityResult(severity=Severity.GREEN)
