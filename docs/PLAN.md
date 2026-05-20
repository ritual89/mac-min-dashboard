# Mac Mini Fleet Dashboard — Product & Technical Plan

> Status: **Planning complete** (grill session May 2026).  
> v1 transport: **SSH-only hub**. v2: **optional agents** (see [Future: agents](#future-agents-phase-2)).

---

## 1. Vision

A **solo-operator, tailnet-only** control plane to **discover**, **monitor**, and **lightly control** workloads across ~10 machines (Mac Mini hub, Vultr Linux boxes, additional macOS/Linux hosts).

Success looks like a **dark-mode, Activity Monitor–style** dashboard: scan the fleet without hand-maintaining entries, see orange/red severity, restart services, tail recent logs, and tune Telegram noise until it feels right.

**Not in scope:** multi-user RBAC, public internet exposure, full observability (Prometheus/Grafana), arbitrary remote shell.

---

## 2. Locked decisions

| Area | Decision |
|------|----------|
| **Audience** | Solo; access from laptop/phone on Tailscale |
| **Security** | Tailnet membership only (no in-app login v1) |
| **Transport v1** | SSH from Mac Mini hub to all hosts |
| **Transport v2** | Optional per-host agents (documented below) |
| **Scale** | Design for **≤10 hosts** |
| **Stack** | **FastAPI** (API) + **worker** (poll/alert) + **Vite/React** (UI), SQLite inventory |
| **Reachability** | **Dedicated port** on hub (avoid path clash with Dashboard for Life on same Tailscale hostname) |
| **Hub uptime** | Mac Mini **always-on**; `launchd` services |
| **Discovery** | Full audit inventory + **rule-based auto-promote** + manual pin |
| **Controls v1** | Restart, view logs (last N), stop non-critical (confirm) |
| **Severity** | **Orange:** not running when expected, restart loop · **Red:** health check failed, error patterns in logs |
| **Alerts** | **Telegram** (single bot + chat ID); **configurable** which severities notify (start permissive, tune down) |
| **UI grouping** | By host → by kind; flat view + filters |
| **Poll interval** | **30s** default; per-host override (15–60s) |
| **Auto-promote rules** | Docker; paths under `~/dev`/`~/projects`/`~/code`; ports >1024; explicit allowlist (hermes, dashboard-for-life, …); exclude `com.apple.*` and system cron |
| **Config** | `config.yaml` + gitignored `.env`; UI persists alert toggles / poll overrides |
| **OS** | Per-host `darwin` \| `linux` scanners |
| **Deploy hub** | Native on macOS: `git pull` + `launchd` (not Docker for hub v1) |
| **SSH** | Partial today; plan includes host onboarding checklist |

---

## 3. Architecture (v1)

```text
┌─────────────────────────────────────────────────────────────┐
│  Tailscale (tailnet only)                                    │
│  Laptop / Phone ──HTTPS──► mac-mini:<PORT> (Serve optional)  │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│  Mac Mini (hub)                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Vite/React  │  │ FastAPI      │  │ Worker              │ │
│  │ static UI   │──│ REST + WS?   │  │ poll · scan · alert │ │
│  └─────────────┘  └──────┬───────┘  └──────────┬──────────┘ │
│                          │                      │            │
│                          └──────────┬───────────┘            │
│                                     ▼                        │
│                              SQLite (inventory,              │
│                              state, settings)                │
└───────────────────────────────┬─────────────────────────────┘
                                │ SSH (keys)
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
         vultr-1 (linux)   vultr-2 (linux)   mac-2 (darwin) …
```

### Processes on hub

| Process | Responsibility |
|---------|----------------|
| `dashboard-api` | HTTP API, on-demand SSH (logs, restart, stop), serve UI static files or proxy |
| `dashboard-worker` | Scheduled poll, discovery/audit pass, severity evaluation, Telegram |

Same Python package; two entrypoints (e.g. `uv run api`, `uv run worker`).

### Repository layout (proposed)

```text
mac-mini-dashboard/
  apps/
    api/          # FastAPI
    worker/       # asyncio poll loop
    web/          # Vite + React + Tailwind
  packages/
    core/         # scanners, ssh, models, severity, telegram
  config/
    config.yaml.example
  deploy/
    launchd/      # plist templates
  docs/
    PLAN.md
```

---

## 4. Core concepts

### Host

Configured machine: `id`, `display_name`, `tailscale_host`, `ssh_user`, `ssh_key_path`, `os: darwin|linux`, `poll_interval_sec` (optional).

### Workload

A monitored unit with stable `workload_id`, e.g.:

- `docker:<host>:<container_name>`
- `compose:<host>:<project>:<service>`
- `systemd:<host>:<unit>`
- `launchd:<host>:<label>`
- `cron:<host>:<hash>` (user crons only)
- `process:<host>:<port|pid signature>` (promoted cautiously)

### Inventory states

| State | Meaning |
|-------|---------|
| `discovered` | Seen by audit; not on main dashboard |
| `monitored` | On main dashboard (auto-promoted or pinned) |
| `muted` | Monitored but alerts suppressed (optional v1.5) |

### Severity (evaluation order)

1. **Red** — Docker health `unhealthy`; HTTP probe failed (if configured); log scan hits (`ERROR`, `Traceback`, `panic`, …) on last N lines.
2. **Orange** — Expected running but stopped; restart loop (>N restarts/hour).
3. **Green** — Otherwise.

Telegram: user-configurable map `{ orange: bool, red: bool }` (default both on; tune in UI).

---

## 5. Scanners (plugins)

Each scanner implements: `discover(host) -> list[WorkloadSnapshot]` (idempotent).

| Scanner | macOS | Linux |
|---------|-------|-------|
| Docker | ✓ | ✓ |
| Docker Compose | ✓ | ✓ |
| systemd | — | ✓ |
| launchd | ✓ | — |
| user cron | ✓ | ✓ |
| listening ports (>1024) | ✓ | ✓ |
| process signature (optional) | ✓ | ✓ |

**Audit pass** (e.g. every 5 min): run all scanners → upsert `discovered` rows → apply promotion rules → update `monitored` set.

**Poll pass** (30s): for `monitored` only → status, health, restart counts, fetch log tail for red evaluation.

### Auto-promote rules (default)

Promote `discovered` → `monitored` when any:

- Docker container or compose service exists
- Compose file or cwd under configured project roots
- Listening port > 1024 (not in denylist)
- Name/label in `allowlist` (hermes, dashboard-for-life, …)

Exclude:

- `com.apple.*` launchd labels
- system paths `/usr`, `/System`, etc.

Rules live in `config.yaml`; allow manual **pin** / **unpin** via API (persisted).

---

## 6. SSH execution layer

- Library: `asyncssh` (or sync `paramiko` in thread pool if simpler v1).
- Connection pool per host; timeout and retry with backoff.
- Commands are **allowlisted templates**, not user shell:
  - `docker inspect`, `docker ps`, `docker logs --tail N`, `docker restart`
  - `systemctl is-active`, `systemctl restart`, `journalctl -u … -n N`
  - `launchctl list`, `launchctl kickstart -k`, `log show --last 5m` (macOS)
  - `crontab -l` (user only)

**Onboarding checklist** (per host):

1. Tailscale installed; MagicDNS name stable.
2. `ssh-copy-id` from Mac Mini hub user.
3. Confirm `docker` group (Linux) or docker.sock access.
4. Test: `ssh user@host docker ps`.
5. Add row to `config.yaml`.

---

## 7. API (v1 sketch)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/hosts` | List hosts + last seen |
| GET | `/api/workloads` | Filter: `monitored`, `discovered`, severity, host |
| GET | `/api/workloads/{id}` | Detail + last log snippet |
| POST | `/api/workloads/{id}/restart` | Confirm optional |
| POST | `/api/workloads/{id}/stop` | Require `?confirm=1` |
| GET | `/api/workloads/{id}/logs?tail=200` | On-demand |
| GET | `/api/audit` | Discovered-not-monitored |
| POST | `/api/workloads/{id}/pin` | Promote to monitored |
| DELETE | `/api/workloads/{id}/pin` | Demote |
| GET/PATCH | `/api/settings` | Telegram toggles, poll overrides |

OpenAPI from FastAPI; UI uses generated types or hand-written fetch wrappers.

---

## 8. UI (v1)

**Theme:** dark, dense table (Activity Monitor–inspired).

**Views:**

1. **Fleet** — default; grouped by host → Docker / systemd / launchd / other.
2. **All workloads** — flat sortable table (host, name, kind, state, severity, updated).
3. **Audit** — discovered, not monitored; pin button.
4. **Settings** — Telegram severity toggles; link to edit `config.yaml` (docs only or read-only display v1).

**Row actions:** Restart, Logs (modal), Stop (secondary + confirm).

**Mobile:** responsive table → cards on narrow width; touch-friendly actions.

---

## 9. Telegram notifier

- `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Worker sends on severity **transition** (debounce: e.g. same workload max 1 msg / 15 min unless red).
- Message: host, workload name, severity, one-line reason, link to dashboard URL (tailnet).
- Settings API persists `{ notify_orange, notify_red }`.

---

## 10. Data store (SQLite)

Tables (conceptual):

- `hosts`
- `workloads` (id, host_id, kind, name, monitored, pinned, metadata JSON)
- `workload_state` (last_seen, status, severity, restart_count_1h, last_error_snippet)
- `settings` (key/value)
- `alert_history` (optional, for debounce)

Migrations: Alembic or lightweight SQL scripts.

---

## 11. Deployment (Mac Mini hub)

1. Install Python 3.12+, `uv`, Node 20+.
2. Clone repo to e.g. `~/dev/mac-mini-dashboard`.
3. `cp config/config.yaml.example config/config.yaml`; edit hosts + paths.
4. `cp .env.example .env`; Telegram + secrets.
5. Build UI: `cd apps/web && npm run build` → output served by API or `caddy`/static.
6. `launchd` plists:
   - `com.macmin.dashboard.api.plist` → port **8081** (or chosen; document in README)
   - `com.macmin.dashboard.worker.plist`
7. Tailscale: expose `https://<mac-mini-hostname>:8081` or Serve TCP proxy to 8081.

**Dashboard for Life:** unchanged; separate app/port/path on same machine.

---

## 12. Phased delivery (weekly shippable)

### Week 1 — Skeleton + one host

- [ ] Monorepo scaffold (api, worker, web, core)
- [ ] `config.yaml` + SQLite schema
- [ ] SSH to Mac Mini localhost + Docker scanner only
- [ ] API: list workloads (monitored)
- [ ] UI: dark single-host table, logs modal (read-only)

### Week 2 — Fleet + discovery

- [ ] Multi-host SSH config + Linux systemd/Docker
- [ ] macOS launchd + cron scanners
- [ ] Audit view + auto-promote rules + pin/unpin
- [ ] Orange/red severity (no Telegram yet)

### Week 3 — Control + alerts

- [ ] Restart + stop + log tail
- [ ] Telegram notifier + settings UI toggles
- [ ] `launchd` deploy docs + plists

### Week 4 — Polish + hardening

- [ ] Restart loop detection; health checks
- [ ] Per-host poll overrides; debounced alerts
- [ ] Mobile layout pass; error empty states
- [ ] SSH onboarding doc; smoke test script

**Post–v1:** agents, start command, HTTP probe config UI, path-based Serve, multi-telegram routing.

---

## 13. Out of scope (v1)

- Agent binaries on remotes
- Start workload / arbitrary SSH commands
- Edit cron/launchd from UI
- Multi-user auth / RBAC
- Public internet / OAuth
- Full metrics (CPU/memory charts) — optional later
- Integration with Dashboard for Life (separate product unless you add links)

---

## 14. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| SSH key compromise | Dedicated `dashboard@` user, docker-only or passwordless sudo for specific units |
| Poll load on 10 hosts | 30s default; stagger polls; connection pooling |
| Discovery noise | Audit vs monitored; exclude rules; pin/unpin |
| Telegram fatigue | Configurable severities; debounce; start loud then tune |
| Mac Mini hub down | Document; v2 agents optional; no false “all green” |
| Scanner false “not running” | “Expected running” from pin + was-running history; orange not red |

---

## 15. Future: agents (Phase 2)

See grill session summary:

- Small outbound-only agent per host (Go/Rust/Python).
- Hub accepts `heartbeat`, `snapshot`, `command`, `log_chunk`.
- Enrollment: hub issues `host_id` + token; install via systemd/launchd/Docker.
- Migration: prefer agent when online, SSH fallback, then SSH removal per host.

No v1 implementation; keep workload IDs stable so UI survives migration.

---

## 16. Open items (fill during Week 1)

- [ ] Exact hub port (default **8081**)
- [ ] Project root paths on Mac Mini and each Vultr host
- [ ] Tailscale hostnames for initial host list
- [ ] Which Telegram bot (1 of 3) + chat ID
- [ ] Explicit allowlist entries (hermes, dashboard-for-life, …)
- [ ] HTTP health probe URLs per workload (optional config, v1.5)

---

## 17. Success checklist

- [ ] Open dashboard from phone on tailnet; see all monitored workloads across hosts
- [ ] New Docker compose stack appears in Audit within 5 min; auto-promotes if under project path
- [ ] Red row after unhealthy container or ERROR in logs; Telegram fires (if enabled)
- [ ] Orange row when container exited; no Telegram if orange disabled
- [ ] Restart from UI recovers service; logs visible without SSH manually
- [ ] No manual YAML entry required for routine Docker workloads
