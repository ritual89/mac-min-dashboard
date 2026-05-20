# Spec 06 — Worker Audit Pass

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §5, §10 |
| Author | mac-mini-dashboard |

## Context

The worker runs periodic passes over configured hosts. The **audit pass** discovers workloads via scanners, upserts inventory, and applies auto-promote rules. Poll pass (status refresh for monitored only) is a follow-up.

## Functional Requirements

- **FR-1:** `AuditPass.run(config, store, executor_factory)` MUST iterate all hosts in config.
- **FR-2:** Each host MUST be scanned with `DockerScanner.discover`.
- **FR-3:** Discovered snapshots MUST be upserted into SQLite (`workloads` + `workload_state`).
- **FR-4:** After upsert, `should_promote` MUST set `monitored=1` when rules match (and respect existing pin).
- **FR-5:** Workloads not seen in a pass MUST remain in DB (no deletion v1).
- **FR-6:** `executor_factory(host)` supplies per-host `SshExecutor` (enables `FakeSshExecutor` in tests).

## Acceptance Criteria

- **AC-6.1:** Given one host and docker fixture, when audit runs, then one workload row exists.
- **AC-6.2:** Given docker container, when audit runs, then `monitored=1` on workload row.
- **AC-6.3:** Given two hosts, when audit runs, then workloads tagged with correct `host_id`.
- **AC-6.4:** Given second audit with same data, when audit runs, then row count unchanged (upsert idempotent).
- **AC-6.5:** Given compose fixture under project root config, when audit runs, then workload is monitored.

## Poll Pass (extension)

- **FR-7:** `PollPass.run(config, store, executor_factory)` MUST update only `monitored=1` workloads.
- **FR-8:** Matching container in `docker ps` output MUST refresh `status`, `severity`, `severity_reason`, `last_seen`.
- **FR-9:** Monitored workload missing from `docker ps` MUST set `status=missing` and severity `orange`.
- **FR-10:** Severity MUST use `evaluate_severity` from snapshot fields (health, status).

### Poll Acceptance Criteria

- **AC-6.6:** Given monitored running healthy container, after poll `severity=green`.
- **AC-6.7:** Given monitored workload not in docker ps, after poll `severity=orange` and `status=missing`.
- **AC-6.8:** Given unhealthy status in fixture, after poll `severity=red`.
- **AC-6.9:** Given unmonitored workload, poll MUST NOT change its state.

## Out of Scope

- Telegram
- Deleting stale workloads
- Log tail fetch on poll
