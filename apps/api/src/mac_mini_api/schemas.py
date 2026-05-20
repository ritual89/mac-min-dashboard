from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HostOut(BaseModel):
    id: str
    display_name: str
    tailscale_host: str
    os: str
    last_seen: str | None


class WorkloadOut(BaseModel):
    id: str
    host_id: str
    kind: str
    name: str
    monitored: bool
    pinned: bool
    status: str
    severity: str
    severity_reason: str | None
    last_seen: str | None
    metadata: dict[str, Any]


class WorkloadDetailOut(WorkloadOut):
    pass
