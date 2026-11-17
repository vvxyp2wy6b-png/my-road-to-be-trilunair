#!/usr/bin/env bash
# ==============================================================================
# سكربت التشغيل المتكامل المحلي (الخادم الخلفي + الواجهة الهولوغرامية)
# My Road to be Trilunair Dr.MaJoOoOoOoD
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting My Road to be Trilunair Dr.MaJoOoOoOoD Command Center..."
echo "🔒 Safety Mode: PAPER TRADING enforced by default."

(
  cd "$ROOT_DIR/backend"
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --host 0.0.0.0 --port 5173
) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT INT TERM
wait
