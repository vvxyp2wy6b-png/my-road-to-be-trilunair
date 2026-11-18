#!/usr/bin/env bash
# ==============================================================================
# المشغل الفوري الأصلي بدون دوكر (Zero-Docker One-Command Native Builder & Server)
# My Road to be Trilunair Dr.MaJoOoOoOoD — v1.3.0-binance-personal-guard
#
# الاستخدام:
#   ./start.sh          -> يبني الواجهة والخلفية تلقائياً (إن لزم) ويشغّل الخادم الموحد على المنفذ 8000
#   ./start.sh build    -> إعادة بناء الواجهة الأمامية والخلفية وتحديث الجداول بدون Docker
#   ./start.sh dev      -> تشغيل الخلفية (:8000) + واجهة التطوير الحية Vite (:5173) معاً بدون Docker
#   ./start.sh stop     -> إيقاف الخادم المحلي الأصلي
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT_DIR/scripts/native_server_ctl.sh" "${1:-start}"
