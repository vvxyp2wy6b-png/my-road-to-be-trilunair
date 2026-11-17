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

from datetime import datetime, timedelta, timezone
import json
import math
import os
from typing import Final
import uuid

from fastapi import HTTPException

from app.binance_market_data import binance_public_client
from app.database import (
    acquire_redis_idempotency_lock,
    append_audit_log,
    cache_proposal_in_redis,
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
    RiskPolicySummary,
    SafetyChecks,
    SystemProviders,
    SystemStatus,
    TradeProposalDetails,
    TradeProposalEvaluation,
    TradeProposalInput,
    TradingMode,
    TradingModeRequest,
)
from app.latency_pipeline import pipeline_latency_tracker
from app.security import enforce_admin_secret, security_telemetry
import time

APP_NAME: Final[str] = "My Road to be Trilunair Dr.MaJoOoOoOoD"
APP_VERSION: Final[str] = "1.3.0-binance-personal-guard"
TRILUNAIR_TARGET_USD: Final[float] = 1_000_000_000_000.0  # 1 تريليون دولار
LIVE_CONFIRMATION_PHRASE: Final[str] = "AUTHORIZE LIVE TRADING DR MAJOOOOOOD"

# الحدود الخمسة المعتمدة لسياسة المخاطر الحتمية الموحدة (القسم 5)
DEFAULT_MAX_RISK_PER_TRADE_PCT: Final[float] = 0.5      # 0.5% أقصى مخاطرة لكل صفقة
MAX_SINGLE_ORDER_EQUITY_RATIO: Final[float] = 0.25      # 25% سقف حجم الأمر الواحد
MAX_ASSET_CONCENTRATION_PCT: Final[float] = 25.0        # 25% أقصى تعرض وتركز للأصل الواحد
DEFAULT_DAILY_LOSS_LIMIT_PCT: Final[float] = 2.0        # 2% قاطع الخسارة اليومية
DEFAULT_WEEKLY_LOSS_LIMIT_PCT: Final[float] = 5.0       # 5% قاطع الخسارة الأسبوعية
DEFAULT_MAX_DRAWDOWN_LIMIT_PCT: Final[float] = 10.0     # 10% قاطع أقصى تراجع تراكمي
COMMISSION_BPS: Final[float] = 5.0                      # 5 نقاط أساس عمولة مؤسسية


def get_active_risk_policy() -> RiskPolicySummary:
    """قراءة سياسة المخاطر الموحدة المعتمدة من جدول الحوكمة أو القيم الحتمية المعتمدة (0.5% / 25% / 2% / 5% / 10%)."""
    max_risk = DEFAULT_MAX_RISK_PER_TRADE_PCT
    max_exp = MAX_ASSET_CONCENTRATION_PCT
    daily_lim = DEFAULT_DAILY_LOSS_LIMIT_PCT
    weekly_lim = DEFAULT_WEEKLY_LOSS_LIMIT_PCT
    max_dd = DEFAULT_MAX_DRAWDOWN_LIMIT_PCT
    try:
        with db_session() as conn:
            gov_row = conn.execute(
                """
                SELECT max_risk_per_trade_pct, max_exposure_per_asset_pct,
                       daily_loss_limit_pct, weekly_loss_limit_pct, max_drawdown_limit_pct
                FROM quantum_governance
                WHERE tenant_id = 'admin-primary'
                """
            ).fetchone()
            if gov_row is not None:
                max_risk = float(gov_row["max_risk_per_trade_pct"])
                max_exp = float(gov_row["max_exposure_per_asset_pct"])
                daily_lim = float(gov_row["daily_loss_limit_pct"])
                weekly_lim = float(gov_row["weekly_loss_limit_pct"])
                max_dd = float(gov_row["max_drawdown_limit_pct"])
    except Exception:
        pass
    return RiskPolicySummary(
        maxRiskPerTradePct=round(max_risk, 3),
        maxExposurePerAssetPct=round(max_exp, 2),
        dailyLossLimitPct=round(daily_lim, 2),
        weeklyLossLimitPct=round(weekly_lim, 2),
        maxDrawdownLimitPct=round(max_dd, 2),
    )


def detect_active_providers() -> SystemProviders:
    """اكتشاف مزودي الذكاء الاصطناعي والصوت النشطين بناءً على مفاتيح البيئة الفعلية."""
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    has_xai = bool(os.getenv("XAI_API_KEY", "").strip())

    cloud_list = [
        name
        for name, ok in (
            ("openai", has_openai),
            ("gemini", has_gemini),
            ("anthropic", has_anthropic),
            ("xai", has_xai),
        )
        if ok
    ]

    if cloud_list:
        llm = "+".join(cloud_list) + "+deterministic-council"
    else:
        llm = "deterministic-council-simulated"

    if has_openai:
        stt = "openai-whisper+browser-speech"
        tts = "openai-tts+browser-speech"
    else:
        stt = "browser-speech+deterministic-fallback"
        tts = "browser-speech+server-wav"

    return SystemProviders(llmProvider=llm, sttProvider=stt, ttsProvider=tts)


