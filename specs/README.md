# Specs index

Each spec defines **functional requirements (FR-*)** and **acceptance criteria (AC-*)** in Given/When/Then form. Tests in `packages/core/tests/` reference AC numbers in docstrings.

| Spec | Status | Tests |
|------|--------|-------|
| [01-config-and-schema.md](01-config-and-schema.md) | Approved | `test_config.py`, `test_db.py` |
| [02-ssh-executor.md](02-ssh-executor.md) | Approved | `test_ssh_commands.py`, `test_ssh_executor.py` |
| [04-severity.md](04-severity.md) | Approved | `test_severity.py` |
| [05-auto-promote.md](05-auto-promote.md) | Approved | `test_promote.py` |
| [03-docker-scanner.md](03-docker-scanner.md) | Approved | `test_docker_scanner.py` |
| [06-worker-poll.md](06-worker-poll.md) | Approved (audit + poll) | `test_worker_audit.py`, `test_worker_poll.py` |
| [07-api-read.md](07-api-read.md) | Approved | `apps/api/tests/test_api_read.py` |
| [08-api-control.md](08-api-control.md) | Approved (logs) | `apps/api/tests/test_api_logs.py` |
| [10-ui-fleet.md](10-ui-fleet.md) | Approved | `apps/web/tests/` |
| [11-worker-entrypoint.md](11-worker-entrypoint.md) | Approved | `apps/worker/tests/` |
| [12-demo-seed.md](12-demo-seed.md) | Approved | `test_seed.py` |
| [13-launchd-deploy.md](13-launchd-deploy.md) | Approved | `deploy/tests/test_launchd_plists.py` |

**Iron law:** no production code without a failing test derived from an AC.

Pending specs (next TDD cycles): `09-telegram`, API restart/stop, audit/settings UI.
