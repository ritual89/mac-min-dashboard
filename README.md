# mac-mini-dashboard

Tailnet-only fleet dashboard for the Mac Mini homelab: discover, monitor, and lightly control workloads across ~10 hosts.

Product plan: [`docs/PLAN.md`](docs/PLAN.md). Feature specs (acceptance criteria): [`specs/`](specs/) and [`specs/README.md`](specs/README.md).

## Dev machine vs Mac Mini hub

| | **Dev machine** (where you code) | **Mac Mini hub** (production) |
|---|----------------------------------|-------------------------------|
| **Role** | Build, test, iterate | Always-on API + worker |
| **Deploy?** | No — run processes manually | Yes — `launchd` via `./scripts/install-launchd.sh` |
| **Who SSHs to the fleet?** | Only if you run `mac-mini-worker` here for a smoke test | Worker on the Mac Mini SSHs to Vultr/other hosts |
| **Typical URL** | `http://127.0.0.1:8081` on this machine | `http://<mac-mini>:8081` over Tailscale from laptop/phone |
| **Demo (seed, no SSH)** | **Best place** — `mac-mini-seed` + API | Optional; same commands, not the main goal |
| **`install-launchd.sh`** | Do not use unless this Mac *is* the hub | **Use on the hub** |

```text
[Laptop]  ──Tailscale──►  [Mac Mini hub]  ──SSH──►  [vultr-1, other hosts…]
              browser              API :8081
                                   worker (poll/audit)
```

### On this dev machine (interactive test)

```bash
uv sync --all-packages --dev
cd apps/web && npm ci && npm run build

export DASHBOARD_DB_PATH=./data/fleet.db
uv run mac-mini-seed
uv run python -m mac_mini_api.main
# open http://127.0.0.1:8081
```

Optional: `cd apps/web && npm run dev` with API on 8081.

### On the Mac Mini hub (real deploy)

1. **Commit and push** from dev machine (cathedral); **git pull** on the Mac Mini.
2. Edit `config/config.yaml` on the hub (SSH aliases, fleet hosts).
3. **One command on the hub:** `./scripts/deploy-hub.sh` — syncs deps, checks SSH+Docker on each host, builds UI, installs launchd. Use `--install-docker` on macOS hosts missing Docker (Colima via Homebrew over SSH).
4. From laptop on Tailscale: `http://<mac-mini-hostname>:8081`.

Details: [`deploy/README.md`](deploy/README.md). Step-by-step runbook: [`docs/runbooks/mac-mini-hub-deploy.md`](docs/runbooks/mac-mini-hub-deploy.md).

## Progress (v0.1 scaffold)

Shipped and covered by tests (100% branch coverage on Python packages; 100% on web `src/`):

| Area | Status | Notes |
|------|--------|--------|
| **Core** | Done | Config, SQLite store, allowlisted SSH + `FakeSshExecutor`, Docker scanner, severity, auto-promote |
| **Scanners** | Done | Docker, systemd, launchd, cron — OS-dispatched via `AuditPass` |
| **Worker passes** | Done | `AuditPass` (multi-scanner discover + upsert + promote), `PollPass` (severity refresh + log tail + restart count + Telegram alerts) |
| **Worker process** | Done | `mac-mini-worker` — poll every 30s, audit every 5m, subprocess SSH |
| **Pin / Unpin API** | Done | `POST/DELETE /api/workloads/{id}/pin` — manual promote/demote |
| **Restart / Stop API** | Done | `POST /api/workloads/{id}/restart`, `POST /api/workloads/{id}/stop?confirm=1` — kind-aware SSH dispatch |
| **Settings API** | Done | `GET/PATCH /api/settings` — Telegram notification toggles |
| **Telegram alerts** | Done | `TelegramNotifier` + `should_alert()` with severity transition detection, debounce, alert history |
| **API** | Done | Read, control, settings endpoints; serves built SPA from `apps/web/dist` |
| **Web UI** | Done | Fleet table (expandable rows with inline logs, restart/stop), Audit view (pin), All Workloads (sortable flat table), Settings (toggle switches), nav tabs, mobile cards — Midjourney "bioluminescent terminal" theme, Tailwind v4, JetBrains Mono |
| **Demo seed** | Done | `mac-mini-seed` — populate DB from Docker fixtures (no SSH) |
| **launchd (hub)** | Done | `scripts/install-launchd.sh` — API + worker LaunchAgents |
| **Hub production (mac-mini)** | Done | `~/dev/mac-mini-dashboard` on hub; launchd API+worker; 3 Docker workloads monitored (2026-05-20) |
| **Test coverage audit** | Done | 100% Python + web gates; `deploy/preflight` tested; CI includes worker cov; SQLite stores auto-closed in tests |
| **Docs** | Done | SSH onboarding checklist (`docs/ssh-onboarding.md`), smoke test script (`scripts/smoke-test.sh`) |

Not yet: Paramiko (subprocess SSH only), HTTP probe config UI, start workload command.

