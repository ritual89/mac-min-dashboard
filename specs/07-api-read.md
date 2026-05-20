# Spec 07 — API Read Endpoints

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §7 |
| Author | mac-mini-dashboard |

## Context

FastAPI exposes fleet state from SQLite for the UI. v1 is read-only (no restart/logs yet).

## Functional Requirements

- **FR-1:** `GET /api/hosts` returns configured hosts with `last_seen` from latest workload state.
- **FR-2:** `GET /api/workloads` supports query filters: `monitored` (bool), `host_id`, `severity`.
- **FR-3:** `GET /api/workloads/{id}` returns 404 when missing, else workload + state + metadata.
- **FR-4:** `GET /api/audit` returns workloads where `monitored=false`.
- **FR-5:** App factory `create_app(store)` MUST accept injected store for tests.

## Acceptance Criteria

- **AC-7.1:** Given seeded DB, `GET /api/hosts` returns host with `last_seen`.
- **AC-7.2:** Given monitored workload, `GET /api/workloads?monitored=true` includes it; `monitored=false` excludes it.
- **AC-7.3:** Given `host_id` filter, only matching workloads returned.
- **AC-7.4:** Given `severity=red` filter, only red workloads returned.
- **AC-7.5:** `GET /api/workloads/{id}` returns 404 for unknown id.
- **AC-7.6:** `GET /api/audit` returns only unmonitored workloads.

## Out of Scope

- POST restart/stop, logs, pin, settings PATCH
