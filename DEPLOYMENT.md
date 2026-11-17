# دليل النشر منخفض الكمون بدون Docker عبر Cloudflare و Ubuntu 24.04
## Cloudflare-First, Docker-Free Production Deployment Guide — `v1.2.0-low-latency-cloudflare`

---

## 1. العزل الصارم عن المنصة الطبية `medinsup.com` والقفل الدائم على `PAPER`
- **عزل السيادة الطبية (`medinsup.com`):** يعمل نظام التداول حصرياً على النطاق الفرعي المستقل **`https://trilunair.medinsup.com`** فوق خادم سحابي مخصص وجديد بالكامل (الموصى به مبدئياً: **طوكيو `Tokyo` — AWS Lightsail 2 GB بتكلفة \$12/شهرياً مع SLA أو Oracle Cloud Tokyo Always Free بتكلفة \$0/شهرياً** بعد تنفيذ فحص الكمون الميداني).
- **حظر المساس بـ `medinsup.com`:** لا يتم تعديل أي سجل DNS قائم للنطاق الرئيسي (`@` أو `www`) أو خوادم الرياض الطبية أو قواعد بياناتها أو شهاداتها، وتُربط الجلسات حصرياً بـ `__Host-trilunair_admin_session` (`Host-Only` بدون `Domain=.medinsup.com`).
- **القفل الدائم على `PAPER`:** يظل `tradingMode = "PAPER"` و `liveAuthorized = false` و `executionLockedToPaper = true` طوال الإصدار `v1.2.0-low-latency-cloudflare`؛ لا يتم إرسال أي أوامر تداول حقيقية مطلقاً.

---

## 2. قياس الكمون الميداني من الخادم السحابي قبل تثبيت المنطقة نهائياً
انسخ السكربت القياسي المستقل (بدون أي اعتماديات خارجية) إلى الخادم السحابي المرشح في طوكيو / أوساكا / سنغافورة / فرانكفورت، ونفذه لقياس الـ 15 مؤشراً ضد نقاط Binance Spot العامة:

```bash
python3 scripts/benchmark_region_probe.py \
  --region-id tokyo-lightsail-apne1 \
  --region-label "Tokyo, Japan (AWS Lightsail ap-northeast-1)" \
  --provider "AWS Lightsail 2 GB" \
  --monthly-cost-usd 12.0 \
  --samples 50 \
  --ws-duration 30 \
  --output probes/tokyo-lightsail.json

python3 scripts/compare_regional_benchmarks.py --probes-dir probes
```

---

## 3. النشر الأصلي السريع بدون Docker (Native Linux `systemd` + PostgreSQL 16 + Cloudflare Tunnel)

### الخطوة 1: تجهيز نظام Ubuntu 24.04 LTS وتصليب الجدار الناري (`UFW`)
على الخادم السحابي الجديد المخصص لـ `trilunair` فقط:
```bash
sudo bash deploy/linux-systemd/install_native_ubuntu.sh
```

### الخطوة 2: إعداد قاعدة بيانات PostgreSQL 16 المحلية (`127.0.0.1:5432` فقط)
```bash
sudo cp deploy/postgresql/postgresql-trilunair.conf /etc/postgresql/16/main/conf.d/99-trilunair-hardening.conf
sudo cp deploy/postgresql/pg_hba-trilunair.conf /etc/postgresql/16/main/pg_hba.conf
sudo systemctl restart postgresql

sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE trilunair_app WITH LOGIN PASSWORD '<REPLACE_WITH_STRONG_SCRAM_PASSWORD>';
CREATE DATABASE trilunair OWNER trilunair_app;
REVOKE ALL ON DATABASE trilunair FROM PUBLIC;
SQL
```

### الخطوة 3: تثبيت التطبيق وبناء الواجهة الأمامية وتشغيل `systemd`
```bash
sudo -u trilunair git clone <PRIVATE_REPO_URL> /opt/trilunair/app
cd /opt/trilunair/app
sudo -u trilunair git checkout v1.2.0-low-latency-cloudflare

# تثبيت بيئة Python الأصلية السريعة عبر uv
cd /opt/trilunair/app/backend
sudo -u trilunair uv sync --frozen

# بناء حزمة React SPA (أو نشرها مباشرة على Cloudflare Pages مع frontend/public/_headers)
cd /opt/trilunair/app/frontend
npm ci && npm run build

# إعداد ملف البيئة المحمي 0640
sudo cp /opt/trilunair/app/.env.example /etc/trilunair/trilunair.env
sudo chown root:trilunair /etc/trilunair/trilunair.env && sudo chmod 0640 /etc/trilunair/trilunair.env

# تفعيل خدمات systemd المعزولة
sudo cp /opt/trilunair/app/deploy/linux-systemd/trilunair-engine.service /etc/systemd/system/
sudo cp /opt/trilunair/app/deploy/linux-systemd/cloudflared-trilunair.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trilunair-engine
```

### الخطوة 4: ربط Cloudflare Tunnel و Cloudflare Zero Trust Access (بموافقة المالك)
1. من لوحة **Cloudflare Zero Trust → Networks → Tunnels**، أنشئ نفقاً مخصصاً باسم `trilunair-tokyo` وضع بيانات اعتماده في `/etc/cloudflared/trilunair-tunnel.json` وملف [`deploy/cloudflare/cloudflared-config.yml`](file:///home/antigravity/my-road-to-be-trilunair/deploy/cloudflare/cloudflared-config.yml) في `/etc/cloudflared/cloudflared-config.yml`.
2. أضف سجل `CNAME` **واحداً فقط** للنطاق الفرعي المستقل `trilunair` يشير إلى `<TUNNEL_UUID>.cfargotunnel.com` (دون المساس مطلقاً بأي سجل من سجلات `medinsup.com`).
3. طبّق سياسة المالك الوحيد من [`deploy/cloudflare/zero-trust-access-policy.json`](file:///home/antigravity/my-road-to-be-trilunair/deploy/cloudflare/zero-trust-access-policy.json) لحماية `trilunair.medinsup.com`.
4. شغّل النفق الصادر: `sudo systemctl enable --now cloudflared-trilunair`.

---

## 4. تسجيل بصمة المالك (Face ID / Touch ID / Security Key) والنسخ الاحتياطي المشفر
1. افتح `https://trilunair.medinsup.com` وسجّل الدخول الأولي للمسؤول ثم افتح **الحوكمة والأمان → المصادقة البيومترية للمالك (WebAuthn Passkeys)**.
2. سجّل مفتاح مرور `Face ID` أو `Touch ID` بالإضافة إلى مفتاح أمان احتياطي، وولّد رموز الاسترداد الطارئة لمرة واحدة واحفظها خارج الاتصال، ثم فعّل `TRILUNAIR_REQUIRE_PASSKEY_STEP_UP=true`.
3. فعّل النسخ الاحتياطي المشفر اليومي لـ PostgreSQL عبر `cron` أو `systemd-timer` لتشغيل [`deploy/postgresql/backup_verify_restore.sh`](file:///home/antigravity/my-road-to-be-trilunair/deploy/postgresql/backup_verify_restore.sh).
4. لإجراءات الاسترداد من الكوارث أو التراجع إلى `v1.1.0-cloud-paper` راجع [`RECOVERY_AND_ROLLBACK.md`](file:///home/antigravity/my-road-to-be-trilunair/RECOVERY_AND_ROLLBACK.md).
