"""
بوابة الأمان المالي، المدقق الموحد للأوامر، ومحرك المخاطر الحتمي (Financial Safety Gateway).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

تطبق هذه الوحدة المبادئ الصارمة التالية دون أي استثناء:
1. التداول الورقي الافتراضي (PAPER): لا يمكن تفعيل وضع التداول الحقيقي (LIVE) إلا بعد التحقق من
   سلامة الأنظمة الخمسة، عدم تفعيل مفتاح الطوارئ، الإقرار الصريح بالمخاطر، مطابقة عبارة التأكيد،
   وإدخال الرمز السري للمسؤول (TRILUNAIR_ADMIN_PIN).
2. مفتاح الإيقاف الطارئ (Kill Switch): يعيد النظام فوراً إلى وضع PAPER، يلغي جميع المقترحات المعلقة،
   ويجمد قبول أو تنفيذ أي أوامر جديدة حتى يتم فك التجميد يدوياً.
3. السياسة الموحدة (Unified Policy): تخضع الأوامر الصوتية (VOICE) والنصية (TEXT) واليدوية (TERMINAL)
   لذات خط أنابيب التحقق والفحص الحتمي والتصريح الصريح قبل التنفيذ.
"""

from __future__ import annotations

import json
import math
import os
from typing import Final
import uuid

from fastapi import HTTPException

from app.database import (
    append_audit_log,
    check_audit_trail_health,
    db_session,
    utc_now_iso,
)
from app.market_engine import market_engine
from app.models import (
    EstimatedTradingCosts,
    KillSwitchRequest,
    MarketAsset,
    OrderExecuteRequest,
    OrderExecuteResponse,
    OrderRecord,
    PortfolioSnapshot,
    PositionItem,
    RiskAssessment,
    RiskCheckItem,
    SafetyChecks,
    SystemProviders,
    SystemStatus,
    TradeProposalDetails,
    TradeProposalEvaluation,
    TradeProposalInput,
    TradingMode,
    TradingModeRequest,
)

APP_NAME: Final[str] = "My Road to be Trilunair Dr.MaJoOoOoOoD"
APP_VERSION: Final[str] = "1.0.0"
TRILUNAIR_TARGET_USD: Final[float] = 1_000_000_000_000.0  # 1 تريليون دولار
LIVE_CONFIRMATION_PHRASE: Final[str] = "AUTHORIZE LIVE TRADING DR MAJOOOOOOD"

# الحدود القصوى الحتمية لمحرك المخاطر
MAX_SINGLE_ORDER_EQUITY_RATIO: Final[float] = 0.25  # 25% من إجمالي حقوق الملكية
MAX_ASSET_CONCENTRATION_PCT: Final[float] = 35.0    # 35% تركز أصل واحد
COMMISSION_BPS: Final[float] = 5.0                  # 5 نقاط أساس عمولة مؤسسية


def get_expected_admin_pin() -> str:
    """قراءة الرمز السري للمسؤول من متغير البيئة مع القيمة الافتراضية الموثقة للاختبار (7777)."""
    return (os.getenv("TRILUNAIR_ADMIN_PIN") or "7777").strip()


def detect_active_providers() -> SystemProviders:
    """اكتشاف مزودي الذكاء الاصطناعي والصوت النشطين بناءً على مفاتيح البيئة."""
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())

    if has_openai:
        llm = "openai-cloud+deterministic-council"
        stt = "openai-whisper+web-speech"
        tts = "openai-tts+speech-synthesis"
    elif has_gemini:
        llm = "gemini-cloud+deterministic-council"
        stt = "web-speech+server-fallback"
        tts = "speech-synthesis+server-wav"
    else:
        llm = "deterministic-council+optional-cloud"
        stt = "web-speech+server-fallback"
        tts = "speech-synthesis+server-wav"

    return SystemProviders(llmProvider=llm, sttProvider=stt, ttsProvider=tts)


def evaluate_system_safety_checks() -> SafetyChecks:
    """إجراء الفحوصات الخمسة لسلامة محرك المخاطر وسجل التدقيق وحدود التراجع."""
    with db_session() as conn:
        state = conn.execute("SELECT * FROM system_state WHERE id = 1").fetchone()

    max_dd_ok = state is not None and 0.5 <= float(state["max_allowed_drawdown_pct"]) <= 20.0
    audit_ok = check_audit_trail_health()
    risk_engine_ok = (
        0.05 <= MAX_SINGLE_ORDER_EQUITY_RATIO <= 0.50
        and 10.0 <= MAX_ASSET_CONCENTRATION_PCT <= 60.0
    )

    return SafetyChecks(
        riskEngineVerified=risk_engine_ok,
        maxDrawdownConfigured=max_dd_ok,
        killSwitchReady=state is not None,
        positionLimitsActive=True,
        auditTrailHealthy=audit_ok,
    )


def get_system_status() -> SystemStatus:
    """استرجاع الحالة الراهنة للنظام ووضع التداول والفحوصات الأمنية الخمسة."""
    checks = evaluate_system_safety_checks()
    providers = detect_active_providers()
    with db_session() as conn:
        state = conn.execute("SELECT * FROM system_state WHERE id = 1").fetchone()

    trading_mode: TradingMode = "LIVE" if state["trading_mode"] == "LIVE" else "PAPER"
    return SystemStatus(
        appName=APP_NAME,
        version=APP_VERSION,
        tradingMode=trading_mode,
        killSwitchActive=bool(state["kill_switch_active"]),
        liveAuthorized=bool(state["live_authorized"]),
        safetyChecks=checks,
        providers=providers,
    )


