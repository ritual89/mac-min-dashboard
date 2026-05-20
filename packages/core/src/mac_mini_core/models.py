from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HostOS(StrEnum):
    DARWIN = "darwin"
    LINUX = "linux"


class Severity(StrEnum):
    GREEN = "green"
    ORANGE = "orange"
    RED = "red"


class WorkloadKind(StrEnum):
    DOCKER = "docker"
    COMPOSE = "compose"
    SYSTEMD = "systemd"
    LAUNCHD = "launchd"
    CRON = "cron"
    PROCESS = "process"


class InventoryState(StrEnum):
    DISCOVERED = "discovered"
    MONITORED = "monitored"


@dataclass(frozen=True)
class WorkloadSnapshot:
    workload_id: str
    host_id: str
    kind: WorkloadKind
    name: str
    status: str
    docker_health: str | None = None
    compose_project: str | None = None
    compose_service: str | None = None
    image: str | None = None
