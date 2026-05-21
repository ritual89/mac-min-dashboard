#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DB_PATH="${TMPDIR:-/tmp}/smoke_fleet.db"
PORT=8099
API_PID=""

cleanup() {
  if [ -n "$API_PID" ]; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
  rm -f "$DB_PATH"
}
trap cleanup EXIT

echo "=== Smoke Test ==="

echo "1. Seeding database..."
cd "$ROOT_DIR"
DASHBOARD_DB_PATH="$DB_PATH" uv run mac-mini-seed
echo "   OK — DB at $DB_PATH"

echo "2. Starting API on port $PORT..."
DASHBOARD_DB_PATH="$DB_PATH" DASHBOARD_PORT="$PORT" uv run mac-mini-api &
API_PID=$!
sleep 2

echo "3. Testing GET /api/hosts..."
HOSTS=$(curl -sf "http://127.0.0.1:$PORT/api/hosts")
echo "   $HOSTS"
echo "$HOSTS" | python3 -c "import sys,json; data=json.load(sys.stdin); assert len(data)>=1, 'no hosts'; print('   OK — found', len(data), 'host(s)')"

echo "4. Testing GET /api/workloads..."
WORKLOADS=$(curl -sf "http://127.0.0.1:$PORT/api/workloads")
echo "   $WORKLOADS" | head -c 200
echo ""
echo "$WORKLOADS" | python3 -c "import sys,json; data=json.load(sys.stdin); assert len(data)>=1, 'no workloads'; print('   OK — found', len(data), 'workload(s)')"

echo "5. Testing GET /api/settings..."
SETTINGS=$(curl -sf "http://127.0.0.1:$PORT/api/settings")
echo "   $SETTINGS"
echo "$SETTINGS" | python3 -c "import sys,json; data=json.load(sys.stdin); assert 'notify_red' in data; print('   OK — settings returned')"

echo "6. Testing GET /api/audit..."
AUDIT=$(curl -sf "http://127.0.0.1:$PORT/api/audit")
echo "   Audit items: $(echo "$AUDIT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")"

echo ""
echo "=== All smoke tests passed ==="