def set_trading_mode(req: TradingModeRequest) -> SystemStatus:
    """
    بوابة تصاريح تبديل وضع التداول بين الورقي (PAPER) والحقيقي (LIVE).
    يُسمح بالعودة إلى PAPER فوراً في جميع الظروف، بينما يتطلب LIVE استيفاء كافة الشروط الخمسة.
    """
    if req.targetMode == "PAPER":
        with db_session() as conn:
            conn.execute(
                """
                UPDATE system_state
                SET trading_mode = 'PAPER', live_authorized = 0, updated_at = ?
                WHERE id = 1
                """,
                (utc_now_iso(),),
            )
            append_audit_log(
                actor="ADMIN_GATEWAY",
                source="TERMINAL",
                action="SWITCH_MODE_PAPER",
                severity="INFO",
                details_ar="تم التبديل الفوري إلى وضع التداول الورقي الآمن (PAPER) وإلغاء تصريح التداول الحقيقي.",
                details_en="Switched immediately to safe PAPER trading mode and revoked live trading authorization.",
                conn=conn,
            )
        return get_system_status()

    # التحقق الصارم لتفعيل التداول الحقيقي (LIVE)
    current_status = get_system_status()

    # أ) التحقق من عدم تفعيل مفتاح الإيقاف الطارئ
    if current_status.killSwitchActive:
        append_audit_log(
            actor="ADMIN_GATEWAY",
            source="TERMINAL",
            action="LIVE_AUTH_BLOCKED_KILL_SWITCH",
            severity="CRITICAL",
            details_ar="رفض تفعيل التداول الحقيقي (LIVE): مفتاح الإيقاف الطارئ مفعل حالياً.",
            details_en="Blocked LIVE trading activation: Emergency Kill Switch is currently active.",
        )
        raise HTTPException(
            status_code=403,
            detail="لا يمكن تفعيل التداول الحقيقي أثناء تفعيل مفتاح الإيقاف الطارئ (Kill Switch Active).",
        )

    # ب) التحقق من سلامة جميع الفحوصات الخمسة
    checks_dict = current_status.safetyChecks.model_dump()
    if not all(checks_dict.values()):
        append_audit_log(
            actor="ADMIN_GATEWAY",
            source="TERMINAL",
            action="LIVE_AUTH_BLOCKED_SAFETY_CHECKS",
            severity="CRITICAL",
            details_ar="رفض تفعيل التداول الحقيقي: لم تجتز جميع فحوصات الأمان الخمسة بنجاح.",
            details_en="Blocked LIVE trading activation: Not all 5 mandatory safety checks passed.",
        )
        raise HTTPException(
            status_code=403,
            detail="فشل التحقق من سلامة الضوابط الأمنية الخمسة الإلزامية.",
        )

    # ج) الإقرار الصريح بمخاطر رأس المال الحقيقي
    if req.acknowledgeRealCapitalRisk is not True:
        append_audit_log(
            actor="ADMIN_GATEWAY",
            source="TERMINAL",
            action="LIVE_AUTH_BLOCKED_NO_RISK_ACK",
            severity="WARNING",
            details_ar="رفض تفعيل التداول الحقيقي: لم يتم الإقرار الصريح بمخاطر رأس المال الحقيقي.",
            details_en="Blocked LIVE trading activation: Real capital risk acknowledgement missing.",
        )
        raise HTTPException(
            status_code=403,
            detail="يجب الإقرار الصريح بمخاطر رأس المال الحقيقي (acknowledgeRealCapitalRisk).",
        )

    # د) مطابقة عبارة التأكيد الحرفية
    if req.confirmationPhrase.strip() != LIVE_CONFIRMATION_PHRASE:
        append_audit_log(
            actor="ADMIN_GATEWAY",
            source="TERMINAL",
            action="LIVE_AUTH_BLOCKED_PHRASE_MISMATCH",
            severity="WARNING",
            details_ar="رفض تفعيل التداول الحقيقي: عبارة التأكيد الإدارية غير مطابقة.",
            details_en="Blocked LIVE trading activation: Confirmation phrase mismatch.",
        )
        raise HTTPException(
            status_code=403,
            detail="عبارة التأكيد الإدارية غير صحيحة — Invalid confirmation phrase.",
        )

    # هـ) مطابقة الرمز السري للمسؤول
    expected_pin = get_expected_admin_pin()
    if not req.adminPin or req.adminPin.strip() != expected_pin:
        append_audit_log(
            actor="ADMIN_GATEWAY",
            source="TERMINAL",
            action="LIVE_AUTH_BLOCKED_INVALID_PIN",
            severity="CRITICAL",
            details_ar="محاولة غير مصرح بها لتفعيل التداول الحقيقي برمز مسؤول (PIN) خاطئ.",
            details_en="Unauthorized attempt to activate LIVE trading with an invalid Admin PIN.",
        )
        raise HTTPException(
            status_code=403,
            detail="رمز التصريح الإداري (Admin PIN) غير صحيح.",
        )

    with db_session() as conn:
        conn.execute(
            """
            UPDATE system_state
            SET trading_mode = 'LIVE', live_authorized = 1, updated_at = ?
            WHERE id = 1
            """,
            (utc_now_iso(),),
        )
        append_audit_log(
            actor="DR_MAJOOOOOOD_ADMIN",
            source="TERMINAL",
            action="LIVE_TRADING_AUTHORIZED",
            severity="WARNING",
            details_ar="تم التصريح الرسمي بتفعيل وضع التداول الحقيقي (LIVE) بعد استيفاء كافة الضوابط الخمسة ورمز المسؤول.",
            details_en="LIVE trading mode formally authorized after passing all 5 safety checks, phrase, and Admin PIN.",
            conn=conn,
        )

    return get_system_status()


