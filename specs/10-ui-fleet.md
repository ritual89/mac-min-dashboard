# Spec 10 — UI Fleet View

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §8 |
| Author | mac-mini-dashboard |

## Context

Dark, dense fleet table showing monitored workloads grouped by host. Read-only except logs modal (v1).

## Functional Requirements

- **FR-1:** Default view lists monitored workloads from `GET /api/workloads?monitored=true`.
- **FR-2:** Rows grouped by `host_id` with host display heading.
- **FR-3:** Severity shown as colored indicator (green/orange/red).
- **FR-4:** Logs button opens modal; fetches `GET /api/workloads/{id}/logs?tail=200`.
- **FR-5:** API client MUST be injectable for tests.

## Acceptance Criteria

- **AC-10.1:** Given API data, fleet table renders workload name and status.
- **AC-10.2:** Given two hosts, renders two group sections.
- **AC-10.3:** Given red severity, row has `data-severity="red"`.
- **AC-10.4:** Clicking Logs calls fetchLogs with workload id.
- **AC-10.5:** Modal displays log text from API.

## Out of Scope

- Restart/stop buttons
- Audit/settings views
- Mobile card layout (v1.1)
