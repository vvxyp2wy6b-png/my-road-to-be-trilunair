"""
Personal CFO, Wealth Architect, Debt Planner, Saudi Employment Benefits Calculator,
Contract Renewal Deadline Intelligence, Investment Capital Allocation Ledger & Wealth Guardian.

المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD (QUANTUM AI TRADING COMMAND CENTER)

الركائز الهندسية والمالية المطبقة:
1. تخصيص الراتب الشهري المعتمد من المالك (20,000 ريال سعودي يصرف عادة يوم 28 ميلادي):
   - المصروفات الشخصية: 8,000 ريال
   - سداد البطاقات الائتمانية: 6,000 ريال (الإمارات دبي الوطني 1,800 ريال + تسهيل 4,200 ريال)
   - اشتراكات الذكاء الاصطناعي: 1,375 ريال
   - مخصص تشغيل وكلاء TRILUNAIR الذكي: 500 ريال
   - مخصص الاستثمار الشهري: 2,125 ريال
   - الادخار النقدي السائل: 2,000 ريال
   - الإجمالي المطابق: 20,000.00 ريال سعودي، مع محرك مطابقة يمنع الازدواج الحسابي عند استيراد كشوف الحساب.
2. مخطط الديون وحارس السيولة (Debt Planner & Wealth Guardian):
   - تسهيل (~14,000 ريال رصيد، 1,700 ريال مستحق يشمل متأخرات -> تخصيص 4,200 ريال)
   - بنك الإمارات دبي الوطني (~17,000 ريال رصيد، 1,800 ريال مستحق يشمل متأخرات -> تخصيص 1,800 ريال)
   - لا يُجعل تصفير البطاقات شرطاً مسبقاً شاملاً لبدء التخطيط الاستثماري، لكن تُعطى الأولوية للمتأخرات والالتزامات
     الواجبة قبل التمويل الاستثماري الاختياري إذا كانت السيولة الفورية غير كافية، مع عرض المقارنة الصريحة بين تكلفة التمويل ومخاطر الاستثمار.
3. حاسبة مستحقات العمل السعودية ومتتبع مهلة عدم التجديد (Saudi Labor Law Calculator & 60-Day Notice Intelligence):
   - تاريخ المباشرة المؤكد: 10 أكتوبر 2024، عقد محدد المدة يتجدد تلقائياً ما لم يُشعر أحد الطرفين بعدم الرغبة في التجديد قبل 60 يوماً على الأقل.
   - المغادرة المتوقعة: عدم التجديد عند انتهاء مدة العقد المحدد (لا يُصنف تلقائياً كاستقالة أثناء سريان العقد).
   - تمييز قانوني صريح بين 4 مسارات (انتهاء العقد المحدد وعدم تجديده م55/م74/م84، الاستقالة العادية م79 مكرر/م85، إنهاء صاحب العمل م74/م77/م84، والحالات النظامية الأخرى م80/م81/م87) + تعويض رصيد الإجازات غير المستعمل م109/م110/م111.
   - للسيناريو الإيضاحي (10 أكتوبر 2027 = 3 سنوات، أجر 20,000 ريال، 63 يوم إجازة): مكافأة كاملة 30,000 ريال (أو ثلث الاستقالة 10,000 ريال) + إجازات 42,000 ريال = 72,000 ريال (أو 52,000 ريال)، موسومة صراحة كـ PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION ومعزولة كلياً عن النقد السائل المتاح أو التداول.
   - حساب الموعد النهائي لإشعار عدم التجديد قبل 60 يوماً (11 أغسطس 2027 لعقد ينتهي 10 أكتوبر 2027) مع تنبيهات استباقية قبل 90 و75 و65 يوماً وحفظ بيانات الإثبات دون إرسال أي إشعار تلقائي إطلاقاً.
4. دفتر الأستاذ المخصص لرأس المال الاستثماري (Investment Capital Allocation Ledger):
   - تخصيص أولي 2,125 ريال شهرياً مع مقارنة المحافظ المتنوعة والأسهم السعودية (تداول) والعملات الرقمية الفورية الورقية (PAPER ONLY)، ونمذجة السيناريوهات الهابطة والرسوم والتذبذب والسيولة دون أي ضمان للعوائد أو اعتماد على أرباح مضاربية لسداد الديون.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from typing import Any, Literal
import uuid

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import append_audit_log, db_session, utc_now_iso
from app.market_engine import market_engine

SAR_PER_USD_PEG = 3.75
PROVISIONAL_LEGAL_LABEL = "PROVISIONAL / SUBJECT TO CONTRACT AND LEGAL VERIFICATION"

BucketCategory = Literal[
    "PERSONAL_EXPENSES",
    "CREDIT_CARD_REPAYMENTS",
    "AI_SUBSCRIPTIONS",
    "TRILUNAIR_AGENT_OPERATIONS",
    "INVESTMENT_ALLOCATION",
    "CASH_SAVINGS",
]

VALID_BUCKETS: tuple[str, ...] = (
    "PERSONAL_EXPENSES",
    "CREDIT_CARD_REPAYMENTS",
    "AI_SUBSCRIPTIONS",
    "TRILUNAIR_AGENT_OPERATIONS",
    "INVESTMENT_ALLOCATION",
    "CASH_SAVINGS",
)

wealth_router = APIRouter(prefix="/api/wealth", tags=["Personal CFO & Wealth Architect"])


# ==============================================================================
# 1. Database Schema & Seed Initialization (Idempotent PostgreSQL + SQLite)
# ==============================================================================


def ensure_wealth_architect_tables() -> None:
    """تهيئة جداول المدير المالي الشخصي ومخطط الديون وحاسبة نظام العمل ودفتر الاستثمار."""
    now = utc_now_iso()
    default_verifications = json.dumps(
        {
            "exactContractExpiryVerified": False,
            "contractTypeAndRenewalTermsVerified": True,  # Confirmed fixed-term w/ 60-day auto-renewal clause; exact date pending contract copy
            "eligibleWageComponentsVerified": False,
            "applicableTerminationReasonVerified": False,
            "officialAccruedLeaveBalanceVerified": False,
            "leaveCarryoverAndSettlementHistoryVerified": False,
            "contractualEnhancementsVerified": False,
            "applicableLegalExceptionsVerified": False,
        }
    )

    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS wealth_cfo_profile (
                profile_id TEXT PRIMARY KEY,
                monthly_salary_sar REAL NOT NULL DEFAULT 20000.0,
                payday_day_of_month INTEGER NOT NULL DEFAULT 28,
                personal_expenses_sar REAL NOT NULL DEFAULT 8000.0,
                credit_card_repayments_sar REAL NOT NULL DEFAULT 6000.0,
                ai_subscriptions_sar REAL NOT NULL DEFAULT 1375.0,
                trilunair_agent_operations_sar REAL NOT NULL DEFAULT 500.0,
                investment_allocation_sar REAL NOT NULL DEFAULT 2125.0,
                cash_savings_sar REAL NOT NULL DEFAULT 2000.0,
                liquid_cash_reserve_sar REAL NOT NULL DEFAULT 2000.0,
                available_cycle_cash_sar REAL NOT NULL DEFAULT 20000.0,
                employment_start_date TEXT NOT NULL DEFAULT '2024-10-10',
                contract_expiry_date TEXT NOT NULL DEFAULT '2027-10-10',
                contract_type TEXT NOT NULL DEFAULT 'FIXED_TERM',
                auto_renews INTEGER NOT NULL DEFAULT 1,
                non_renewal_notice_days INTEGER NOT NULL DEFAULT 60,
                expected_departure_method TEXT NOT NULL DEFAULT 'NON_RENEWAL_UPON_EXPIRY',
                eligible_final_wage_sar REAL NOT NULL DEFAULT 20000.0,
                annual_leave_days_per_year REAL NOT NULL DEFAULT 21.0,
                annual_leave_taken_days REAL NOT NULL DEFAULT 0.0,
                verification_flags_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wealth_credit_cards (
                card_id TEXT PRIMARY KEY,
                issuer_name_en TEXT NOT NULL,
                issuer_name_ar TEXT NOT NULL,
                approximate_balance_sar REAL NOT NULL,
                reported_due_incl_arrears_sar REAL NOT NULL,
                provisional_monthly_allocation_sar REAL NOT NULL,
                estimated_annual_apr_pct REAL NOT NULL DEFAULT 32.0,
                payment_due_day INTEGER NOT NULL DEFAULT 5,
                current_dues_verified INTEGER NOT NULL DEFAULT 0,
                delinquency_verified INTEGER NOT NULL DEFAULT 0,
                financing_charges_verified INTEGER NOT NULL DEFAULT 0,
                payment_date_verified INTEGER NOT NULL DEFAULT 0,
                notes_en TEXT NOT NULL DEFAULT '',
                notes_ar TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wealth_statement_transactions (
                tx_id TEXT PRIMARY KEY,
                tx_fingerprint TEXT NOT NULL UNIQUE,
                salary_cycle_id TEXT NOT NULL,
                tx_date TEXT NOT NULL,
                merchant_or_description TEXT NOT NULL,
                amount_sar REAL NOT NULL,
                category TEXT NOT NULL,
                account_source TEXT NOT NULL DEFAULT 'BANK_CURRENT',
                entry_kind TEXT NOT NULL DEFAULT 'ACTUAL_EXPENSE',
                reconciliation_mode TEXT NOT NULL DEFAULT 'RECONCILED_AGAINST_PLANNED_BUCKET',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wealth_investment_ledger (
                entry_id TEXT PRIMARY KEY,
                salary_cycle_id TEXT NOT NULL,
                contribution_date TEXT NOT NULL,
                amount_sar REAL NOT NULL,
                amount_usd_equiv REAL NOT NULL,
                diversified_etf_sukuk_sar REAL NOT NULL,
                saudi_equities_tadawul_sar REAL NOT NULL,
                crypto_spot_paper_sar REAL NOT NULL,
                execution_mode TEXT NOT NULL DEFAULT 'PAPER_SIMULATION_ONLY',
                liquidity_guard_status TEXT NOT NULL DEFAULT 'APPROVED_NORMAL_CASHFLOW',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wealth_contract_evidence (
                evidence_id TEXT PRIMARY KEY,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                document_sha256 TEXT NOT NULL,
                delivery_channel TEXT NOT NULL DEFAULT 'INTERNAL_VAULT_ONLY',
                verified_by_owner INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                recorded_at TEXT NOT NULL
            );
            """
        )

        row = conn.execute(
            "SELECT profile_id FROM wealth_cfo_profile WHERE profile_id = 'owner-primary'"
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO wealth_cfo_profile (
                    profile_id, monthly_salary_sar, payday_day_of_month,
                    personal_expenses_sar, credit_card_repayments_sar, ai_subscriptions_sar,
                    trilunair_agent_operations_sar, investment_allocation_sar, cash_savings_sar,
                    liquid_cash_reserve_sar, available_cycle_cash_sar,
                    employment_start_date, contract_expiry_date, contract_type,
                    auto_renews, non_renewal_notice_days, expected_departure_method,
                    eligible_final_wage_sar, annual_leave_days_per_year, annual_leave_taken_days,
                    verification_flags_json, updated_at
                ) VALUES (
                    'owner-primary', 20000.0, 28,
                    8000.0, 6000.0, 1375.0,
                    500.0, 2125.0, 2000.0,
                    2000.0, 20000.0,
                    '2024-10-10', '2027-10-10', 'FIXED_TERM',
                    1, 60, 'NON_RENEWAL_UPON_EXPIRY',
                    20000.0, 21.0, 0.0,
                    ?, ?
                )
                """,
                (default_verifications, now),
            )

        cards_count = conn.execute("SELECT COUNT(*) AS c FROM wealth_credit_cards").fetchone()
        if cards_count is None or int(cards_count["c"]) == 0:
            cards_seed = [
                (
                    "tasheel",
                    "Tasheel Finance (Credit Facility / Card)",
                    "تسهيل للتمويل (بطاقة / تسهيل ائتماني)",
                    14000.0,
                    1700.0,
                    4200.0,
                    34.0,
                    4,
                    "Provisional accelerated paydown: SAR 1,700 reported due incl. arrears + SAR 2,500 principal reduction.",
                    "تخصيص سداد معجل مبدئي: 1,700 ريال مستحق ومتأخرات معلنة + 2,500 ريال خفض إضافي لأصل المديونية.",
                ),
                (
                    "emirates_nbd",
                    "Emirates NBD Saudi Arabia Credit Card",
                    "بطاقة بنك الإمارات دبي الوطني الائتمانية",
                    17000.0,
                    1800.0,
                    1800.0,
                    31.0,
                    6,
                    "Provisional allocation covers full SAR 1,800 reported amount due including arrears; verify statement cutoff.",
                    "يغطي التخصيص المبدئي كامل المبلغ المستحق المعلن شاملاً المتأخرات (1,800 ريال)؛ يلزم التحقق من كشف الحساب الرسمي.",
                ),
            ]
            for cid, nen, nar, bal, due, alloc, apr, pday, note_en, note_ar in cards_seed:
                conn.execute(
                    """
                    INSERT INTO wealth_credit_cards (
                        card_id, issuer_name_en, issuer_name_ar,
                        approximate_balance_sar, reported_due_incl_arrears_sar,
                        provisional_monthly_allocation_sar, estimated_annual_apr_pct,
                        payment_due_day, notes_en, notes_ar, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (cid, nen, nar, bal, due, alloc, apr, pday, note_en, note_ar, now),
                )

        ledger_count = conn.execute("SELECT COUNT(*) AS c FROM wealth_investment_ledger").fetchone()
        if ledger_count is None or int(ledger_count["c"]) == 0:
            cycle_id = resolve_salary_cycle_id(date.today(), payday_day=28)
            # Initial SAR 2,125 monthly capital allocation split prudently across Diversified (45%), Saudi Equities (35%), Crypto PAPER (20%)
            init_amt = 2125.0
            div_sar = round(init_amt * 0.45, 2)      # 956.25 SAR
            saudi_sar = round(init_amt * 0.35, 2)    # 743.75 SAR
            crypto_sar = round(init_amt - div_sar - saudi_sar, 2)  # 425.00 SAR
            conn.execute(
                """
                INSERT INTO wealth_investment_ledger (
                    entry_id, salary_cycle_id, contribution_date, amount_sar, amount_usd_equiv,
                    diversified_etf_sukuk_sar, saudi_equities_tadawul_sar, crypto_spot_paper_sar,
                    execution_mode, liquidity_guard_status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PAPER_SIMULATION_ONLY', 'INITIAL_OWNER_APPROVED_PLAN', ?, ?)
                """,
                (
                    "inv_seed_initial_cycle",
                    cycle_id,
                    date.today().isoformat(),
                    init_amt,
                    round(init_amt / SAR_PER_USD_PEG, 2),
                    div_sar,
                    saudi_sar,
                    crypto_sar,
                    "Owner-approved SAR 2,125/mo investment-first allocation ledger (research & PAPER simulation only; zero real orders).",
                    now,
                ),
            )


# ==============================================================================
# 2. Salary-Cycle Calendar & Statement Anti-Double-Counting Engine
# ==============================================================================


def _parse_iso_date(val: str) -> date:
    try:
        return date.fromisoformat(val.strip()[:10])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid ISO date '{val}'; expected YYYY-MM-DD.") from exc


def resolve_salary_cycle_id(ref_date: date, payday_day: int = 28) -> str:
    """
    تحديد معرّف دورة الراتب الشهرية الممتدة من يوم 28 في الشهر إلى يوم 27 من الشهر التالي.
    مثال: تاريخ 2026-11-29 ينتمي لدورة 2026-11-28، بينما 2026-11-16 ينتمي لدورة 2026-10-28.
    """
    safe_day = max(1, min(28, int(payday_day)))
    if ref_date.day >= safe_day:
        cycle_start = date(ref_date.year, ref_date.month, safe_day)
    else:
        first_of_month = date(ref_date.year, ref_date.month, 1)
        prev_month_end = first_of_month - timedelta(days=1)
        cycle_start = date(prev_month_end.year, prev_month_end.month, safe_day)
    return f"cycle-{cycle_start.isoformat()}"


def compute_next_payday_info(ref_date: date, payday_day: int = 28) -> dict[str, Any]:
    safe_day = max(1, min(28, int(payday_day)))
    if ref_date.day <= safe_day:
        next_payday = date(ref_date.year, ref_date.month, safe_day)
    else:
        if ref_date.month == 12:
            next_payday = date(ref_date.year + 1, 1, safe_day)
        else:
            next_payday = date(ref_date.year, ref_date.month + 1, safe_day)
    return {
        "paydayDayOfMonth": safe_day,
        "currentSalaryCycleId": resolve_salary_cycle_id(ref_date, safe_day),
        "nextPaydayDate": next_payday.isoformat(),
        "daysUntilNextPayday": (next_payday - ref_date).days,
    }


def compute_statement_fingerprint(
    tx_date: str,
    description: str,
    amount_sar: float,
    account_source: str,
) -> str:
    norm_desc = " ".join((description or "").strip().lower().split())
    norm_acct = (account_source or "BANK_CURRENT").strip().upper()
    canonical = f"{tx_date.strip()[:10]}|{norm_desc}|{round(float(amount_sar), 2):.2f}|{norm_acct}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ==============================================================================
# 3. Saudi Labor Law Employment Benefits & 60-Day Contract Deadline Engine
# ==============================================================================


def _compute_exact_service_years(start_dt: date, end_dt: date) -> dict[str, Any]:
    """
    حساب مدة الخدمة الفعلية بالسنوات الكاملة والكسور التناسبية وفق المادة 84 من نظام العمل السعودي.
    مثال: من 2024-10-10 إلى 2027-10-10 = 3 سنوات مكتملة بالضبط (3.0000 سنة).
    """
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End date must be after employment start date.")

    full_years = end_dt.year - start_dt.year
    try:
        anniversary = date(start_dt.year + full_years, start_dt.month, start_dt.day)
    except ValueError:
        # Handle Feb 29 leap-year edge case
        anniversary = date(start_dt.year + full_years, start_dt.month, 28)

    if anniversary > end_dt:
        full_years -= 1
        try:
            anniversary = date(start_dt.year + full_years, start_dt.month, start_dt.day)
        except ValueError:
            anniversary = date(start_dt.year + full_years, start_dt.month, 28)

    remainder_days = (end_dt - anniversary).days
    service_years_decimal = full_years + (remainder_days / 365.0)
    total_calendar_days = (end_dt - start_dt).days
    return {
        "completedFullYears": full_years,
        "remainderDays": remainder_days,
        "totalCalendarDays": total_calendar_days,
        "serviceYearsExact": round(service_years_decimal, 6),
    }


def _compute_article_84_full_award(service_years: float, eligible_monthly_wage_sar: float) -> float:
    """
    المادة 84 من نظام العمل السعودي:
    - أجر نصف شهر عن كل سنة من السنوات الخمس الأولى.
    - أجر شهر كامل عن كل سنة من السنوات التالية، مع حساب أجزاء السنة بنسبة ما قضاه منها في العمل.
    """
    first_five = min(max(0.0, service_years), 5.0)
    beyond_five = max(0.0, service_years - 5.0)
    award = (0.5 * eligible_monthly_wage_sar * first_five) + (1.0 * eligible_monthly_wage_sar * beyond_five)
    return round(award, 2)


def _compute_article_85_resignation_multiplier(service_years: float) -> tuple[float, str]:
    """
    المادة 85 من نظام العمل السعودي (حالة استقالة العامل):
    - أقل من سنتين متتاليتين: لا يستحق مكافأة (0).
    - سنتان فأكثر وحتى 5 سنوات: ثلث المكافأة (1/3).
    - أكثر من 5 سنوات وأقل من 10 سنوات: ثلثا المكافأة (2/3).
    - 10 سنوات فأكثر: المكافأة كاملة (1.0).
    """
    if service_years < 2.0:
        return 0.0, "Under 2 consecutive years: 0% under Art. 85"
    if service_years <= 5.0:
        return 1.0 / 3.0, "2 to 5 years inclusive: 1/3 of Art. 84 award under Art. 85"
    if service_years < 10.0:
        return 2.0 / 3.0, "Over 5 and under 10 years: 2/3 of Art. 84 award under Art. 85"
    return 1.0, "10 consecutive years or more: 100% full award under Art. 85"


def _compute_statutory_accrued_leave_days(
    service_years: float,
    base_annual_leave_days: float = 21.0,
    leave_taken_days: float = 0.0,
) -> float:
    """
    المادة 109 والمادة 111 من نظام العمل السعودي:
    - الحد الأدنى النظامي 21 يوماً عن كل سنة من السنوات الخمس الأولى، ويزداد إلى 30 يوماً إذا أمضى العامل 5 سنوات متصلة
      (ما لم ينص العقد على رصيد أعلى كـ 30 يوماً منذ البداية).
    """
    eff_first_tier = max(21.0, float(base_annual_leave_days))
    first_five_years = min(max(0.0, service_years), 5.0)
    after_five_years = max(0.0, service_years - 5.0)
    post_five_rate = max(30.0, eff_first_tier)
    gross_accrued = (first_five_years * eff_first_tier) + (after_five_years * post_five_rate)
    return round(max(0.0, gross_accrued - max(0.0, float(leave_taken_days))), 2)


def calculate_saudi_employment_benefits(
    start_date_str: str = "2024-10-10",
    end_date_str: str = "2027-10-10",
    eligible_monthly_wage_sar: float = 20000.0,
    annual_leave_days_per_year: float = 21.0,
    annual_leave_taken_days: float = 0.0,
    override_unused_leave_days: float | None = None,
    contract_type: str = "FIXED_TERM",
    auto_renews: bool = True,
    non_renewal_notice_days: int = 60,
    expected_departure_method: str = "NON_RENEWAL_UPON_EXPIRY",
    verification_flags: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """
    حاسبة مستحقات نهاية الخدمة وتعويض الإجازات وفق أحكام نظام العمل السعودي الساري (المواد 55، 74، 75، 77، 79 مكرر، 80، 81، 84، 85، 87، 88، 109، 110، 111).
    لا تفترض تلقائياً أن عدم تجديد العقد المحدد المدة عند انتهائه يساوي استقالة أثناء سريان العقد.
    """
    start_dt = _parse_iso_date(start_date_str)
    end_dt = _parse_iso_date(end_date_str)
    svc = _compute_exact_service_years(start_dt, end_dt)
    years = svc["serviceYearsExact"]

    full_art84_eosb = _compute_article_84_full_award(years, eligible_monthly_wage_sar)
    resig_mult, resig_band_note = _compute_article_85_resignation_multiplier(years)
    resig_art85_eosb = round(full_art84_eosb * resig_mult, 2)

    unused_leave_days = (
        round(float(override_unused_leave_days), 2)
        if override_unused_leave_days is not None
        else _compute_statutory_accrued_leave_days(
            service_years=years,
            base_annual_leave_days=annual_leave_days_per_year,
            leave_taken_days=annual_leave_taken_days,
        )
    )
    daily_wage_sar = eligible_monthly_wage_sar / 30.0
    unused_leave_payout_sar = round(unused_leave_days * daily_wage_sar, 2)

    scenarios = {
        "fixedTermExpiryNonRenewal": {
            "scenarioId": "FIXED_TERM_EXPIRY_NON_RENEWAL",
            "titleEn": "1. Fixed-Term Contract Expiry & Timely Non-Renewal (Expected Departure Path)",
            "titleAr": "1. انتهاء العقد محدد المدة وعدم تجديده بإشعار نظامي (مسار المغادرة المتوقع)",
            "legalBasis": "Saudi Labor Law Articles 55, 74(1), 84, 88, 109 & 111",
            "classifiedAsMidTermResignation": False,
            "eosbAwardSar": full_art84_eosb,
            "unusedLeaveCompensationSar": unused_leave_payout_sar,
            "combinedEstimatedBenefitsSar": round(full_art84_eosb + unused_leave_payout_sar, 2),
            "settlementDeadlineRule": "Within 1 week of contract end (or up to 2 weeks if treated as worker-ended under Art. 88)",
            "statusLabel": PROVISIONAL_LEGAL_LABEL,
            "legalCaveatEn": (
                "Under Art. 74(1) & Art. 84, natural expiration of a fixed-term contract following timely 60-day non-renewal "
                "notice is distinct from mid-term resignation under Art. 85 and carries full Art. 84 EOSB. Exact Qiwa/contract "
                "wording on automatic renewal & non-renewal notice mechanics must be verified before giving notice."
            ),
            "legalCaveatAr": (
                "بموجب المادة 74(1) والمادة 84، انتهاء العقد محدد المدة بانقضاء مدته بعد إشعار عدم التجديد قبل 60 يوماً يختلف عن "
                "الاستقالة أثناء سريان العقد (م85) ويستحق المكافأة الكاملة؛ ويلزم التحقق من الصياغة الحرفية لبند التجديد في عقد قوى."
            ),
        },
        "ordinaryResignation": {
            "scenarioId": "ORDINARY_RESIGNATION",
            "titleEn": "2. Ordinary Resignation During Active Term (Conservative Comparison)",
            "titleAr": "2. الاستقالة العادية (مقارنة تحفظية وفق المادة 85 والمادة 79 مكرر)",
            "legalBasis": f"Saudi Labor Law Articles 79 (bis), 84, 85 ({resig_band_note}), 88 & 111",
            "classifiedAsMidTermResignation": True,
            "eosbMultiplier": round(resig_mult, 6),
            "eosbAwardSar": resig_art85_eosb,
            "unusedLeaveCompensationSar": unused_leave_payout_sar,
            "combinedEstimatedBenefitsSar": round(resig_art85_eosb + unused_leave_payout_sar, 2),
            "settlementDeadlineRule": "Within 2 weeks of effective termination date under Art. 88",
            "statusLabel": PROVISIONAL_LEGAL_LABEL,
            "legalCaveatEn": (
                "Applies if exit is legally executed or classified as a worker resignation under Art. 79 (bis) / Art. 85 "
                "rather than fixed-term non-renewal at expiry."
            ),
            "legalCaveatAr": (
                "ينطبق هذا التخفيض (ثلث المكافأة لخدمة 2 إلى 5 سنوات) فقط إذا صُنفت المغادرة قانوناً كاستقالة وليس انتهاء عقد محدد المدة."
            ),
        },
        "employerInitiatedTermination": {
            "scenarioId": "EMPLOYER_INITIATED_TERMINATION",
            "titleEn": "3. Employer-Initiated Termination / Employer Non-Renewal",
            "titleAr": "3. إنهاء العقد أو عدم تجديده من قِبل صاحب العمل",
            "legalBasis": "Saudi Labor Law Articles 74, 75, 77, 84, 88 & 111",
            "classifiedAsMidTermResignation": False,
            "eosbAwardSar": full_art84_eosb,
            "unusedLeaveCompensationSar": unused_leave_payout_sar,
            "combinedEstimatedBenefitsSar": round(full_art84_eosb + unused_leave_payout_sar, 2),
            "settlementDeadlineRule": "Within 1 week of termination under Art. 88",
            "statusLabel": PROVISIONAL_LEGAL_LABEL,
            "legalCaveatEn": (
                "Full Art. 84 EOSB + Art. 111 accrued leave apply. If terminated mid-term without valid statutory cause, "
                "separate Art. 77 compensation (wages for remaining fixed term, min 2 months unless contract states otherwise) may also apply."
            ),
            "legalCaveatAr": (
                "تستحق المكافأة الكاملة (م84) وتعويض الإجازات (م111)، وإذا كان الإنهاء قبل نهاية المدة لغير سبب مشروع فقد ينشأ تعويض إضافي بموجب المادة 77."
            ),
        },
        "otherStatutoryScenarios": {
            "forceMajeureOrEmployerBreach": {
                "scenarioId": "FORCE_MAJEURE_ART_87_OR_ART_81",
                "titleEn": "4a. Force Majeure (Art. 87) or Employer Statutory Breach (Art. 81)",
                "legalBasis": "Saudi Labor Law Articles 81, 84, 87 & 111",
                "eosbAwardSar": full_art84_eosb,
                "unusedLeaveCompensationSar": unused_leave_payout_sar,
                "combinedEstimatedBenefitsSar": round(full_art84_eosb + unused_leave_payout_sar, 2),
                "statusLabel": PROVISIONAL_LEGAL_LABEL,
            },
            "dismissalForCauseArt80": {
                "scenarioId": "CAUSE_DISMISSAL_ART_80",
                "titleEn": "4b. Dismissal for Cause Under Article 80 (EOSB Forfeited; Earned Leave Preserved)",
                "legalBasis": "Saudi Labor Law Articles 80 & 111",
                "eosbAwardSar": 0.0,
                "unusedLeaveCompensationSar": unused_leave_payout_sar,
                "combinedEstimatedBenefitsSar": unused_leave_payout_sar,
                "statusLabel": PROVISIONAL_LEGAL_LABEL,
            },
        },
    }

    flags = verification_flags or {}
    verification_checklist = [
        {
            "itemId": "contractTypeAndRenewalTerms",
            "labelEn": "Employment contract type, exact current term expiry date, and 60-day renewal/notice clause wording (Qiwa copy)",
            "labelAr": "نوع عقد العمل وتاريخ الانتهاء الدقيق للفترة الحالية والنص الحرفي لبند التجديد التلقائي ومهلة 60 يوماً في منصة قوى",
            "verified": bool(flags.get("exactContractExpiryVerified", False)),
        },
        {
            "itemId": "eligibleWageComponents",
            "labelEn": "Actual eligible final wage components (basic salary + housing/transport vs excluded variable commissions under Art. 86)",
            "labelAr": "مكونات الأجر الفعلي الخاضع للحساب (الأساسي + البدلات الثابتة مقابل أي عمولات متغيرة مستثناة بموجب المادة 86)",
            "verified": bool(flags.get("eligibleWageComponentsVerified", False)),
        },
        {
            "itemId": "applicableTerminationReason",
            "labelEn": "Applicable legal termination classification (Art. 74(1) fixed-term expiry non-renewal vs Art. 85 resignation)",
            "labelAr": "التكييف النظامي لسبب انتهاء العلاقة العمالية (انتهاء مدة العقد المحدد م74 مقابل الاستقالة م85)",
            "verified": bool(flags.get("applicableTerminationReasonVerified", False)),
        },
        {
            "itemId": "officialAccruedLeaveBalance",
            "labelEn": "Official HR / ERP recorded accrued annual leave balance (confirming 0 days taken / 63 days accrued)",
            "labelAr": "رصيد الإجازات السنوية الرسمي المسجل في نظام الموارد البشرية (التثبت من عدم استنفاد أي أيام واستحقاق 63 يوماً)",
            "verified": bool(flags.get("officialAccruedLeaveBalanceVerified", False)),
        },
        {
            "itemId": "leaveCarryoverAndSettlementHistory",
            "labelEn": "Annual leave carryover / written postponement consents under Art. 110 and prior cash-out history",
            "labelAr": "سياسة ترحيل الإجازات وموافقات التأجيل المكتوبة بموجب المادة 110 وسجل التسويات السابقة",
            "verified": bool(flags.get("leaveCarryoverAndSettlementHistoryVerified", False)),
        },
        {
            "itemId": "contractualEnhancements",
            "labelEn": "Contractual enhancements (e.g. 30-day annual leave tier from Year 1 or bonus clauses)",
            "labelAr": "المزايا التعاقدية الإضافية (مثل إجازة 30 يوماً سنوياً منذ السنة الأولى أو بدلات إضافية)",
            "verified": bool(flags.get("contractualEnhancementsVerified", False)),
        },
        {
            "itemId": "applicableLegalExceptions",
            "labelEn": "Applicable statutory exceptions, GOSI deductions/status, or employer work-related set-offs (Art. 88)",
            "labelAr": "الاستثناءات النظامية المنطبقة وحالة التأمينات الاجتماعية (GOSI) أو أي مقاصة نظامية بموجب المادة 88",
            "verified": bool(flags.get("applicableLegalExceptionsVerified", False)),
        },
    ]

    return {
        "statusLabel": PROVISIONAL_LEGAL_LABEL,
        "accountingTreatment": "CONTINGENT_FUTURE_RECEIVABLE",
        "countedAsAvailableLiquidCash": False,
        "countedInLiquidEmergencyReserve": False,
        "usableForTradingOrImmediateDebtPayments": False,
        "legalEntitlementGuaranteedWithoutReview": False,
        "contractSummary": {
            "jurisdiction": "Saudi Arabia (HRSD / Saudi Labor Law)",
            "commencementDate": start_dt.isoformat(),
            "illustrativeOrTargetEndDate": end_dt.isoformat(),
            "exactExpiryDateVerified": bool(flags.get("exactContractExpiryVerified", False)),
            "contractType": contract_type,
            "autoRenews": auto_renews,
            "nonRenewalNoticeDays": non_renewal_notice_days,
            "expectedDepartureMethod": expected_departure_method,
            "eligibleFinalMonthlyWageSar": round(eligible_monthly_wage_sar, 2),
            "dailyEligibleWageSar": round(daily_wage_sar, 4),
            "annualLeaveDaysPerYear": annual_leave_days_per_year,
            "annualLeaveTakenDays": annual_leave_taken_days,
            "accruedUnusedLeaveDays": unused_leave_days,
            "serviceDuration": svc,
        },
        "primaryExpectedScenario": scenarios["fixedTermExpiryNonRenewal"],
        "scenarios": scenarios,
        "verificationChecklist": verification_checklist,
    }


def compute_contract_renewal_deadlines(
    expiry_date_str: str = "2027-10-10",
    notice_days: int = 60,
    exact_expiry_verified: bool = False,
    reference_date: date | None = None,
    evidence_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    حساب الموعد النهائي التعاقدي لإشعار عدم التجديد (60 يوماً قبل انتهاء العقد) وجدولة تنبيهات 90 و75 و65 يوماً.
    لعقد ينتهي في 2027-10-10 فإن موعد الـ 60 يوماً هو 2027-08-11 بالضبط.
    """
    ref_dt = reference_date or date.today()
    exp_dt = _parse_iso_date(expiry_date_str)
    safe_notice_days = max(1, int(notice_days))
    final_deadline_dt = exp_dt - timedelta(days=safe_notice_days)

    milestone_offsets = [
        (
            90,
            "REMINDER_90D_AUDIT_CONTRACT_AND_LEAVE",
            "90-Day Advance Checkpoint: Verify signed Qiwa contract expiry date, notice delivery method, and HR leave ledger.",
            "تنبيه مبكر (قبل 90 يوماً): التحقق من تاريخ انتهاء العقد الرسمي في منصة قوى وطريقة الإشعار ورصيد الإجازات.",
        ),
        (
            75,
            "REMINDER_75D_LEGAL_AND_DRAFT_PREPARATION",
            "75-Day Advance Checkpoint: Prepare written non-renewal notice draft & confirm cash/debt buffer before notice window.",
            "تنبيه تحضيري (قبل 75 يوماً): تجهيز مسودة إشعار عدم التجديد ومراجعة احتياطي السيولة قبل دخول نافذة الإشعار.",
        ),
        (
            65,
            "REMINDER_65D_FINAL_PRE_NOTICE_WARNING",
            "65-Day Urgent Checkpoint (5 days before 60-day cutoff): Final owner decision required on serving non-renewal notice.",
            "تنبيه عاجل (قبل 65 يوماً — قبل المهلة بـ 5 أيام): قرار المالك النهائي لتقديم إشعار عدم التجديد رسمياً.",
        ),
    ]

    reminders: list[dict[str, Any]] = []
    for offset_days, code, msg_en, msg_ar in milestone_offsets:
        rem_dt = exp_dt - timedelta(days=offset_days)
        days_until = (rem_dt - ref_dt).days
        reminders.append(
            {
                "milestoneCode": code,
                "daysBeforeExpiry": offset_days,
                "reminderDate": rem_dt.isoformat(),
                "daysFromToday": days_until,
                "status": "DUE_OR_PASSED" if days_until <= 0 else ("IMMINENT" if days_until <= 14 else "SCHEDULED"),
                "messageEn": msg_en,
                "messageAr": msg_ar,
            }
        )

    days_to_final_cutoff = (final_deadline_dt - ref_dt).days
    days_to_expiry = (exp_dt - ref_dt).days
    if days_to_final_cutoff < 0:
        deadline_state = "NOTICE_WINDOW_PASSED_AUTO_RENEWAL_RISK"
    elif days_to_final_cutoff <= 10:
        deadline_state = "CRITICAL_FINAL_NOTICE_IMMINENT"
    elif days_to_final_cutoff <= 30:
        deadline_state = "ACTIVE_PREPARATION_WINDOW"
    else:
        deadline_state = "TRACKING_AHEAD_OF_SCHEDULE"

    return {
        "contractExpiryDate": exp_dt.isoformat(),
        "exactExpiryDateVerified": exact_expiry_verified,
        "requiredAdvanceNoticeDays": safe_notice_days,
        "finalNoticeDeadlineDate": final_deadline_dt.isoformat(),
        "daysUntilFinalNoticeDeadline": days_to_final_cutoff,
        "daysUntilContractExpiry": days_to_expiry,
        "deadlineState": deadline_state,
        "noticeCalculationRuleNoteEn": (
            f"Calculated as {exp_dt.isoformat()} minus {safe_notice_days} calendar days = {final_deadline_dt.isoformat()}, "
            "subject to verifying whether the contract specifies Gregorian vs Hijri calendar days and Qiwa electronic notice rules."
        ),
        "noticeCalculationRuleNoteAr": (
            f"محتسب بطرح {safe_notice_days} يوماً تقويمياً من {exp_dt.isoformat()} = {final_deadline_dt.isoformat()}، "
            "مع وجوب التحقق مما إذا كان العقد يعتمد التقويم الميلادي ومسطرة الإشعار عبر منصة قوى."
        ),
        "autoSendNonRenewalNotice": False,
        "ownerApprovalPolicy": "NEVER_AUTO_SEND_WITHOUT_EXPLICIT_OWNER_ACTION",
        "reminders": reminders,
        "evidenceVault": evidence_records or [],
    }


# ==============================================================================
# 4. Debt vs Investment Trade-Off, Multi-Asset Comparison & Snapshot Builder
# ==============================================================================


def _simulate_debt_payoff_months(cards: list[dict[str, Any]]) -> dict[str, Any]:
    """محاكاة زمن سداد البطاقات الائتمانية وإجمالي تكلفة التمويل التقديرية تحت خطة 6,000 ريال شهرياً."""
    sim_balances = [
        {
            "cardId": c["cardId"],
            "balance": float(c["approximateBalanceSar"]),
            "alloc": float(c["provisionalMonthlyAllocationSar"]),
            "monthlyRate": (float(c["estimatedAnnualAprPct"]) / 100.0) / 12.0,
        }
        for c in cards
    ]
    total_budget = sum(x["alloc"] for x in sim_balances)
    if total_budget <= 0:
        return {"estimatedMonthsToDebtFree": None, "estimatedTotalFinancingCostSar": None}

    months = 0
    total_interest_sar = 0.0
    while any(x["balance"] > 0.5 for x in sim_balances) and months < 120:
        months += 1
        # Accrue monthly financing charge
        for x in sim_balances:
            if x["balance"] > 0:
                charge = x["balance"] * x["monthlyRate"]
                x["balance"] += charge
                total_interest_sar += charge

        # Apply scheduled card allocation; snowball any freed allocation from paid-off card to remaining cards
        rollover_pool = 0.0
        for x in sim_balances:
            if x["balance"] <= 0:
                rollover_pool += x["alloc"]
            elif x["alloc"] >= x["balance"]:
                rollover_pool += x["alloc"] - x["balance"]
                x["balance"] = 0.0
            else:
                x["balance"] -= x["alloc"]

        if rollover_pool > 0:
            # Direct freed budget to highest-APR remaining card (debt avalanche rollover)
            for x in sorted(sim_balances, key=lambda item: item["monthlyRate"], reverse=True):
                if x["balance"] > 0 and rollover_pool > 0:
                    pay = min(x["balance"], rollover_pool)
                    x["balance"] -= pay
                    rollover_pool -= pay

    weighted_apr = 0.0
    total_bal = sum(float(c["approximateBalanceSar"]) for c in cards)
    if total_bal > 0:
        weighted_apr = sum(
            float(c["approximateBalanceSar"]) * float(c["estimatedAnnualAprPct"]) for c in cards
        ) / total_bal

    return {
        "estimatedMonthsToDebtFree": months,
        "estimatedTotalFinancingCostSar": round(total_interest_sar, 2),
        "weightedEstimatedCardAprPct": round(weighted_apr, 2),
        "postPayoffFreedMonthlyCashflowSar": round(total_budget, 2),
    }


def _build_investment_opportunity_comparison(monthly_allocation_sar: float) -> dict[str, Any]:
    """
    مقارنة بحثية ومؤسسية شفافة بين المحافظ المتنوعة، الأسهم السعودية (تداول)، والعملات الرقمية الورقية (Binance Spot PAPER)
    مع نمذجة الرسوم، التذبذب، السيولة، وسيناريوهات الهبوط دون أي ضمان للعوائد.
    """
    btc_asset = market_engine.get_asset("BTC-USD")
    eth_asset = market_engine.get_asset("ETH-USD")
    btc_price = round(float(btc_asset.price), 2) if btc_asset else 91250.0
    eth_price = round(float(eth_asset.price), 2) if eth_asset else 3120.0

    sleeves = [
        {
            "sleeveId": "DIVERSIFIED_GLOBAL_ETF_SUKUK",
            "nameEn": "Diversified Global Index ETFs & Short-Duration Sukuk Sleeve",
            "nameAr": "سلة الصناديق العالمية المتنوعة والصكوك قصيرة الأجل",
            "targetWeightPct": 45.0,
            "monthlyAllocationSar": round(monthly_allocation_sar * 0.45, 2),
            "illustrativeAnnualReturnBandPct": "6.5% – 9.5% (Non-Guaranteed)",
            "annualizedVolatilityPct": 10.8,
            "estimatedTransactionFeeBps": 12.0,
            "liquidityProfile": "High (T+1 / T+2 regulated exchange settlement)",
            "moderatePullbackLoss10PctSar": round(monthly_allocation_sar * 12 * 0.45 * -0.08, 2),
            "severeStressDrawdownPct": -16.0,
            "roleInPortfolioEn": "Core compounding anchor & volatility dampener independent of single-country or crypto shocks.",
            "roleInPortfolioAr": "ركيزة التراكم الأساسي وتخفيف التذبذب بعيداً عن صدمات الأصل الواحد.",
        },
        {
            "sleeveId": "SAUDI_EQUITIES_TADAWUL",
            "nameEn": "Saudi Equities Sleeve (Tadawul Blue-Chip / Dividend & Growth)",
            "nameAr": "سلة الأسهم السعودية (تداول — شركات قيادية وتوزيعات ونمو)",
            "targetWeightPct": 35.0,
            "monthlyAllocationSar": round(monthly_allocation_sar * 0.35, 2),
            "illustrativeAnnualReturnBandPct": "7.5% – 11.5% (Non-Guaranteed)",
            "annualizedVolatilityPct": 16.4,
            "estimatedTransactionFeeBps": 17.8,  # ~15.5 bps Tadawul brokerage/exchange + 15% VAT on commission
            "liquidityProfile": "High SAR Native Liquidity (T+2 Tadawul settlement; zero FX conversion cost)",
            "moderatePullbackLoss10PctSar": round(monthly_allocation_sar * 12 * 0.35 * -0.12, 2),
            "severeStressDrawdownPct": -24.0,
            "roleInPortfolioEn": "Zero-FX SAR alignment with domestic Vision 2030 growth & dividend cashflows (research/simulation).",
            "roleInPortfolioAr": "توافق مباشر بالريال السعودي دون عمولات صرف مع نمو السوق السعودي وتوزيعاته.",
        },
        {
            "sleeveId": "CRYPTO_SPOT_PAPER",
            "nameEn": "Cryptocurrency Spot Sleeve (Binance Spot Public Data — PAPER ONLY)",
            "nameAr": "سلة العملات الرقمية الفورية (بيانات Binance Spot العامة — تداول ورقي PAPER فقط)",
            "targetWeightPct": 20.0,
            "monthlyAllocationSar": round(monthly_allocation_sar * 0.20, 2),
            "illustrativeAnnualReturnBandPct": "Highly Uncertain / Wide Dispersion (Non-Guaranteed)",
            "annualizedVolatilityPct": 54.0,
            "estimatedTransactionFeeBps": 20.0,  # 10 bps entry + 10 bps exit Spot fee + spread/slippage
            "liquidityProfile": f"24/7 Instant Spot Book (Ref: BTC ${btc_price:,.2f} / ETH ${eth_price:,.2f}) — Execution Locked to PAPER",
            "moderatePullbackLoss10PctSar": round(monthly_allocation_sar * 12 * 0.20 * -0.20, 2),
            "severeStressDrawdownPct": -48.0,
            "roleInPortfolioEn": "Capped asymmetric upside research & PAPER strategy testing with zero leverage and strict 20% sleeve ceiling.",
            "roleInPortfolioAr": "بحث ومحاكاة ورقية مقيدة السقف (20%) بدون أي رافعة مالية ومع بقاء قفل التنفيذ على PAPER.",
        },
    ]

    annual_invested_sar = round(monthly_allocation_sar * 12.0, 2)
    downside_scenarios = [
        {
            "scenarioId": "MODERATE_CORRECTION",
            "labelEn": "Moderate Market Pullback (-10% Blended)",
            "labelAr": "تصحيح سوقي معتدل (-10% موزون)",
            "year1ContributedSar": annual_invested_sar,
            "stressedPortfolioValueSar": round(annual_invested_sar * 0.90, 2),
            "unrealizedDrawdownSar": round(annual_invested_sar * -0.10, 2),
            "mandatoryDebtImpact": "ZERO — Mandatory SAR 6,000 card repayments & SAR 8,000 expenses are funded strictly from salary, never portfolio gains.",
        },
        {
            "scenarioId": "MULTI_ASSET_BEAR_MARKET",
            "labelEn": "Severe Multi-Asset Bear Market (-25.2% Weighted Stress)",
            "labelAr": "سوق هابطة حادة (-25.2% إجهاد موزون عبر الفئات الثلاث)",
            "year1ContributedSar": annual_invested_sar,
            "stressedPortfolioValueSar": round(annual_invested_sar * (1.0 - 0.252), 2),
            "unrealizedDrawdownSar": round(annual_invested_sar * -0.252, 2),
            "mandatoryDebtImpact": "ZERO — Liquid SAR 2,000/mo cash savings buffer absorbs emergencies without forced fire-sale liquidation.",
        },
        {
            "scenarioId": "CRYPTO_WINTER_SHOCK",
            "labelEn": "Crypto -50% Shock + Equity -15% Correlation Spike",
            "labelAr": "صدمة هبوط العملات الرقمية (-50%) مع تراجع الأسهم (-15%)",
            "year1ContributedSar": annual_invested_sar,
            "stressedPortfolioValueSar": round(annual_invested_sar * (1.0 - (0.45 * 0.10 + 0.35 * 0.15 + 0.20 * 0.50)), 2),
            "unrealizedDrawdownSar": round(annual_invested_sar * -(0.45 * 0.10 + 0.35 * 0.15 + 0.20 * 0.50), 2),
            "mandatoryDebtImpact": "CONTAINED — 20% cap on Crypto PAPER sleeve limits total portfolio drawdown to ~19.75%.",
        },
    ]

    return {
        "monthlyAllocationSar": round(monthly_allocation_sar, 2),
        "monthlyAllocationUsdEquiv": round(monthly_allocation_sar / SAR_PER_USD_PEG, 2),
        "annualizedContributionRunRateSar": annual_invested_sar,
        "executionSafeguards": {
            "binanceTradingMode": "PAPER",
            "liveTradingAuthorized": False,
            "realMoneyOrdersPlaced": False,
            "externalBrokerageAccountsOpened": False,
            "returnsGuaranteed": False,
            "reliesOnSpeculativeProfitsForMandatoryPayments": False,
        },
        "sleeves": sleeves,
        "downsideScenarios": downside_scenarios,
    }


def _evaluate_liquidity_and_overdue_priority(
    profile: dict[str, Any],
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    حارس الثروة والسيولة (Wealth Guardian):
    - يفحص كفاية النقد الفوري للدورة الحالية لتغطية الالتزامات المعيشية والمتأخرات الواجبة قبل تمرير التخصيص الاستثماري الاختياري.
    - لا يشترط إغلاق البطاقات بالكامل لبدء الاستثمار طالما أن المتأخرات والأقساط الواجبة ممولة بالكامل.
    """
    available_cash = float(profile["available_cycle_cash_sar"])
    personal_exp = float(profile["personal_expenses_sar"])
    total_reported_dues = sum(
        float(c.get("reportedAmountDueInclArrearsSar", c.get("reported_due_incl_arrears_sar", 0.0)))
        for c in cards
    )
    planned_card_paydown = float(profile["credit_card_repayments_sar"])
    ai_subs = float(profile["ai_subscriptions_sar"])
    trilunair_ops = float(profile["trilunair_agent_operations_sar"])
    planned_investment = float(profile["investment_allocation_sar"])
    planned_savings = float(profile["cash_savings_sar"])

    minimum_mandatory_floor_sar = round(personal_exp + total_reported_dues, 2)
    full_pre_investment_commitments_sar = round(
        personal_exp + planned_card_paydown + ai_subs + trilunair_ops + planned_savings,
        2,
    )

    if available_cash < minimum_mandatory_floor_sar:
        shortfall = round(minimum_mandatory_floor_sar - available_cash, 2)
        recommended_inv = 0.0
        guard_status = "HALT_OPTIONAL_INVESTMENT_PRIORITIZE_OVERDUE_DUES"
        summary_en = (
            f"Immediate cycle cash (SAR {available_cash:,.2f}) is below essential living + overdue card dues "
            f"(SAR {minimum_mandatory_floor_sar:,.2f}; shortfall SAR {shortfall:,.2f}). Optional SAR {planned_investment:,.2f} "
            "investment funding is paused until overdue obligations are cured."
        )
        summary_ar = (
            f"النقد الفوري المتاح للدورة ({available_cash:,.2f} ريال) أقل من المصروفات الأساسية ومستحقات البطاقات المتأخرة "
            f"({minimum_mandatory_floor_sar:,.2f} ريال؛ عجز {shortfall:,.2f} ريال). تم توجيه الأولوية القصوى لسداد المتأخرات وتجميد التمويل الاستثماري الاختياري مؤقتاً."
        )
    elif available_cash < (full_pre_investment_commitments_sar + planned_investment):
        # Partial buffer: cover mandatory expenses + scheduled card repayments + cash savings first, then fund remaining into investment
        core_before_inv = personal_exp + planned_card_paydown + ai_subs + trilunair_ops
        residual_for_sav_and_inv = max(0.0, available_cash - core_before_inv)
        # Preserve at least half cash savings first, allocate rest up to planned_investment
        protected_sav = min(planned_savings, residual_for_sav_and_inv)
        recommended_inv = round(min(planned_investment, max(0.0, residual_for_sav_and_inv - protected_sav)), 2)
        guard_status = "PARTIAL_INVESTMENT_AFTER_OBLIGATION_PROTECTION"
        summary_en = (
            f"Overdue & scheduled card repayments (SAR {planned_card_paydown:,.2f}) and essential liquidity are funded first; "
            f"optional investment scaled to SAR {recommended_inv:,.2f} for this cycle."
        )
        summary_ar = (
            f"تم تأمين سداد البطاقات ({planned_card_paydown:,.2f} ريال) والسيولة الأساسية أولاً، وتعديل التخصيص الاستثماري المتاح لهذه الدورة إلى {recommended_inv:,.2f} ريال."
        )
    else:
        recommended_inv = round(planned_investment, 2)
        guard_status = "INVESTMENT_ACTIVE_PARALLEL_WITH_DEBT_PAYDOWN"
        summary_en = (
            f"Full SAR {planned_card_paydown:,.2f}/mo debt paydown (covering SAR {total_reported_dues:,.2f} reported dues/arrears) "
            f"and SAR {planned_savings:,.2f}/mo liquid savings are covered; SAR {recommended_inv:,.2f}/mo investment proceeds immediately."
        )
        summary_ar = (
            f"جميع الالتزامات وسداد البطاقات ({planned_card_paydown:,.2f} ريال شهرياً شاملاً المتأخرات المعلنة {total_reported_dues:,.2f} ريال) "
            f"والادخار النقدي ({planned_savings:,.2f} ريال) مغطاة بالكامل؛ يستمر تخصيص الاستثمار ({recommended_inv:,.2f} ريال شهرياً) بالتوازي فوراً."
        )

    return {
        "guardianStatus": guard_status,
        "debtEliminationRequiredBeforeInvesting": False,
        "availableImmediateCycleCashSar": round(available_cash, 2),
        "minimumMandatoryLivingAndOverdueFloorSar": minimum_mandatory_floor_sar,
        "scheduledCardRepaymentSar": round(planned_card_paydown, 2),
        "recommendedCycleInvestmentSar": recommended_inv,
        "summaryEn": summary_en,
        "summaryAr": summary_ar,
    }


def get_wealth_architect_overview(reference_date: date | None = None) -> dict[str, Any]:
    """تجميع اللوحة الشاملة للمدير المالي الشخصي، مخطط الديون، مستحقات نظام العمل، مهلة الـ 60 يوماً، ودفتر الاستثمار."""
    ensure_wealth_architect_tables()
    ref_dt = reference_date or date.today()

    with db_session() as conn:
        prof_row = conn.execute(
            "SELECT * FROM wealth_cfo_profile WHERE profile_id = 'owner-primary'"
        ).fetchone()
        assert prof_row is not None
        prof = dict(prof_row)

        card_rows = conn.execute(
            "SELECT * FROM wealth_credit_cards ORDER BY provisional_monthly_allocation_sar DESC"
        ).fetchall()
        cards_raw = [dict(r) for r in card_rows]

        payday_day = int(prof["payday_day_of_month"])
        active_cycle_id = resolve_salary_cycle_id(ref_dt, payday_day)

        tx_rows = conn.execute(
            "SELECT * FROM wealth_statement_transactions WHERE salary_cycle_id = ? ORDER BY tx_date DESC, created_at DESC",
            (active_cycle_id,),
        ).fetchall()
        cycle_txs = [dict(r) for r in tx_rows]

        ledger_rows = conn.execute(
            "SELECT * FROM wealth_investment_ledger ORDER BY contribution_date DESC, created_at DESC LIMIT 36"
        ).fetchall()
        ledger_entries = [dict(r) for r in ledger_rows]

        ev_rows = conn.execute(
            "SELECT * FROM wealth_contract_evidence ORDER BY recorded_at DESC"
        ).fetchall()
        evidence_list = [
            {
                "evidenceId": r["evidence_id"],
                "documentType": r["document_type"],
                "title": r["title"],
                "documentSha256": r["document_sha256"],
                "deliveryChannel": r["delivery_channel"],
                "verifiedByOwner": bool(r["verified_by_owner"]),
                "notes": r["notes"],
                "recordedAt": r["recorded_at"],
            }
            for r in ev_rows
        ]

    # 1. Salary Allocation & Anti-Double-Counting Reconciliation
    buckets_planned = {
        "PERSONAL_EXPENSES": round(float(prof["personal_expenses_sar"]), 2),
        "CREDIT_CARD_REPAYMENTS": round(float(prof["credit_card_repayments_sar"]), 2),
        "AI_SUBSCRIPTIONS": round(float(prof["ai_subscriptions_sar"]), 2),
        "TRILUNAIR_AGENT_OPERATIONS": round(float(prof["trilunair_agent_operations_sar"]), 2),
        "INVESTMENT_ALLOCATION": round(float(prof["investment_allocation_sar"]), 2),
        "CASH_SAVINGS": round(float(prof["cash_savings_sar"]), 2),
    }
    planned_total = round(sum(buckets_planned.values()), 2)
    monthly_salary = round(float(prof["monthly_salary_sar"]), 2)

    actual_by_bucket: dict[str, float] = {k: 0.0 for k in VALID_BUCKETS}
    card_purchase_memo_only_sar = 0.0
    for tx in cycle_txs:
        cat = str(tx["category"])
        amt = float(tx["amount_sar"])
        # Underlying purchases on a credit card statement are tracked for analytics ONLY and NOT added on top of
        # CREDIT_CARD_REPAYMENTS when the owner already budgets SAR 6,000 card repayment transfers!
        if str(tx["entry_kind"]) == "CREDIT_CARD_PURCHASE_MEMO":
            card_purchase_memo_only_sar = round(card_purchase_memo_only_sar + amt, 2)
            continue
        if cat in actual_by_bucket:
            actual_by_bucket[cat] = round(actual_by_bucket[cat] + amt, 2)

    reconciled_buckets: list[dict[str, Any]] = []
    bucket_labels = {
        "PERSONAL_EXPENSES": ("Personal Expenses", "المصروفات الشخصية والمعيشية"),
        "CREDIT_CARD_REPAYMENTS": ("Credit-Card Repayments", "سداد البطاقات الائتمانية (الإمارات دبي الوطني + تسهيل)"),
        "AI_SUBSCRIPTIONS": ("AI Subscriptions", "اشتراكات منصات الذكاء الاصطناعي"),
        "TRILUNAIR_AGENT_OPERATIONS": ("TRILUNAIR AI Agent Allowance", "مخصص تشغيل وكلاء TRILUNAIR الذكي"),
        "INVESTMENT_ALLOCATION": ("Investment Capital Allocation", "مخصص المحفظة الاستثمارية الشهري"),
        "CASH_SAVINGS": ("Liquid Cash Savings", "الادخار النقدي السائل والطوارئ"),
    }
    effective_cycle_outflow = 0.0
    for b_key in VALID_BUCKETS:
        planned_amt = buckets_planned[b_key]
        actual_amt = actual_by_bucket[b_key]
        effective_amt = round(max(planned_amt, actual_amt), 2)
        overrun_amt = round(max(0.0, actual_amt - planned_amt), 2)
        remaining_amt = round(max(0.0, planned_amt - actual_amt), 2)
        effective_cycle_outflow = round(effective_cycle_outflow + effective_amt, 2)
        en_lbl, ar_lbl = bucket_labels[b_key]
        reconciled_buckets.append(
            {
                "category": b_key,
                "labelEn": en_lbl,
                "labelAr": ar_lbl,
                "plannedSar": planned_amt,
                "shareOfSalaryPct": round((planned_amt / monthly_salary) * 100.0, 2) if monthly_salary > 0 else 0.0,
                "importedActualSar": actual_amt,
                "effectiveReconciledOutflowSar": effective_amt,
                "remainingPlannedAllowanceSar": remaining_amt,
                "budgetOverrunSar": overrun_amt,
            }
        )

    # 2. Credit Cards & Trade-Off Analysis
    cards_formatted: list[dict[str, Any]] = []
    for c in cards_raw:
        cards_formatted.append(
            {
                "cardId": c["card_id"],
                "issuerNameEn": c["issuer_name_en"],
                "issuerNameAr": c["issuer_name_ar"],
                "approximateBalanceSar": round(float(c["approximate_balance_sar"]), 2),
                "reportedAmountDueInclArrearsSar": round(float(c["reported_due_incl_arrears_sar"]), 2),
                "provisionalMonthlyAllocationSar": round(float(c["provisional_monthly_allocation_sar"]), 2),
                "excessAboveReportedDueSar": round(
                    float(c["provisional_monthly_allocation_sar"]) - float(c["reported_due_incl_arrears_sar"]),
                    2,
                ),
                "estimatedAnnualAprPct": round(float(c["estimated_annual_apr_pct"]), 2),
                "paymentDueDay": int(c["payment_due_day"]),
                "verifications": {
                    "currentDuesVerified": bool(c["current_dues_verified"]),
                    "delinquencyVerified": bool(c["delinquency_verified"]),
                    "financingChargesVerified": bool(c["financing_charges_verified"]),
                    "paymentDateVerified": bool(c["payment_date_verified"]),
                },
                "notesEn": c["notes_en"],
                "notesAr": c["notes_ar"],
            }
        )

    payoff_sim = _simulate_debt_payoff_months(cards_formatted)
    total_card_balance = round(sum(c["approximateBalanceSar"] for c in cards_formatted), 2)
    total_card_due = round(sum(c["reportedAmountDueInclArrearsSar"] for c in cards_formatted), 2)
    total_card_alloc = round(sum(c["provisionalMonthlyAllocationSar"] for c in cards_formatted), 2)

    debt_vs_inv_tradeoff = {
        "policy": "PARALLEL_INVESTMENT_AND_ACCELERATED_DEBT_REDUCTION",
        "debtEliminationIsBlanketPrerequisite": False,
        "weightedCardFinancingCostAprPct": payoff_sim["weightedEstimatedCardAprPct"],
        "guaranteedEffectiveReturnOfDebtPaydownPct": payoff_sim["weightedEstimatedCardAprPct"],
        "illustrativeDiversifiedInvestmentReturnBandPct": "6.5% – 11.5% (Uncertain / Non-Guaranteed / Subject to Drawdown)",
        "tradeOffExplanationEn": (
            f"Revolving credit-card financing carries an estimated ~{payoff_sim['weightedEstimatedCardAprPct']}% annual cost — "
            "materially higher than expected risk-adjusted market returns. The owner's hybrid plan cures all reported dues/arrears "
            f"(SAR {total_card_due:,.2f}) and allocates SAR {total_card_alloc:,.2f}/mo to extinguish ~SAR {total_card_balance:,.2f} "
            f"in ~{payoff_sim['estimatedMonthsToDebtFree']} months while simultaneously building investment discipline & habit "
            f"with SAR {buckets_planned['INVESTMENT_ALLOCATION']:,.2f}/mo."
        ),
        "tradeOffExplanationAr": (
            f"تكلفة التمويل المتجدد للبطاقات (~{payoff_sim['weightedEstimatedCardAprPct']}% سنوياً تقديرياً) تتجاوز العائد المتوقع للأسواق، "
            f"لذلك تجمع خطة المالك المتوازنة بين تغطية كامل المتأخرات والمستحقات ({total_card_due:,.2f} ريال) وسداد معجل بقيمة {total_card_alloc:,.2f} ريال شهرياً "
            f"(يُطفئ أصل الدين خلال ~{payoff_sim['estimatedMonthsToDebtFree']} أشهر تقديرياً) بالتوازي مع بدء البناء الاستثماري الفوري بمبلغ {buckets_planned['INVESTMENT_ALLOCATION']:,.2f} ريال شهرياً."
        ),
    }

    # 3. Employment Benefits & 60-Day Contract Deadline Intelligence
    ver_flags = json.loads(prof["verification_flags_json"] or "{}")
    employment_benefits = calculate_saudi_employment_benefits(
        start_date_str=str(prof["employment_start_date"]),
        end_date_str=str(prof["contract_expiry_date"]),
        eligible_monthly_wage_sar=float(prof["eligible_final_wage_sar"]),
        annual_leave_days_per_year=float(prof["annual_leave_days_per_year"]),
        annual_leave_taken_days=float(prof["annual_leave_taken_days"]),
        contract_type=str(prof["contract_type"]),
        auto_renews=bool(prof["auto_renews"]),
        non_renewal_notice_days=int(prof["non_renewal_notice_days"]),
        expected_departure_method=str(prof["expected_departure_method"]),
        verification_flags=ver_flags,
    )

    contract_deadlines = compute_contract_renewal_deadlines(
        expiry_date_str=str(prof["contract_expiry_date"]),
        notice_days=int(prof["non_renewal_notice_days"]),
        exact_expiry_verified=bool(ver_flags.get("exactContractExpiryVerified", False)),
        reference_date=ref_dt,
        evidence_records=evidence_list,
    )

    # 4. Wealth Guardian Solvency & Investment Ledger
    guardian = _evaluate_liquidity_and_overdue_priority(prof, cards_formatted)
    investment_comparison = _build_investment_opportunity_comparison(buckets_planned["INVESTMENT_ALLOCATION"])

    formatted_ledger = [
        {
            "entryId": r["entry_id"],
            "salaryCycleId": r["salary_cycle_id"],
            "contributionDate": r["contribution_date"],
            "amountSar": round(float(r["amount_sar"]), 2),
            "amountUsdEquiv": round(float(r["amount_usd_equiv"]), 2),
            "diversifiedEtfSukukSar": round(float(r["diversified_etf_sukuk_sar"]), 2),
            "saudiEquitiesTadawulSar": round(float(r["saudi_equities_tadawul_sar"]), 2),
            "cryptoSpotPaperSar": round(float(r["crypto_spot_paper_sar"]), 2),
            "executionMode": r["execution_mode"],
            "liquidityGuardStatus": r["liquidity_guard_status"],
            "notes": r["notes"],
            "createdAt": r["created_at"],
        }
        for r in ledger_entries
    ]
    cumulative_invested_sar = round(sum(item["amountSar"] for item in formatted_ledger), 2)
    liquid_cash_reserve_sar = round(float(prof["liquid_cash_reserve_sar"]), 2)

    # 4b. Personal Binance Spot Read-Only Bridge (SAR 2,125/mo Allocation, Anti-Double-Counting & Actual-vs-PAPER)
    from app.binance_personal_account import get_personal_binance_overview
    from app.safety_gateway import get_portfolio_snapshot

    binance_overview = get_personal_binance_overview()
    paper_portfolio = get_portfolio_snapshot()
    paper_starting_usd = 1_000_000.0
    paper_net_return_pct = round(
        ((float(paper_portfolio.totalEquity) - paper_starting_usd) / paper_starting_usd) * 100.0,
        3,
    )

    b_summary = binance_overview["portfolioSummary"]
    b_conn_status = str(binance_overview["connectionStatus"])

    # Reconcile active salary-cycle Binance deposits & Spot purchases without double-counting against bank statements or CFO ledger
    cycle_binance_deposits_sar = 0.0
    for cf in binance_overview.get("recentCashflows", []):
        if str(cf.get("direction")) == "DEPOSIT":
            try:
                cf_dt = _parse_iso_date(str(cf.get("occurredAtIso", ""))[:10])
                if resolve_salary_cycle_id(cf_dt, payday_day) == active_cycle_id:
                    cycle_binance_deposits_sar = round(cycle_binance_deposits_sar + float(cf.get("amountSar", 0.0)), 2)
            except Exception:
                pass

    cycle_binance_spot_buys_sar = 0.0
    for tr in binance_overview.get("recentTrades", []):
        if str(tr.get("side")) == "BUY":
            try:
                tr_dt = _parse_iso_date(str(tr.get("tradeTimeIso", ""))[:10])
                if resolve_salary_cycle_id(tr_dt, payday_day) == active_cycle_id:
                    cycle_binance_spot_buys_sar = round(
                        cycle_binance_spot_buys_sar + (float(tr.get("quoteQty", 0.0)) * SAR_PER_USD_PEG),
                        2,
                    )
            except Exception:
                pass

    cycle_ledger_alloc_sar = round(
        sum(
            float(item["cryptoSpotPaperSar"])
            for item in formatted_ledger
            if item["salaryCycleId"] == active_cycle_id and item["entryId"] != "inv_seed_initial_cycle"
        ),
        2,
    )
    statement_inv_actual_sar = actual_by_bucket["INVESTMENT_ALLOCATION"]
    planned_inv_sar = buckets_planned["INVESTMENT_ALLOCATION"]

    # Anti-double-counting rule: a bank transfer to Binance (statement), a CFO ledger allocation, a synced Binance deposit,
    # and subsequent Spot purchases using that same deposited quote cash represent stages of the SAME capital deployment!
    # Therefore effective cycle deployment = max(statement_inv_actual, cycle_ledger_alloc, cycle_binance_deposits, cycle_binance_spot_buys).
    verified_actual_deployment_sar = round(
        max(statement_inv_actual_sar, cycle_ledger_alloc_sar, cycle_binance_deposits_sar, cycle_binance_spot_buys_sar),
        2,
    )
    effective_reconciled_inv_outflow_sar = round(max(planned_inv_sar, verified_actual_deployment_sar), 2)

    contributed_cap_sar = float(b_summary["netContributedCapitalSar"])
    net_pnl_after_fees_sar = float(b_summary["netPnlAfterFeesSar"])
    actual_net_return_pct = (
        round((net_pnl_after_fees_sar / contributed_cap_sar) * 100.0, 2)
        if contributed_cap_sar > 0.01
        else 0.0
    )

    binance_cfo_bridge = {
        "primaryFocus": "CRYPTOCURRENCY_SPOT_MARKETS",
        "connectionStatus": b_conn_status,
        "plannedMonthlyCryptoAllocationSar": planned_inv_sar,
        "plannedMonthlyCryptoAllocationUsd": round(planned_inv_sar / SAR_PER_USD_PEG, 2),
        "activeSalaryCycleId": active_cycle_id,
        "cycleReconciliation": {
            "importedBankStatementInvestmentSar": statement_inv_actual_sar,
            "cfoLedgerCycleAllocationSar": cycle_ledger_alloc_sar,
            "syncedBinanceCycleDepositsSar": cycle_binance_deposits_sar,
            "syncedBinanceCycleSpotPurchasesSar": cycle_binance_spot_buys_sar,
            "deduplicatedActualDeploymentSar": verified_actual_deployment_sar,
            "effectiveReconciledBudgetOutflowSar": effective_reconciled_inv_outflow_sar,
            "remainingPlannedMonthlyBudgetSar": round(max(0.0, planned_inv_sar - verified_actual_deployment_sar), 2),
            "budgetOverrunSar": round(max(0.0, verified_actual_deployment_sar - planned_inv_sar), 2),
            "reconciledWithoutDoubleCount": True,
        },
        "capitalVsPerformanceSeparation": {
            "cumulativeContributedCapitalSar": contributed_cap_sar,
            "realizedPnlSar": float(b_summary["realizedPnlSar"]),
            "unrealizedPnlSar": float(b_summary["unrealizedPnlSar"]),
            "cumulativeTradingFeesSar": float(b_summary["cumulativeFeesSar"]),
            "netMarketPnlAfterFeesSar": net_pnl_after_fees_sar,
            "totalActualBinanceEquitySar": float(b_summary["totalEquitySar"]),
        },
        "cashVsCryptoExposure": {
            "availableBinanceQuoteCashSar": float(b_summary["availableQuoteCashSar"]),
            "investedBinanceCryptoExposureSar": float(b_summary["investedCryptoCapitalSar"]),
            "cryptoMarketExposurePct": float(b_summary["cryptoExposurePct"]),
        },
        "actualVsPaperStrategyComparison": {
            "actualAccountStatus": b_conn_status,
            "actualNetReturnAfterFeesPct": actual_net_return_pct if b_conn_status != "PENDING_OWNER_SETUP" else None,
            "paperSimulatedPortfolioEquityUsd": round(float(paper_portfolio.totalEquity), 2),
            "paperStrategyNetReturnPct": paper_net_return_pct,
            "segregatedBalancesAndReturns": True,
            "comparisonNoteEn": (
                "Personal Binance account is PENDING OWNER SETUP; PAPER simulation metrics are never mixed with actual personal returns."
                if b_conn_status == "PENDING_OWNER_SETUP"
                else "Actual personal Binance Spot performance is measured net of fees on contributed capital and kept strictly separate from the $1M PAPER simulation."
            ),
        },
        "governanceInvariants": {
            "assumesGuaranteedReturns": False,
            "treatsProjectedEmploymentBenefitsAsCash": False,
            "tradingMode": "PAPER",
            "liveAuthorized": False,
        },
    }

    # 5. Long-Term 36-Month Forecast (Strictly Separating Liquid/Invested Assets vs Contingent Employment Benefits)
    est_payoff_m = payoff_sim["estimatedMonthsToDebtFree"] or 6
    horizon_months = 36
    projected_liquid_savings_36m = round(liquid_cash_reserve_sar + (buckets_planned["CASH_SAVINGS"] * horizon_months), 2)
    # Conservative 0% speculative gain baseline on principal contributions (never assuming guaranteed market profit)
    post_debt_extra_months = max(0, horizon_months - est_payoff_m)
    projected_invested_principal_base_36m = round(
        buckets_planned["INVESTMENT_ALLOCATION"] * horizon_months,
        2,
    )
    projected_invested_if_card_budget_redirected_36m = round(
        projected_invested_principal_base_36m + (post_debt_extra_months * total_card_alloc),
        2,
    )

    # 6. Actionable Financial & Legal Alerts
    alerts: list[dict[str, Any]] = []
    unverified_cards = [
        c["issuerNameEn"]
        for c in cards_formatted
        if not (
            c["verifications"]["currentDuesVerified"]
            and c["verifications"]["delinquencyVerified"]
            and c["verifications"]["financingChargesVerified"]
            and c["verifications"]["paymentDateVerified"]
        )
    ]
    if unverified_cards:
        alerts.append(
            {
                "alertId": "CREDIT_CARD_STATEMENTS_VERIFICATION_REQUIRED",
                "severity": "WARNING",
                "category": "DEBT_AND_ARREARS",
                "titleEn": "Verify Official Credit-Card Statements & Arrears Cutoff Dates",
                "titleAr": "التحقق الإلزامي من كشوف البطاقات الائتمانية الرسمية وتواريخ الاستحقاق والمتأخرات",
                "detailEn": (
                    f"Reported dues including arrears (Tasheel SAR 1,700 + Emirates NBD SAR 1,800 = SAR {total_card_due:,.0f}) "
                    "are provisional. Confirm exact statement due dates, delinquency status, and APR charges immediately."
                ),
                "detailAr": (
                    f"المبالغ المستحقة المعلنة شاملة المتأخرات (تسهيل 1,700 ريال + الإمارات دبي الوطني 1,800 ريال = {total_card_due:,.0f} ريال) "
                    "تقديرية؛ يجب مطابقتها مع كشف الحساب الرسمي وتاريخ الاستحقاق الفعلي."
                ),
            }
        )

    if not contract_deadlines["exactExpiryDateVerified"]:
        alerts.append(
            {
                "alertId": "VERIFY_QIWA_FIXED_TERM_CONTRACT_EXPIRY",
                "severity": "IMPORTANT",
                "category": "EMPLOYMENT_CONTRACT",
                "titleEn": f"Verify Exact Fixed-Term Expiry Date (Illustrative 60-Day Cutoff: {contract_deadlines['finalNoticeDeadlineDate']})",
                "titleAr": f"تثبيت تاريخ انتهاء العقد المحدد من منصة قوى (الموعد الإيضاحي لمهلة 60 يوماً: {contract_deadlines['finalNoticeDeadlineDate']})",
                "detailEn": (
                    "Contract auto-renews unless non-renewal notice is served at least 60 days prior to expiry. "
                    f"If expiry is {contract_deadlines['contractExpiryDate']}, final notice deadline is {contract_deadlines['finalNoticeDeadlineDate']} "
                    "(reminders set at 90, 75, and 65 days). System will NEVER auto-send any notice."
                ),
                "detailAr": (
                    "يتجدد العقد المحدد المدة تلقائياً ما لم يُقدّم إشعار عدم التجديد قبل 60 يوماً على الأقل. "
                    f"إذا كان الانتهاء {contract_deadlines['contractExpiryDate']} فالموعد النهائي للإشعار هو {contract_deadlines['finalNoticeDeadlineDate']} "
                    "(مع تنبيهات قبل 90 و75 و65 يوماً). لن يرسل النظام أي إشعار تلقائياً مطلقاً."
                ),
            }
        )

    if guardian["guardianStatus"] != "INVESTMENT_ACTIVE_PARALLEL_WITH_DEBT_PAYDOWN":
        alerts.append(
            {
                "alertId": "LIQUIDITY_OVERDUE_PRIORITY_TRIGGERED",
                "severity": "CRITICAL",
                "category": "LIQUIDITY_GUARDIAN",
                "titleEn": "Overdue Obligations Prioritized Ahead of Optional Investment",
                "titleAr": "تفعيل أولوية المتأخرات والسيولة الأساسية قبل التمويل الاستثماري الاختياري",
                "detailEn": guardian["summaryEn"],
                "detailAr": guardian["summaryAr"],
            }
        )

    alerts.append(
        {
            "alertId": "PAPER_EXECUTION_AND_BENEFITS_SEGREGATION_LOCK",
            "severity": "INFO",
            "category": "GOVERNANCE_SAFEGUARD",
            "titleEn": "Contingent Benefits Segregated & Binance PAPER-Only Lock Active",
            "titleAr": "عزل المستحقات المستقبلية المحتملة واستمرار قفل التداول الورقي PAPER",
            "detailEn": (
                "Projected Saudi employment benefits (SAR 72,000 / SAR 52,000 provisional) are strictly excluded from liquid cash "
                "and trading balances. TRILUNAIR execution remains locked to PAPER mode with zero real orders."
            ),
            "detailAr": (
                "مستحقات نهاية الخدمة والإجازات المقدرة (72,000 / 52,000 ريال بصفة تقديرية) مفصولة كلياً عن السيولة النقدية ورصيد التداول، "
                "ويعمل محرك التنفيذ بوضع PAPER الورقي حصراً."
            ),
        }
    )

    return {
        "generatedAt": utc_now_iso(),
        "currency": "SAR",
        "fxPegSarPerUsd": SAR_PER_USD_PEG,
        "salaryAndCashFlow": {
            "monthlySalarySar": monthly_salary,
            **compute_next_payday_info(ref_dt, payday_day),
            "plannedTotalAllocatedSar": planned_total,
            "unallocatedSalarySar": round(monthly_salary - planned_total, 2),
            "balancedToExactSalary": abs(monthly_salary - planned_total) < 0.01,
            "buckets": reconciled_buckets,
            "reconciledCycleTotalOutflowSar": effective_cycle_outflow,
            "reconciledCycleSurplusOrDeficitSar": round(monthly_salary - effective_cycle_outflow, 2),
            "importedStatementCountInCycle": len(cycle_txs),
            "cardPurchaseMemoExcludedFromDoubleCountSar": card_purchase_memo_only_sar,
            "antiDoubleCountingPolicy": (
                "Imported statement items deduplicate by SHA-256 fingerprint and reconcile against planned category buckets "
                "(effective = max(planned, actual)); credit-card purchase memos never double-count alongside SAR 6,000 card payoff transfers."
            ),
        },
        "debtPlanner": {
            "totalApproximateCardBalanceSar": total_card_balance,
            "totalReportedDueInclArrearsSar": total_card_due,
            "monthlyRepaymentBudgetSar": buckets_planned["CREDIT_CARD_REPAYMENTS"],
            "allocatedAcrossCardsSar": total_card_alloc,
            "budgetFullyAssigned": abs(buckets_planned["CREDIT_CARD_REPAYMENTS"] - total_card_alloc) < 0.01,
            "cards": cards_formatted,
            "payoffProjection": payoff_sim,
            "debtVsInvestmentTradeOff": debt_vs_inv_tradeoff,
        },
        "employmentBenefits": employment_benefits,
        "contractRenewalIntelligence": contract_deadlines,
        "investmentCommandCenter": {
            "ledgerSummary": {
                "EntryCount": len(formatted_ledger),
                "entryCount": len(formatted_ledger),
                "cumulativeAllocatedCapitalSar": cumulative_invested_sar,
                "cumulativeAllocatedCapitalUsdEquiv": round(cumulative_invested_sar / SAR_PER_USD_PEG, 2),
                "entries": formatted_ledger,
            },
            "opportunityAndRiskAnalysis": investment_comparison,
            "binancePersonalCfoBridge": binance_cfo_bridge,
        },
        "binancePersonalCfoBridge": binance_cfo_bridge,
        "balanceSheetAndForecast": {
            "liquidAssetsAvailableNow": {
                "liquidCashReserveSar": liquid_cash_reserve_sar,
                "availableCurrentCycleCashSar": round(float(prof["available_cycle_cash_sar"]), 2),
                "cumulativeInvestedCapitalLedgerSar": cumulative_invested_sar,
                "actualBinanceSpotEquitySar": float(b_summary["totalEquitySar"]),
                "includesUnreceivedEmploymentBenefits": False,
            },
            "contingentFutureReceivablesSegregated": {
                "statusLabel": PROVISIONAL_LEGAL_LABEL,
                "classification": "CONTINGENT_FUTURE_RECEIVABLE_NOT_LIQUID_CASH",
                "fixedTermNonRenewalCombinedEstimateSar": employment_benefits["scenarios"]["fixedTermExpiryNonRenewal"]["combinedEstimatedBenefitsSar"],
                "ordinaryResignationCombinedEstimateSar": employment_benefits["scenarios"]["ordinaryResignation"]["combinedEstimatedBenefitsSar"],
                "usableForImmediateDebtOrTrading": False,
            },
            "thirtySixMonthIllustrativeForecast": {
                "horizonMonths": horizon_months,
                "projectedLiquidCashSavingsSar": projected_liquid_savings_36m,
                "projectedInvestedPrincipalBaselineSar": projected_invested_principal_base_36m,
                "projectedInvestedPrincipalWithPostDebtSnowballSar": projected_invested_if_card_budget_redirected_36m,
                "contingentEmploymentSettlementSeparateSar": employment_benefits["scenarios"]["fixedTermExpiryNonRenewal"]["combinedEstimatedBenefitsSar"],
                "assumesSpeculativeMarketGains": False,
            },
        },
        "wealthGuardian": guardian,
        "financialAlerts": alerts,
    }


# ==============================================================================
# 5. Request Schemas & REST API Endpoints (/api/wealth/*)
# ==============================================================================


class SalaryAllocationUpdateRequest(BaseModel):
    monthlySalarySar: float = Field(default=20000.0, gt=0)
    paydayDayOfMonth: int = Field(default=28, ge=1, le=28)
    personalExpensesSar: float = Field(default=8000.0, ge=0)
    creditCardRepaymentsSar: float = Field(default=6000.0, ge=0)
    aiSubscriptionsSar: float = Field(default=1375.0, ge=0)
    trilunairAgentOperationsSar: float = Field(default=500.0, ge=0)
    investmentAllocationSar: float = Field(default=2125.0, ge=0)
    cashSavingsSar: float = Field(default=2000.0, ge=0)
    liquidCashReserveSar: float | None = Field(default=None, ge=0)
    availableCycleCashSar: float | None = Field(default=None, ge=0)


class CreditCardItemUpdate(BaseModel):
    cardId: str
    approximateBalanceSar: float = Field(ge=0)
    reportedAmountDueInclArrearsSar: float = Field(ge=0)
    provisionalMonthlyAllocationSar: float = Field(ge=0)
    estimatedAnnualAprPct: float = Field(default=32.0, ge=0, le=100)
    paymentDueDay: int = Field(default=5, ge=1, le=28)
    currentDuesVerified: bool = False
    delinquencyVerified: bool = False
    financingChargesVerified: bool = False
    paymentDateVerified: bool = False


class StatementTransactionInput(BaseModel):
    txDate: str
    description: str
    amountSar: float = Field(gt=0)
    category: BucketCategory
    accountSource: str = "BANK_CURRENT"
    entryKind: Literal["ACTUAL_EXPENSE", "CARD_REPAYMENT_TRANSFER", "CREDIT_CARD_PURCHASE_MEMO"] = "ACTUAL_EXPENSE"


class StatementImportRequest(BaseModel):
    transactions: list[StatementTransactionInput]


class EmploymentContractUpdateRequest(BaseModel):
    commencementDate: str = "2024-10-10"
    contractExpiryDate: str = "2027-10-10"
    contractType: Literal["FIXED_TERM", "INDEFINITE"] = "FIXED_TERM"
    autoRenews: bool = True
    nonRenewalNoticeDays: int = Field(default=60, ge=1, le=180)
    expectedDepartureMethod: str = "NON_RENEWAL_UPON_EXPIRY"
    eligibleFinalWageSar: float = Field(default=20000.0, gt=0)
    annualLeaveDaysPerYear: float = Field(default=21.0, ge=21.0, le=60.0)
    annualLeaveTakenDays: float = Field(default=0.0, ge=0.0)
    exactContractExpiryVerified: bool = False
    eligibleWageComponentsVerified: bool = False
    applicableTerminationReasonVerified: bool = False
    officialAccruedLeaveBalanceVerified: bool = False
    leaveCarryoverAndSettlementHistoryVerified: bool = False
    contractualEnhancementsVerified: bool = False
    applicableLegalExceptionsVerified: bool = False


class EmploymentScenarioCalcRequest(BaseModel):
    commencementDate: str = "2024-10-10"
    targetEndDate: str = "2027-10-10"
    eligibleMonthlyWageSar: float = Field(default=20000.0, gt=0)
    annualLeaveDaysPerYear: float = Field(default=21.0, ge=21.0, le=60.0)
    annualLeaveTakenDays: float = Field(default=0.0, ge=0.0)
    overrideUnusedLeaveDays: float | None = Field(default=None, ge=0.0)
    nonRenewalNoticeDays: int = Field(default=60, ge=1, le=180)


class ContractEvidenceCreateRequest(BaseModel):
    documentType: Literal[
        "SIGNED_EMPLOYMENT_CONTRACT",
        "QIWA_CONTRACT_EXTRACT",
        "HR_LEAVE_BALANCE_STATEMENT",
        "DRAFT_NON_RENEWAL_NOTICE",
        "NOTICE_DELIVERY_PROOF",
    ] = "QIWA_CONTRACT_EXTRACT"
    title: str
    contentOrReferenceForHash: str = ""
    precomputedSha256: str | None = None
    deliveryChannel: str = "QIWA_PLATFORM"
    verifiedByOwner: bool = False
    notes: str = ""


class InvestmentLedgerCreateRequest(BaseModel):
    contributionDate: str | None = None
    amountSar: float = Field(default=2125.0, gt=0)
    diversifiedWeightPct: float = Field(default=45.0, ge=0, le=100)
    saudiEquitiesWeightPct: float = Field(default=35.0, ge=0, le=100)
    cryptoSpotPaperWeightPct: float = Field(default=20.0, ge=0, le=100)
    notes: str = "Monthly investment capital allocation (PAPER simulation & research)"


@wealth_router.get("/overview")
def api_get_wealth_overview() -> dict[str, Any]:
    """استرجاع اللوحة الشاملة للمدير المالي الشخصي، الديون، مستحقات العمل السعودية، مهلة العقد، ودفتر الاستثمار."""
    return get_wealth_architect_overview()


@wealth_router.put("/allocation")
def api_update_salary_allocation(req: SalaryAllocationUpdateRequest) -> dict[str, Any]:
    """تحديث خطة توزيع الراتب الشهري والسيولة المتاحة مع التحقق الصارم من توازن الميزانية."""
    ensure_wealth_architect_tables()
    total_buckets = round(
        req.personalExpensesSar
        + req.creditCardRepaymentsSar
        + req.aiSubscriptionsSar
        + req.trilunairAgentOperationsSar
        + req.investmentAllocationSar
        + req.cashSavingsSar,
        2,
    )
    if total_buckets > round(req.monthlySalarySar, 2) + 0.01:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Allocation sum (SAR {total_buckets:,.2f}) exceeds monthly salary (SAR {req.monthlySalarySar:,.2f})."
            ),
        )

    now = utc_now_iso()
    with db_session() as conn:
        existing = conn.execute(
            "SELECT liquid_cash_reserve_sar, available_cycle_cash_sar FROM wealth_cfo_profile WHERE profile_id = 'owner-primary'"
        ).fetchone()
        liq_res = (
            req.liquidCashReserveSar
            if req.liquidCashReserveSar is not None
            else float(existing["liquid_cash_reserve_sar"])
        )
        avail_cash = (
            req.availableCycleCashSar
            if req.availableCycleCashSar is not None
            else float(existing["available_cycle_cash_sar"])
        )
        conn.execute(
            """
            UPDATE wealth_cfo_profile
            SET monthly_salary_sar = ?, payday_day_of_month = ?,
                personal_expenses_sar = ?, credit_card_repayments_sar = ?,
                ai_subscriptions_sar = ?, trilunair_agent_operations_sar = ?,
                investment_allocation_sar = ?, cash_savings_sar = ?,
                liquid_cash_reserve_sar = ?, available_cycle_cash_sar = ?,
                updated_at = ?
            WHERE profile_id = 'owner-primary'
            """,
            (
                req.monthlySalarySar,
                req.paydayDayOfMonth,
                req.personalExpensesSar,
                req.creditCardRepaymentsSar,
                req.aiSubscriptionsSar,
                req.trilunairAgentOperationsSar,
                req.investmentAllocationSar,
                req.cashSavingsSar,
                liq_res,
                avail_cash,
                now,
            ),
        )
        append_audit_log(
            actor="OWNER_CFO",
            source="TERMINAL",
            action="WEALTH_SALARY_ALLOCATION_UPDATED",
            severity="INFO",
            details_ar=f"تم تحديث خطة توزيع الراتب الشهري ({req.monthlySalarySar:,.0f} ريال) ومخصص الاستثمار ({req.investmentAllocationSar:,.0f} ريال).",
            details_en=f"Updated Personal CFO salary allocation (Salary SAR {req.monthlySalarySar:,.0f}, Investment SAR {req.investmentAllocationSar:,.0f}).",
            conn=conn,
        )
    return get_wealth_architect_overview()


@wealth_router.put("/credit-cards")
def api_update_credit_cards(cards: list[CreditCardItemUpdate] = Body(...)) -> dict[str, Any]:
    """تحديث أرصدة البطاقات الائتمانية والمبالغ المستحقة وتوزيعات السداد وحالة التثبت الرسمي."""
    ensure_wealth_architect_tables()
    now = utc_now_iso()
    with db_session() as conn:
        for item in cards:
            row = conn.execute(
                "SELECT card_id FROM wealth_credit_cards WHERE card_id = ?",
                (item.cardId,),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail=f"Unknown cardId '{item.cardId}'")
            conn.execute(
                """
                UPDATE wealth_credit_cards
                SET approximate_balance_sar = ?, reported_due_incl_arrears_sar = ?,
                    provisional_monthly_allocation_sar = ?, estimated_annual_apr_pct = ?,
                    payment_due_day = ?, current_dues_verified = ?, delinquency_verified = ?,
                    financing_charges_verified = ?, payment_date_verified = ?, updated_at = ?
                WHERE card_id = ?
                """,
                (
                    item.approximateBalanceSar,
                    item.reportedAmountDueInclArrearsSar,
                    item.provisionalMonthlyAllocationSar,
                    item.estimatedAnnualAprPct,
                    item.paymentDueDay,
                    int(item.currentDuesVerified),
                    int(item.delinquencyVerified),
                    int(item.financingChargesVerified),
                    int(item.paymentDateVerified),
                    now,
                    item.cardId,
                ),
            )
    return get_wealth_architect_overview()


@wealth_router.post("/statements/import")
def api_import_statement_transactions(req: StatementImportRequest) -> dict[str, Any]:
    """
    استيراد حركات كشف الحساب البنكي أو البطاقات مع منع الازدواج الحسابي:
    1. بصمة SHA-256 تمنع تكرار نفس القيد عند إعادة رفع نفس الكشف.
    2. الحركات الفعلية تُطابق مقابل المخصص الشهري المخطط للفئة ولا تُجمع فوقه مرتين.
    3. مشتريات البطاقة التفصيلية المعلّمة كـ CREDIT_CARD_PURCHASE_MEMO لا تُحسب مرتين بجانب دفعة سداد البطاقة البالغة 6,000 ريال.
    """
    ensure_wealth_architect_tables()
    now = utc_now_iso()
    imported_count = 0
    duplicates_skipped = 0

    with db_session() as conn:
        prof = conn.execute(
            "SELECT payday_day_of_month FROM wealth_cfo_profile WHERE profile_id = 'owner-primary'"
        ).fetchone()
        payday = int(prof["payday_day_of_month"]) if prof else 28

        for tx in req.transactions:
            tx_dt = _parse_iso_date(tx.txDate)
            cycle_id = resolve_salary_cycle_id(tx_dt, payday)
            fp = compute_statement_fingerprint(
                tx_date=tx_dt.isoformat(),
                description=tx.description,
                amount_sar=tx.amountSar,
                account_source=tx.accountSource,
            )
            exists = conn.execute(
                "SELECT tx_id FROM wealth_statement_transactions WHERE tx_fingerprint = ?",
                (fp,),
            ).fetchone()
            if exists is not None:
                duplicates_skipped += 1
                continue

            rec_mode = (
                "MEMO_EXCLUDED_COVERED_BY_CARD_REPAYMENT_BUCKET"
                if tx.entryKind == "CREDIT_CARD_PURCHASE_MEMO"
                else "RECONCILED_AGAINST_PLANNED_BUCKET"
            )
            conn.execute(
                """
                INSERT INTO wealth_statement_transactions (
                    tx_id, tx_fingerprint, salary_cycle_id, tx_date, merchant_or_description,
                    amount_sar, category, account_source, entry_kind, reconciliation_mode, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"stx_{uuid.uuid4().hex[:12]}",
                    fp,
                    cycle_id,
                    tx_dt.isoformat(),
                    tx.description.strip()[:160],
                    round(float(tx.amountSar), 2),
                    tx.category,
                    tx.accountSource.strip().upper()[:40],
                    tx.entryKind,
                    rec_mode,
                    now,
                ),
            )
            imported_count += 1

    overview = get_wealth_architect_overview()
    return {
        "importedCount": imported_count,
        "duplicatesSkippedCount": duplicates_skipped,
        "salaryAndCashFlow": overview["salaryAndCashFlow"],
    }


@wealth_router.put("/employment/contract")
def api_update_employment_contract(req: EmploymentContractUpdateRequest) -> dict[str, Any]:
    """حفظ وتحديث بيانات عقد العمل المحدد المدة وبنود التثبت القانوني في السجل المستديم."""
    ensure_wealth_architect_tables()
    _ = _parse_iso_date(req.commencementDate)
    _ = _parse_iso_date(req.contractExpiryDate)

    ver_json = json.dumps(
        {
            "exactContractExpiryVerified": req.exactContractExpiryVerified,
            "contractTypeAndRenewalTermsVerified": True,
            "eligibleWageComponentsVerified": req.eligibleWageComponentsVerified,
            "applicableTerminationReasonVerified": req.applicableTerminationReasonVerified,
            "officialAccruedLeaveBalanceVerified": req.officialAccruedLeaveBalanceVerified,
            "leaveCarryoverAndSettlementHistoryVerified": req.leaveCarryoverAndSettlementHistoryVerified,
            "contractualEnhancementsVerified": req.contractualEnhancementsVerified,
            "applicableLegalExceptionsVerified": req.applicableLegalExceptionsVerified,
        }
    )
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE wealth_cfo_profile
            SET employment_start_date = ?, contract_expiry_date = ?, contract_type = ?,
                auto_renews = ?, non_renewal_notice_days = ?, expected_departure_method = ?,
                eligible_final_wage_sar = ?, annual_leave_days_per_year = ?, annual_leave_taken_days = ?,
                verification_flags_json = ?, updated_at = ?
            WHERE profile_id = 'owner-primary'
            """,
            (
                req.commencementDate,
                req.contractExpiryDate,
                req.contractType,
                int(req.autoRenews),
                req.nonRenewalNoticeDays,
                req.expectedDepartureMethod,
                req.eligibleFinalWageSar,
                req.annualLeaveDaysPerYear,
                req.annualLeaveTakenDays,
                ver_json,
                now,
            ),
        )
        append_audit_log(
            actor="OWNER_CFO",
            source="TERMINAL",
            action="EMPLOYMENT_CONTRACT_TERMS_UPDATED",
            severity="INFO",
            details_ar=f"تحديث معطيات عقد العمل المحدد المدة (انتهاء: {req.contractExpiryDate}، مهلة إشعار: {req.nonRenewalNoticeDays} يوماً).",
            details_en=f"Updated Saudi fixed-term employment contract profile (expiry={req.contractExpiryDate}, noticeDays={req.nonRenewalNoticeDays}).",
            conn=conn,
        )
    return get_wealth_architect_overview()


@wealth_router.post("/employment/calculate")
def api_calculate_employment_scenario(req: EmploymentScenarioCalcRequest) -> dict[str, Any]:
    """تشغيل محاكاة فورية لمستحقات نظام العمل السعودي ومواعيد مهلة الإشعار لأي تاريخ أو أجر مفترض."""
    benefits = calculate_saudi_employment_benefits(
        start_date_str=req.commencementDate,
        end_date_str=req.targetEndDate,
        eligible_monthly_wage_sar=req.eligibleMonthlyWageSar,
        annual_leave_days_per_year=req.annualLeaveDaysPerYear,
        annual_leave_taken_days=req.annualLeaveTakenDays,
        override_unused_leave_days=req.overrideUnusedLeaveDays,
        non_renewal_notice_days=req.nonRenewalNoticeDays,
    )
    deadlines = compute_contract_renewal_deadlines(
        expiry_date_str=req.targetEndDate,
        notice_days=req.nonRenewalNoticeDays,
        exact_expiry_verified=False,
    )
    return {
        "benefitsCalculation": benefits,
        "contractRenewalDeadlines": deadlines,
    }


@wealth_router.post("/contract/evidence")
def api_record_contract_evidence(req: ContractEvidenceCreateRequest) -> dict[str, Any]:
    """حفظ بصمة ومرجع مستندات العقد وإثباتات الإشعار بأمان دون إرسال أي إشعار خارجي تلقائياً."""
    ensure_wealth_architect_tables()
    if req.precomputedSha256 and len(req.precomputedSha256.strip()) == 64:
        digest = req.precomputedSha256.strip().lower()
    else:
        digest = hashlib.sha256((req.contentOrReferenceForHash or req.title).encode("utf-8")).hexdigest()

    ev_id = f"ev_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO wealth_contract_evidence (
                evidence_id, document_type, title, document_sha256,
                delivery_channel, verified_by_owner, notes, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev_id,
                req.documentType,
                req.title.strip()[:140],
                digest,
                req.deliveryChannel.strip()[:60],
                int(req.verifiedByOwner),
                req.notes.strip()[:400],
                now,
            ),
        )
        append_audit_log(
            actor="OWNER_CFO",
            source="TERMINAL",
            action="CONTRACT_EVIDENCE_VAULTED",
            severity="INFO",
            details_ar=f"حفظ دليل تعاقدي في الخزنة ({req.documentType}): {req.title[:60]} — لم يتم إرسال أي إشعار خارجي تلقائي.",
            details_en=f"Vaulted contract/notice evidence ({req.documentType}): {req.title[:60]} — autoSendNonRenewalNotice=false.",
            conn=conn,
        )

    return {
        "evidenceId": ev_id,
        "documentSha256": digest,
        "autoNoticeSent": False,
        "recordedAt": now,
    }