def set_kill_switch(req: KillSwitchRequest) -> SystemStatus:
    """
    تفعيل أو إلغاء مفتاح الإيقاف الطارئ (Emergency Kill Switch).
    عند التفعيل: يعيد النظام فوراً إلى وضع PAPER، يلغي التصريح الحقيقي، ويلغي المقترحات المعلقة.
    """
    reason_clean = req.reason.strip() or (
        "تجميد احترازي طارئ بأمر المسؤول" if req.active else "إلغاء التجميد الطارئ والبقاء في الوضع الورقي"
    )
    now = utc_now_iso()

    with db_session() as conn:
        if req.active:
            conn.execute(
                """
                UPDATE system_state
                SET trading_mode = 'PAPER',
                    live_authorized = 0,
                    kill_switch_active = 1,
                    updated_at = ?
                WHERE id = 1
                """,
                (now,),
            )
            conn.execute(
                """
                UPDATE trade_proposals
                SET status = 'CANCELLED_BY_KILL_SWITCH'
                WHERE status = 'APPROVED_FOR_AUTH'
                """
            )
            append_audit_log(
                actor="EMERGENCY_KILL_SWITCH",
                source="TERMINAL",
                action="KILL_SWITCH_ACTIVATED",
                severity="CRITICAL",
                details_ar=f"تم تفعيل مفتاح الإيقاف الطارئ وإرجاع النظام فوراً إلى PAPER وإلغاء المقترحات المعلقة. السبب: {reason_clean}",
                details_en=f"Emergency Kill Switch ACTIVATED: Forced PAPER mode, revoked live auth, cancelled pending proposals. Reason: {reason_clean}",
                conn=conn,
            )
        else:
            conn.execute(
                """
                UPDATE system_state
                SET trading_mode = 'PAPER',
                    live_authorized = 0,
                    kill_switch_active = 0,
                    updated_at = ?
                WHERE id = 1
                """,
                (now,),
            )
            append_audit_log(
                actor="EMERGENCY_KILL_SWITCH",
                source="TERMINAL",
                action="KILL_SWITCH_DEACTIVATED",
                severity="WARNING",
                details_ar=f"تم إلغاء مفتاح الإيقاف الطارئ مع إبقاء النظام في وضع التداول الورقي الآمن (PAPER). الملاحظة: {reason_clean}",
                details_en=f"Emergency Kill Switch deactivated; system remains safely in PAPER mode. Note: {reason_clean}",
                conn=conn,
            )

    return get_system_status()


def get_portfolio_snapshot() -> PortfolioSnapshot:
    """حساب اللقطة الحية للمحفظة المالية استناداً إلى الأسعار الحية ومراكز SQLite."""
    live_assets = {a.symbol: a for a in market_engine.get_assets()}

    with db_session() as conn:
        state = conn.execute("SELECT * FROM system_state WHERE id = 1").fetchone()
        pos_rows = conn.execute(
            "SELECT * FROM positions WHERE quantity > 0 ORDER BY symbol ASC"
        ).fetchall()
        order_rows = conn.execute(
            "SELECT * FROM orders ORDER BY rowid DESC LIMIT 30"
        ).fetchall()

        cash_balance = round(float(state["cash_balance"]), 2)
        initial_equity = round(float(state["initial_equity"]), 2)
        peak_equity = float(state["peak_equity"])
        max_dd_pct = float(state["max_allowed_drawdown_pct"])
        trading_mode: TradingMode = "LIVE" if state["trading_mode"] == "LIVE" else "PAPER"

        raw_positions: list[dict] = []
        positions_value = 0.0
        var_95_usd = 0.0

        for r in pos_rows:
            sym = r["symbol"]
            qty = float(r["quantity"])
            avg_entry = float(r["avg_entry_price"])
            asset = live_assets.get(sym)
            curr_price = asset.price if asset else avg_entry
            vol_pct = asset.volatilityPct if asset else 2.5

            mkt_val = qty * curr_price
            cost_basis = qty * avg_entry
            unrealized_usd = mkt_val - cost_basis
            unrealized_pct = (unrealized_usd / cost_basis * 100.0) if cost_basis > 0 else 0.0

            positions_value += mkt_val
            # حساب القيمة المعرضة للمخاطر اليومية عند مستوى ثقة 95% (معامل 1.645)
            var_95_usd += mkt_val * (vol_pct / 100.0) * 1.645

            raw_positions.append(
                {
                    "symbol": sym,
                    "nameAr": r["name_ar"],
                    "nameEn": r["name_en"],
                    "quantity": round(qty, 6),
                    "avgEntryPrice": round(avg_entry, 2),
                    "currentPrice": round(curr_price, 2),
                    "marketValueUsd": round(mkt_val, 2),
                    "unrealizedPnlUsd": round(unrealized_usd, 2),
                    "unrealizedPnlPct": round(unrealized_pct, 2),
                }
            )

        total_equity = round(cash_balance + positions_value, 2)
        if total_equity > peak_equity:
            peak_equity = total_equity
            conn.execute(
                "UPDATE system_state SET peak_equity = ? WHERE id = 1",
                (peak_equity,),
            )

    positions_items: list[PositionItem] = []
    for p in raw_positions:
        weight_pct = (
            round((p["marketValueUsd"] / total_equity) * 100.0, 2)
            if total_equity > 0
            else 0.0
        )
        positions_items.append(PositionItem(**p, weightPct=weight_pct))

    daily_pnl = round(total_equity - initial_equity, 2)
    daily_pnl_pct = round((daily_pnl / initial_equity) * 100.0, 2) if initial_equity > 0 else 0.0
    reference_peak = max(initial_equity, peak_equity)
    current_drawdown_pct = (
        round(max(0.0, ((reference_peak - total_equity) / reference_peak) * 100.0), 2)
        if reference_peak > 0
        else 0.0
    )
    trilunair_progress_pct = round((total_equity / TRILUNAIR_TARGET_USD) * 100.0, 6)

    recent_orders = [
        OrderRecord(
            orderId=o["order_id"],
            proposalId=o["proposal_id"],
            symbol=o["symbol"],
            side=o["side"],
            orderType=o["order_type"],
            quantity=float(o["quantity"]),
            executedPrice=float(o["executed_price"]),
            notionalUsd=float(o["notional_usd"]),
            totalFeeUsd=float(o["total_fee_usd"]),
            tradingMode=o["trading_mode"],
            source=o["source"],
            status=o["status"],
            createdAt=o["created_at"],
        )
        for o in order_rows
    ]

    return PortfolioSnapshot(
        tradingMode=trading_mode,
        cashBalance=cash_balance,
        positionsValue=round(positions_value, 2),
        totalEquity=total_equity,
        initialEquity=initial_equity,
        dailyPnl=daily_pnl,
        dailyPnlPct=daily_pnl_pct,
        trilunairTargetUsd=TRILUNAIR_TARGET_USD,
        trilunairProgressPct=trilunair_progress_pct,
        currentDrawdownPct=current_drawdown_pct,
        maxAllowedDrawdownPct=round(max_dd_pct, 2),
        var95Usd=round(var_95_usd, 2),
        positions=positions_items,
        recentOrders=recent_orders,
    )


