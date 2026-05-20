# Spec 03 — Docker Scanner

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §5 |
| Author | mac-mini-dashboard |

## Context

The Docker scanner discovers containers on a host via SSH (`docker ps --format '{{json .}}'`), producing stable `WorkloadSnapshot` rows for audit and poll passes.

## Functional Requirements

- **FR-1:** `DockerScanner.discover(host, executor)` MUST return `list[WorkloadSnapshot]`.
- **FR-2:** Discovery MUST use only the allowlisted `DOCKER_PS` command via `SshExecutor`.
- **FR-3:** Standalone containers MUST use `kind=docker` and `workload_id=docker:<host_id>:<name>`.
- **FR-4:** Compose containers MUST use `kind=compose` and `workload_id=compose:<host_id>:<project>:<service>` when `com.docker.compose.project` and `com.docker.compose.service` labels exist.
- **FR-5:** Container `name` MUST strip a leading `/` from Docker `Names` field.
- **FR-6:** `status` MUST map from Docker `State` field (lowercase).
- **FR-7:** `docker_health` MUST be parsed from `Status` when it contains `(healthy)` or `(unhealthy)`; otherwise `None`.
- **FR-8:** Discovery MUST be idempotent: duplicate `workload_id` in one pass deduped (last wins).
- **FR-9:** Empty or whitespace-only SSH stdout MUST return `[]`.
- **FR-10:** Malformed JSON lines MUST be skipped (not fail entire discover).

## Acceptance Criteria

- **AC-3.1:** Given one standalone running container in fixture output, when discover runs, then one snapshot with `kind=docker` and correct `workload_id`.
- **AC-3.2:** Given container with compose labels, when discover runs, then `kind=compose` and `workload_id` includes project and service.
- **AC-3.3:** Given same fixture twice, when discover runs twice, then equal snapshot lists.
- **AC-3.4:** Given empty docker ps output, when discover runs, then `[]`.
- **AC-3.5:** Given executor history, when discover runs, then exactly one `DOCKER_PS` command executed.
- **AC-3.6:** Given status `Up 2 hours (healthy)`, when discover runs, then `docker_health=healthy`.
- **AC-3.7:** Given state `exited`, when discover runs, then `status=exited`.
- **AC-3.8:** Given two containers same name in output (duplicate ids), when discover runs, then one snapshot returned.

## Edge Cases

- **EC-3.1:** Missing `Names` field — skip line.
- **EC-3.2:** Compose project without service label — treat as `docker` kind.

## Out of Scope

- `docker inspect` (poll pass)
- Restart counts
- Non-Docker runtimes
