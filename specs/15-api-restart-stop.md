# Spec 15 — API Restart / Stop

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §7 |
| Author | mac-mini-dashboard |

## Context

Users need to restart and stop workloads from the dashboard. Commands are dispatched via allowlisted SSH templates based on workload kind. Stop requires explicit confirmation.

## Functional Requirements

- **FR-1:** `POST /api/workloads/{id}/restart` dispatches kind-specific restart command via SSH.
- **FR-2:** `POST /api/workloads/{id}/stop?confirm=1` dispatches kind-specific stop command. Without `confirm=1`, returns 400.
- **FR-3:** Restart supports docker, compose, systemd, launchd workloads.
- **FR-4:** Stop supports docker, compose, systemd workloads. Launchd stop is out of scope v1.
- **FR-5:** Core exposes `restart_workload()` and `stop_workload()` testable with `FakeSshExecutor`.
- **FR-6:** `DOCKER_STOP` and `SYSTEMCTL_STOP` command templates added.

## Acceptance Criteria

- **AC-15.1:** Given docker workload, when POST restart, then `DOCKER_RESTART` executed, returns 200.
- **AC-15.2:** Given docker workload, when POST stop with `confirm=1`, then `DOCKER_STOP` executed, returns 200.
- **AC-15.3:** Given docker workload, when POST stop without confirm, then 400.
- **AC-15.4:** Given unknown workload id, when POST restart, then 404.
- **AC-15.5:** Given unknown workload id, when POST stop, then 404.
- **AC-15.6:** Given systemd workload, when POST restart, then `SYSTEMCTL_RESTART` executed.
- **AC-15.7:** Given launchd workload, when POST restart, then `LAUNCHCTL_KICKSTART` executed.
- **AC-15.8:** Given launchd workload, when POST stop, then 400 (unsupported).
- **AC-15.9:** Given SSH failure (nonzero exit), when restart, then 502.

## Out of Scope

- Start (create new workload)
- Cron/process restart
