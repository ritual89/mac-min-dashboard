# Spec 04 — Severity Evaluation

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §4 |
| Author | mac-mini-dashboard |

## Context

Severity drives dashboard row color and Telegram alerts. Evaluation order is fixed: red conditions trump orange; green is the default.

## Functional Requirements

- **FR-1:** Severity MUST be one of `green`, `orange`, `red`.
- **FR-2:** Red MUST be assigned when any: Docker health is `unhealthy`; HTTP probe failed (if configured); log tail matches error patterns (`ERROR`, `Traceback`, `panic`, case-insensitive for `ERROR`/`panic`).
- **FR-3:** Orange MUST be assigned when: workload expected running but status is stopped/exited; restart count in last hour exceeds threshold (default 5).
- **FR-4:** Green MUST be assigned when no red or orange condition applies.
- **FR-5:** Red MUST take precedence over orange when both apply.

## Acceptance Criteria

- **AC-4.1:** Given running container with healthy status and clean logs, then severity is `green`.
- **AC-4.2:** Given Docker health `unhealthy`, then severity is `red` with reason mentioning health.
- **AC-4.3:** Given log tail containing `Traceback`, then severity is `red` with reason mentioning logs.
- **AC-4.4:** Given log tail containing `panic:`, then severity is `red`.
- **AC-4.5:** Given HTTP probe configured and probe failed, then severity is `red`.
- **AC-4.6:** Given expected running and status `exited`, then severity is `orange`.
- **AC-4.7:** Given restart_count_1h > threshold, then severity is `orange`.
- **AC-4.8:** Given unhealthy AND exited, then severity is `red` (not orange).
- **AC-4.9:** Given no probe configured and probe result absent, then probe does not contribute to red.

## Edge Cases

- **EC-4.1:** Empty log tail — no log-based red.
- **EC-4.2:** `ERROR` substring in benign text (e.g. `NO ERROR HERE`) — still red per pattern match (documented; tune patterns in v1.1).

## Out of Scope

- Muted workloads (v1.5)
- Custom regex per workload
