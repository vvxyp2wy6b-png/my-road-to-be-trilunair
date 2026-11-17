# بنية النظام وعقد التكامل (Architecture & API Contract)
## مشروع: My Road to be Trilunair Dr.MaJoOoOoOoD
### مركز القيادة الهولوغرامي الفاخر ونظام الأوامر الصوتية بالذكاء الاصطناعي

---

## 1. المبادئ الحاكمة والأمان المالي (Core Safety & Governance)
1. **التداول الورقي افتراضياً (Paper Trading Default)**:
   - يبدأ النظام دائماً في وضع `PAPER` برصيد افتراضي تجريبي قدره `$1,000,000.00` (في رحلة الوصول إلى التريليون — Trilunair).
   - يُمنع منعاً باتاً تفعيل التداول الحقيقي (`LIVE`) إلا عبر بوابة تصاريح المسؤول (`POST /api/auth/trading-mode`) بعد اجتياز كافة فحوصات الأمان الحتمية وإدخال رمز التصريح الإداري الصريح وعبارة التأكيد.
2. **وحدة السياسات للأوامر الصوتية والنصية واليدوية (Unified Authorization Policy)**:
   - تمر جميع الأوامر المالية (سواء صدرت من الإدخال الصوتي `source="VOICE"` أو المحادثة النصية `source="TEXT"` أو تذكرة التداول المباشرة `source="TERMINAL"`) عبر نفس خط الأنابيب الحتمي:
     `CommandValidator` -> `DeterministicRiskEngine` -> `AuthorizationGateway` -> `ExecutionEngine`.
   - لا يُنفذ أي أمر مالي ناتج عن الصوت أو المحادثة تلقائياً دون إصدار **مقترح صفقة مهيكل (`TradeProposal`)** واجتياز فحص المخاطر وتوقيع التصريح الصريح (`POST /api/orders/execute`).

---

## 2. نقاط النهاية الخلفية (Backend REST & WebSocket API - Port `8000`)

### أ. حالة النظام وبوابة التصاريح (`/api/system` & `/api/auth`)
- `GET /api/system/status`:
  ```json
  {
    "appName": "My Road to be Trilunair Dr.MaJoOoOoOoD",
    "version": "1.0.0",
    "tradingMode": "PAPER",
    "killSwitchActive": false,
    "liveAuthorized": false,
    "safetyChecks": {
      "riskEngineVerified": true,
      "maxDrawdownConfigured": true,
      "killSwitchReady": true,
      "positionLimitsActive": true,
      "auditTrailHealthy": true
    },
    "providers": {
      "llmProvider": "deterministic-council+optional-cloud",
      "sttProvider": "web-speech+server-fallback",
      "ttsProvider": "speech-synthesis+server-wav"
    }
  }
  ```
- `POST /api/auth/trading-mode`:
  - Request:
    ```json
    {
      "targetMode": "LIVE" | "PAPER",
      "adminPin": "string",
      "confirmationPhrase": "AUTHORIZE LIVE TRADING DR MAJOOOOOOD",
      "acknowledgeRealCapitalRisk": true
    }
    ```
  - يتحقق من `safetyChecks` كافة + `adminPin` (الافتراضي القابل للتهيئة عبر البيئة `TRILUNAIR_ADMIN_PIN`، القيمة التجريبية `7777` موثقة بوضوح للاختبار) + عبارة التأكيد، ويرفض فوراً إذا كان مفتاح الإيقاف الطارئ (`killSwitchActive`) مفعلاً.
- `POST /api/auth/kill-switch`:
  - Request: `{ "active": true | false, "reason": "string" }`
  - عند التفعيل، يعيد النظام فوراً إلى وضع `PAPER` ويجمد تنفيذ الصفقات الجديدة ويلغي المقترحات المعلقة.
- `GET /api/auth/audit-logs`: يعيد سجل التدقيق الأمني الكامل لجميع الأوامر الصوتية والنصية والقرارات.

