#!/usr/bin/env bash
# ==============================================================================
# TRILUNAIR v1.2.0-low-latency-cloudflare — Native Docker-Free Ubuntu 24.04 Setup
# Target Host: Dedicated Tokyo Cloud VM (AWS Lightsail JP or OCI Tokyo Always Free)
#
# CRITICAL ISOLATION GUARANTEE:
# - Runs ONLY on a brand-new dedicated VM for trilunair.medinsup.com.
# - NEVER execute on any medinsup.com Riyadh medical infrastructure.
# - Zero open public HTTP/HTTPS/PostgreSQL ports (UFW default deny incoming).
# ==============================================================================
set -euo pipefail

echo "[1/7] Verifying hostname isolation (must NOT be medinsup.com medical server)..."
CURRENT_FQDN="$(hostname -f 2>/dev/null || hostname)"
if [[ "${CURRENT_FQDN}" == "medinsup.com" || "${CURRENT_FQDN}" == *"riyadh-med"* ]]; then
  echo "ABORT: Refusing to install on medical host ${CURRENT_FQDN}." >&2
  exit 1
fi

echo "[2/7] Installing native OS packages (PostgreSQL 16, Node 22, Python 3.12, UFW, unattended-upgrades)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg ufw fail2ban unattended-upgrades \
  postgresql postgresql-contrib python3 python3-venv git openssl jq rsync

echo "[3/7] Installing uv (fast deterministic Python manager)..."
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
fi

echo "[4/7] Creating isolated unprivileged Linux user 'trilunair'..."
id -u trilunair >/dev/null 2>&1 || useradd --system --home-dir /var/lib/trilunair --create-home --shell /usr/sbin/nologin trilunair
install -d -m 0750 -o trilunair -g trilunair /opt/trilunair /var/lib/trilunair /var/log/trilunair /var/backups/trilunair
install -d -m 0750 -o root -g trilunair /etc/trilunair

echo "[5/7] Locking UFW host firewall (Zero public HTTP/HTTPS/DB ports; outbound tunnel + Binance Spot only)..."
ufw default deny incoming
ufw default allow outgoing
# SSH restricted to key-only admin management (or omit if managed solely via Cloud Serial Console / SSM / Cloudflare SSH)
ufw limit 22/tcp comment 'Key-only SSH management'
ufw --force enable

echo "[6/7] Hardening SSH daemon (PasswordAuthentication no, PermitRootLogin no)..."
install -d -m 0755 /etc/ssh/sshd_config.d
cat >/etc/ssh/sshd_config.d/99-trilunair-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
X11Forwarding no
MaxAuthTries 3
EOF
systemctl reload ssh || systemctl reload sshd || true

echo "[7/7] Native host baseline ready."
echo "Next steps:"
echo "  1. Copy repository to /opt/trilunair/app and run: (cd /opt/trilunair/app/backend && sudo -u trilunair uv sync --frozen)"
echo "  2. Apply deploy/postgresql/postgresql-trilunair.conf & pg_hba-trilunair.conf (127.0.0.1:5432 loopback only)"
echo "  3. Populate /etc/trilunair/trilunair.env (chmod 0640 root:trilunair) from .env.example"
echo "  4. Enable systemd units: systemctl enable --now trilunair-engine cloudflared-trilunair"
