from __future__ import annotations

from mac_mini_core.models import WorkloadKind


def build_workload_id(kind: WorkloadKind | str, host_id: str, *parts: str) -> str:
    kind_value = kind.value if isinstance(kind, WorkloadKind) else str(kind)
    if not host_id:
        msg = "host_id is required"
        raise ValueError(msg)
    if not parts:
        msg = "at least one identifying part is required"
        raise ValueError(msg)
    safe_parts = [part.replace(":", "_") for part in parts]
    return ":".join([kind_value, host_id, *safe_parts])
