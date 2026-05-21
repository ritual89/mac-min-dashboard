# Spec 14 — Pin / Unpin API

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §7 |
| Author | mac-mini-dashboard |

## Context

Users need to manually promote discovered workloads to monitored (pin) and demote them back (unpin). Pinned workloads remain monitored regardless of auto-promote rules. Unpinning re-evaluates auto-promote to decide if the workload stays monitored.

## Functional Requirements

- **FR-1:** `POST /api/workloads/{id}/pin` sets `pinned=1` and `monitored=1`.
- **FR-2:** `DELETE /api/workloads/{id}/pin` sets `pinned=0` and re-evaluates `monitored` via `should_promote()`.
- **FR-3:** Both endpoints return 404 when workload id does not exist.
- **FR-4:** Pin is idempotent — pinning an already-pinned workload succeeds with no change.
- **FR-5:** Store exposes `pin_workload(id)` and `unpin_workload(id, rules)` methods.

## Acceptance Criteria

- **AC-14.1:** Given a discovered (unmonitored) workload, when POST pin, then workload becomes pinned and monitored, returns 200.
- **AC-14.2:** Given a pinned Docker workload, when DELETE pin, then pinned=false but monitored=true (Docker auto-promotes).
- **AC-14.3:** Given a pinned non-auto-promotable workload, when DELETE pin, then pinned=false and monitored=false.
- **AC-14.4:** Given unknown workload id, when POST pin, then 404.
- **AC-14.5:** Given unknown workload id, when DELETE pin, then 404.
- **AC-14.6:** Given already-pinned workload, when POST pin, then 200 (idempotent).

## Out of Scope

- Bulk pin/unpin
- Muted state (v1.5)