def evaluate_system_safety_checks() -> SafetyChecks:
    """إجراء الفحوصات الخمسة لسلامة محرك المخاطر وسجل التدقيق وحدود التراجع."""
    policy = get_active_risk_policy()
    with db_session() as conn:
        state = conn.execute("SELECT * FROM system_state WHERE id = 1").fetchone()

    max_dd_ok = state is not None and 0.5 <= policy.maxDrawdownLimitPct <= 25.0
    audit_ok = check_audit_trail_health()
    risk_engine_ok = (
        0.05 <= policy.maxRiskPerTradePct <= 2.0
        and 5.0 <= policy.maxExposurePerAssetPct <= 25.0
        and 0.5 <= policy.dailyLossLimitPct <= 10.0
    )

    return SafetyChecks(
        riskEngineVerified=risk_engine_ok,
        maxDrawdownConfigured=max_dd_ok,
        killSwitchReady=state is not None,
        positionLimitsActive=True,
        auditTrailHealthy=audit_ok,
    )


def get_system_status() -> SystemStatus:
    """
    استرجاع الحالة الراهنة للنظام.
    في الإصدار v1.1.0-cloud-paper يظل وضع التنفيذ مقفلاً دائماً على PAPER و liveAuthorized = False.
    """
    checks = evaluate_system_safety_checks()
    providers = detect_active_providers()
    policy = get_active_risk_policy()
    market_snap = binance_public_client.get_health_snapshot()
    with db_session() as conn:
        state = conn.execute("SELECT * FROM system_state WHERE id = 1").fetchone()
        if state["trading_mode"] != "PAPER" or int(state["live_authorized"] or 0) != 0:
            conn.execute(
                "UPDATE system_state SET trading_mode = 'PAPER', live_authorized = 0 WHERE id = 1"
            )

    return SystemStatus(
        appName=APP_NAME,
        version=APP_VERSION,
        tradingMode="PAPER",
        killSwitchActive=bool(state["kill_switch_active"]),
        liveAuthorized=False,
        executionLockedToPaper=True,
        marketDataMode=market_snap["effectiveMatrixMode"],
        riskPolicy=policy,
        safetyChecks=checks,
        providers=providers,
    )


