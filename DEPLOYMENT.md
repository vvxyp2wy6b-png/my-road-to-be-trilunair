# دليل النشر والتشغيل الإنتاجي وضوابط الأمان
## Deployment & Safety Guide — My Road to be Trilunair Dr.MaJoOoOoOoD

---

## 1. المتطلبات المسبقة (Prerequisites)
- **للتشغيل عبر الحاويات (موصى به للإنتاج)**: Docker 24+ و Docker Compose v2+.
- **للتشغيل المباشر بدون حاويات**:
  - Python `3.11+` مع مدير الحزم `uv`.
  - Node.js `22+` أو `24 LTS` مع `npm`.
  - مكتبة `sqlite3` مدمجة في النظام.

---

## 2. إعداد متغيرات البيئة (`.env`)
انسخ ملف الإعداد النموذجي واضبط القيم الإنتاجية قبل النشر:
```bash
cp .env.example .env
```

| المتغير | الوصف | القيمة الافتراضية |
|---|---|---|
| `TRILUNAIR_DEFAULT_MODE` | وضع التداول عند الإقلاع (يُحظر تغييره عن `PAPER` لضمان الأمان الافتراضي) | `PAPER` |
| `TRILUNAIR_ADMIN_PIN` | رمز التصريح السري لتفعيل وضع التداول الحقيقي وتوقيع أوامره | `7777` (غيّره في الإنتاج!) |
| `TRILUNAIR_DB_PATH` | مسار ملف قاعدة بيانات SQLite المستديمة | `./data/trilunair.db` |
| `OPENAI_API_KEY` | مفتاح اختياري لتفعيل Whisper STT / TTS السحابي والنماذج اللغوية | فارغ (يعمل النظام محلياً بدونه) |
| `GEMINI_API_KEY` | مفتاح اختياري لإثراء مداولات مجلس الوكلاء عبر Gemini | فارغ |
| `ELEVENLABS_API_KEY` | مفتاح اختياري للنطق الصوتي السحابي الفاخر | فارغ |

---

## 3. النشر باستخدام Docker Compose
يقوم ملف `Dockerfile` متعدد المراحل ببناء حزمة الإنتاج للواجهة الهولوغرامية (`frontend/dist`) ثم تشغيل خادم `FastAPI` بمستخدم غير جذري (`trilunair`) وتقديم كلٍ من واجهة المستخدم ونقاط `/api` وبث `/ws/market` عبر منفذ واحد (`8000`):

```bash
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:8000/api/system/status
```

---

## 4. ضوابط الأمان المالي الإلزامية (Mandatory Financial Safety Controls)
1. **التداول الورقي افتراضياً (`PAPER`)**:
   - يقلع النظام دائماً في وضع `PAPER` حتى بعد إعادة التشغيل.
2. **شروط تفعيل التداول الحقيقي (`LIVE`)**:
   - اجتياز جميع فحوصات الجاهزية الخمسة (`riskEngineVerified`, `maxDrawdownConfigured`, `killSwitchReady`, `positionLimitsActive`, `auditTrailHealthy`).
   - عدم تفعيل مفتاح الإيقاف الطارئ (`killSwitchActive == false`).
   - إدخال رمز المسؤول الصحيح (`TRILUNAIR_ADMIN_PIN`).
   - كتابة عبارة التفويض الصريحة: `AUTHORIZE LIVE TRADING DR MAJOOOOOOD`.
   - الإقرار الصريح بمخاطر رأس المال الحقيقي.
3. **وحدة السياسات للأوامر الصوتية والنصية**:
   - لا يمكن لأي أمر صوتي أو نصي تنفيذ صفقة مباشرة؛ بل يُنشئ مقترح صفقة مهيكل (`TradeProposal`) يخضع لفحص `DeterministicRiskEngine` ويتطلب توقيع المستخدم الصريح عبر بوابة التصاريح (`AuthorizationModal`).
4. **مفتاح الإيقاف الطارئ (Emergency Kill Switch)**:
   - متاح في شاشة الحوكمة والتصاريح لإلغاء كافة المقترحات المعلقة وتجميد التنفيذ وإعادة النظام فوراً إلى وضع `PAPER`.

---

## 5. مزودات الصوت والذكاء الاصطناعي والحدود التشغيلية
- **التعرف الصوتي (STT)**: يعتمد في المتصفح مباشرة على `Web Speech API` (`SpeechRecognition` / `webkitSpeechRecognition`) باللغتين `ar-SA` و `en-US` (مدعوم في متصفحات Chromium/Edge/Safari الحديثة عبر `HTTPS` أو `localhost`)، مع نقطة نهاية خلفية `/api/voice/stt` جاهزة للربط مع OpenAI Whisper عند ضبط `OPENAI_API_KEY`.
- **تحويل النص إلى كلام (TTS)**: يعمل محلياً عبر `window.speechSynthesis` مع اختيار أفضل صوت عربي/إنجليزي متاح ومقاطعة فورية، بالإضافة إلى نقطة `/api/voice/tts` الخلفية.
- **استقلالية النص**: تعمل جميع قدرات المحادثة واجتماعات الوكلاء وتجهيز مقترحات الصفقات نصياً بنسبة 100% حتى بدون ميكروفون أو بدون مفاتيح سحابية خارجية.