### ب. الأسواق والمحفظة والأوامر وفحص المخاطر (`/api/market`, `/api/portfolio`, `/api/orders`)
- `GET /api/market/assets`: قائمة الأصول المتاحة (`BTC-USD`, `ETH-USD`, `NVDA`, `XAU-USD`, `SOL-USD`, `ARAMCO.SR`) مع الأسعار الحية، التغير المئوي، السيولة، التقلب، والسبريد.
- `GET /api/market/candles/{symbol}?timeframe=15m&limit=90`: بيانات الشموع اليابانية OHLCV للرسم البياني الهولوغرامي + مستويات الدعم والمقاومة وعمق دفتر الأوامر (`bids` / `asks`).
- `GET /api/portfolio`:
  - الرصيد النقدي (`cashBalance`)، إجمالي حقوق الملكية (`totalEquity`)، الأرباح والخسائر اليومية (`dailyPnl`, `dailyPnlPct`)، التقدم نحو هدف التريليون (`trilunairProgress`)، أقصى تراجع حالي (`currentDrawdownPct`)، قيمة المخاطرة اليومية (`var95Usd`)، المراكز المفتوحة (`positions`)، وسجل الصفقات (`orders`).
- `POST /api/orders/propose`:
  - ينشئ مقترح صفقة مهيكل (`TradeProposal`) ويجري عليه فحص `CommandValidator` + `DeterministicRiskEngine` دون تنفيذ فوري:
    ```json
    {
      "symbol": "BTC-USD",
      "side": "BUY" | "SELL",
      "orderType": "MARKET" | "LIMIT",
      "quantity": 0.25,
      "limitPrice": null,
      "stopLoss": 91500,
      "takeProfit": 102000,
      "source": "VOICE" | "TEXT" | "TERMINAL",
      "rationale": "string"
    }
    ```
  - Response:
    ```json
    {
      "proposalId": "prop_...",
      "status": "APPROVED_FOR_AUTH" | "REJECTED_BY_RISK",
      "proposal": { ... },
      "estimatedCosts": {
        "notionalUsd": 24125.0,
        "spreadCostUsd": 7.24,
        "commissionUsd": 12.06,
        "slippageCostUsd": 9.65,
        "totalEstimatedCostUsd": 28.95,
        "costBps": 12.0
      },
      "riskAssessment": {
        "passed": true,
        "riskScore": 28,
        "riskLevel": "LOW" | "MODERATE" | "HIGH" | "CRITICAL",
        "postTradeConcentrationPct": 2.41,
        "varImpactUsd": 482.5,
        "checks": [
          { "code": "KILL_SWITCH", "passed": true, "messageAr": "...", "messageEn": "..." },
          { "code": "MAX_ORDER_NOTIONAL", "passed": true, "messageAr": "...", "messageEn": "..." },
          { "code": "MAX_CONCENTRATION", "passed": true, "messageAr": "...", "messageEn": "..." },
          { "code": "DAILY_DRAWDOWN_LIMIT", "passed": true, "messageAr": "...", "messageEn": "..." },
          { "code": "SUFFICIENT_BUYING_POWER", "passed": true, "messageAr": "...", "messageEn": "..." }
        ],
        "violations": []
      },
      "tradingMode": "PAPER",
      "requiresLivePin": false
    }
    ```
- `POST /api/orders/execute`:
  - Request: `{ "proposalId": "prop_...", "confirmedByUser": true, "adminPin": "optional-required-if-LIVE", "source": "VOICE" | "TEXT" | "TERMINAL" }`
  - يعيد التحقق من صلاحية المقترح وعدم انتهاء صلاحيته واجتيازه فحص المخاطر وبوابة التصاريح قبل التنفيذ وتحديث المحفظة وتسجيل سجل التدقيق.

### ج. محرك السمات الديناميكي المستديم (`/api/themes`)
- `GET /api/themes`: يعيد السمات الخمس الأساسية + السمات المخصصة المحفوظة + الإعداد النشط الحالي (`activeState`).
- `PUT /api/themes/active`: يحفظ السمة النشطة وتخصيصات المسؤول (ألوان التمييز، الخلفية، التوهج، الضبابية، الشفافية، شدة الحركة، تعطيل الحركة، التباين العالي، وضع الطاقة المنخفضة).
- `POST /api/themes/custom`: يحفظ سمة مخصصة جديدة أو يحدثها.
- `DELETE /api/themes/custom/{themeId}`: يحذف سمة مخصصة.
- `POST /api/themes/import`: يتحقق من ملف إعداد السمة المستورد ويحفظه.

