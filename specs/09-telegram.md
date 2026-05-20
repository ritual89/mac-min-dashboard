# Spec 09 — Telegram Notifier

| Field | Value |
|-------|-------|
| Status | **Pending** (v1.1) |
| Source | PLAN.md §9 |
| Author | mac-mini-dashboard |

## Context

Worker sends Telegram messages on severity transitions with debounce. Settings API persists notify toggles.

## Functional Requirements

- **FR-1:** `.env` provides `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
- **FR-2:** Worker sends on severity **transition** (not every poll).
- **FR-3:** Debounce: same workload max one message per 15 minutes unless severity is red.
- **FR-4:** Message includes host, workload name, severity, one-line reason, dashboard URL.
- **FR-5:** Settings persist `{ notify_orange, notify_red }` in SQLite.

## Acceptance Criteria

- **AC-9.1:** Given orange transition and `notify_orange=true`, when worker evaluates, then Telegram API called once.
- **AC-9.2:** Given orange transition and `notify_orange=false`, when worker evaluates, then no Telegram call.
- **AC-9.3:** Given repeated orange polls within 15 minutes, when worker evaluates, then at most one message sent.
- **AC-9.4:** Given red transition, when `notify_red=true`, then message sent even if orange was debounced.

## Out of Scope (v1)

- Implementation (spec documents intent only until v1.1 slice).
