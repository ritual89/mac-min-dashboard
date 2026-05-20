# Spec 08 — API Control (logs v1)

| Field | Value |
|-------|-------|
| Status | **Approved** (logs only) |
| Source | PLAN.md §7 |
| Author | mac-mini-dashboard |

## Context

On-demand log fetch for the UI logs modal. Restart/stop deferred to v1.1.

## Functional Requirements

- **FR-1:** `GET /api/workloads/{id}/logs?tail=N` returns plain-text log body (default 200, max 10000).
- **FR-2:** Only `docker` and `compose` workloads support logs.
- **FR-3:** Logs MUST be fetched via allowlisted `DOCKER_LOGS` SSH command.
- **FR-4:** `fetch_workload_logs` in core MUST be testable with `FakeSshExecutor`.

## Acceptance Criteria

- **AC-8.1:** Given docker workload, when logs requested, then `DOCKER_LOGS` executed with container name and tail.
- **AC-8.2:** Given successful stdout, API returns 200 with `text/plain` body.
- **AC-8.3:** Given unknown workload id, returns 404.
- **AC-8.4:** Given systemd workload, returns 400 unsupported.
- **AC-8.5:** Given SSH failure (nonzero exit), returns 502.

## Out of Scope (v1.1)

- POST restart/stop
- pin/unpin API
