#!/usr/bin/env bash
# Install or uninstall Mac Mini dashboard LaunchAgents (macOS hub).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCHD_SRC="${REPO_ROOT}/deploy/launchd"
AGENTS_DIR="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/mac-mini-dashboard"
PYTHON="${REPO_ROOT}/.venv/bin/python"
WORKER_BIN="${REPO_ROOT}/.venv/bin/mac-mini-worker"
RENDER="${REPO_ROOT}/deploy/plist_render.py"

LABELS=(
  "com.macmin.dashboard.api"
  "com.macmin.dashboard.worker"
)

usage() {
  echo "Usage: $0 [--uninstall]"
  echo "  Installs LaunchAgents for API (:8081) and worker."
  exit 1
}

render_plist() {
  local template="$1"
  local dest="$2"
  PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}" "${PYTHON}" - "${template}" "${dest}" <<'PY'
import os
import sys
from pathlib import Path

from deploy.plist_render import render_launchd_plist

template_path, dest_path = Path(sys.argv[1]), Path(sys.argv[2])
values = {
    "REPO_ROOT": os.environ["REPO_ROOT"],
    "PYTHON": os.environ["PYTHON"],
    "WORKER_BIN": os.environ["WORKER_BIN"],
    "LOG_DIR": os.environ["LOG_DIR"],
}
rendered = render_launchd_plist(template_path.read_text(), values)
dest_path.write_text(rendered)
PY
}

bootstrap_agent() {
  local plist="$1"
  launchctl bootout "gui/$(id -u)" "${plist}" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "${plist}"
  launchctl enable "gui/$(id -u)/$(basename "${plist}" .plist)"
}

bootout_agent() {
  local plist="$1"
  launchctl bootout "gui/$(id -u)" "${plist}" 2>/dev/null || true
  rm -f "${plist}"
}

UNINSTALL=false
if [[ "${1:-}" == "--uninstall" ]]; then
  UNINSTALL=true
elif [[ -n "${1:-}" ]]; then
  usage
fi

export REPO_ROOT PYTHON WORKER_BIN LOG_DIR

if [[ "${UNINSTALL}" == "true" ]]; then
  for label in "${LABELS[@]}"; do
    bootout_agent "${AGENTS_DIR}/${label}.plist"
  done
  echo "Uninstalled dashboard LaunchAgents."
  exit 0
fi

if [[ ! -x "${PYTHON}" ]]; then
  echo "Missing venv. Run: cd ${REPO_ROOT} && uv sync --all-packages --dev" >&2
  exit 1
fi
if [[ ! -x "${WORKER_BIN}" ]]; then
  echo "Missing mac-mini-worker. Run: uv sync --all-packages --dev" >&2
  exit 1
fi
if [[ ! -f "${REPO_ROOT}/config/config.yaml" ]]; then
  echo "Missing config/config.yaml. Copy from config/config.yaml.example" >&2
  exit 1
fi

mkdir -p "${AGENTS_DIR}" "${LOG_DIR}" "${REPO_ROOT}/data"

for template in "${LAUNCHD_SRC}"/*.plist; do
  name="$(basename "${template}")"
  dest="${AGENTS_DIR}/${name}"
  render_plist "${template}" "${dest}"
  bootstrap_agent "${dest}"
done

echo "Installed dashboard LaunchAgents."
echo "  API:    http://127.0.0.1:8081 (logs: ${LOG_DIR}/api.log)"
echo "  Worker: poll/audit loop (logs: ${LOG_DIR}/worker.log)"
echo "  Plists: ${AGENTS_DIR}/com.macmin.dashboard.*.plist"