## Quick start (demo, no SSH)

```bash
uv sync --all-packages --dev
cd apps/web && npm ci && npm run build

export DASHBOARD_DB_PATH=./data/fleet.db
uv run mac-mini-seed

uv run python -m mac_mini_api.main
# open http://127.0.0.1:8081 — fleet table shows fixture workloads (e.g. nginx)
# If you see JSON {"detail":"Not Found"} at /, the UI was not built — rerun npm run build and restart the API
```

Uses built-in demo host `mac-mini` and `packages/core/fixtures/docker/`. Optional: set `DASHBOARD_CONFIG_PATH` to seed against your `config.yaml` hosts (fixture map: `mac-mini` → `ps_standalone.jsonl`, `vultr-1` → `ps_compose.jsonl`).

## Quick start (real fleet over SSH)

```bash
uv sync --all-packages --dev
cp config/config.yaml.example config/config.yaml
cp .env.example .env
cd apps/web && npm install && npm run build

export DASHBOARD_CONFIG_PATH=config/config.yaml
export DASHBOARD_DB_PATH=./data/fleet.db

# terminal 1 — worker (populates DB from fleet over SSH)
uv run mac-mini-worker

# terminal 2 — API + UI
uv run python -m mac_mini_api.main
# open http://127.0.0.1:8081
```

One-shot worker smoke (no long loop):

```bash
uv run python -c "from mac_mini_worker.main import run_worker; run_worker(max_ticks=1)"
```

### SSH config must match what works in your terminal

If `ssh mac-mini` works but the worker shows `Permission denied (publickey)`, the dashboard was probably using the wrong **user** or **key**. Interactive SSH uses `~/.ssh/config`; the worker used explicit `ssh -i … user@host`, and `user@host` overrides the config `User` line.

**Discover values** (same machine you run the worker from):

```bash
ssh -G mac-mini | egrep '^(user|hostname|identityfile) '
```

**Recommended** in `config/config.yaml`: set `ssh_host` to your config `Host` name (e.g. `mac-mini`) so the worker runs `ssh mac-mini '…'` — same as your shell. Keep `ssh_user` / `ssh_key_path` for the DB; they are ignored when `ssh_host` is set.

**Hub polls itself:** On the Mac Mini, `~/.ssh/config` needs a `Host mac-mini` entry (e.g. `HostName 127.0.0.1`, `IdentityFile ~/.ssh/id_ed25519`) and that public key in `~/.ssh/authorized_keys`. Cathedral’s key alone is not enough for loopback SSH from the worker.

**Alternative** (no `ssh_host`): set `ssh_user` and `ssh_key_path` to match `ssh -G`, and use `tailscale_host` as the hostname (not necessarily the config alias).

### Docker over SSH (macOS / Homebrew)

Docker is **not** installed per-project. The worker only needs the SSH user in `config.yaml` to run `docker ps` on that host (Colima, Docker Desktop, compose stacks, etc. are all fine).

If SSH works but you see `command not found: docker`, Docker is often already installed under Homebrew (`/opt/homebrew/bin/docker`) while **non-interactive SSH** uses a minimal `PATH` (`/usr/bin:/bin`) that omits Homebrew. That is not a missing engine and you usually should **not** run `./scripts/deploy-hub.sh --install-docker` on a host that already has Colima or Desktop.

The worker and [`scripts/preflight_fleet.py`](scripts/preflight_fleet.py) prepend `/opt/homebrew/bin` and `/usr/local/bin` on macOS hosts before allowlisted `docker` commands.

**Verify** (same paths as production — from the machine that runs the worker):

```bash
ssh -G mac-mini | egrep '^(user|hostname|identityfile) '
uv run python scripts/preflight_fleet.py
uv run python -c "from mac_mini_worker.main import run_worker; run_worker(max_ticks=1)"
```

If preflight still fails, test with the full CLI path on the host: `ssh mac-mini '/opt/homebrew/bin/docker ps'`. Optional fix on the server: add Homebrew to `~/.zshenv` for the SSH user so any non-interactive session sees `docker`.

Dev UI with hot reload (API must still be running on :8081):

```bash
cd apps/web && npm run dev
```

### Mac Mini hub (launchd, always-on)

Runbook: [`docs/runbooks/mac-mini-hub-deploy.md`](docs/runbooks/mac-mini-hub-deploy.md).

```bash
./scripts/deploy-hub.sh
# API http://127.0.0.1:8081 — logs ~/Library/Logs/mac-mini-dashboard/
# Remove: ./scripts/install-launchd.sh --uninstall
```

## Environment variables