@wealth_router.post("/investment/ledger")
def api_record_investment_allocation(req: InvestmentLedgerCreateRequest) -> dict[str, Any]:
    """
    تسجيل دفعة تخصيص استثماري في دفتر الأستاذ المخصص مع فحص حارس السيولة أولاً:
    - يرفض التمويل الاختياري تلقائياً (HTTP 409) إذا كانت السيولة الفورية للدورة لا تغطي المصروفات الأساسية والمتأخرات الواجبة.
    - يحافظ دائماً على وضع التنفيذ الورقي (PAPER_SIMULATION_ONLY).
    """
    ensure_wealth_architect_tables()
    total_w = req.diversifiedWeightPct + req.saudiEquitiesWeightPct + req.cryptoSpotPaperWeightPct
    if abs(total_w - 100.0) > 0.05:
        raise HTTPException(status_code=422, detail=f"Sleeve weights must sum to 100%; got {total_w:.2f}%.")

    overview = get_wealth_architect_overview()
    guardian = overview["wealthGuardian"]
    if guardian["guardianStatus"] == "HALT_OPTIONAL_INVESTMENT_PRIORITIZE_OVERDUE_DUES":
        raise HTTPException(
            status_code=409,
            detail=(
                "OVERDUE_OBLIGATION_PRIORITY: Optional investment allocation paused because immediate cycle cash "
                "is insufficient to cover mandatory living expenses and overdue credit-card dues."
            ),
        )

    dt = _parse_iso_date(req.contributionDate) if req.contributionDate else date.today()
    payday = int(overview["salaryAndCashFlow"]["paydayDayOfMonth"])
    cycle_id = resolve_salary_cycle_id(dt, payday)

    amt_sar = round(float(req.amountSar), 2)
    div_sar = round(amt_sar * (req.diversifiedWeightPct / 100.0), 2)
    saudi_sar = round(amt_sar * (req.saudiEquitiesWeightPct / 100.0), 2)
    crypto_sar = round(amt_sar - div_sar - saudi_sar, 2)
    now = utc_now_iso()
    entry_id = f"inv_{uuid.uuid4().hex[:12]}"

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO wealth_investment_ledger (
                entry_id, salary_cycle_id, contribution_date, amount_sar, amount_usd_equiv,
                diversified_etf_sukuk_sar, saudi_equities_tadawul_sar, crypto_spot_paper_sar,
                execution_mode, liquidity_guard_status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PAPER_SIMULATION_ONLY', ?, ?, ?)
            """,
            (
                entry_id,
                cycle_id,
                dt.isoformat(),
                amt_sar,
                round(amt_sar / SAR_PER_USD_PEG, 2),
                div_sar,
                saudi_sar,
                crypto_sar,
                guardian["guardianStatus"],
                req.notes.strip()[:300],
                now,
            ),
        )
        append_audit_log(
            actor="OWNER_WEALTH_ARCHITECT",
            source="TERMINAL",
            action="INVESTMENT_LEDGER_ALLOCATION_RECORDED",
            severity="INFO",
            details_ar=f"قيد تخصيص استثماري بقيمة {amt_sar:,.2f} ريال (وضع المحاكاة الورقية PAPER فقط دون أوامر حقيقية).",
            details_en=f"Recorded SAR {amt_sar:,.2f} investment capital ledger allocation (PAPER_SIMULATION_ONLY).",
            conn=conn,
        )

    return get_wealth_architect_overview()
