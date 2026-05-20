# Runbook: Mac Mini hub deploy and test

| Field | Value |
|-------|--------|
| **Service** | mac-mini-dashboard (API :8081 + worker) |
| **Environment** | Mac Mini homelab hub (production) |
| **Owner** | Solo / homelab |
| **Last validated** | 2026-05-20 |
| **Repo** | https://github.com/ritual89/mac-mini-dashboard |

## Purpose

Deploy the fleet dashboard on the **Mac Mini hub**: sync code, verify fleet SSH/Docker, build the UI, install `launchd` agents, and confirm end-to-end behavior before using Tailscale from a laptop.

## Architecture (who runs what)

```text
[Cathedral / dev]     commit + push only (optional smoke)
[Mac Mini hub]        git pull, config, deploy-hub.sh, launchd, local tests
[Laptop / phone]      browser → http://<mac-mini>:8081 over Tailscale

[Mac Mini worker] ──SSH──► [each host in config.yaml]  →  docker ps / logs
```

The worker SSHs **from the Mac Mini** to every host in `config/config.yaml`. SSH config and keys on the **Mini** must work for `ssh <ssh_host>` on that machine—not only on your dev laptop.

## Prerequisites (Mac Mini, one-time)

| Requirement | Check |
|-------------|--------|
| Python 3.12+ | `python3 --version` |
| [uv](https://docs.astral.sh/uv/) | `uv --version` |
| Node 20+ | `node --version` |
| git | `git --version` |
| Tailscale on hub | Mini reachable on tailnet |
| Repo cloned | `~/dev/mac-mini-dashboard` (adjust path below) |
| `~/.ssh/config` on **hub** | `ssh -G mac-mini` shows expected user/key |
| Docker on **polled** hosts | Colima/Homebrew/etc.; not a repo install |

**SSH smoke on the Mini** (must pass before deploy):

```bash
ssh -G mac-mini | egrep '^(user|hostname|identityfile) '
ssh -o BatchMode=yes mac-mini 'whoami; /opt/homebrew/bin/docker ps --format "{{.Names}}" | head -3'
```

**Expected:** correct user (e.g. `headlessroboto`), container names listed.  
**Do not** use `./scripts/deploy-hub.sh --install-docker` if Docker/Colima is already running.

**Hub loopback (one-time):** The worker SSHs from the Mini to `ssh_host` (often `mac-mini`). On the hub itself, add `Host mac-mini` → `127.0.0.1` in `~/.ssh/config` and append `~/.ssh/id_ed25519.pub` to `~/.ssh/authorized_keys` if loopback `ssh mac-mini` fails with `Permission denied`.

---

## Phase 0 — Dev machine (optional)

Confirm latest code is on GitHub:

```bash
cd ~/dev/mac-mini-dashboard
git pull
uv run pytest -q
```

Cathedral smoke does **not** replace hub SSH checks.

---

## Phase 1 — First-time clone on Mac Mini

Skip if repo already exists.

```bash
mkdir -p ~/dev
cd ~/dev
git clone https://github.com/ritual89/mac-mini-dashboard.git
cd mac-mini-dashboard
```

---

## Phase 2 — Config on Mac Mini

### 2.1 Pull latest (every deploy)

```bash
cd ~/dev/mac-mini-dashboard
git pull
```

Minimum commit: `951916e` (ssh_host, Homebrew PATH, deploy scripts).

### 2.2 Create or update `config/config.yaml`

```bash
cp -n config/config.yaml.example config/config.yaml
```

Edit to match **hub** `ssh -G` output, for example:

```yaml
hosts:
  - id: mac-mini
    display_name: Mac Mini Hub
    tailscale_host: mac-mini
    ssh_host: mac-mini
    ssh_user: headlessroboto
    ssh_key_path: ~/.ssh/id_ed25519
    os: darwin
```

- **`ssh_host`:** `~/.ssh/config` `Host` name (recommended).
- **`ssh_user` / `ssh_key_path`:** stored in DB; ignored for SSH when `ssh_host` is set.

Add other fleet hosts when ready; each must pass preflight from the Mini.

### 2.3 Optional environment file

```bash
cp -n .env.example .env
```

Telegram is not required for v0.1.

---

## Phase 3 — Deploy

Run **on the Mac Mini only**:

```bash
cd ~/dev/mac-mini-dashboard
./scripts/deploy-hub.sh
```

| Step | What it does |
|------|----------------|
| 1 | `uv sync --all-packages --dev` |
| 2 | `scripts/preflight_fleet.py` — SSH + `docker ps` per host |
| 3 | `npm ci && npm run build` → `apps/web/dist` |
| 4 | `scripts/install-launchd.sh` — API + worker LaunchAgents |

**Flags:**

| Flag | When |
|------|------|
| `--install-docker` | macOS host has **no** Docker engine (installs Colima via Homebrew over SSH) |
| `--skip-fleet-preflight` | Iterating on UI/launchd only |
| `--skip-web-build` | UI already built |

**Logs after install:** `~/Library/Logs/mac-mini-dashboard/{api,worker}.{log,err}`

### Phase 3 — Failure recovery

| Symptom | Action |
|---------|--------|
| `Permission denied (publickey)` | Fix hub `~/.ssh/config` / keys; set `ssh_host` in config |
| `command not found: docker` | Start Colima; confirm `/opt/homebrew/bin/docker ps` over SSH |
| Missing `config.yaml` | `cp config/config.yaml.example config/config.yaml` |
| Web build fails | Install Node 20+; `(cd apps/web && npm ci && npm run build)` |

Re-run partial steps:

```bash
uv run python scripts/preflight_fleet.py
./scripts/install-launchd.sh
```

---

## Phase 4 — Test (in order)

### 4.1 Fleet preflight

```bash
cd ~/dev/mac-mini-dashboard
uv run python scripts/preflight_fleet.py
```

**Pass:** `OK <host-id> (...)` for each host; `Fleet preflight passed`.

### 4.2 One worker tick (populate DB)

```bash
export DASHBOARD_CONFIG_PATH=config/config.yaml
export DASHBOARD_DB_PATH=./data/fleet.db
uv run python -c "from mac_mini_worker.main import run_worker; run_worker(max_ticks=1)"
```

**Pass:** exits 0, no traceback.

### 4.3 Manual API + UI (optional)

```bash
uv run python -m mac_mini_api.main
```

Open **http://127.0.0.1:8081** on the Mini.

| Check | Pass |
|-------|------|
| Fleet table | Hosts and workloads visible |
| `/` | HTML UI, not `{"detail":"Not Found"}` |
| Logs on a workload | Plain-text docker logs |

Stop API: Ctrl+C.

### 4.4 launchd (production)

Installed by `deploy-hub.sh`. Verify:

```bash
launchctl print gui/$(id -u)/com.macmin.dashboard.api | head -20
launchctl print gui/$(id -u)/com.macmin.dashboard.worker | head -20
tail -20 ~/Library/Logs/mac-mini-dashboard/worker.log
tail -20 ~/Library/Logs/mac-mini-dashboard/api.log
```

Restart agents:

```bash
launchctl kickstart -k gui/$(id -u)/com.macmin.dashboard.api
launchctl kickstart -k gui/$(id -u)/com.macmin.dashboard.worker
```

**Pass:** logs show poll/audit activity; UI updates within ~30s (poll) / up to 5m (audit).

### 4.5 Tailscale from laptop

```text
http://<mac-mini-magic-dns-name>:8081
```

Repeat fleet table, logs, and live updates.

---

## Success checklist

- [ ] `git pull` on Mini (≥ `951916e`)
- [ ] `config/config.yaml` on Mini matches hub SSH
- [ ] `preflight_fleet.py` — all hosts OK
- [ ] One worker tick succeeds
- [ ] http://127.0.0.1:8081 shows real containers
- [ ] Workload Logs returns docker output
- [ ] launchd api + worker running, logs clean
- [ ] http://&lt;mac-mini&gt;:8081 works from laptop on Tailscale

---

## Rollback / uninstall

Stop services and remove LaunchAgents:

```bash
cd ~/dev/mac-mini-dashboard
./scripts/install-launchd.sh --uninstall
```

SQLite DB remains at `data/fleet.db`. Re-deploy with `./scripts/deploy-hub.sh` after fixing issues.

---

## Operations reference

| Action | Command |
|--------|---------|
| Full redeploy | `git pull && ./scripts/deploy-hub.sh` |
| Preflight only | `uv run python scripts/preflight_fleet.py` |
| Restart API | `launchctl kickstart -k gui/$(id -u)/com.macmin.dashboard.api` |
| Restart worker | `launchctl kickstart -k gui/$(id -u)/com.macmin.dashboard.worker` |
| API logs | `tail -f ~/Library/Logs/mac-mini-dashboard/api.log` |
| Worker logs | `tail -f ~/Library/Logs/mac-mini-dashboard/worker.log` |

**Environment (launchd sets these in plists):**

| Variable | Default |
|----------|---------|
| `DASHBOARD_CONFIG_PATH` | `{REPO}/config/config.yaml` |
| `DASHBOARD_DB_PATH` | `{REPO}/data/fleet.db` |
| `DASHBOARD_PORT` | `8081` |
| `DASHBOARD_AUDIT_INTERVAL_SEC` | `300` |

---

## Do not

- Run `./scripts/deploy-hub.sh` on cathedral for production (worker would SSH from the wrong machine).
- Use `--install-docker` when Colima/Docker already works.
- Skip `npm run build` on the Mini (API serves `apps/web/dist`).
- Assume cathedral `config/config.yaml` applies on the hub—maintain config on the Mini.

---

## Related docs

- [README.md](../../README.md) — dev vs hub, SSH/Docker notes
- [deploy/README.md](../../deploy/README.md) — launchd labels and manual control
- [docs/PLAN.md](../PLAN.md) — product plan and host onboarding
