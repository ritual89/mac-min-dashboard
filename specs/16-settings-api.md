# Spec 16 — Settings API

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §7, §9 |
| Author | mac-mini-dashboard |

## Context

Read and update dashboard settings (Telegram notification toggles). Settings persist in SQLite `settings` table with defaults from schema init.

## Functional Requirements

- **FR-1:** `GET /api/settings` returns `{ notify_orange: bool, notify_red: bool }`.
- **FR-2:** `PATCH /api/settings` accepts partial JSON body and updates only provided keys.
- **FR-3:** Only known setting keys are accepted; unknown keys return 400.
- **FR-4:** Store exposes `get_settings()` and `update_settings(patch)` methods.

## Acceptance Criteria

- **AC-16.1:** Given default database, when GET settings, then `{ notify_orange: true, notify_red: true }`.
- **AC-16.2:** Given PATCH with `{ notify_orange: false }`, when GET settings, then notify_orange is false and notify_red is still true.
- **AC-16.3:** Given PATCH with unknown key, then 400.
- **AC-16.4:** Given PATCH with empty body, then 200 (no-op).

## Out of Scope

- Poll interval overrides via settings API (config.yaml only v1)
