# Spec 11 — Worker entrypoint & scheduler

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §5, §10 |
| Author | mac-mini-dashboard |

## Context

The worker process runs **poll** (default 30s) and **audit** (default 5m) passes against configured hosts using the same `AuditPass` / `PollPass` logic as core tests.

## Functional Requirements

- **FR-1:** `WorkerScheduler` MUST run `AuditPass` on startup and whenever `audit_interval_sec` has elapsed.
- **FR-2:** `WorkerScheduler` MUST run `PollPass` on every tick.
- **FR-3:** Sleep between ticks MUST use `config.default_poll_interval_sec` unless overridden.
- **FR-4:** `run_forever` MUST accept `max_ticks` for deterministic tests.
- **FR-5:** `main` MUST load `config.yaml` and open SQLite at `DASHBOARD_DB_PATH`.
- **FR-6:** Production SSH MUST use allowlisted commands via `SubprocessSshExecutor` wrapped in `RetryingExecutor`.

## Acceptance Criteria

- **AC-11.1:** Given scheduler with zero elapsed audit time, when first tick runs, then audit and poll both execute.
- **AC-11.2:** Given audit just ran, when next tick within audit interval, then only poll runs.
- **AC-11.3:** Given audit interval elapsed, when tick runs, then audit runs again.
- **AC-11.4:** Given `max_ticks=2`, when `run_forever`, then exactly two ticks execute.
- **AC-11.5:** Given host config, when `SubprocessSshExecutor` runs `docker_ps`, then ssh invokes rendered allowlisted command.

## Defaults

| Setting | Default | Override |
|---------|---------|----------|
| Poll interval | 30s | `default_poll_interval_sec` in config |
| Audit interval | 300s (5m) | `DASHBOARD_AUDIT_INTERVAL_SEC` env |
