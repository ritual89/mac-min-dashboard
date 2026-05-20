# Spec 01 — Config and Schema

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §2, §10 |
| Author | mac-mini-dashboard |

## Context

The hub loads static host inventory from `config.yaml` and persists discovered workload state in SQLite. Configuration must validate at startup so misconfiguration fails fast.

## Functional Requirements

- **FR-1:** The system MUST load `config.yaml` from a configurable path (default `./config/config.yaml`).
- **FR-2:** Each host MUST have `id`, `display_name`, `tailscale_host`, `ssh_user`, `ssh_key_path`, and `os` (`darwin` \| `linux`).
- **FR-3:** Host `poll_interval_sec` MAY override the default 30s; valid range 15–60 inclusive.
- **FR-4:** SQLite MUST initialize tables: `hosts`, `workloads`, `workload_state`, `settings`.
- **FR-5:** Settings MUST support keys `notify_orange` and `notify_red` (default `true`).

## Acceptance Criteria

### Config

- **AC-1.1:** Given a valid `config.yaml`, when loaded, then all hosts are parsed with correct types.
- **AC-1.2:** Given `poll_interval_sec` outside 15–60, when loaded, then validation error is raised.
- **AC-1.3:** Given missing required host field, when loaded, then validation error is raised.
- **AC-1.4:** Given invalid `os` value, when loaded, then validation error is raised.

### Schema

- **AC-1.5:** Given empty database, when schema init runs, then all four tables exist.
- **AC-1.6:** Given schema init, when default settings queried, then `notify_orange` and `notify_red` are `true`.

## Edge Cases

- **EC-1.1:** Empty hosts list — valid (fleet starts empty).
- **EC-1.2:** Duplicate host `id` — MUST reject at config load.

## Out of Scope

- UI editing of `config.yaml`
- Multi-file config merge
