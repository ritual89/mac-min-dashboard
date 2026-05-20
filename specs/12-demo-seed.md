# Spec 12 — Demo database seed

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §11 (local dev without fleet SSH) |
| Author | mac-mini-dashboard |

## Context

Developers need a populated `fleet.db` to exercise the API and UI without SSH access to real hosts. Seeding replays Docker scanner fixtures through `AuditPass` and `FakeSshExecutor`.

## Functional Requirements

- **FR-1:** `seed_database` MUST run `AuditPass` with per-host fixture-backed `FakeSshExecutor`.
- **FR-2:** Default fixtures MUST ship under `packages/core/fixtures/docker/`.
- **FR-3:** `seed_database_file` MUST open (or create) SQLite at a given path and return upserted workload count.
- **FR-4:** CLI `mac-mini-seed` MUST respect `DASHBOARD_DB_PATH` and optional `DASHBOARD_CONFIG_PATH`.

## Acceptance Criteria

- **AC-12.1:** Given `ps_standalone.jsonl` and one host, when seed runs, then at least one monitored workload exists.
- **AC-12.2:** Given seed run twice, when second seed runs, then workload count unchanged.
- **AC-12.3:** Given per-host fixture map, when seed runs, then each host uses its fixture stdout.
- **AC-12.4:** Given empty db path, when `seed_database_file` runs, then db file exists and is readable.