class CommandValidator:
    """
    المدقق الموحد للأوامر المالية (Unified Command Validator).
    يطبق نفس معايير التحقق الصارمة على الأوامر الصوتية (VOICE) والنصية (TEXT) واليدوية (TERMINAL).
    """

    @staticmethod
    def validate_and_normalize(
        proposal: TradeProposalInput,
    ) -> tuple[TradeProposalInput, MarketAsset]:
        """التحقق من صحة الرمز والكمية ونوع الأمر والسعر المحدد وإرجاع الأصل المطابق."""
        canonical_symbol = market_engine.resolve_symbol(proposal.symbol)
        if not canonical_symbol:
            raise HTTPException(
                status_code=400,
                detail=f"رمز الأصل غير معروف أو غير مدعوم: {proposal.symbol}",
            )

        asset = market_engine.get_asset(canonical_symbol)
        if asset is None:
            raise HTTPException(
                status_code=400,
                detail=f"تعذر استرجاع بيانات السوق للأصل: {canonical_symbol}",
            )

        if not math.isfinite(proposal.quantity) or proposal.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="يجب أن تكون كمية الأمر رقماً موجباً أكبر من الصفر.",
            )

        if proposal.orderType == "LIMIT":
            if (
                proposal.limitPrice is None
                or not math.isfinite(proposal.limitPrice)
                or proposal.limitPrice <= 0
            ):
                raise HTTPException(
                    status_code=400,
                    detail="يتطلب الأمر المحدد (LIMIT) تحديد سعر صالح أكبر من الصفر (limitPrice).",
                )

        normalized = proposal.model_copy(
            update={
                "symbol": canonical_symbol,
                "quantity": round(float(proposal.quantity), 6),
                "rationale": (proposal.rationale or "").strip()
                or f"أمر مهيكل عبر قناة {proposal.source}",
            }
        )
        return normalized, asset


