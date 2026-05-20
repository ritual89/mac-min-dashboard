# Spec 02 — SSH Executor

| Field | Value |
|-------|-------|
| Status | **Approved** |
| Source | PLAN.md §6 |
| Author | mac-mini-dashboard |

## Context

All remote inspection and control flows through SSH using allowlisted command templates. Arbitrary shell from API or worker is forbidden — compromise of the dashboard must not become arbitrary code execution on fleet hosts.

## Functional Requirements

- **FR-1:** Commands MUST be selected from a fixed allowlist of templates; free-form shell strings MUST NOT be accepted.
- **FR-2:** Template parameters (container name, unit name, tail line count) MUST be validated; shell metacharacters MUST be rejected.
- **FR-3:** Execution MUST honor a configurable timeout (default 30s).
- **FR-4:** Transient failures MUST retry with exponential backoff (max 3 attempts).
- **FR-5:** A `FakeSshExecutor` MUST exist for tests, recording invocations without network I/O.
- **FR-6:** Non-interactive SSH MUST prepend an OS-appropriate `PATH` export before allowlisted commands (Homebrew on macOS, `/usr/local/bin` and `/snap/bin` on Linux).

## Allowlisted Commands

| Template | Rendered example |
|----------|------------------|
| `docker_ps` | `docker ps --format '{{json .}}'` |
| `docker_inspect` | `docker inspect {name}` |
| `docker_logs` | `docker logs --tail {n} {name}` |
| `docker_restart` | `docker restart {name}` |
| `systemctl_is_active` | `systemctl is-active {unit}` |
| `systemctl_restart` | `systemctl restart {unit}` |
| `journalctl_unit` | `journalctl -u {unit} -n {n} --no-pager` |
| `launchctl_list` | `launchctl list` |
| `launchctl_kickstart` | `launchctl kickstart -k {label}` |
| `log_show_last` | `log show --last {duration} --style compact` |
| `crontab_list` | `crontab -l` |

## Acceptance Criteria

- **AC-2.1:** Given each allowlisted template with valid args, when rendered, then output matches expected shell string.
- **AC-2.2:** Given args containing `;`, `|`, `` ` ``, `$`, `&`, when render attempted, then `CommandValidationError` is raised.
- **AC-2.3:** Given unknown template id, when render attempted, then `UnknownCommandError` is raised.
- **AC-2.4:** Given `FakeSshExecutor`, when execute called, then command is recorded and canned stdout returned.
- **AC-2.5:** Given executor with retry policy, when first two attempts raise timeout and third succeeds, then result is returned and three attempts recorded.
- **AC-2.6:** Given executor with retry policy, when all attempts fail, then `SshExecutionError` is raised.
- **AC-2.7:** Given `wrap_remote_command` with Darwin or Linux `HostOS`, when called, then the rendered remote command prefixes the command with the matching `PATH` export and preserves the original command body.

## Edge Cases

- **EC-2.1:** Empty container/unit name — reject.
- **EC-2.2:** `tail` / journal line count ≤ 0 or > 10000 — reject.
- **EC-2.3:** `log show` duration must match `^\d+[smhd]$` — reject otherwise.

## Out of Scope

- Connection pooling (v1.1)
- asyncssh migration
- SSH key generation
