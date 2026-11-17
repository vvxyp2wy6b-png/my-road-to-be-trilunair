# دليل النشر والتشغيل الإنتاجي وضوابط الأمان
## Deployment & Safety Guide — My Road to be Trilunair Dr.MaJoOoOoOoD

---

## 1. المتطلبات المسبقة (Prerequisites)
- **للتشغيل عبر الحاويات (موصى به للإنتاج والوصول من متصفح Safari/Chrome محلياً)**: Docker 24+ و Docker Compose v2+.
- **للتشغيل المباشر بدون حاويات**:
  - Python `3.11+` مع مدير الحزم `uv`.
  - Node.js `22+` أو `24 LTS` مع `npm`.
  - قاعدة بيانات `PostgreSQL 15+` و `Redis 7+` (أو وضع SQLite المحلي عند عدم ضبط `DATABASE_URL`).

---

## 2. إعداد متغيرات البيئة (`.env`)
انسخ ملف الإعداد النموذجي واضبط القيم الإنتاجية قبل النشر:
```bash
cp .env.example .env
```

| المتغير | الوصف | القيمة الافتراضية |
|---|---|---|
| `TRILUNAIR_DEFAULT_MODE` | وضع التداول عند الإقلاع (يبقى `PAPER` افتراضياً لضمان الأمان) | `PAPER` |
| `TRILUNAIR_ADMIN_PIN` | رمز التصريح السري لتفعيل التداول الحقيقي وتوقيع الأوامر | `7777` (غيّره في الإنتاج!) |
| `DATABASE_URL` | عنوان اتصال PostgreSQL المستديم | `postgresql://trilunair:trilunair_secret@postgres:5432/trilunair` |
| `REDIS_URL` | عنوان اتصال Redis لأقفال منع تكرار الأوامر وانتهاء صلاحية المقترحات | `redis://redis:6379/0` |
| `TRILUNAIR_DB_PATH` | مسار SQLite البديل عند عدم ضبط `DATABASE_URL` | `./data/trilunair.db` |
| `OPENAI_API_KEY` | مفتاح اختياري لمزود OpenAI (Whisper STT / TTS + مداولات الوكلاء) | فارغ |
| `GEMINI_API_KEY` | مفتاح اختياري لمزود Google Gemini في مجلس الوكلاء | فارغ |
| `ANTHROPIC_API_KEY` | مفتاح اختياري لمزود Anthropic Claude في مجلس الوكلاء | فارغ |
| `XAI_API_KEY` | مفتاح اختياري لمزود xAI Grok في مجلس الوكلاء | فارغ |
| `BINANCE_SPOT_API_KEY` | مفتاح قراءة/اختبار Binance Spot (مع `BINANCE_SPOT_BASE_URL` للبيئة الاختبارية) | فارغ |

---

## 3. النشر الكامل باستخدام Docker Compose (PostgreSQL + Redis + FastAPI + React SPA)
يقوم ملف `docker-compose.yml` بتشغيل ثلاث خدمات متكاملة:
1. `postgres` (`postgres:16-alpine`) مع وحدة تخزين دائمة `trilunair_pg_data` وفحص `pg_isready`.
2. `redis` (`redis:7-alpine`) مع تفعيل `appendonly yes` ووحدة تخزين `trilunair_redis_data`.
3. `trilunair-command-center` المبني عبر `Dockerfile` متعدد المراحل (يبني `frontend/dist` ويشغل `FastAPI` بمستخدم غير جذري `trilunair`).

لتشغيل المنظومة على جهازك الشخصي أو خادم سحابي والوصول إليها من متصفح Safari/Chrome:
```bash
git clone <YOUR_REPO_URL> my-road-to-be-trilunair
cd my-road-to-be-trilunair
cp .env.example .env
docker compose up --build -d
docker compose ps
```
> عند التشغيل على جهازك الشخصي مباشرةً (وليس داخل حاوية سحابية معزولة)، افتح التطبيق عبر المتصفح على المنفذ المُعلَن `8000`، أو اربطه بنطاق HTTPS عكسي (`Caddy` / `Nginx` / `Cloudflare Tunnel`) عند التشغيل على خادم بعيد.

---

## 4. ضوابط الأمان المالي الإلزامية (Mandatory Financial Safety Controls)
1. **التداول الورقي افتراضياً (`PAPER`)**:
   - يقلع النظام دائماً في وضع `PAPER` بمحفظة افتراضية قدرها \$1,000,000 ولا ينفذ أي أوامر مالية حقيقية.
2. **محرك المخاطر الحتمي ومنع التكرار وانتهاء الصلاحية**:
   - حد مخاطرة وقف الخسارة لكل صفقة: `0.5%` كحد أقصى من حقوق الملكية (`STOP_LOSS_RISK_LIMIT`).
   - حد حجم الأمر الواحد: `25%` من حقوق الملكية، وحد التركز للأصل الواحد: `35%`.
   - فحص تقادم بيانات السوق (`STALE_MARKET_DATA`) وحالة عدم يقين الحساب (`ACCOUNT_STATE_UNCERTAIN`).
   - صلاحية زمنية إلزامية لكل مقترح (`expiresAt`) ومنع ذري لتكرار الأوامر عبر `clientOrderId` وأقفال Redis وفهارس قاعدة البيانات الفريدة.
3. **مفتاح الإيقاف الطارئ (Emergency Kill Switch)**:
   - يلغي فوراً كافة المقترحات المعلقة (`CANCELLED_BY_KILL_SWITCH`)، يجمّد أي تنفيذ جديد، ويعيد النظام فوراً إلى وضع `PAPER`.