class DeterministicRiskEngine:
    """
    محرك المخاطر الحتمي (Deterministic Risk Engine).
    يجري الحسابات التقديرية للتكاليف والفحوصات الخمسة الإلزامية بشكل حتمي ومطابق لجميع القنوات.
    """

    @staticmethod
    def calculate_costs(
        proposal: TradeProposalInput, asset: MarketAsset, reference_price: float
    ) -> EstimatedTradingCosts:
        """حساب القيمة الاسمية وتكلفة السبريد والعمولة والانزلاق السعري ونقاط الأساس."""
        notional_usd = round(proposal.quantity * reference_price, 2)
        spread_factor = 0.50 if proposal.orderType == "MARKET" else 0.20
        spread_cost = round(
            notional_usd * (asset.spreadBps / 10000.0) * spread_factor, 2
        )
        commission_usd = round(notional_usd * (COMMISSION_BPS / 10000.0), 2)

        size_factor = min(2.5, max(0.25, notional_usd / 100_000.0))
        if proposal.orderType == "MARKET":
            slippage_bps = asset.volatilityPct * 0.85 * size_factor
        else:
            slippage_bps = asset.volatilityPct * 0.15

        slippage_cost = round(notional_usd * (slippage_bps / 10000.0), 2)
        total_cost = round(spread_cost + commission_usd + slippage_cost, 2)
        cost_bps = (
            round((total_cost / notional_usd) * 10000.0, 2) if notional_usd > 0 else 0.0
        )

        return EstimatedTradingCosts(
            notionalUsd=notional_usd,
            spreadCostUsd=spread_cost,
            commissionUsd=commission_usd,
            slippageCostUsd=slippage_cost,
            totalEstimatedCostUsd=total_cost,
            costBps=cost_bps,
        )

    @classmethod
    def evaluate(
        cls,
        proposal: TradeProposalInput,
        asset: MarketAsset,
        portfolio: PortfolioSnapshot | None = None,
        kill_switch_active: bool | None = None,
    ) -> tuple[ float, EstimatedTradingCosts, RiskAssessment ]:
        """
        تنفيذ الفحوصات الخمسة الإلزامية لمحرك المخاطر الحتمي:
        1. KILL_SWITCH
        2. MAX_ORDER_NOTIONAL (<= 25% من إجمالي حقوق الملكية)
        3. MAX_CONCENTRATION (<= 35% للشراء، وتوفر الكمية المملوكة للبيع دون بيع مكشوف)
        4. DAILY_DRAWDOWN_LIMIT (< 5.0%)
        5. SUFFICIENT_BUYING_POWER (تغطية النقد للقيمة الاسمية + التكاليف عند الشراء)
        """
        snap = portfolio or get_portfolio_snapshot()
        if kill_switch_active is None:
            status = get_system_status()
            ks_active = status.killSwitchActive
        else:
            ks_active = kill_switch_active

        ref_price = (
            float(proposal.limitPrice)
            if proposal.orderType == "LIMIT" and proposal.limitPrice
            else asset.price
        )
        costs = cls.calculate_costs(proposal, asset, ref_price)

        total_equity = max(snap.totalEquity, 1.0)
        max_notional_usd = round(total_equity * MAX_SINGLE_ORDER_EQUITY_RATIO, 2)
        order_notional_pct = round((costs.notionalUsd / total_equity) * 100.0, 2)

        # البحث عن المركز المفتوح الحالي للأصل
        existing_pos = next(
            (p for p in snap.positions if p.symbol == asset.symbol), None
        )
        held_qty = existing_pos.quantity if existing_pos else 0.0
        held_val = existing_pos.marketValueUsd if existing_pos else 0.0

        checks: list[RiskCheckItem] = []

        # 1. فحص مفتاح الإيقاف الطارئ (KILL_SWITCH)
        ks_passed = not ks_active
        checks.append(
            RiskCheckItem(
                code="KILL_SWITCH",
                passed=ks_passed,
                messageAr=(
                    "مفتاح الإيقاف الطارئ غير مفعل؛ خط الأنابيب مفتوح."
                    if ks_passed
                    else "مرفوض: مفتاح الإيقاف الطارئ (Kill Switch) مفعل وجميع الصفقات مجمدة."
                ),
                messageEn=(
                    "Emergency Kill Switch is inactive; execution pipeline clear."
                    if ks_passed
                    else "Rejected: Emergency Kill Switch is active; all trading frozen."
                ),
            )
        )

        # 2. فحص الحد الأقصى لحجم الأمر المفرد (MAX_ORDER_NOTIONAL <= 25%)
        notional_passed = costs.notionalUsd <= max_notional_usd
        checks.append(
            RiskCheckItem(
                code="MAX_ORDER_NOTIONAL",
                passed=notional_passed,
                messageAr=(
                    f"حجم الصفقة (${costs.notionalUsd:,.2f} / {order_notional_pct}%) ضمن السقف المسموح (25% = ${max_notional_usd:,.2f})."
                    if notional_passed
                    else f"مرفوض: حجم الصفقة (${costs.notionalUsd:,.2f} / {order_notional_pct}%) يتجاوز سقف 25% من حقوق الملكية (${max_notional_usd:,.2f})."
                ),
                messageEn=(
                    f"Order notional (${costs.notionalUsd:,.2f} / {order_notional_pct}%) is within the 25% equity cap (${max_notional_usd:,.2f})."
                    if notional_passed
                    else f"Rejected: Order notional (${costs.notionalUsd:,.2f} / {order_notional_pct}%) exceeds 25% max single-order cap (${max_notional_usd:,.2f})."
                ),
            )
        )

        # 3. فحص التركز الأقصى أو ملكية الأصل عند البيع (MAX_CONCENTRATION)
        if proposal.side == "BUY":
            post_val = held_val + costs.notionalUsd
            post_conc_pct = round((post_val / total_equity) * 100.0, 2)
            conc_passed = post_conc_pct <= MAX_ASSET_CONCENTRATION_PCT
            conc_msg_ar = (
                f"التركز بعد الشراء ({post_conc_pct}%) ضمن الحد الأقصى المسموح ({MAX_ASSET_CONCENTRATION_PCT}%)."
                if conc_passed
                else f"مرفوض: التركز بعد الشراء ({post_conc_pct}%) يتجاوز سقف التركز المسموح للأصل الواحد ({MAX_ASSET_CONCENTRATION_PCT}%)."
            )
            conc_msg_en = (
                f"Post-trade concentration ({post_conc_pct}%) is within the {MAX_ASSET_CONCENTRATION_PCT}% asset limit."
                if conc_passed
                else f"Rejected: Post-trade concentration ({post_conc_pct}%) exceeds the {MAX_ASSET_CONCENTRATION_PCT}% maximum concentration limit."
            )
        else:
            # منع البيع المكشوف (No Naked Shorting)
            conc_passed = (held_qty + 1e-9) >= proposal.quantity
            rem_qty = max(0.0, held_qty - proposal.quantity)
            post_conc_pct = round(((rem_qty * asset.price) / total_equity) * 100.0, 2)
            conc_msg_ar = (
                f"الكمية المملوكة ({held_qty:g} {asset.symbol}) كافية لتغطية أمر البيع ({proposal.quantity:g})."
                if conc_passed
                else f"مرفوض: البيع المكشوف محظور؛ الكمية المطلوبة للبيع ({proposal.quantity:g}) تتجاوز الرصيد المملوك ({held_qty:g} {asset.symbol})."
            )
            conc_msg_en = (
                f"Held position ({held_qty:g} {asset.symbol}) covers the sell quantity ({proposal.quantity:g})."
                if conc_passed
                else f"Rejected: Naked shorting prohibited; sell quantity ({proposal.quantity:g}) exceeds held balance ({held_qty:g} {asset.symbol})."
            )

        checks.append(
            RiskCheckItem(
                code="MAX_CONCENTRATION",
                passed=conc_passed,
                messageAr=conc_msg_ar,
                messageEn=conc_msg_en,
            )
        )

        # 4. فحص حد التراجع اليومي للمحفظة (DAILY_DRAWDOWN_LIMIT < 5.0%)
        dd_passed = snap.currentDrawdownPct < snap.maxAllowedDrawdownPct
        checks.append(
            RiskCheckItem(
                code="DAILY_DRAWDOWN_LIMIT",
                passed=dd_passed,
                messageAr=(
                    f"التراجع الحالي للمحفظة ({snap.currentDrawdownPct}%) أقل من الحد الأقصى المسموح ({snap.maxAllowedDrawdownPct}%)."
                    if dd_passed
                    else f"مرفوض: التراجع الحالي ({snap.currentDrawdownPct}%) بلغ أو تجاوز حد الإيقاف اليومي ({snap.maxAllowedDrawdownPct}%)."
                ),
                messageEn=(
                    f"Current portfolio drawdown ({snap.currentDrawdownPct}%) is below the {snap.maxAllowedDrawdownPct}% limit."
                    if dd_passed
                    else f"Rejected: Portfolio drawdown ({snap.currentDrawdownPct}%) breached the {snap.maxAllowedDrawdownPct}% daily limit."
                ),
            )
        )

        # 5. فحص القوة الشرائية الكافية (SUFFICIENT_BUYING_POWER)
        required_cash = round(costs.notionalUsd + costs.totalEstimatedCostUsd, 2)
        if proposal.side == "BUY":
            cash_passed = snap.cashBalance >= required_cash
            cash_msg_ar = (
                f"السيولة النقدية المتاحة (${snap.cashBalance:,.2f}) تغطي التكلفة الإجمالية (${required_cash:,.2f})."
                if cash_passed
                else f"مرفوض: السيولة النقدية المتاحة (${snap.cashBalance:,.2f}) غير كافية لتغطية الصفقة والتكاليف (${required_cash:,.2f})."
            )
            cash_msg_en = (
                f"Available cash (${snap.cashBalance:,.2f}) covers notional plus estimated fees (${required_cash:,.2f})."
                if cash_passed
                else f"Rejected: Insufficient cash balance (${snap.cashBalance:,.2f}) for total required (${required_cash:,.2f})."
            )
        else:
            cash_passed = True
            cash_msg_ar = f"أمر بيع يعزز السيولة النقدية المتاحة (${snap.cashBalance:,.2f})."
            cash_msg_en = f"Sell order increases available cash liquidity (${snap.cashBalance:,.2f})."

        checks.append(
            RiskCheckItem(
                code="SUFFICIENT_BUYING_POWER",
                passed=cash_passed,
                messageAr=cash_msg_ar,
                messageEn=cash_msg_en,
            )
        )

        violations = [f"{c.code}: {c.messageEn}" for c in checks if not c.passed]
        all_passed = len(violations) == 0

        var_impact_usd = round(
            costs.notionalUsd * (asset.volatilityPct / 100.0) * 1.645, 2
        )

        # حساب درجة ومستوى المخاطر (0 - 100)
        base_score = (
            (order_notional_pct / 25.0) * 35.0
            + (post_conc_pct / 35.0) * 30.0
            + min(25.0, asset.volatilityPct * 4.5)
        )
        if not all_passed:
            risk_score = min(100, max(82, int(round(base_score + 40))))
            risk_level = (
                "CRITICAL"
                if (not ks_passed or not dd_passed or len(violations) >= 2)
                else "HIGH"
            )
        else:
            risk_score = max(8, min(78, int(round(base_score))))
            if risk_score < 32:
                risk_level = "LOW"
            elif risk_score < 60:
                risk_level = "MODERATE"
            else:
                risk_level = "HIGH"

        assessment = RiskAssessment(
            passed=all_passed,
            riskScore=risk_score,
            riskLevel=risk_level,
            postTradeConcentrationPct=post_conc_pct,
            varImpactUsd=var_impact_usd,
            checks=checks,
            violations=violations,
        )
        return round(ref_price, 2), costs, assessment


