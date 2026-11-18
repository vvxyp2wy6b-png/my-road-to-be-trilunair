#!/usr/bin/env bash
# ==============================================================================
# مشغل وباني المنصة المحلي الأصلي بدون دوكر (Zero-Docker Native Build & Server CLI)
# المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — v1.3.0-binance-personal-guard
# يدعم: Linux و macOS (Apple Silicon / Intel) عبر uv / venv + Node.js + PostgreSQL/SQLite
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PGDATA_DIR="$BACKEND_DIR/data/pgdata"
PORT="${PORT:-8000}"

resolve_python() {
  if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    echo "$BACKEND_DIR/.venv/bin/python"
  elif command -v uv >/dev/null 2>&1; then
    (cd "$BACKEND_DIR" && uv sync --no-dev >/dev/null)
    echo "$BACKEND_DIR/.venv/bin/python"
  else
    python3 -m venv "$BACKEND_DIR/.venv"
    "$BACKEND_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
    "$BACKEND_DIR/.venv/bin/pip" install -e "$BACKEND_DIR" >/dev/null
    echo "$BACKEND_DIR/.venv/bin/python"
  fi
}

start_native_postgres_if_present() {
  # تشغيل PostgreSQL المحلي الأصلي إن كانت قاعدة البيانات مهيأة محلياً (دون أي حاويات Docker)
  if [[ -d "$PGDATA_DIR" ]]; then
    local pg_ctl_bin=""
    if [[ -x "/usr/lib/postgresql/15/bin/pg_ctl" ]]; then
      pg_ctl_bin="/usr/lib/postgresql/15/bin/pg_ctl"
    elif command -v pg_ctl >/dev/null 2>&1; then
      pg_ctl_bin="$(command -v pg_ctl)"
    fi

    if [[ -n "$pg_ctl_bin" ]]; then
      mkdir -p /tmp/pgsocket
      if ! "$pg_ctl_bin" -D "$PGDATA_DIR" status >/dev/null 2>&1; then
        echo "🗄️  [Native DB] Starting local PostgreSQL server (Zero Docker)..."
        "$pg_ctl_bin" -D "$PGDATA_DIR" -l "$BACKEND_DIR/data/postgres.log" -o "-k /tmp/pgsocket -h 127.0.0.1 -p 5432" start >/dev/null
      else
        echo "🗄️  [Native DB] Local PostgreSQL server is already active on 127.0.0.1:5432."
      fi
    fi
  fi
}

cmd_build() {
  echo "======================================================================"
  echo " 🔨 بناء المنصة الكاملة محلياً بدون دوكر (Backend + Frontend Native Build)"
  echo "======================================================================"

  echo "1️⃣  [Backend] Preparing native Python virtual environment & compiling modules..."
  if command -v uv >/dev/null 2>&1 && [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    (cd "$BACKEND_DIR" && uv sync)
  fi
  local py_bin
  py_bin="$(resolve_python)"
  "$py_bin" -m py_compile "$BACKEND_DIR"/app/*.py
  echo "   ✓ Backend Python bytecode verified ($("$py_bin" --version))."

  echo "2️⃣  [Frontend] Building React 19 + TypeScript + Vite production bundle..."
  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    (cd "$FRONTEND_DIR" && npm install)
  fi
  (cd "$FRONTEND_DIR" && npm run build)
  echo "   ✓ Frontend production bundle ready at: $FRONTEND_DIR/dist"

  start_native_postgres_if_present
  echo "3️⃣  [Database] Verifying & migrating native schema (PAPER lock enforced)..."
  PYTHONPATH="$BACKEND_DIR" "$py_bin" - <<'PY'
from app.database import init_db
from app.webauthn_passkeys import ensure_passkey_tables
from app.admin_identity import ensure_admin_identity_tables
from app.quantum_hub import ensure_quantum_tables
from app.wealth_architect import ensure_wealth_architect_tables
from app.binance_personal_account import ensure_binance_personal_tables
from app.binance_spot_execution_adapter import ensure_spot_execution_tables

init_db()
ensure_passkey_tables()
ensure_admin_identity_tables()
ensure_quantum_tables()
ensure_wealth_architect_tables()
ensure_binance_personal_tables()
ensure_spot_execution_tables()
print("   ✓ All native database & encrypted vault tables initialized.")
PY

  echo "======================================================================"
  echo " ✅ اكتمل البناء المحلي الأصلي بنجاح بدون Docker!"
  echo "======================================================================"
}

cmd_start() {
  if [[ ! -f "$FRONTEND_DIR/dist/index.html" ]]; then
    cmd_build
  else
    start_native_postgres_if_present
  fi
  local py_bin
  py_bin="$(resolve_python)"
  exec env PORT="$PORT" PYTHONPATH="$BACKEND_DIR" "$py_bin" "$BACKEND_DIR/scripts/run_local_stack.py"
}

cmd_dev() {
  start_native_postgres_if_present
  local py_bin
  py_bin="$(resolve_python)"
  echo "🚀 Starting Native Backend (:8000) + Native Vite Dev Server (:5173) [Zero Docker]..."
  (
    cd "$BACKEND_DIR"
    PORT="$PORT" PYTHONPATH="$BACKEND_DIR" "$py_bin" "$BACKEND_DIR/scripts/run_local_stack.py"
  ) &
  local b_pid=$!
  (
    cd "$FRONTEND_DIR"
    npm run dev -- --host 0.0.0.0 --port 5173
  ) &
  local f_pid=$!
  trap "kill $b_pid $f_pid 2>/dev/null || true" EXIT INT TERM
  wait
}

cmd_stop() {
  pkill -f "run_local_stack.py" 2>/dev/null || true
  pkill -f "vite.*5173" 2>/dev/null || true
  if [[ -d "$PGDATA_DIR" && -x "/usr/lib/postgresql/15/bin/pg_ctl" ]]; then
    /usr/lib/postgresql/15/bin/pg_ctl -D "$PGDATA_DIR" stop >/dev/null 2>&1 || true
  fi
  echo "🛑 Stopped native TRILUNAIR processes."
}

cmd_install_macos_service() {
  local plist_dir="$HOME/Library/LaunchAgents"
  local plist_file="$plist_dir/com.trilunair.commandcenter.plist"
  mkdir -p "$plist_dir" "$BACKEND_DIR/data"
  cat > "$plist_file" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.trilunair.commandcenter</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ROOT_DIR/scripts/native_server_ctl.sh</string>
    <string>start</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$BACKEND_DIR/data/native_server.out.log</string>
  <key>StandardErrorPath</key>
  <string>$BACKEND_DIR/data/native_server.err.log</string>
</dict>
</plist>
EOF
  echo "✅ Generated native macOS LaunchAgent (Zero Docker): $plist_file"
  echo "   To activate on macOS: launchctl load -w \"$plist_file\""
}

ACTION="${1:-start}"
case "$ACTION" in
  build) cmd_build ;;
  start) cmd_start ;;
  dev) cmd_dev ;;
  stop) cmd_stop ;;
  install-macos-service) cmd_install_macos_service ;;
  *)
    echo "Usage: $0 {build|start|dev|stop|install-macos-service}"
    exit 1
    ;;
esac
