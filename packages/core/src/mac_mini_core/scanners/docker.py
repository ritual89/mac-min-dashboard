from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from mac_mini_core.config import HostConfig
from mac_mini_core.models import WorkloadKind, WorkloadSnapshot
from mac_mini_core.ssh.commands import CommandTemplate
from mac_mini_core.workload_id import build_workload_id

if TYPE_CHECKING:
    from mac_mini_core.ssh.executor import SshExecutor

_HEALTH_RE = re.compile(r"\((healthy|unhealthy)\)", re.IGNORECASE)


def _parse_labels(raw: str) -> dict[str, str]:
    if not raw:
        return {}
    labels: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        labels[key.strip()] = value.strip()
    return labels


def _container_name(names_field: str) -> str | None:
    if not names_field:
        return None
    return names_field.lstrip("/").split(",")[0].strip() or None


def _parse_health(status: str) -> str | None:
    match = _HEALTH_RE.search(status)
    if match is None:
        return None
    return match.group(1).lower()


def _snapshot_from_row(host_id: str, row: dict[str, object]) -> WorkloadSnapshot | None:
    name = _container_name(str(row.get("Names", "")))
    if name is None:
        return None

    state = str(row.get("State", "unknown")).lower()
    status_text = str(row.get("Status", ""))
    labels = _parse_labels(str(row.get("Labels", "")))
    image = str(row.get("Image", "")) or None

    project = labels.get("com.docker.compose.project")
    service = labels.get("com.docker.compose.service")

    if project and service:
        workload_id = build_workload_id(WorkloadKind.COMPOSE, host_id, project, service)
        kind = WorkloadKind.COMPOSE
    else:
        workload_id = build_workload_id(WorkloadKind.DOCKER, host_id, name)
        kind = WorkloadKind.DOCKER

    return WorkloadSnapshot(
        workload_id=workload_id,
        host_id=host_id,
        kind=kind,
        name=name,
        status=state,
        docker_health=_parse_health(status_text),
        compose_project=project,
        compose_service=service,
        image=image,
    )


def parse_docker_ps_output(host_id: str, stdout: str) -> list[WorkloadSnapshot]:
    if not stdout.strip():
        return []

    by_id: dict[str, WorkloadSnapshot] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        snapshot = _snapshot_from_row(host_id, row)
        if snapshot is not None:
            by_id[snapshot.workload_id] = snapshot

    return list(by_id.values())


class DockerScanner:
    def discover(self, host: HostConfig, executor: SshExecutor) -> list[WorkloadSnapshot]:
        result = executor.execute(CommandTemplate.DOCKER_PS)
        if result.exit_code != 0:
            msg = f"docker ps failed on {host.id}: {result.stderr.strip()}"
            raise RuntimeError(msg)
        return parse_docker_ps_output(host.id, result.stdout)
