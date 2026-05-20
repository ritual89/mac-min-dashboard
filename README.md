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

1. Clone/sync repo **on the Mac Mini**.
2. `uv sync --all-packages --dev`, edit `config/config.yaml`, `npm run build`.
3. **Production:** `./scripts/install-launchd.sh` — or manual: `uv run mac-mini-worker` + `uv run python -m mac_mini_api.main`.
4. From laptop on Tailscale: `http://<mac-mini-hostname>:8081`.

## Progress (v0.1 scaffold)

Shipped and covered by tests (100% branch coverage on Python packages; 100% on web `src/`):

| Area | Status | Notes |
|------|--------|--------|
| **Core** | Done | Config, SQLite store, allowlisted SSH + `FakeSshExecutor`, Docker scanner, severity, auto-promote |
| **Worker passes** | Done | `AuditPass` (discover + upsert + promote), `PollPass` (monitored severity refresh) |
| **Worker process** | Done | `mac-mini-worker` — poll every 30s, audit every 5m, subprocess SSH |
| **API** | Done | Read endpoints + workload logs; serves built SPA from `apps/web/dist` |
| **Web UI** | Done | Fleet table by host, severity dots, logs modal |
| **Demo seed** | Done | `mac-mini-seed` — populate DB from Docker fixtures (no SSH) |
| **launchd (hub)** | Done | `scripts/install-launchd.sh` — API + worker LaunchAgents |

Not yet: Telegram alerts, audit/settings UI, restart/stop controls, Paramiko (subprocess SSH only).

## Quick start (demo, no SSH)

```bash
uv sync --all-packages --dev
cd apps/web && npm install && npm run build

export DASHBOARD_DB_PATH=./data/fleet.db
uv run mac-mini-seed

uv run python -m mac_mini_api.main
# open http://127.0.0.1:8081 — fleet table shows fixture workloads (e.g. nginx)
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

Dev UI with hot reload (API must still be running on :8081):

```bash
cd apps/web && npm run dev
```

### Mac Mini hub (launchd, always-on)

After `uv sync`, config, and `npm run build`:

```bash
./scripts/install-launchd.sh
# API http://127.0.0.1:8081 — logs ~/Library/Logs/mac-mini-dashboard/
# Remove: ./scripts/install-launchd.sh --uninstall
```

Details: [`deploy/README.md`](deploy/README.md).

## Environment variables

| Variable | Default | Used by |
|----------|---------|---------|
| `DASHBOARD_CONFIG_PATH` | `config/config.yaml` (optional for seed) | Worker, seed |
| `DASHBOARD_DB_PATH` | `./data/fleet.db` | API, worker, seed |
| `DASHBOARD_PORT` | `8081` | API |
| `DASHBOARD_STATIC_DIR` | `apps/web/dist` (if dir exists) | API |
| `DASHBOARD_AUDIT_INTERVAL_SEC` | `300` | Worker |

Poll interval comes from `default_poll_interval_sec` in `config.yaml` (15–60s).

## API (read + logs)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/hosts` | Configured hosts |
| GET | `/api/workloads` | Workloads (`?monitored=true`, `host_id`, `severity`) |
| GET | `/api/workloads/{id}` | Single workload |
| GET | `/api/workloads/{id}/logs?tail=200` | Docker logs (plain text) |
| GET | `/api/audit` | Discovered, not monitored |

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
```

CI (`.github/workflows/ci.yml`) runs Python and web coverage on every push/PR.

### Repository layout

```text
packages/core/     # mac_mini_core — domain logic, store, scanners, seed, audit/poll passes
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