def propose_order(proposal_input: TradeProposalInput) -> TradeProposalEvaluation:
    """
    إنشاء وتقييم مقترح صفقة مهيكل عبر المدقق ومحرك المخاطر الحتمي وحفظه في SQLite.
    تطبق هذه الدالة نفس السياسة تماماً على الأوامر الصوتية (VOICE) والنصية (TEXT) واليدوية (TERMINAL)،
    ولا تنفذ الصفقة تلقائياً تحت أي ظرف.
    """
    normalized_proposal, asset = CommandValidator.validate_and_normalize(proposal_input)
    sys_status = get_system_status()
    portfolio = get_portfolio_snapshot()

    ref_price, costs, risk_assessment = DeterministicRiskEngine.evaluate(
        proposal=normalized_proposal,
        asset=asset,
        portfolio=portfolio,
        kill_switch_active=sys_status.killSwitchActive,
    )

    proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
    created_at = utc_now_iso()
    eval_status = "APPROVED_FOR_AUTH" if risk_assessment.passed else "REJECTED_BY_RISK"
    requires_live_pin = sys_status.tradingMode == "LIVE"

    proposal_details = TradeProposalDetails(
        **normalized_proposal.model_dump(),
        referencePrice=ref_price,
        createdAt=created_at,
    )

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO trade_proposals (
                proposal_id, status, symbol, side, order_type, quantity,
                limit_price, stop_loss, take_profit, source, rationale,
                reference_price, estimated_costs_json, risk_assessment_json,
                trading_mode, requires_live_pin, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal_id,
                eval_status,
                normalized_proposal.symbol,
                normalized_proposal.side,
                normalized_proposal.orderType,
                normalized_proposal.quantity,
                normalized_proposal.limitPrice,
                normalized_proposal.stopLoss,
                normalized_proposal.takeProfit,
                normalized_proposal.source,
                normalized_proposal.rationale,
                ref_price,
                json.dumps(costs.model_dump(), ensure_ascii=False),
                json.dumps(risk_assessment.model_dump(), ensure_ascii=False),
                sys_status.tradingMode,
                1 if requires_live_pin else 0,
                created_at,
            ),
        )

        append_audit_log(
            actor="RISK_GATEWAY",
            source=normalized_proposal.source,
            action=f"PROPOSAL_{eval_status}",
            severity="INFO" if risk_assessment.passed else "WARNING",
            details_ar=(
                f"تم تقييم مقترح {normalized_proposal.side} بكمية {normalized_proposal.quantity:g} {normalized_proposal.symbol} "
                f"عبر قناة {normalized_proposal.source} بقيمة ${costs.notionalUsd:,.2f} -> الحالة: {eval_status}."
            ),
            details_en=(
                f"Evaluated {normalized_proposal.side} proposal for {normalized_proposal.quantity:g} {normalized_proposal.symbol} "
                f"via {normalized_proposal.source} (${costs.notionalUsd:,.2f}) -> Status: {eval_status}."
            ),
            conn=conn,
        )

    return TradeProposalEvaluation(
        proposalId=proposal_id,
        status=eval_status,
        proposal=proposal_details,
        estimatedCosts=costs,
        riskAssessment=risk_assessment,
        tradingMode=sys_status.tradingMode,
        requiresLivePin=requires_live_pin,
    )


