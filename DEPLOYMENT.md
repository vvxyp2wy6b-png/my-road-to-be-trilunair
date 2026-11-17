# دليل النشر السحابي، التصليب الأمني، والنسخ الاحتياطي الخاص
## Cloud Deployment, Security Hardening & Private Backup Guide — `v1.1.0-cloud-paper`

---

## 1. القواعد الأمنية غير القابلة للتفاوض (Non-Negotiable Safety Lock)
- **وضع التنفيذ مقفل نهائياً على `PAPER`** (`liveAuthorized = false`) طوال الإصدار `v1.1.0-cloud-paper`.
- التداول الذاتي الحقيقي (`AUTONOMOUS`) والأوامر المالية الحقيقية والسحوبات والهامش والرافعة المالية والعقود الآجلة **معطلة ومحظورة برمجياً**.
- الاتصال العام ببيانات سوق Binance Spot (`https://data-api.binance.vision`) مخصص **لقراءة الأسعار الحية ودفتر الأوامر والشموع فقط** بينما يظل التنفيذ ورقياً محاكياً بنسبة 100%.
- تمت إزالة جميع رموز PIN التجريبية الافتراضية نهائياً؛ تعمل مصادقة المسؤول بنظام **الإغلاق الآمن (`Fail-Closed` — HTTP 503)** ما لم يتم تزويد تجزئة قوية في `TRILUNAIR_ADMIN_SECRET_HASH`.

---

## 2. توليد الأسرار المشفرة وتجهيز ملف `.env`
انسخ القالب الخالي من الأسرار واضبط القيم على خادمك أو جهازك:
```bash
cp .env.example .env
```

توليد تجزئة `PBKDF2-HMAC-SHA256` لسر المسؤول (8 محارف قوية فأكثر) ومفتاح توقيع الجلسات:
```bash
cd backend
uv run python -c "import secrets; from app.security import hash_admin_secret; print('TRILUNAIR_SESSION_SECRET=' + secrets.token_hex(32)); print('TRILUNAIR_ADMIN_SECRET_HASH=\x27' + hash_admin_secret('REPLACE_WITH_YOUR_STRONG_PASSPHRASE') + '\x27')"
```

| المتغير | الوصف | الحالة في `v1.1.0-cloud-paper` |
|---|---|---|
| `TRILUNAIR_DEFAULT_MODE` | وضع التداول المقفل برمجياً | `PAPER` (إلزامي ودائم) |
| `TRILUNAIR_ADMIN_SECRET_HASH` | تجزئة `PBKDF2-HMAC-SHA256` لسر المسؤول | إلزامي للعمليات الإدارية (`Fail-Closed`) |
| `TRILUNAIR_SESSION_SECRET` | سر توقيع جلسات `HMAC-SHA256` (`HttpOnly` + `X-CSRF-Token`) | إلزامي للإنتاج |
| `TRILUNAIR_ALLOWED_ORIGINS` | قائمة النطاقات المسموحة لـ `CORS` و`WebSocket Origin` | قائمة محددة بدون `*` |
| `TRILUNAIR_MARKET_DATA_MODE` | مصدر بيانات السوق (`LIVE_PUBLIC` لبينانس العام أو `SIMULATED`) | `LIVE_PUBLIC` |
| `DATABASE_URL` | عنوان اتصال `PostgreSQL 16` المستديم | `postgresql://trilunair:<STRONG_PW>@postgres:5432/trilunair` |
| `REDIS_URL` | عنوان اتصال `Redis 7` لأقفال منع تكرار الأوامر والصلاحية الزمنية | `redis://redis:6379/0` |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `XAI_API_KEY` | مفاتيح اختيارية لمزودات الوكلاء السحابية والصوت | اختيارية (تُعلَم كـ `UNAVAILABLE_NO_KEY` عند غيابها) |

---

## 3. النشر على macOS عبر Docker Desktop أو على خادم سحابي (HTTPS + WSS)

### أ) التشغيل على macOS مع Docker Desktop
```bash
docker compose up --build -d
docker compose ps
```

### ب) التشغيل السحابي الكامل مع TLS تلقائي (`https://` + `wss://` لمتصفح Safari على macOS / iOS)
يقوم ملف `docker-compose.cloud.yml` مع `deploy/Caddyfile` بتشغيل خادم `Caddy 2` كوكيل عكسي يصدر شهادات TLS تلقائياً ويمرر اتصالات REST API وحزمة React SPA وبث `wss://<YOUR_DOMAIN>/ws/market`:
```bash
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up --build -d
```

### ج) التحقق من صحة الخدمات بعد النشر
```bash
curl -fsS https://<YOUR_DOMAIN>/api/health
curl -fsS https://<YOUR_DOMAIN>/api/system/operations
```

---

## 4. سياسة المخاطر الموحدة المعتمدة (Unified 5-Limit Risk Policy)
تُطبق الحدود الخمسة التالية بشكل متطابق عبر قاعدة البيانات ومحرك المخاطر الحتمي والواجهة الأمامية:
1. **أقصى مخاطرة لكل صفقة (`STOP_LOSS_RISK_LIMIT`):** `0.5%` من إجمالي حقوق الملكية.
2. **أقصى تعرض / تركز للأصل الواحد (`MAX_CONCENTRATION` & `MAX_ORDER_NOTIONAL`):** `25.0%` من إجمالي حقوق الملكية.
3. **قاطع الخسارة اليومية (`DAILY_DRAWDOWN_LIMIT`):** `2.0%`.
4. **قاطع الخسارة الأسبوعية (`WEEKLY_LOSS_LIMIT`):** `5.0%`.
5. **أقصى سحب تراكمي مسموح (`MAX_DRAWDOWN_LIMIT`):** `10.0%`.

---

## 5. إجراء النسخ الاحتياطي الآمن إلى مستودع GitHub خاص (Private GitHub Backup)
لدفع النسخة الموثقة والوسوم (`v1.0.0-paper-verified` و `v1.1.0-cloud-paper`) إلى مستودع GitHub **خاص (Private)** دون تسريب أي أسرار:
1. تحقق أولاً من خلو شجرة العمل من أي ملفات بيئة حساسة:
   ```bash
   git status --ignored
   ```
2. أنشئ مستودعاً خاصاً فارغاً (`Private Repository`) على حسابك في GitHub باسم `my-road-to-be-trilunair`.
3. اربط المستودع البعيد وادفع الفرع الرئيسي وفرع الإصدار والوسوم الموثقة:
   ```bash
   git remote add origin git@github.com:<YOUR_GITHUB_USER>/my-road-to-be-trilunair.git
   git push -u origin main
   git push -u origin release/cloud-paper-v1.1
   git push origin --tags
   ```
