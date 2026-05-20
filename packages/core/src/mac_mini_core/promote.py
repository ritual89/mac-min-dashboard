from __future__ import annotations

from dataclasses import dataclass

from mac_mini_core.config import PromoteRulesConfig
from mac_mini_core.models import WorkloadKind


_SYSTEM_PATH_PREFIXES = ("/usr", "/System", "/bin", "/sbin")


@dataclass(frozen=True)
class WorkloadPromoteInput:
    kind: WorkloadKind | str
    name: str
    project_path: str | None = None
    listen_port: int | None = None
    pinned: bool = False


def _path_is_system(path: str) -> bool:
    normalized = path.rstrip("/")
    return any(
        normalized == prefix or normalized.startswith(f"{prefix}/")
        for prefix in _SYSTEM_PATH_PREFIXES
    )


def _path_under_root(project_path: str, root: str) -> bool:
    if root.endswith("/"):
        root = root[:-1]
    if project_path == root:
        return True
    return project_path.startswith(f"{root}/")


def _is_apple_launchd(name: str, kind: WorkloadKind | str) -> bool:
    kind_value = kind.value if isinstance(kind, WorkloadKind) else str(kind)
    return kind_value == WorkloadKind.LAUNCHD.value and name.startswith("com.apple.")


def should_promote(
    workload: WorkloadPromoteInput,
    rules: PromoteRulesConfig,
) -> bool:
    if workload.pinned:
        return True

    kind_value = workload.kind.value if isinstance(workload.kind, WorkloadKind) else str(workload.kind)

    if _is_apple_launchd(workload.name, workload.kind):
        return False

    if workload.project_path and _path_is_system(workload.project_path):
        return False

    if kind_value in {WorkloadKind.DOCKER.value, WorkloadKind.COMPOSE.value}:
        return True

    if workload.project_path:
        for root in rules.project_roots:
            if _path_under_root(workload.project_path, root):
                return True

    if workload.listen_port is not None:
        if workload.listen_port > 1024 and workload.listen_port not in rules.port_denylist:
            return True

    if workload.name in rules.allowlist:
        return True

    return False
