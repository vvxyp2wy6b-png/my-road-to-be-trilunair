# Recovery, Disaster Response & Baseline Rollback Runbook
## TRILUNAIR Quantum Command Center — `v1.2.0-low-latency-cloudflare`

> **CRITICAL MEDICAL ISOLATION RULE:**  
> All recovery, restore, DNS, and rollback steps apply **exclusively** to `trilunair.medinsup.com` and its dedicated cloud VM. Never run any command on `medinsup.com` Riyadh medical hosts, databases, or DNS records.

---

## 1. Owner Passkey Loss / Device Replacement Recovery
Because TRILUNAIR stores **zero biometric templates** (only FIDO2 public keys on device hardware enclaves), losing an iPhone or MacBook requires cryptographic recovery rather than biometric resets:

1. **Primary Recovery Path — Synced Apple Passkey / Hardware Backup Key:**
   - Register **at least two authenticators** immediately upon onboarding (e.g., MacBook Touch ID / iPhone Face ID via iCloud Keychain + one offline YubiKey FIDO2 hardware key).
   - Sign in with the secondary hardware key at `https://trilunair.medinsup.com` → **Governance & Security** → **Revoke** the lost Credential ID immediately.
2. **Emergency Offline Recovery Path — Single-Use PBKDF2 Recovery Code:**
   - Open `https://trilunair.medinsup.com` (gated by Cloudflare Zero Trust Access owner email).
   - Navigate to **Governance & Security → Biometric Passkey Gate → Recover via One-Time Emergency Code**.
   - Enter one unused offline recovery code (`TRIL-XXXX-XXXX-XXXX`). The backend atomically marks `used_at` so the code can never be replayed, establishes a fresh `__Host-trilunair_admin_session` + `X-Step-Up-Token`, and lets you revoke the lost Passkey and enroll your replacement device.
3. **Break-Glass SSH Console Reset (If All Devices & Recovery Codes Are Lost):**
   - Connect via key-only SSH to the dedicated Tokyo TRILUNAIR VM and rotate `TRILUNAIR_ADMIN_SECRET_HASH` in `/etc/trilunair/trilunair.env`, restart `systemctl restart trilunair-engine`, sign in once via `/api/auth/session`, generate fresh recovery codes, and register a new Passkey.

---

## 2. Encrypted PostgreSQL Backup & Point-in-Time / Snapshot Restore
Daily automated backups run via [`deploy/postgresql/backup_verify_restore.sh`](file:///home/antigravity/my-road-to-be-trilunair/deploy/postgresql/backup_verify_restore.sh) producing AES-256-CBC (PBKDF2 600,000-iteration) encrypted snapshots (`*.dump.enc` + `.sha256`).

### Restore Procedure on Fresh or Replacement Linux VM
```bash
# 1. Verify SHA-256 integrity of encrypted archive before decryption
sha256sum -c /var/backups/trilunair/trilunair_<TIMESTAMP>.dump.enc.sha256

# 2. Stop FastAPI engine to prevent concurrent writes during restore
sudo systemctl stop trilunair-engine

# 3. Decrypt archive to a root-only temporary file (0600 permissions)
umask 0077
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -pass file:/etc/trilunair/backup.passphrase \
  -in /var/backups/trilunair/trilunair_<TIMESTAMP>.dump.enc \
  -out /tmp/trilunair_restore.dump

# 4. Recreate clean database and restore custom dump
sudo -u postgres dropdb --if-exists trilunair
sudo -u postgres createdb --owner=trilunair_app trilunair
sudo -u postgres pg_restore --dbname=trilunair --no-owner --no-privileges /tmp/trilunair_restore.dump
shred -u /tmp/trilunair_restore.dump

# 5. Restart engine (schema auto-migration & PAPER mode safety lock verify on boot)
sudo systemctl start trilunair-engine
curl -fsS http://127.0.0.1:8000/api/health
```

---

## 3. Cloud VM Failure / Region Migration Failover (Tokyo → Osaka or Singapore)
If the primary Tokyo VM (`ap-northeast-1` / `ap-tokyo-1`) experiences a host or zone outage:
1. Provision a clean Ubuntu 24.04 LTS VM in the secondary candidate region (**Osaka `ap-osaka-1`** or **Singapore `ap-southeast-1`**).
2. Run [`deploy/linux-systemd/install_native_ubuntu.sh`](file:///home/antigravity/my-road-to-be-trilunair/deploy/linux-systemd/install_native_ubuntu.sh).
3. Restore the latest encrypted PostgreSQL snapshot (`/var/backups/trilunair/*.dump.enc`) using Section 2 above.
4. Copy `/etc/trilunair/trilunair.env` and `/etc/cloudflared/trilunair-tunnel.json` (or issue a new Cloudflare Tunnel token in Cloudflare Zero Trust Dashboard → Networks → Tunnels).
5. Start `trilunair-engine` and `cloudflared-trilunair`. Because Cloudflare Tunnel is outbound-only, **`trilunair.medinsup.com` fails over with zero firewall openings and zero changes to `medinsup.com`**.

---

## 4. Cloudflare Tunnel Compromise / Token Rotation
If a tunnel credential is ever suspected of exposure:
1. In Cloudflare Zero Trust → **Networks → Tunnels**, revoke the old `trilunair` tunnel token immediately.
2. Generate a new tunnel credential JSON into `/etc/cloudflared/trilunair-tunnel.json` (`chmod 0400`, owned by `cloudflared:cloudflared`).
3. Run `sudo systemctl restart cloudflared-trilunair`.

---

## 5. Clean Git Rollback to Verified Baselines
Both historical verified tags are preserved untouched in Git:
- **`v1.1.0-cloud-paper`** (`1337db3`) — Cloud-hardened PAPER baseline prior to Cloudflare/WebAuthn v1.2 additions.
- **`v1.0.0-paper-verified`** (`fc3ee21`) — Original verified local/Docker PAPER baseline.

```bash
# Roll back application code on the dedicated TRILUNAIR VM to v1.1.0-cloud-paper:
cd /opt/trilunair/app
sudo systemctl stop trilunair-engine
sudo -u trilunair git checkout v1.1.0-cloud-paper
cd backend && sudo -u trilunair uv sync --frozen
sudo systemctl start trilunair-engine
curl -fsS http://127.0.0.1:8000/api/system/status | jq '{version, tradingMode, liveAuthorized}'
```
All `v1.2` PostgreSQL tables (`owner_passkeys`, `webauthn_challenges`, `owner_recovery_codes`) are strictly additive (`CREATE TABLE IF NOT EXISTS`), so rolling back to `v1.1.0-cloud-paper` requires **zero destructive schema downgrades**.
