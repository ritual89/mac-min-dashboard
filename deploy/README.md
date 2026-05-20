# Deploy (macOS hub)

## One-command hub deploy

Run **on the Mac Mini** (not your dev laptop):

```bash
cd ~/dev/mac-mini-dashboard   # or your clone path
git pull
cp -n config/config.yaml.example config/config.yaml   # first time only; then edit hosts
./scripts/deploy-hub.sh
```

`deploy-hub.sh` runs, in order:

1. `uv sync --all-packages --dev`
2. **Fleet preflight** — SSH to each host in `config.yaml` and verify `docker ps` works
3. `npm ci && npm run build` in `apps/web`
4. `./scripts/install-launchd.sh`

If the hub (or a macOS fleet host) is missing Docker:

```bash
./scripts/deploy-hub.sh --install-docker
```

That installs **Colima + Docker CLI via Homebrew over SSH** on macOS hosts only. Linux hosts still need manual `docker` + group setup (see PLAN onboarding checklist).

Skip steps when iterating locally:

```bash
./scripts/deploy-hub.sh --skip-fleet-preflight --skip-web-build
```

Preflight only:

```bash
uv run python scripts/preflight_fleet.py
uv run python scripts/preflight_fleet.py --install-docker
```

### Prerequisites (on the hub)

- Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+
- `config/config.yaml` with `ssh_host` / users matching `~/.ssh/config` on **this** machine
- Hub SSH user can reach every fleet host (`ssh-copy-id` from hub — PLAN §6)
- **Docker on polled hosts**, not on the hub process itself unless `mac-mini` is in `hosts`

### Install launchd only

```bash
./scripts/install-launchd.sh
```

Installs:

| Label | Role |
|-------|------|
| `com.macmin.dashboard.api` | FastAPI + static UI |
| `com.macmin.dashboard.worker` | SSH poll + audit |

Logs: `~/Library/Logs/mac-mini-dashboard/{api,worker}.{log,err}`

### Uninstall

```bash
./scripts/install-launchd.sh --uninstall
```

### Manual control

```bash
launchctl kickstart -k gui/$(id -u)/com.macmin.dashboard.api
launchctl kickstart -k gui/$(id -u)/com.macmin.dashboard.worker
launchctl print gui/$(id -u)/com.macmin.dashboard.api
```
