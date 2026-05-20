#!/usr/bin/env bash
# Build, verify fleet SSH/Docker, and install launchd on the Mac Mini hub.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_ROOT}"

INSTALL_DOCKER=false
SKIP_FLEET=false
SKIP_WEB=false

usage() {
  echo "Usage: $0 [--install-docker] [--skip-fleet-preflight] [--skip-web-build]"
  echo "  Run on the Mac Mini hub after git pull."
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-docker) INSTALL_DOCKER=true ;;
    --skip-fleet-preflight) SKIP_FLEET=true ;;
    --skip-web-build) SKIP_WEB=true ;;
    -h | --help) usage ;;
    *) usage ;;
  esac
  shift
done

if [[ ! -f "${REPO_ROOT}/config/config.yaml" ]]; then
  echo "Missing config/config.yaml. Copy from config/config.yaml.example and edit hosts." >&2
  exit 1
fi

echo "==> Python deps (uv sync)"
uv sync --all-packages --dev

if [[ "${SKIP_FLEET}" != "true" ]]; then
  echo "==> Fleet preflight (SSH + docker on each configured host)"
  PREFLIGHT_ARGS=()
  if [[ "${INSTALL_DOCKER}" == "true" ]]; then
    PREFLIGHT_ARGS+=(--install-docker)
  fi
  uv run python scripts/preflight_fleet.py "${PREFLIGHT_ARGS[@]}"
fi

if [[ "${SKIP_WEB}" != "true" ]]; then
  echo "==> Web UI build"
  (cd apps/web && npm ci && npm run build)
fi

echo "==> launchd (API + worker)"
./scripts/install-launchd.sh

echo ""
echo "Deployed. API: http://127.0.0.1:8081"
echo "Logs: ${HOME}/Library/Logs/mac-mini-dashboard/"
echo "Smoke: uv run python -c \"from mac_mini_worker.main import run_worker; run_worker(max_ticks=1)\""
