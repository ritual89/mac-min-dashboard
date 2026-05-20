# Spec 13 — macOS launchd deploy

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §12, deploy hub |
| Author | mac-mini-dashboard |

## Context

The Mac Mini hub runs API and worker as per-user **LaunchAgents** (not Docker). Templates live in-repo; install script renders paths and loads services.

## Functional Requirements

- **FR-1:** Provide `com.macmin.dashboard.api.plist` and `com.macmin.dashboard.worker.plist` templates.
- **FR-2:** `scripts/install-launchd.sh` MUST substitute `REPO_ROOT`, `PYTHON`, `LOG_DIR`, and install to `~/Library/LaunchAgents/`.
- **FR-3:** Services MUST set `DASHBOARD_CONFIG_PATH`, `DASHBOARD_DB_PATH`, and API `DASHBOARD_PORT=8081`.
- **FR-4:** `KeepAlive` + `RunAtLoad` MUST be enabled; stdout/stderr logged under `~/Library/Logs/mac-mini-dashboard/`.
- **FR-5:** Install script MUST support `--uninstall` (bootout + remove plists).

## Acceptance Criteria

- **AC-13.1:** Rendered API plist `ProgramArguments` ends with `mac_mini_api.main` module execution.
- **AC-13.2:** Rendered worker plist invokes `mac-mini-worker` from the repo venv.
- **AC-13.3:** Both plists set `WorkingDirectory` to repo root.
- **AC-13.4:** `render_launchd_plist` rejects unknown placeholders.