### د. غرفة الأوامر الصوتية وقاعة اجتماع الوكلاء (`/api/ai` & `/api/voice`)
- `GET /api/ai/agents`: قائمة الوكلاء المتخصصين وحالتهم وتخصصهم:
  - `quant-alpha` (د. ريان — المحلل الكمي)
  - `risk-sentinel` (سارة — حارسة المخاطر)
  - `macro-oracle` (طارق — استراتيجي السيولة والاقتصاد الكلي)
  - `execution-architect` (خالد — مهندس التنفيذ وتكاليف التداول)
  - `chief-strategist` (المجلس التنفيذي — كبير المستشارين)
- `GET /api/ai/history`: سجل المحادثات والأوامر السابقة واجتماعات الوكلاء.
- `DELETE /api/ai/history`: مسح سجل المحادثة عند الطلب.
- `POST /api/ai/command`:
  - Request:
    ```json
    {
      "message": "حلل BTC وقارنها مع الذهب وجهز مقترح شراء 0.2 BTC",
      "language": "ar" | "en",
      "source": "VOICE" | "TEXT",
      "selectedAgent": "team" | "quant-alpha" | "risk-sentinel" | "macro-oracle" | "execution-architect",
      "triggerMeeting": true
    }
    ```
  - يدعم تحليل الأصول، مقارنة الفرص، شرح أداء المحفظة، تعديل إعدادات لوحة التحكم/السمات (`uiAction` مثل تغيير السمة أو تفعيل التباين العالي أو وضع الطاقة المنخفضة أو الانتقال إلى تبويب)، وإعداد مقترحات الصفقات المهيكلة (`tradeProposalEvaluation` المار عبر `CommandValidator` + `DeterministicRiskEngine` دون تنفيذ تلقائي!).
  - يعيد أيضاً كائن `meeting` كامل لقاعة اجتماع الوكلاء (`AgentMeetingResult`) يتضمن:
    - `topic`, `symbol`, `timestamp`
    - `agentResponses`: ردود كل وكيل (`agentId`, `nameAr`, `nameEn`, `roleAr`, `roleEn`, `status`, `stance`: `BUY|SELL|HOLD|CAUTION`, `confidence`, `summaryAr`, `summaryEn`, `keyMetrics`)
    - `consensus`: نسبة التوافق، نقاط الاتفاق (`agreementsAr`/`En`)، نقاط الاختلاف (`disagreementsAr`/`En`)
    - `evidenceAndUncertainty`: الأدلة الداعمة (`evidenceAr`/`En`)، عوامل عدم اليقين (`uncertaintiesAr`/`En`)، درجة عدم اليقين
    - `estimatedCosts`: التكاليف التقديرية للصفقة المقترحة أو المعيارية
    - `riskAssessment`: تقييم المخاطر الحتمي
    - `finalRecommendation`: التوصية النهائية المجمعة (`stance`, `confidence`, `headlineAr`, `headlineEn`, `actionableSummaryAr`, `actionableSummaryEn`)
- `POST /api/ai/meeting`: يعقد اجتماع طاولة مستديرة مخصص لرمز أصل معين (`symbol`, `horizon`, `language`).
- `POST /api/voice/tts`: يولد ملف صوتي أو تعليمات نطق متوافقة عند توفر مزود سحابي أو مولد صوتي محلي احتياطي، مع تكامل كامل في الواجهة مع `window.speechSynthesis` العربي والإنجليزي القابل للمقاطعة الفورية.
- `POST /api/voice/stt`: نقطة نهاية لتحويل الصوت إلى نص عبر المزود المهيأ (OpenAI Whisper / Gemini Audio إن وجد مفتاح API) مع إرجاع حالة المزود بوضوح، بالتكامل مع `SpeechRecognition` في المتصفح.

### هـ. البث الحي عبر WebSocket (`/ws/market`)
- يبث كل ثانية تحديثات الأسعار الحية (`tick`) لجميع الأصول الستة + القيمة الإجمالية المحدثة للمحفظة دون إغراق وحدة المعالجة الرسومية.