def execute_order(req: OrderExecuteRequest) -> OrderExecuteResponse:
    """
    التنفيذ المحكوم لمقترح صفقة بعد:
    1. التأكيد الصريح من المستخدم (confirmedByUser == True).
    2. التحقق من أن المقترح معتمد للتصريح ولم يُرفض أو يُنفذ مسبقاً.
    3. التحقق من عدم تفعيل مفتاح الإيقاف الطارئ.
    4. التحقق من رمز المسؤول (Admin PIN) مجدداً إذا كان النظام في وضع LIVE.
    5. إعادة إجراء الفحوصات الخمسة لمحرك المخاطر لحظة التنفيذ الفعلي.
    """
    if req.confirmedByUser is not True:
        append_audit_log(
            actor="EXECUTION_ENGINE",
            source=req.source,
            action="EXECUTION_BLOCKED_UNCONFIRMED",
            severity="WARNING",
            details_ar=f"رفض تنفيذ المقترح {req.proposalId}: غياب التأكيد الصريح من المستخدم.",
            details_en=f"Blocked execution of {req.proposalId}: Explicit user confirmation required.",
        )
        raise HTTPException(
            status_code=400,
            detail="لا يمكن تنفيذ أي صفقة دون تأكيد صريح من المستخدم (confirmedByUser=true).",
        )

    sys_status = get_system_status()
    if sys_status.killSwitchActive:
        append_audit_log(
            actor="EXECUTION_ENGINE",
            source=req.source,
            action="EXECUTION_BLOCKED_KILL_SWITCH",
            severity="CRITICAL",
            details_ar=f"رفض تنفيذ المقترح {req.proposalId}: مفتاح الإيقاف الطارئ مفعل.",
            details_en=f"Blocked execution of {req.proposalId}: Emergency Kill Switch is active.",
        )
        raise HTTPException(
            status_code=403,
            detail="التنفيذ مجمد بالكامل بسبب تفعيل مفتاح الإيقاف الطارئ (Kill Switch Active).",
        )

    with db_session() as conn:
        prop_row = conn.execute(
            "SELECT * FROM trade_proposals WHERE proposal_id = ?",
            (req.proposalId,),
        ).fetchone()

    if prop_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"مقترح الصفقة غير موجود: {req.proposalId}",
        )

    if prop_row["status"] != "APPROVED_FOR_AUTH":
        append_audit_log(
            actor="EXECUTION_ENGINE",
            source=req.source,
            action="EXECUTION_BLOCKED_INVALID_STATUS",
            severity="WARNING",
            details_ar=f"رفض تنفيذ المقترح {req.proposalId} لأن حالته الحالية هي {prop_row['status']}.",
            details_en=f"Blocked execution of proposal {req.proposalId} with non-executable status {prop_row['status']}.",
        )
        raise HTTPException(
            status_code=403,
            detail=f"لا يمكن تنفيذ مقترح صفقة بحالة {prop_row['status']}.",
        )

    # التحقق الإضافي من رمز المسؤول إذا كان النظام في وضع التداول الحقيقي LIVE
    if sys_status.tradingMode == "LIVE":
        expected_pin = get_expected_admin_pin()
        if not sys_status.liveAuthorized or not req.adminPin or req.adminPin.strip() != expected_pin:
            append_audit_log(
                actor="EXECUTION_ENGINE",
                source=req.source,
                action="LIVE_EXECUTION_BLOCKED_PIN",
                severity="CRITICAL",
                details_ar=f"رفض تنفيذ صفقة حقيقية ({req.proposalId}) لعدم صحة رمز المسؤول (Admin PIN).",
                details_en=f"Blocked LIVE order execution ({req.proposalId}): Missing or invalid Admin PIN.",
            )
            raise HTTPException(
                status_code=403,
                detail="يتطلب التنفيذ في وضع التداول الحقيقي (LIVE) إدخال رمز المسؤول الصحيح (Admin PIN).",
            )

    # إعادة بناء المقترح وإعادة فحص المخاطر الحتمية على الأسعار والسيولة اللحظية
    recheck_input = TradeProposalInput(
        symbol=prop_row["symbol"],
        side=prop_row["side"],
        orderType=prop_row["order_type"],
        quantity=float(prop_row["quantity"]),
        limitPrice=float(prop_row["limit_price"]) if prop_row["limit_price"] is not None else None,
        stopLoss=float(prop_row["stop_loss"]) if prop_row["stop_loss"] is not None else None,
        takeProfit=float(prop_row["take_profit"]) if prop_row["take_profit"] is not None else None,
        source=prop_row["source"],
        rationale=prop_row["rationale"],
    )
    _, asset = CommandValidator.validate_and_normalize(recheck_input)
    exec_price, costs, live_risk = DeterministicRiskEngine.evaluate(
        proposal=recheck_input,
        asset=asset,
        kill_switch_active=sys_status.killSwitchActive,
    )

    if not live_risk.passed:
        with db_session() as conn:
            conn.execute(
                "UPDATE trade_proposals SET status = 'REJECTED_BY_RISK' WHERE proposal_id = ?",
                (req.proposalId,),
            )
            append_audit_log(
                actor="EXECUTION_ENGINE",
                source=req.source,
                action="EXECUTION_REJECTED_AT_RECHECK",
                severity="WARNING",
                details_ar=f"رفض التنفيذ اللحظي للمقترح {req.proposalId} بعد إعادة فحص المخاطر: {', '.join(live_risk.violations)}",
                details_en=f"Execution re-check rejected proposal {req.proposalId}: {', '.join(live_risk.violations)}",
                conn=conn,
            )
        raise HTTPException(
            status_code=403,
            detail=f"فشل إعادة فحص المخاطر عند التنفيذ: {'; '.join(live_risk.violations)}",
        )

    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    effective_source = prop_row["source"] or req.source

    with db_session() as conn:
        state = conn.execute("SELECT * FROM system_state WHERE id = 1").fetchone()
        cash_balance = float(state["cash_balance"])
        pos_row = conn.execute(
            "SELECT * FROM positions WHERE symbol = ?", (asset.symbol,)
        ).fetchone()

        if recheck_input.side == "BUY":
            new_cash = round(
                cash_balance - costs.notionalUsd - costs.totalEstimatedCostUsd, 2
            )
            if pos_row is None:
                conn.execute(
                    """
                    INSERT INTO positions (
                        symbol, name_ar, name_en, quantity, avg_entry_price, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        asset.symbol,
                        asset.nameAr,
                        asset.nameEn,
                        recheck_input.quantity,
                        exec_price,
                        now,
                    ),
                )
            else:
                old_qty = float(pos_row["quantity"])
                old_avg = float(pos_row["avg_entry_price"])
                new_qty = round(old_qty + recheck_input.quantity, 6)
                new_avg = round(
                    ((old_qty * old_avg) + (recheck_input.quantity * exec_price)) / new_qty,
                    4,
                )
                conn.execute(
                    """
                    UPDATE positions
                    SET quantity = ?, avg_entry_price = ?, updated_at = ?
                    WHERE symbol = ?
                    """,
                    (new_qty, new_avg, now, asset.symbol),
                )
        else:
            new_cash = round(
                cash_balance + costs.notionalUsd - costs.totalEstimatedCostUsd, 2
            )
            old_qty = float(pos_row["quantity"]) if pos_row else 0.0
            rem_qty = round(old_qty - recheck_input.quantity, 6)
            if rem_qty <= 1e-8:
                conn.execute("DELETE FROM positions WHERE symbol = ?", (asset.symbol,))
            else:
                conn.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? WHERE symbol = ?",
                    (rem_qty, now, asset.symbol),
                )

        conn.execute(
            "UPDATE system_state SET cash_balance = ?, updated_at = ? WHERE id = 1",
            (new_cash, now),
        )
        conn.execute(
            "UPDATE trade_proposals SET status = 'EXECUTED' WHERE proposal_id = ?",
            (req.proposalId,),
        )
        conn.execute(
            """
            INSERT INTO orders (
                order_id, proposal_id, symbol, side, order_type, quantity,
                executed_price, notional_usd, total_fee_usd, trading_mode,
                source, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'FILLED', ?)
            """,
            (
                order_id,
                req.proposalId,
                asset.symbol,
                recheck_input.side,
                recheck_input.orderType,
                recheck_input.quantity,
                exec_price,
                costs.notionalUsd,
                costs.totalEstimatedCostUsd,
                sys_status.tradingMode,
                effective_source,
                now,
            ),
        )

        append_audit_log(
            actor="EXECUTION_ENGINE",
            source=effective_source,
            action=f"ORDER_FILLED_{sys_status.tradingMode}",
            severity="INFO" if sys_status.tradingMode == "PAPER" else "WARNING",
            details_ar=(
                f"تم تنفيذ أمر {recheck_input.side} بكمية {recheck_input.quantity:g} {asset.symbol} "
                f"بسعر ${exec_price:,.2f} في وضع {sys_status.tradingMode} (المصدر الأصلي: {effective_source})."
            ),
            details_en=(
                f"Executed {recheck_input.side} {recheck_input.quantity:g} {asset.symbol} "
                f"@ ${exec_price:,.2f} in {sys_status.tradingMode} mode (origin source: {effective_source})."
            ),
            conn=conn,
        )

    order_record = OrderRecord(
        orderId=order_id,
        proposalId=req.proposalId,
        symbol=asset.symbol,
        side=recheck_input.side,
        orderType=recheck_input.orderType,
        quantity=recheck_input.quantity,
        executedPrice=exec_price,
        notionalUsd=costs.notionalUsd,
        totalFeeUsd=costs.totalEstimatedCostUsd,
        tradingMode=sys_status.tradingMode,
        source=effective_source,
        status="FILLED",
        createdAt=now,
    )

    return OrderExecuteResponse(
        order=order_record,
        portfolio=get_portfolio_snapshot(),
    )