| Variable | Default | Used by |
|----------|---------|---------|
| `DASHBOARD_CONFIG_PATH` | `config/config.yaml` (required for API logs) | Worker, API, seed |
| `DASHBOARD_DB_PATH` | `./data/fleet.db` | API, worker, seed |
| `DASHBOARD_PORT` | `8081` | API |
| `DASHBOARD_STATIC_DIR` | `apps/web/dist` (if dir exists) | API |
| `DASHBOARD_AUDIT_INTERVAL_SEC` | `300` | Worker |
| `TELEGRAM_BOT_TOKEN` | _(empty — disabled)_ | Worker |
| `TELEGRAM_CHAT_ID` | _(empty — disabled)_ | Worker |
| `DASHBOARD_URL` | _(empty)_ | Worker (included in Telegram messages) |

Poll interval comes from `default_poll_interval_sec` in `config.yaml` (15–60s).

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/hosts` | Configured hosts |
| GET | `/api/workloads` | Workloads (`?monitored=true`, `host_id`, `severity`) |
| GET | `/api/workloads/{id}` | Single workload |
| GET | `/api/workloads/{id}/logs?tail=200` | Docker logs (plain text) |
| GET | `/api/audit` | Discovered, not monitored |
| POST | `/api/workloads/{id}/pin` | Pin (promote to monitored) |
| DELETE | `/api/workloads/{id}/pin` | Unpin (re-evaluate auto-promote) |
| POST | `/api/workloads/{id}/restart` | Restart workload via SSH |
| POST | `/api/workloads/{id}/stop?confirm=1` | Stop workload (requires confirm) |
| GET | `/api/settings` | Notification settings |
| PATCH | `/api/settings` | Update notification settings |

## Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node 20+ (for `apps/web`)

### Setup

```bash
uv sync --all-packages --dev
cp config/config.yaml.example config/config.yaml
cp .env.example .env
cd apps/web && npm install
```

### Test-driven workflow

Strict TDD: **spec → failing test (RED) → minimal impl (GREEN) → refactor**. Tests reference acceptance criteria from `specs/` (e.g. `# AC-4.2`).

```bash
# Python: core + API + worker (100% branch coverage gate)
uv run pytest --cov=mac_mini_core --cov=mac_mini_api --cov=mac_mini_worker --cov-branch --cov-report=term-missing

# Web UI (100% coverage gate on src/, excludes main.tsx)
cd apps/web && npm run test:coverage

# Mutation testing (core logic; optional — not in CI yet)
uv run mutmut run --CI

Python tests use root `conftest.py` to close SQLite stores after each test (avoids ResourceWarning noise).
```

CI (`.github/workflows/ci.yml`) runs Python (`mac_mini_core`, `mac_mini_api`, `mac_mini_worker`) and web coverage on every push/PR.

### Repository layout

```text
packages/core/     # mac_mini_core — domain logic, store, scanners, seed, audit/poll passes
packages/core/src/mac_mini_core/deploy/  # fleet preflight helpers (used by scripts/preflight_fleet.py)
packages/core/fixtures/docker/  # shipped JSONL for mac-mini-seed
apps/api/          # mac_mini_api — FastAPI (:8081), static SPA
apps/worker/       # mac_mini_worker — scheduler + subprocess SSH
apps/web/          # Vite/React fleet UI
specs/             # FR/AC specs (01–13); tests cite AC numbers
config/            # config.yaml.example
data/              # fleet.db (gitignored; created at runtime)
deploy/launchd/    # LaunchAgent plist templates
scripts/           # install-launchd.sh
```

## Default persona: Solo Founder

Every Cursor session in this repo uses the **Solo Founder** persona by default (pragmatic, time-aware, anti–scope-creep). Adapted from [agents/personas/solo-founder.md](https://github.com/alirezarezvani/claude-skills/blob/main/agents/personas/solo-founder.md).

| File | Role |
|------|------|
| `.cursor/rules/solo-founder.mdc` | Always-on rule (`alwaysApply: true`) |
| `.cursor/agents/solo-founder.md` | Full persona reference |
| `.cursor/rules/readme-on-ship.mdc` | Update README when shipping a slice |

To disable temporarily, turn off the rule in Cursor Settings → Rules, or set `alwaysApply: false` in the `.mdc` file.

## Skills

Engineering-focused curated set (not the full 313-skill library):

- `engineering-team/` — core engineering roles (architecture, frontend, backend, DevOps, QA, security, etc.)
- `engineering/` — advanced engineering (CI/CD, observability, RAG, MCP, reliability, etc.)

Upstream pin: **v2.8.0** (see `skills.lock.json`). Currently **129** skills installed.

### Install or refresh skills

```bash
./scripts/install-skills.sh
```

Requires `git`. Clones upstream into `vendor/claude-skills/` (gitignored) and copies skills into `.cursor/skills/`.

### Verify

```bash
find .cursor/skills -name SKILL.md | wc -l
python3 .cursor/skills/*/scripts/*.py --help 2>/dev/null | head -1 || true
```

In Cursor, open this folder; skills under `.cursor/skills/` load automatically for the project.

## License

Application code: TBD. Bundled skills follow the upstream [MIT license](https://github.com/alirezarezvani/claude-skills/blob/main/LICENSE).
