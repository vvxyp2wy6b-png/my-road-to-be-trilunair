#!/usr/bin/env bash
# ==============================================================================
# HOW TO BE A TRILLIONAIRE — One-Command Tokyo Server + Cloudflare Tunnel Deploy
# المنطقة الموصى بها رقم #1 لبينانس:
#   - Oracle Cloud Always Free: Japan East (Tokyo / ap-tokyo-1) — $0/شهر مجاناً مدى الحياة
#   - AWS Lightsail: Tokyo (ap-northeast-1) — $5/شهر (نفس مركز بيانات محرك مطابقة Binance ~1.5ms)
#
# طريقة التشغيل على سيرفر Ubuntu 22.04 / 24.04 في طوكيو مع ربط Cloudflare التلقائي:
#   CF_TUNNEL_TOKEN="توكن_كلاود_فلير_الخاص_بك" sudo -E bash deploy/tokyo_one_click_deploy.sh
# ==============================================================================
set -euo pipefail

REPO_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="/opt/trilunair/app"
VAULT_ENV="/etc/trilunair/trilunair.env"
CF_TUNNEL_TOKEN="${CF_TUNNEL_TOKEN:-}"

echo "=================================================================="
echo "🚀 HOW TO BE A TRILLIONAIRE — نشر سيرفر طوكيو + نفق Cloudflare"
echo "=================================================================="

echo "[1/7] قياس سرعة الاتصال المباشر من هذا السيرفر إلى محرك Binance (api.binance.com)..."
if command -v curl >/dev/null 2>&1; then
  RTT_SEC=$(curl -o /dev/null -s -w '%{time_connect}' https://api.binance.com/api/v3/ping || echo "N/A")
  echo "  -> زمن تأسيس اتصال TCP مع Binance: ${RTT_SEC}s"
fi

echo "[2/7] كشف الـ Static Public IP لإضافته في Binance API Whitelist..."
PUBLIC_IP=$(curl -4 -fsSL https://ifconfig.me 2>/dev/null || echo "UNKNOWN_IP")
echo "  -> عنوان السيرفر الثابت (Static IP): ${PUBLIC_IP}"

echo "[3/7] تجهيز نظام Ubuntu وجدار الحماية UFW وقاعدة البيانات PostgreSQL..."
if [ -f "${REPO_SRC}/deploy/linux-systemd/install_native_ubuntu.sh" ]; then
  sudo bash "${REPO_SRC}/deploy/linux-systemd/install_native_ubuntu.sh"
fi

echo "[4/7] تهيئة قاعدة بيانات PostgreSQL المحلية وتأمين خزنة AES-256-GCM..."
DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='trilunair'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER trilunair WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='trilunair'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE trilunair OWNER trilunair;"

sudo mkdir -p /etc/trilunair
if [ ! -f "${VAULT_ENV}" ]; then
  VAULT_KEY=$(python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
  SESSION_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
  cat <<EOF | sudo tee "${VAULT_ENV}" >/dev/null
# خزنة HOW TO BE A TRILLIONAIRE المشفرة (AES-256-GCM) — لا تشارك هذا الملف أبداً
TRILUNAIR_ENV=production
TRILUNAIR_REGION=ap-northeast-1
TRILUNAIR_TRADING_MODE=PAPER
TRILUNAIR_LIVE_AUTHORIZED=false
DATABASE_URL=postgresql+psycopg://trilunair:${DB_PASS}@127.0.0.1:5432/trilunair
TRILUNAIR_VAULT_MASTER_KEY=${VAULT_KEY}
TRILUNAIR_SESSION_SECRET=${SESSION_SECRET}
EOF
fi
sudo chown root:trilunair "${VAULT_ENV}"
sudo chmod 0640 "${VAULT_ENV}"

echo "[5/7] نسخ ملفات المنصة وبناء بيئة المحرك السريع (FastAPI + Uvicorn)..."
sudo mkdir -p "${APP_DIR}/frontend/dist"
sudo rsync -a --delete --exclude '.git' --exclude '.venv' "${REPO_SRC}/" "${APP_DIR}/"
if [ -f "${APP_DIR}/standalone-preview.html" ]; then
  sudo cp "${APP_DIR}/standalone-preview.html" "${APP_DIR}/frontend/dist/index.html"
fi
sudo chown -R trilunair:trilunair "${APP_DIR}" /var/lib/trilunair /var/log/trilunair

sudo -u trilunair bash -c "cd '${APP_DIR}/backend' && /usr/local/bin/uv venv .venv && /usr/local/bin/uv pip install --python .venv/bin/python -r requirements.txt 2>/dev/null || /usr/local/bin/uv sync"

echo "[6/7] تفعيل خدمة المحرك الدائمة (systemd 24/7) على 127.0.0.1:8000..."
sudo cp "${APP_DIR}/deploy/linux-systemd/trilunair-engine.service" /etc/systemd/system/trilunair-engine.service
sudo systemctl daemon-reload
sudo systemctl enable --now trilunair-engine.service

echo "[7/7] ربط حساب Cloudflare عبر نفق Cloudflare Zero-Trust السريع (QUIC)..."
if ! command -v cloudflared >/dev/null 2>&1; then
  ARCH=$(dpkg --print-architecture)
  curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb" -o /tmp/cloudflared.deb
  sudo dpkg -i /tmp/cloudflared.deb
  rm -f /tmp/cloudflared.deb
fi

if [ -n "${CF_TUNNEL_TOKEN}" ]; then
  sudo cloudflared service install "${CF_TUNNEL_TOKEN}" || sudo systemctl restart cloudflared
  echo "  -> ✅ تم ربط السيرفر بحسابك في Cloudflare بنجاح!"
else
  echo "  -> ℹ️ تم تثبيت cloudflared. لربط نطاقك من Cloudflare فوراً شغّل:"
  echo "     sudo cloudflared service install <YOUR_CLOUDFLARE_TUNNEL_TOKEN>"
fi

echo "=================================================================="
echo "✅ اكتمل نشر سيرفر طوكيو بنجاح!"
echo "   • المحرك المحلي: http://127.0.0.1:8000"
echo "   • الـ Static IP لقائمة Binance البيضاء: ${PUBLIC_IP}"
echo "=================================================================="
