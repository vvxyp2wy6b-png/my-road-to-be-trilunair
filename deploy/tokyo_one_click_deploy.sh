#!/usr/bin/env bash
# ==============================================================================
# TMJ (TrilMajed) — One-Command Tokyo Low-Latency Cloud Provisioner & Vault Init
# المنطقة الموصى بها رقم #1 لبينانس: Tokyo, Japan (AWS ap-northeast-1 / OCI ap-tokyo-1)
# زمن الوصول المتوقع لمحرك مطابقة Binance في طوكيو: ~1.2ms - 3.5ms
# ==============================================================================
set -euo pipefail

echo "=================================================================="
echo "🚀 تريلماجد (TMJ) — تجهيز سيرفر طوكيو منخفض الكمون + خزنة الأسرار المشفرة"
echo "=================================================================="

APP_DIR="/opt/trilunair/app"
VAULT_ENV="/etc/trilunair/trilunair.env"

echo "[1/5] قياس زمن الاتصال المباشر مع سيرفرات Binance الفورية (api.binance.com)..."
if command -v curl >/dev/null 2>&1; then
  RTT_SEC=$(curl -o /dev/null -s -w '%{time_connect}' https://api.binance.com/api/v3/ping || echo "N/A")
  echo "  -> زمن تأسيس اتصال TCP مع Binance: ${RTT_SEC}s"
fi

echo "[2/5] كشف عنوان الـ IP العام الثابت للسيرفر (لإضافته في القائمة البيضاء IP Whitelist داخل Binance)..."
PUBLIC_IP=$(curl -4 -fsSL https://ifconfig.me 2>/dev/null || echo "UNKNOWN_IP")
echo "  -> عنوان السيرفر الثابت للقائمة البيضاء في Binance: ${PUBLIC_IP}"

echo "[3/5] إنشاء خزنة الأسرار المشفرة (AES-256-GCM Master Key) بصلاحيات 0600..."
sudo mkdir -p /etc/trilunair
if [ ! -f "${VAULT_ENV}" ]; then
  VAULT_KEY=$(python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
  SESSION_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
  cat <<EOF | sudo tee "${VAULT_ENV}" >/dev/null
# خزنة تريلماجد السيادية المشفرة (AES-256-GCM) — لا تشارك هذا الملف أبداً
TRILUNAIR_ENV=production
TRILUNAIR_REGION=ap-northeast-1
TRILUNAIR_TRADING_MODE=PAPER
TRILUNAIR_LIVE_AUTHORIZED=false
TRILUNAIR_VAULT_MASTER_KEY=${VAULT_KEY}
TRILUNAIR_SESSION_SECRET=${SESSION_SECRET}
EOF
  sudo chmod 0600 "${VAULT_ENV}"
  echo "  -> تم توليد وتأمين خزنة الأسرار المشفرة في ${VAULT_ENV} (0600)."
else
  echo "  -> خزنة الأسرار موجودة مسبقاً ومحفوظة بأمان."
fi

echo "[4/5] تثبيت الاعتماديات وبناء الواجهة وتشغيل خدمة المحرك..."
if [ -f "deploy/linux-systemd/install_native_ubuntu.sh" ]; then
  sudo bash deploy/linux-systemd/install_native_ubuntu.sh
fi

echo "[5/5] اكتمل التجهيز! أضف الـ IP (${PUBLIC_IP}) في Binance API Whitelist ثم افتح خزنة المنصة لإلصاق المفتاح العام Ed25519."
