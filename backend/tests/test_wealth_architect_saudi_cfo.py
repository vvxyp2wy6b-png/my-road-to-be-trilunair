"""
حزمة الاختبارات الشاملة للمدير المالي الشخصي (Personal CFO)، خطة الاستثمار المعتمدة،
حاسبة مستحقات نظام العمل السعودي، وذكاء مواعيد عدم تجديد العقد المحدد المدة (60 يوماً):

1. توزيع الراتب الشهري المعتمد (20,000 ريال يوم 28):
   - 8,000 مصروفات شخصية | 6,000 سداد بطاقات | 1,375 اشتراكات AI | 500 تشغيل وكلاء TRILUNAIR | 2,125 استثمار | 2,000 ادخار نقدي
   - رفض أي توزيع يتجاوز الراتب (HTTP 422).
2. منع الازدواج الحسابي عند استيراد كشوف الحساب (SHA-256 Deduplication + Bucket Reconciliation + استثناء CREDIT_CARD_PURCHASE_MEMO).
3. مخطط سداد البطاقات الائتمانية (تسهيل: 14,000 رصيد / 1,700 مستحق / 4,200 مخصص؛ بنك الإمارات دبي الوطني: 17,000 رصيد / 1,800 مستحق / 1,800 مخصص)،
   وعدم اشتراط سداد كامل الديون قبل الاستثمار، مع تفعيل أولوية المتأخرات (HTTP 409) عند نقص السيولة الفورية عن الحد الإلزامي (11,500 ريال).
4. عقد العمل السعودي المحدد المدة (بداية 2024-10-10، راتب 20,000 ريال، تجديد تلقائي ما لم يُشعر قبل 60 يوماً، 0 أيام إجازة مستخدمة):
   - عدم تصنيف عدم التجديد عند انتهاء المدة كاستقالة خلال سريان العقد تلقائياً.
   - السيناريو التوضيحي حتى 2027-10-10 (3 سنوات، 63 يوم إجازة غير مستخدم):
     * انتهاء العقد وعدم التجديد: مكافأة 30,000 + إجازات 42,000 = 72,000 ريال.
     * الاستقالة العادية (1/3 بموجب المادة 85): مكافأة 10,000 + إجازات 42,000 = 52,000 ريال.
     * إنهاء من صاحب العمل: 72,000 ريال | فسخ المادة 80: مكافأة 0 + إجازات 42,000 ريال.
   - وسم كافة التقديرات بـ PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION وعزلها تماماً عن السيولة النقدية المتاحة ورأس مال التداول.
5. ذكاء مواعيد تجديد العقد وخزنة الأدلة:
   - الموعد النهائي لـ 60 يوماً قبل 2027-10-10 هو 2027-08-11 بالضبط، مع تنبيهات 90 يوماً (2027-07-12)، 75 يوماً (2027-07-27)، و65 يوماً (2027-08-06).
   - حفظ بصمات المستندات بـ SHA-256 مع حظر الإرسال التلقائي لأي إشعار خارجي (autoSendNonRenewalNotice=False).
6. دفتر الأستاذ المخصص لرأس المال الاستثماري (2,125 ريال/شهر) ومقارنة الأصول وسيناريوهات الهبوط وبقاء التداول مقفلاً على PAPER.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.database import init_db, reset_db_init_cache
from app.main import app
from app.market_engine import market_engine
from app.quantum_hub import ensure_quantum_tables
from app.security import hash_admin_secret, rate_limiter
from app.wealth_architect import PROVISIONAL_LEGAL_LABEL, ensure_wealth_architect_tables


@pytest.fixture()
def cfo_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "wealth_architect_cfo.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("TRILUNAIR_DB_PATH", str(db_file))
    monkeypatch.setenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED")
    monkeypatch.setenv(
        "TRILUNAIR_ADMIN_SECRET_HASH",
        hash_admin_secret("SovereignOwner#Bootstrap2026!"),
    )
    monkeypatch.setenv("TRILUNAIR_SESSION_SECRET", "7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b")

    rate_limiter.reset()
    reset_db_init_cache()
    market_engine.reset()
    init_db()
    ensure_quantum_tables()
    ensure_wealth_architect_tables()
    yield db_file
    rate_limiter.reset()
    market_engine.reset()


def test_owner_approved_salary_allocation_and_anti_double_counting_statement_import(cfo_env: Path) -> None:
    """التحقق من توزيع الراتب المعتمد (20,000 ريال يوم 28) ومنع الازدواج الحسابي عند استيراد الكشوف."""
    with TestClient(app) as client:
        res = client.get("/api/wealth/overview")
        assert res.status_code == 200
        overview = res.json()

        sal = overview["salaryAndCashFlow"]
        assert sal["monthlySalarySar"] == 20000.0
        assert sal["paydayDayOfMonth"] == 28
        assert sal["plannedTotalAllocatedSar"] == 20000.0
        assert sal["unallocatedSalarySar"] == 0.0
        assert sal["balancedToExactSalary"] is True

        bucket_map = {b["category"]: b["plannedSar"] for b in sal["buckets"]}
        assert bucket_map == {
            "PERSONAL_EXPENSES": 8000.0,
            "CREDIT_CARD_REPAYMENTS": 6000.0,
            "AI_SUBSCRIPTIONS": 1375.0,
            "TRILUNAIR_AGENT_OPERATIONS": 500.0,
            "INVESTMENT_ALLOCATION": 2125.0,
            "CASH_SAVINGS": 2000.0,
        }

        # رفض أي ميزانية تتجاوز الراتب الشهري
        bad_alloc = client.put(
            "/api/wealth/allocation",
            json={
                "monthlySalarySar": 20000.0,
                "paydayDayOfMonth": 28,
                "personalExpensesSar": 9500.0,
                "creditCardRepaymentsSar": 6000.0,
                "aiSubscriptionsSar": 1375.0,
                "trilunairAgentOperationsSar": 500.0,
                "investmentAllocationSar": 2125.0,
                "cashSavingsSar": 2000.0,
            },
        )
        assert bad_alloc.status_code == 422

        # استيراد حركات كشف حساب في الدورة الحالية والتحقق من:
        # 1) عدم مضاعفة المصروف المخطط (3,200 ريال فعلي من أصل 8,000 مخطط يبقى الإجمالي المحتسب 8,000 لا 11,200)
        # 2) استثناء مشتريات البطاقة التفصيلية (CREDIT_CARD_PURCHASE_MEMO) من الجمع المزدوج مع دفعة سداد البطاقة 6,000
        # 3) منع التكرار ببصمة SHA-256 عند إعادة رفع نفس الكشف
        today_cycle_date = sal["nextPaydayDate"]  # يقع ضمن نافذة الرواتب؛ نستخدم تاريخ بداية الدورة الحالية
        cycle_start_str = sal["currentSalaryCycleId"].replace("cycle-", "")
        tx_payload = {
            "transactions": [
                {
                    "txDate": cycle_start_str,
                    "description": "Tamimi Markets Grocery & Living",
                    "amountSar": 3200.0,
                    "category": "PERSONAL_EXPENSES",
                    "accountSource": "BANK_CURRENT",
                    "entryKind": "ACTUAL_EXPENSE",
                },
                {
                    "txDate": cycle_start_str,
                    "description": "Tasheel Card Retail Purchase Memo",
                    "amountSar": 950.0,
                    "category": "PERSONAL_EXPENSES",
                    "accountSource": "TASHEEL_CARD_STATEMENT",
                    "entryKind": "CREDIT_CARD_PURCHASE_MEMO",
                },
            ]
        }
        imp1 = client.post("/api/wealth/statements/import", json=tx_payload)
        assert imp1.status_code == 200
        imp1_body = imp1.json()
        assert imp1_body["importedCount"] == 2
        assert imp1_body["duplicatesSkippedCount"] == 0
        assert imp1_body["salaryAndCashFlow"]["reconciledCycleTotalOutflowSar"] == 20000.0
        assert imp1_body["salaryAndCashFlow"]["cardPurchaseMemoExcludedFromDoubleCountSar"] == 950.0

        personal_bucket = next(
            b for b in imp1_body["salaryAndCashFlow"]["buckets"] if b["category"] == "PERSONAL_EXPENSES"
        )
        assert personal_bucket["importedActualSar"] == 3200.0
        assert personal_bucket["effectiveReconciledOutflowSar"] == 8000.0
        assert personal_bucket["remainingPlannedAllowanceSar"] == 4800.0
        assert today_cycle_date is not None

        # إعادة استيراد نفس الكشف تتخطى القيود المكررة بالكامل
        imp2 = client.post("/api/wealth/statements/import", json=tx_payload)
        assert imp2.status_code == 200
        assert imp2.json()["importedCount"] == 0
        assert imp2.json()["duplicatesSkippedCount"] == 2


def test_credit_card_repayment_plan_tradeoff_and_overdue_liquidity_priority(cfo_env: Path) -> None:
    """التحقق من خطة سداد تسهيل (4,200) وبنك الإمارات دبي الوطني (1,800) وأولوية المتأخرات عند شح السيولة."""
    with TestClient(app) as client:
        overview = client.get("/api/wealth/overview").json()
        debt = overview["debtPlanner"]
        assert debt["totalApproximateCardBalanceSar"] == 31000.0
        assert debt["totalReportedDueInclArrearsSar"] == 3500.0
        assert debt["monthlyRepaymentBudgetSar"] == 6000.0
        assert debt["allocatedAcrossCardsSar"] == 6000.0
        assert debt["budgetFullyAssigned"] is True

        cards_by_id = {c["cardId"]: c for c in debt["cards"]}
        assert cards_by_id["tasheel"]["approximateBalanceSar"] == 14000.0
        assert cards_by_id["tasheel"]["reportedAmountDueInclArrearsSar"] == 1700.0
        assert cards_by_id["tasheel"]["provisionalMonthlyAllocationSar"] == 4200.0
        assert cards_by_id["emirates_nbd"]["approximateBalanceSar"] == 17000.0
        assert cards_by_id["emirates_nbd"]["reportedAmountDueInclArrearsSar"] == 1800.0
        assert cards_by_id["emirates_nbd"]["provisionalMonthlyAllocationSar"] == 1800.0

        # التحقق من أن سداد كامل الدين ليس شرطاً مسبقاً شاملاً للاستثمار، مع عرض المفاضلة بوضوح
        tradeoff = debt["debtVsInvestmentTradeOff"]
        assert tradeoff["debtEliminationIsBlanketPrerequisite"] is False
        assert tradeoff["weightedCardFinancingCostAprPct"] > 0

        initial_entries = overview["investmentCommandCenter"]["ledgerSummary"]["entryCount"]
        assert initial_entries == 1

        # في الوضع الطبيعي (السيولة الفورية 20,000 >= الحد الإلزامي 11,500) يُسمح بقيد مخصص الاستثمار الورقي 2,125 ريال
        ok_ledger = client.post(
            "/api/wealth/investment/ledger",
            json={
                "amountSar": 2125.0,
                "diversifiedWeightPct": 45.0,
                "saudiEquitiesWeightPct": 35.0,
                "cryptoSpotPaperWeightPct": 20.0,
                "notes": "Scheduled cycle allocation",
            },
        )
        assert ok_ledger.status_code == 200
        inv_center = ok_ledger.json()["investmentCommandCenter"]
        assert inv_center["ledgerSummary"]["entryCount"] == 2
        assert inv_center["ledgerSummary"]["cumulativeAllocatedCapitalSar"] == 4250.0
        safeguards = inv_center["opportunityAndRiskAnalysis"]["executionSafeguards"]
        assert safeguards["binanceTradingMode"] == "PAPER"
        assert safeguards["liveTradingAuthorized"] is False
        assert safeguards["realMoneyOrdersPlaced"] is False
        assert safeguards["returnsGuaranteed"] is False

        # عند انخفاض السيولة الفورية المتاحة في الدورة إلى 9,500 ريال (< 8,000 مصروفات + 3,500 متأخرات = 11,500)
        # يمنح حارس الثروة الأولوية للمتأخرات والالتزامات الأساسية ويوقف التمويل الاختياري للاستثمار (HTTP 409)
        tight_cash = client.put(
            "/api/wealth/allocation",
            json={
                "monthlySalarySar": 20000.0,
                "paydayDayOfMonth": 28,
                "personalExpensesSar": 8000.0,
                "creditCardRepaymentsSar": 6000.0,
                "aiSubscriptionsSar": 1375.0,
                "trilunairAgentOperationsSar": 500.0,
                "investmentAllocationSar": 2125.0,
                "cashSavingsSar": 2000.0,
                "availableCycleCashSar": 9500.0,
            },
        )
        assert tight_cash.status_code == 200
        guardian = tight_cash.json()["wealthGuardian"]
        assert guardian["guardianStatus"] == "HALT_OPTIONAL_INVESTMENT_PRIORITIZE_OVERDUE_DUES"
        assert guardian["recommendedCycleInvestmentSar"] == 0.0

        blocked_ledger = client.post(
            "/api/wealth/investment/ledger",
            json={"amountSar": 2125.0},
        )
        assert blocked_ledger.status_code == 409
        assert "OVERDUE_OBLIGATION_PRIORITY" in blocked_ledger.json()["detail"]


def test_saudi_employment_contract_benefits_60day_deadline_and_balance_sheet_segregation(cfo_env: Path) -> None:
    """التحقق القانوني والمحاسبي لحاسبة نظام العمل السعودي وموعد إشعار 60 يوماً (2027-08-11) وعزل المستحقات."""
    with TestClient(app) as client:
        overview = client.get("/api/wealth/overview").json()
        emp = overview["employmentBenefits"]

        assert emp["statusLabel"] == PROVISIONAL_LEGAL_LABEL
        assert emp["accountingTreatment"] == "CONTINGENT_FUTURE_RECEIVABLE"
        assert emp["countedAsAvailableLiquidCash"] is False
        assert emp["countedInLiquidEmergencyReserve"] is False
        assert emp["usableForTradingOrImmediateDebtPayments"] is False
        assert emp["legalEntitlementGuaranteedWithoutReview"] is False

        cs = emp["contractSummary"]
        assert cs["commencementDate"] == "2024-10-10"
        assert cs["illustrativeOrTargetEndDate"] == "2027-10-10"
        assert cs["contractType"] == "FIXED_TERM"
        assert cs["autoRenews"] is True
        assert cs["nonRenewalNoticeDays"] == 60
        assert cs["expectedDepartureMethod"] == "NON_RENEWAL_UPON_EXPIRY"
        assert cs["annualLeaveTakenDays"] == 0.0
        assert cs["accruedUnusedLeaveDays"] == 63.0
        assert cs["exactExpiryDateVerified"] is False

        # 1) السيناريو الأساسي المتوقع: انتهاء العقد المحدد المدة وعدم تجديده (لا يُصنف تلقائياً كاستقالة خلال العقد)
        non_renewal = emp["scenarios"]["fixedTermExpiryNonRenewal"]
        assert non_renewal["classifiedAsMidTermResignation"] is False
        assert non_renewal["eosbAwardSar"] == 30000.0
        assert non_renewal["unusedLeaveCompensationSar"] == 42000.0
        assert non_renewal["combinedEstimatedBenefitsSar"] == 72000.0
        assert non_renewal["statusLabel"] == PROVISIONAL_LEGAL_LABEL

        # 2) سيناريو الاستقالة العادية (ثلث المكافأة لخدمة 3 سنوات بموجب المادة 85 + كامل رصيد الإجازات)
        resignation = emp["scenarios"]["ordinaryResignation"]
        assert resignation["classifiedAsMidTermResignation"] is True
        assert resignation["eosbAwardSar"] == 10000.0
        assert resignation["unusedLeaveCompensationSar"] == 42000.0
        assert resignation["combinedEstimatedBenefitsSar"] == 52000.0

        # 3) إنهاء من صاحب العمل وفسخ المادة 80
        emp_term = emp["scenarios"]["employerInitiatedTermination"]
        assert emp_term["combinedEstimatedBenefitsSar"] == 72000.0
        art80 = emp["scenarios"]["otherStatutoryScenarios"]["dismissalForCauseArt80"]
        assert art80["eosbAwardSar"] == 0.0
        assert art80["unusedLeaveCompensationSar"] == 42000.0

        # قائمة بنود التحقق السبعة قبل الاعتماد النهائي
        assert len(emp["verificationChecklist"]) >= 7

        # 4) ذكاء مواعيد تجديد العقد: 2027-10-10 ناقص 60 يوماً = 2027-08-11 بالضبط + تنبيهات 90/75/65 يوماً
        intel = overview["contractRenewalIntelligence"]
        assert intel["contractExpiryDate"] == "2027-10-10"
        assert intel["requiredAdvanceNoticeDays"] == 60
        assert intel["finalNoticeDeadlineDate"] == "2027-08-11"
        assert intel["autoSendNonRenewalNotice"] is False
        reminders_by_days = {r["daysBeforeExpiry"]: r["reminderDate"] for r in intel["reminders"]}
        assert reminders_by_days[90] == "2027-07-12"
        assert reminders_by_days[75] == "2027-07-27"
        assert reminders_by_days[65] == "2027-08-06"

        # 5) حفظ مرجع مستند العقد في خزنة الأدلة دون إرسال أي إشعار خارجي تلقائي
        ev_res = client.post(
            "/api/wealth/contract/evidence",
            json={
                "documentType": "QIWA_CONTRACT_EXTRACT",
                "title": "Qiwa Fixed-Term Contract Clause 60-Day Notice Extract",
                "contentOrReferenceForHash": "QIWA-2024-10-10-FIXED-TERM-60D-AUTO-RENEW",
                "deliveryChannel": "QIWA_PLATFORM",
                "verifiedByOwner": True,
            },
        )
        assert ev_res.status_code == 200
        ev_body = ev_res.json()
        assert ev_body["autoNoticeSent"] is False
        assert len(ev_body["documentSha256"]) == 64

        # 6) التحقق من عزل الميزانية العمومية ومنع احتساب الـ 72,000 ريال ضمن النقد المتاح
        bs = overview["balanceSheetAndForecast"]
        assert bs["liquidAssetsAvailableNow"]["includesUnreceivedEmploymentBenefits"] is False
        assert bs["contingentFutureReceivablesSegregated"]["usableForImmediateDebtOrTrading"] is False
        assert bs["contingentFutureReceivablesSegregated"]["fixedTermNonRenewalCombinedEstimateSar"] == 72000.0
        assert bs["thirtySixMonthIllustrativeForecast"]["assumesSpeculativeMarketGains"] is False

        # 7) اختبار التفاعل عبر شريط الأوامر العربي للمدير المالي الشخصي وبقاء وضع PAPER
        cmd_res = client.post(
            "/api/ai/command",
            json={
                "message": "احسب مكافأة نهاية الخدمة وموعد إشعار عدم تجديد العقد",
                "source": "TEXT",
                "language": "ar",
            },
        )
        assert cmd_res.status_code == 200
        reply_ar = cmd_res.json()["assistantMessage"]["contentAr"]
        assert "2027-08-11" in reply_ar
        assert "72,000" in reply_ar

        sys_st = client.get("/api/system/status").json()
        assert sys_st["tradingMode"] == "PAPER"
        assert sys_st["liveAuthorized"] is False