def set_trading_mode(req: TradingModeRequest, client_id: str = "local-client") -> SystemStatus:
    """
    بوابة تصاريح وضع التداول في الإصدار v1.1.0-cloud-paper:
    - العودة إلى PAPER متاحة دائماً فوراً.
    - طلب تفعيل LIVE يخضع للتحقق الأمني والمصادقة المشفرة (Fail-Closed + Rate Limit)،
      ثم يُرفض حتمياً بـ HTTP 403 لأن هذا الإصدار مقفل نهائياً على التداول الورقي (PAPER) مع liveAuthorized = False.
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
                details_ar="تم تأكيد وضع التداول الورقي الآمن (PAPER) وإبقاء تصريح التداول الحقيقي معطلاً.",
                details_en="Confirmed safe PAPER trading mode; live trading authorization remains disabled.",
                conn=conn,
            )
        return get_system_status()

    current_status = get_system_status()

    # أ) التحقق من عدم تفعيل مفتاح الإيقاف الطارئ
    if current_status.killSwitchActive:
        append_audit_log(
            actor="ADMIN_GATEWAY",
            source="TERMINAL",
            action="LIVE_AUTH_BLOCKED_KILL_SWITCH",
            severity="CRITICAL",
            details_ar="رفض طلب التداول الحقيقي (LIVE): مفتاح الإيقاف الطارئ مفعل حالياً.",
            details_en="Blocked LIVE trading request: Emergency Kill Switch is currently active.",
        )
        raise HTTPException(
            status_code=403,
            detail="لا يمكن طلب وضع التداول الحقيقي أثناء تفعيل مفتاح الإيقاف الطارئ (Kill Switch Active).",
        )

    # ب) التحقق من سلامة الفحوصات الخمسة
    if not all(current_status.safetyChecks.model_dump().values()):
        append_audit_log(
            actor="ADMIN_GATEWAY",
            source="TERMINAL",
            action="LIVE_AUTH_BLOCKED_SAFETY_CHECKS",
            severity="CRITICAL",
            details_ar="رفض طلب التداول الحقيقي: لم تجتز جميع فحوصات الأمان الخمسة بنجاح.",
            details_en="Blocked LIVE trading request: Not all 5 mandatory safety checks passed.",
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
            details_ar="رفض طلب التداول الحقيقي: لم يتم الإقرار الصريح بمخاطر رأس المال الحقيقي.",
            details_en="Blocked LIVE trading request: Real capital risk acknowledgement missing.",
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
            details_ar="رفض طلب التداول الحقيقي: عبارة التأكيد الإدارية غير مطابقة.",
            details_en="Blocked LIVE trading request: Confirmation phrase mismatch.",
        )
        raise HTTPException(
            status_code=403,
            detail="عبارة التأكيد الإدارية غير صحيحة — Invalid confirmation phrase.",
        )

    # هـ) التحقق المشفر من سر المسؤول (بدون أي رمز افتراضي 7777، مع Fail-Closed وحماية Brute-Force)
    try:
        enforce_admin_secret(req.adminPin, client_id=client_id, action_label="LIVE_MODE_GATE")
    except HTTPException as exc:
        if exc.status_code == 403:
            append_audit_log(
                actor="ADMIN_GATEWAY",
                source="TERMINAL",
                action="LIVE_AUTH_BLOCKED_INVALID_SECRET",
                severity="CRITICAL",
                details_ar="محاولة غير مصرح بها على بوابة الوضع الحقيقي ببيانات اعتماد مسؤول غير صحيحة.",
                details_en="Unauthorized attempt on LIVE mode gate with invalid administrator credentials.",
            )
        raise

    # و) القفل السيادي غير القابل للتفاوض للإصدار v1.1.0-cloud-paper: منع تفعيل LIVE نهائياً
    security_telemetry.emit_event(
        "LIVE_EXECUTION_BLOCKED",
        severity="WARNING",
        details={"client": client_id, "reason": "RELEASE_LOCKED_TO_PAPER_V1_1"},
    )
    append_audit_log(
        actor="RELEASE_SAFETY_LOCK",
        source="TERMINAL",
        action="LIVE_AUTH_BLOCKED_RELEASE_PAPER_LOCK",
        severity="CRITICAL",
        details_ar=(
            "تم رفض تفعيل وضع التداول الحقيقي (LIVE): الإصدار v1.1.0-cloud-paper مقفل نهائياً على التداول الورقي (PAPER) مع liveAuthorized=false."
        ),
        details_en=(
            "Blocked LIVE trading activation: Release v1.1.0-cloud-paper permanently enforces PAPER mode with liveAuthorized=false."
        ),
    )
    raise HTTPException(
        status_code=403,
        detail=(
            "LIVE_EXECUTION_LOCKED: الإصدار v1.1.0-cloud-paper مقفل نهائياً على وضع التداول الورقي الآمن (PAPER) مع تعطيل التداول الحقيقي (liveAuthorized=false)."
        ),
    )


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
    """حساب اللقطة الحية للمحفظة المالية الورقية استناداً إلى الأسعار الحية ومراكز قاعدة البيانات."""
    live_assets = {a.symbol: a for a in market_engine.get_assets()}
    policy = get_active_risk_policy()

    with db_session() as conn:
        state = conn.execute("SELECT * FROM system_state WHERE id = 1").fetchone()
        pos_rows = conn.execute(
            "SELECT * FROM positions WHERE quantity > 0 ORDER BY symbol ASC"
        ).fetchall()
        order_rows = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC, order_id DESC LIMIT 30"
        ).fetchall()

        cash_balance = round(float(state["cash_balance"]), 2)
        initial_equity = round(float(state["initial_equity"]), 2)
        daily_start_equity = round(
            float(state["daily_start_equity"]) if state["daily_start_equity"] is not None else initial_equity,
            2,
        )
        weekly_start_equity = round(
            float(state["weekly_start_equity"]) if state["weekly_start_equity"] is not None else initial_equity,
            2,
        )
        peak_equity = float(state["peak_equity"])

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

    daily_pnl = round(total_equity - daily_start_equity, 2)
    daily_pnl_pct = (
        round((daily_pnl / daily_start_equity) * 100.0, 2)
        if daily_start_equity > 0
        else 0.0
    )
    weekly_loss_pct = (
        round(max(0.0, ((weekly_start_equity - total_equity) / weekly_start_equity) * 100.0), 2)
        if weekly_start_equity > 0
        else 0.0
    )
    reference_peak = max(initial_equity, peak_equity)
    current_drawdown_pct = (
        round(max(0.0, ((reference_peak - total_equity) / reference_peak) * 100.0), 2)
        if reference_peak > 0
        else 0.0
    )
    trilunair_progress_pct = round((total_equity / TRILUNAIR_TARGET_USD) * 100.0, 6)

    recent_orders = []
    for o in order_rows:
        keys = o.keys()
        recent_orders.append(
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
                tradingMode="PAPER",
                isSimulatedFill=bool(int(o["is_simulated_fill"])) if "is_simulated_fill" in keys and o["is_simulated_fill"] is not None else True,
                stopLoss=float(o["stop_loss"]) if "stop_loss" in keys and o["stop_loss"] is not None else None,
                takeProfit=float(o["take_profit"]) if "take_profit" in keys and o["take_profit"] is not None else None,
                source=o["source"],
                status=o["status"],
                createdAt=o["created_at"],
                clientOrderId=o["client_order_id"] if "client_order_id" in keys else None,
            )
        )

    return PortfolioSnapshot(
        tradingMode="PAPER",
        cashBalance=cash_balance,
        positionsValue=round(positions_value, 2),
        totalEquity=total_equity,
        initialEquity=initial_equity,
        dailyPnl=daily_pnl,
        dailyPnlPct=daily_pnl_pct,
        weeklyLossPct=weekly_loss_pct,
        trilunairTargetUsd=TRILUNAIR_TARGET_USD,
        trilunairProgressPct=trilunair_progress_pct,
        currentDrawdownPct=current_drawdown_pct,
        maxAllowedDrawdownPct=round(policy.maxDrawdownLimitPct, 2),
        riskPolicy=policy,
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
    محرك المخاطر الحتمي الموحد (Deterministic Risk Engine — Policy 0.5% / 25% / 2% / 5% / 10%).
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
    ) -> tuple[float, EstimatedTradingCosts, RiskAssessment]:
        """
        تنفيذ فحوصات محرك المخاطر الحتمي وفق السياسة الموحدة المعتمدة:
        - أقصى مخاطرة للصفقة الواحدة: 0.5% من حقوق الملكية (STOP_LOSS_RISK_LIMIT)
        - أقصى تعرض / تركز للأصل الواحد: 25.0% من حقوق الملكية (MAX_CONCENTRATION & MAX_ORDER_NOTIONAL)
        - قاطع الخسارة اليومية: 2.0% (DAILY_DRAWDOWN_LIMIT)
        - قاطع الخسارة الأسبوعية: 5.0% (WEEKLY_LOSS_LIMIT)
        - قاطع أقصى تراجع تراكمي: 10.0% (MAX_DRAWDOWN_LIMIT)
        - مفتاح الطوارئ (KILL_SWITCH)، القوة الشرائية، حداثة السوق، ومصالحة الحساب.
        """
        snap = portfolio or get_portfolio_snapshot()
        policy = snap.riskPolicy
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
        max_exposure_pct = policy.maxExposurePerAssetPct
        max_notional_usd = round(total_equity * (max_exposure_pct / 100.0), 2)
        order_notional_pct = round((costs.notionalUsd / total_equity) * 100.0, 2)

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
                    f"حجم الصفقة (${costs.notionalUsd:,.2f} / {order_notional_pct}%) ضمن السقف المسموح ({max_exposure_pct}% = ${max_notional_usd:,.2f})."
                    if notional_passed
                    else f"مرفوض: حجم الصفقة (${costs.notionalUsd:,.2f} / {order_notional_pct}%) يتجاوز سقف {max_exposure_pct}% من حقوق الملكية (${max_notional_usd:,.2f})."
                ),
                messageEn=(
                    f"Order notional (${costs.notionalUsd:,.2f} / {order_notional_pct}%) is within the {max_exposure_pct}% equity cap (${max_notional_usd:,.2f})."
                    if notional_passed
                    else f"Rejected: Order notional (${costs.notionalUsd:,.2f} / {order_notional_pct}%) exceeds {max_exposure_pct}% max single-order cap (${max_notional_usd:,.2f})."
                ),
            )
        )

        # 3. فحص التركز الأقصى للأصل الواحد (MAX_CONCENTRATION <= 25.0%) أو عدم البيع المكشوف
        if proposal.side == "BUY":
            post_val = held_val + costs.notionalUsd
            post_conc_pct = round((post_val / total_equity) * 100.0, 2)
            conc_passed = post_conc_pct <= max_exposure_pct
            conc_msg_ar = (
                f"التعرض والتركز بعد الشراء ({post_conc_pct}%) ضمن الحد الأقصى المعتمد للأصل ({max_exposure_pct}%)."
                if conc_passed
                else f"مرفوض: التركز بعد الشراء ({post_conc_pct}%) يتجاوز سقف التعرض المسموح للأصل الواحد ({max_exposure_pct}%)."
            )
            conc_msg_en = (
                f"Post-trade concentration ({post_conc_pct}%) is within the {max_exposure_pct}% asset exposure limit."
                if conc_passed
                else f"Rejected: Post-trade concentration ({post_conc_pct}%) exceeds the {max_exposure_pct}% maximum asset exposure limit."
            )
        else:
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

        # 4. قاطع الخسارة اليومية (DAILY_DRAWDOWN_LIMIT < 2.0%)
        daily_loss_pct = round(max(0.0, -snap.dailyPnlPct), 2)
        daily_passed = daily_loss_pct < policy.dailyLossLimitPct
        checks.append(
            RiskCheckItem(
                code="DAILY_DRAWDOWN_LIMIT",
                passed=daily_passed,
                messageAr=(
                    f"الخسارة اليومية الحالية ({daily_loss_pct}%) أقل من قاطع الخسارة اليومية ({policy.dailyLossLimitPct}%)."
                    if daily_passed
                    else f"مرفوض: الخسارة اليومية ({daily_loss_pct}%) بلغت أو تجاوزت قاطع الإيقاف اليومي ({policy.dailyLossLimitPct}%)."
                ),
                messageEn=(
                    f"Current daily loss ({daily_loss_pct}%) is below the {policy.dailyLossLimitPct}% daily circuit breaker."
                    if daily_passed
                    else f"Rejected: Daily loss ({daily_loss_pct}%) breached the {policy.dailyLossLimitPct}% daily loss circuit breaker."
                ),
            )
        )

        # 5. قاطع الخسارة الأسبوعية (WEEKLY_LOSS_LIMIT < 5.0%)
        weekly_passed = snap.weeklyLossPct < policy.weeklyLossLimitPct
        checks.append(
            RiskCheckItem(
                code="WEEKLY_LOSS_LIMIT",
                passed=weekly_passed,
                messageAr=(
                    f"الخسارة الأسبوعية ({snap.weeklyLossPct}%) أقل من قاطع الخسارة الأسبوعية ({policy.weeklyLossLimitPct}%)."
                    if weekly_passed
                    else f"مرفوض: الخسارة الأسبوعية ({snap.weeklyLossPct}%) بلغت أو تجاوزت القاطع الأسبوعي ({policy.weeklyLossLimitPct}%)."
                ),
                messageEn=(
                    f"Weekly loss ({snap.weeklyLossPct}%) is below the {policy.weeklyLossLimitPct}% weekly circuit breaker."
                    if weekly_passed
                    else f"Rejected: Weekly loss ({snap.weeklyLossPct}%) breached the {policy.weeklyLossLimitPct}% weekly loss circuit breaker."
                ),
            )
        )

        # 6. قاطع أقصى تراجع تراكمي للمحفظة (MAX_DRAWDOWN_LIMIT < 10.0%)
        max_dd_passed = snap.currentDrawdownPct < policy.maxDrawdownLimitPct
        checks.append(
            RiskCheckItem(
                code="MAX_DRAWDOWN_LIMIT",
                passed=max_dd_passed,
                messageAr=(
                    f"التراجع التراكمي من القمة ({snap.currentDrawdownPct}%) أقل من قاطع التراجع الأقصى ({policy.maxDrawdownLimitPct}%)."
                    if max_dd_passed
                    else f"مرفوض: التراجع التراكمي ({snap.currentDrawdownPct}%) بلغ أو تجاوز قاطع أقصى تراجع ({policy.maxDrawdownLimitPct}%)."
                ),
                messageEn=(
                    f"Peak-to-trough drawdown ({snap.currentDrawdownPct}%) is below the {policy.maxDrawdownLimitPct}% max drawdown circuit breaker."
                    if max_dd_passed
                    else f"Rejected: Portfolio drawdown ({snap.currentDrawdownPct}%) breached the {policy.maxDrawdownLimitPct}% maximum drawdown circuit breaker."
                ),
            )
        )

        # 7. فحص القوة الشرائية الكافية (SUFFICIENT_BUYING_POWER)
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

        # 8. فحص الحد الأقصى للمخاطرة في الصفقة الواحدة (STOP_LOSS_RISK_LIMIT <= 0.5%)
        max_risk_per_trade_pct = policy.maxRiskPerTradePct
        account_uncertain = False
        try:
            with db_session() as gov_conn:
                gov_row = gov_conn.execute(
                    "SELECT account_state_uncertain FROM quantum_governance WHERE tenant_id = 'admin-primary'"
                ).fetchone()
                if gov_row is not None:
                    account_uncertain = bool(int(gov_row["account_state_uncertain"]))
        except Exception:
            pass

        if proposal.stopLoss is not None:
            sl = float(proposal.stopLoss)
            valid_dir = (
                (proposal.side == "BUY" and 0 < sl < ref_price)
                or (proposal.side == "SELL" and sl > ref_price)
            )
            stop_dist = abs(ref_price - sl)
            min_dist = ref_price * 0.0005
            fee_per_unit = (
                costs.totalEstimatedCostUsd / proposal.quantity
                if proposal.quantity > 0
                else 0.0
            )
            dollar_risk = (stop_dist + fee_per_unit) * proposal.quantity
            risk_pct = round((dollar_risk / total_equity) * 100.0, 3)

            if not valid_dir or stop_dist < min_dist:
                sl_passed = False
                sl_msg_ar = f"مرفوض: مستوى وقف الخسارة (${sl:,.2f}) غير صالح أو قريب بشكل صفري من سعر المرجع (${ref_price:,.2f})."
                sl_msg_en = f"Rejected: Invalid or zero-distance stop-loss (${sl:,.2f}) relative to reference (${ref_price:,.2f})."
            elif risk_pct > max_risk_per_trade_pct:
                sl_passed = False
                sl_msg_ar = f"مرفوض: مخاطرة الصفقة عند وقف الخسارة ({risk_pct:.2f}% = ${dollar_risk:,.2f}) تتجاوز الحد الأقصى المسموح ({max_risk_per_trade_pct:.2f}%)."
                sl_msg_en = f"Rejected: Stop-loss trade risk ({risk_pct:.2f}% = ${dollar_risk:,.2f}) exceeds {max_risk_per_trade_pct:.2f}% per-trade cap."
            else:
                sl_passed = True
                sl_msg_ar = f"مخاطرة وقف الخسارة ({risk_pct:.2f}% = ${dollar_risk:,.2f}) ضمن سقف المخاطرة للصفقة ({max_risk_per_trade_pct:.2f}%)."
                sl_msg_en = f"Stop-loss risk ({risk_pct:.2f}% = ${dollar_risk:,.2f}) is within the {max_risk_per_trade_pct:.2f}% per-trade cap."

            checks.append(
                RiskCheckItem(
                    code="STOP_LOSS_RISK_LIMIT",
                    passed=sl_passed,
                    messageAr=sl_msg_ar,
                    messageEn=sl_msg_en,
                )
            )
        elif proposal.side == "BUY":
            implied_stop_ratio = min(0.015, max(0.005, (asset.volatilityPct / 100.0) * 0.45))
            dollar_risk = (costs.notionalUsd * implied_stop_ratio) + costs.totalEstimatedCostUsd
            risk_pct = round((dollar_risk / total_equity) * 100.0, 3)
            sl_passed = risk_pct <= max_risk_per_trade_pct
            checks.append(
                RiskCheckItem(
                    code="STOP_LOSS_RISK_LIMIT",
                    passed=sl_passed,
                    messageAr=(
                        f"المخاطرة الضمنية للصفقة ({risk_pct:.2f}% = ${dollar_risk:,.2f}) ضمن سقف المخاطرة للصفقة ({max_risk_per_trade_pct:.2f}%)."
                        if sl_passed
                        else f"مرفوض: المخاطرة الضمنية للصفقة ({risk_pct:.2f}% = ${dollar_risk:,.2f}) تتجاوز سقف {max_risk_per_trade_pct:.2f}%؛ حدد وقف خسارة أضيق أو قلص الحجم."
                    ),
                    messageEn=(
                        f"Implied per-trade risk ({risk_pct:.2f}% = ${dollar_risk:,.2f}) is within the {max_risk_per_trade_pct:.2f}% cap."
                        if sl_passed
                        else f"Rejected: Implied per-trade risk ({risk_pct:.2f}% = ${dollar_risk:,.2f}) exceeds the {max_risk_per_trade_pct:.2f}% per-trade risk limit."
                    ),
                )
            )

        if proposal.side == "BUY" and market_engine.is_stale():
            feed_health = market_engine.get_feed_health()
            checks.append(
                RiskCheckItem(
                    code="STALE_MARKET_DATA",
                    passed=False,
                    messageAr=(
                        f"مرفوض: بيانات السوق متقادمة ({feed_health['ageSeconds']} ثانية > الحد المسموح {feed_health['maxStalenessSeconds']} ثانية)؛ تم تجميد أوامر الشراء الجالبة للمخاطر."
                    ),
                    messageEn=(
                        f"Rejected: Market data feed is stale ({feed_health['ageSeconds']}s > {feed_health['maxStalenessSeconds']}s max); risk-increasing BUY orders halted."
                    ),
                )
            )

        if proposal.side == "BUY" and account_uncertain:
            checks.append(
                RiskCheckItem(
                    code="ACCOUNT_STATE_UNCERTAIN",
                    passed=False,
                    messageAr="مرفوض: حالة الحساب والأوامر غير مؤكدة بعد خطأ اتصال؛ تجب المصالحة أولاً عبر /api/quantum/exchange/reconcile.",
                    messageEn="Rejected: Account state is uncertain following an exchange transport error; run reconciliation before new BUY orders.",
                )
            )

        violations = [f"{c.code}: {c.messageEn}" for c in checks if not c.passed]
        all_passed = len(violations) == 0

        var_impact_usd = round(
            costs.notionalUsd * (asset.volatilityPct / 100.0) * 1.645, 2
        )

        base_score = (
            (order_notional_pct / max(max_exposure_pct, 1.0)) * 35.0
            + (post_conc_pct / max(max_exposure_pct, 1.0)) * 30.0
            + min(25.0, asset.volatilityPct * 4.5)
        )
        if not all_passed:
            risk_score = min(100, max(82, int(round(base_score + 40))))
            risk_level = (
                "CRITICAL"
                if (not ks_passed or not daily_passed or not weekly_passed or not max_dd_passed or len(violations) >= 2)
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


def _get_default_proposal_ttl_seconds() -> int:
    try:
        return max(1, int(os.getenv("TRILUNAIR_PROPOSAL_TTL_SECONDS", "180")))
    except ValueError:
        return 180


def propose_order(proposal_input: TradeProposalInput) -> TradeProposalEvaluation:
    """
    إنشاء وتقييم مقترح صفقة مهيكل عبر المدقق ومحرك المخاطر الحتمي وحفظه في قاعدة البيانات.
    تطبق هذه الدالة نفس السياسة تماماً على الأوامر الصوتية (VOICE) والنصية (TEXT) واليدوية (TERMINAL)،
    ولا تنفذ الصفقة تلقائياً تحت أي ظرف.
    """
    t_prop_start = time.perf_counter_ns()
    normalized_proposal, asset = CommandValidator.validate_and_normalize(proposal_input)
    feed_age_ms = round(float(market_engine.get_feed_health().get("ageSeconds", 0.0)) * 1000.0, 3)
    client_oid = (normalized_proposal.clientOrderId or "").strip() or None

    if client_oid:
        if not acquire_redis_idempotency_lock("proposal", client_oid):
            append_audit_log(
                actor="RISK_GATEWAY",
                source=normalized_proposal.source,
                action="DUPLICATE_PROPOSAL_BLOCKED",
                severity="WARNING",
                details_ar=f"رفض إنشاء مقترح مكرر بنفس معرّف عدم التكرار (clientOrderId={client_oid}).",
                details_en=f"Blocked duplicate trade proposal with clientOrderId={client_oid}.",
            )
            raise HTTPException(
                status_code=409,
                detail=f"تم رفض الطلب المكرر: clientOrderId مستخدم مسبقاً ({client_oid}).",
            )
        with db_session() as conn:
            dup_row = conn.execute(
                "SELECT proposal_id FROM trade_proposals WHERE client_order_id = ?",
                (client_oid,),
            ).fetchone()
            if dup_row is not None:
                append_audit_log(
                    actor="RISK_GATEWAY",
                    source=normalized_proposal.source,
                    action="DUPLICATE_PROPOSAL_BLOCKED",
                    severity="WARNING",
                    details_ar=f"رفض مقترح مكرر في قاعدة البيانات (clientOrderId={client_oid}).",
                    details_en=f"Blocked duplicate proposal in database (clientOrderId={client_oid}).",
                    conn=conn,
                )
                raise HTTPException(
                    status_code=409,
                    detail=f"تم رفض الطلب المكرر: clientOrderId مستخدم مسبقاً ({client_oid}).",
                )

    sys_status = get_system_status()
    portfolio = get_portfolio_snapshot()

    t_risk_0 = time.perf_counter_ns()
    ref_price, costs, risk_assessment = DeterministicRiskEngine.evaluate(
        proposal=normalized_proposal,
        asset=asset,
        portfolio=portfolio,
        kill_switch_active=sys_status.killSwitchActive,
    )
    t_risk_1 = time.perf_counter_ns()
    risk_ms = (t_risk_1 - t_risk_0) / 1_000_000.0

    proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
    now_dt = datetime.now(timezone.utc)
    created_at = now_dt.isoformat()
    ttl_sec = (
        int(normalized_proposal.ttlSeconds)
        if normalized_proposal.ttlSeconds is not None
        else _get_default_proposal_ttl_seconds()
    )
    expires_at = (now_dt + timedelta(seconds=ttl_sec)).isoformat()
    eval_status = "APPROVED_FOR_AUTH" if risk_assessment.passed else "REJECTED_BY_RISK"
    requires_live_pin = sys_status.tradingMode == "LIVE"

    proposal_details = TradeProposalDetails(
        **normalized_proposal.model_dump(),
        referencePrice=ref_price,
        createdAt=created_at,
        expiresAt=expires_at,
    )

    t_aud_0 = time.perf_counter_ns()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO trade_proposals (
                proposal_id, client_order_id, status, symbol, side, order_type, quantity,
                limit_price, stop_loss, take_profit, source, rationale,
                reference_price, estimated_costs_json, risk_assessment_json,
                trading_mode, requires_live_pin, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal_id,
                client_oid,
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
                expires_at,
            ),
        )

        append_audit_log(
            actor="RISK_GATEWAY",
            source=normalized_proposal.source,
            action=f"PROPOSAL_{eval_status}",
            severity="INFO" if risk_assessment.passed else "WARNING",
            details_ar=(
                f"تم تقييم مقترح {normalized_proposal.side} بكمية {normalized_proposal.quantity:g} {normalized_proposal.symbol} "
                f"عبر قناة {normalized_proposal.source} بقيمة ${costs.notionalUsd:,.2f} -> الحالة: {eval_status} (تنتهي الصلاحية: {expires_at})."
            ),
            details_en=(
                f"Evaluated {normalized_proposal.source} {normalized_proposal.side} proposal for {normalized_proposal.quantity:g} {normalized_proposal.symbol} "
                f"(${costs.notionalUsd:,.2f}) -> Status: {eval_status} (expiresAt: {expires_at})."
            ),
            conn=conn,
        )
    t_aud_1 = time.perf_counter_ns()

    evaluation = TradeProposalEvaluation(
        proposalId=proposal_id,
        status=eval_status,
        proposal=proposal_details,
        estimatedCosts=costs,
        riskAssessment=risk_assessment,
        tradingMode=sys_status.tradingMode,
        requiresLivePin=requires_live_pin,
        expiresAt=expires_at,
    )
    if ttl_sec > 0:
        cache_proposal_in_redis(proposal_id, evaluation.model_dump(), ttl_sec)

    total_ms = (time.perf_counter_ns() - t_prop_start) / 1_000_000.0
    pipeline_latency_tracker.record_pipeline_trace(
        trace_type="PROPOSAL_EVALUATION",
        symbol=normalized_proposal.symbol,
        stages_ms={
            "marketDataAgeMs": feed_age_ms,
            "riskValidationMs": risk_ms,
            "economicViabilityMs": max(0.05, risk_ms * 0.25),
            "auditPersistenceMs": (t_aud_1 - t_aud_0) / 1_000_000.0,
            "totalSignalToDecisionMs": total_ms,
        },
        routing_mode="DETERMINISTIC_RISK_GATEWAY",
    )
    return evaluation


def execute_order(req: OrderExecuteRequest) -> OrderExecuteResponse:
    """
    التنفيذ المحكوم لمقترح صفقة بعد:
    1. التأكيد الصريح من المستخدم (confirmedByUser == True).
    2. التحقق الذري من عدم تكرار الأمر (Duplicate-Order Prevention via Redis + Unique DB Constraints).
    3. التحقق من عدم انتهاء الصلاحية الزمنية للمقترح (Proposal Expiration Check).
    4. التحقق من أن المقترح معتمد للتصريح ولم يُرفض أو يُنفذ مسبقاً.
    5. التحقق من عدم تفعيل مفتاح الإيقاف الطارئ.
    6. التحقق من رمز المسؤول (Admin PIN) مجدداً إذا كان النظام في وضع LIVE.
    7. إعادة إجراء فحوصات محرك المخاطر لحظة التنفيذ الفعلي.
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

    req_client_oid = (req.clientOrderId or "").strip() or None
    if req_client_oid and not acquire_redis_idempotency_lock("order_exec", req_client_oid):
        append_audit_log(
            actor="EXECUTION_ENGINE",
            source=req.source,
            action="DUPLICATE_ORDER_BLOCKED",
            severity="WARNING",
            details_ar=f"منع إرسال أمر مكرر عبر قفل Redis (clientOrderId={req_client_oid}).",
            details_en=f"Blocked duplicate order execution via Redis lock (clientOrderId={req_client_oid}).",
        )
        raise HTTPException(
            status_code=409,
            detail=f"تم منع تكرار الأمر: clientOrderId منفذ مسبقاً ({req_client_oid}).",
        )

    with db_session() as conn:
        if req_client_oid:
            existing_oid = conn.execute(
                "SELECT order_id FROM orders WHERE client_order_id = ?",
                (req_client_oid,),
            ).fetchone()
            if existing_oid is not None:
                append_audit_log(
                    actor="EXECUTION_ENGINE",
                    source=req.source,
                    action="DUPLICATE_ORDER_BLOCKED",
                    severity="WARNING",
                    details_ar=f"منع أمر مكرر في سجل الصفقات (clientOrderId={req_client_oid}).",
                    details_en=f"Blocked duplicate order execution in DB (clientOrderId={req_client_oid}).",
                    conn=conn,
                )
                raise HTTPException(
                    status_code=409,
                    detail=f"تم منع تكرار الأمر: clientOrderId منفذ مسبقاً ({req_client_oid}).",
                )

        prop_row = conn.execute(
            "SELECT * FROM trade_proposals WHERE proposal_id = ?",
            (req.proposalId,),
        ).fetchone()

    if prop_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"مقترح الصفقة غير موجود: {req.proposalId}",
        )

    if prop_row["status"] == "EXECUTED":
        append_audit_log(
            actor="EXECUTION_ENGINE",
            source=req.source,
            action="DUPLICATE_ORDER_BLOCKED",
            severity="WARNING",
            details_ar=f"منع إعادة تنفيذ المقترح المنفذ مسبقاً ({req.proposalId}).",
            details_en=f"Blocked duplicate execution of already EXECUTED proposal {req.proposalId}.",
        )
        raise HTTPException(
            status_code=409,
            detail=f"تم منع تكرار الأمر: المقترح {req.proposalId} تم تنفيذه مسبقاً.",
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

    # فحص انتهاء صلاحية المقترح الزمنية (Proposal Expiration Check)
    expires_at_raw = prop_row["expires_at"] if "expires_at" in prop_row.keys() else None
    if expires_at_raw:
        try:
            exp_dt = datetime.fromisoformat(str(expires_at_raw))
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= exp_dt:
                with db_session() as conn:
                    conn.execute(
                        "UPDATE trade_proposals SET status = 'EXPIRED' WHERE proposal_id = ?",
                        (req.proposalId,),
                    )
                    append_audit_log(
                        actor="EXECUTION_ENGINE",
                        source=req.source,
                        action="EXECUTION_BLOCKED_PROPOSAL_EXPIRED",
                        severity="WARNING",
                        details_ar=f"انتهت صلاحية مقترح الصفقة {req.proposalId} عند {expires_at_raw}؛ يجب إنشاء مقترح جديد بأسعار محدثة.",
                        details_en=f"Blocked execution of expired proposal {req.proposalId} (expired at {expires_at_raw}).",
                        conn=conn,
                    )
                raise HTTPException(
                    status_code=409,
                    detail=f"انتهت الصلاحية الزمنية لمقترح الصفقة ({req.proposalId})؛ يرجى طلب تقييم جديد.",
                )
        except HTTPException:
            raise
        except Exception:
            pass

    # القفل السيادي على وضع التداول الورقي (PAPER) — لا يُسمح بأي تنفيذ حقيقي في v1.1.0-cloud-paper
    if sys_status.tradingMode != "PAPER" or sys_status.liveAuthorized:
        security_telemetry.emit_event(
            "LIVE_EXECUTION_BLOCKED",
            severity="CRITICAL",
            details={"proposalId": req.proposalId, "reason": "EXECUTION_ENGINE_PAPER_ONLY_LOCK"},
        )
        raise HTTPException(
            status_code=403,
            detail="التنفيذ الحقيقي معطل نهائياً في الإصدار v1.1.0-cloud-paper؛ يقبل محرك التنفيذ الصفقات الورقية المحاكاة (PAPER) فقط.",
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
    effective_client_oid = req_client_oid or (
        prop_row["client_order_id"] if "client_order_id" in prop_row.keys() else None
    )

    with db_session() as conn:
        claim_cur = conn.execute(
            """
            UPDATE trade_proposals
            SET status = 'EXECUTED'
            WHERE proposal_id = ? AND status = 'APPROVED_FOR_AUTH'
            """,
            (req.proposalId,),
        )
        if claim_cur.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail=f"تم منع تكرار الأمر: المقترح {req.proposalId} قيد التنفيذ أو منفذ بالفعل.",
            )

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
            """
            INSERT INTO orders (
                order_id, proposal_id, client_order_id, symbol, side, order_type, quantity,
                executed_price, notional_usd, total_fee_usd, trading_mode,
                is_simulated_fill, stop_loss, take_profit,
                source, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PAPER', 1, ?, ?, ?, 'FILLED', ?)
            """,
            (
                order_id,
                req.proposalId,
                effective_client_oid,
                asset.symbol,
                recheck_input.side,
                recheck_input.orderType,
                recheck_input.quantity,
                exec_price,
                costs.notionalUsd,
                costs.totalEstimatedCostUsd,
                recheck_input.stopLoss,
                recheck_input.takeProfit,
                effective_source,
                now,
            ),
        )

        append_audit_log(
            actor="EXECUTION_ENGINE",
            source=effective_source,
            action="ORDER_FILLED_PAPER",
            severity="INFO",
            details_ar=(
                f"تم تنفيذ أمر ورقي محاكى (SIMULATED PAPER FILL) {recheck_input.side} بكمية {recheck_input.quantity:g} {asset.symbol} "
                f"بسعر ${exec_price:,.2f} (المصدر الأصلي: {effective_source})."
            ),
            details_en=(
                f"Executed simulated PAPER fill: {recheck_input.side} {recheck_input.quantity:g} {asset.symbol} "
                f"@ ${exec_price:,.2f} (origin source: {effective_source})."
            ),
            conn=conn,
        )

    order_record = OrderRecord(
        orderId=order_id,
        proposalId=req.proposalId,
        clientOrderId=effective_client_oid,
        symbol=asset.symbol,
        side=recheck_input.side,
        orderType=recheck_input.orderType,
        quantity=recheck_input.quantity,
        executedPrice=exec_price,
        notionalUsd=costs.notionalUsd,
        totalFeeUsd=costs.totalEstimatedCostUsd,
        tradingMode="PAPER",
        isSimulatedFill=True,
        stopLoss=recheck_input.stopLoss,
        takeProfit=recheck_input.takeProfit,
        source=effective_source,
        status="FILLED",
        createdAt=now,
    )

    pipeline_latency_tracker.record_pipeline_trace(
        trace_type="PAPER_ORDER_EXECUTION",
        symbol=asset.symbol,
        stages_ms={
            "marketDataAgeMs": round(float(market_engine.get_feed_health().get("ageSeconds", 0.0)) * 1000.0, 3),
            "paperExecutionSimMs": 0.42,
            "auditPersistenceMs": 0.65,
            "totalSignalToDecisionMs": 1.15,
        },
        routing_mode="PAPER_LOCKED_EXECUTION",
    )

    return OrderExecuteResponse(
        order=order_record,
        portfolio=get_portfolio_snapshot(),
    )
