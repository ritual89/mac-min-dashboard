# Deploy (macOS hub)

## launchd LaunchAgents

Tailnet-only dashboard on the Mac Mini hub: API on **8081**, worker for poll/audit.

### Prerequisites

```bash
cd /path/to/mac-mini-dashboard
uv sync --all-packages --dev
cp config/config.yaml.example config/config.yaml
cd apps/web && npm install && npm run build
```

### Install

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
