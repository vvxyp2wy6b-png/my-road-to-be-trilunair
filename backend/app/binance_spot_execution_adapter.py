"""
محول التنفيذ الفوري المعزول المستقبلي وبوابة اعتماد المالك ذات البوابات الثماني (Isolated LIVE_SPOT Adapter & 8-Gate Guard).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.3.0-binance-personal-guard

القواعد الهندسية غير القابلة للتفاوض في هذه الوحدة:
1. العزل الكامل والوضع الافتراضي المعطل:
   - يبقى النظام مقفلاً دائماً في هذا الإصدار على:
     tradingMode = "PAPER"
     liveAuthorized = False
     executionLockedToPaper = True
   - إن ربط حساب Binance الشخصي أو اجتياز التصعيد البيومتري لا يفعّل التداول الحقيقي مطلقاً، ولا يُرسل أي أمر حقيقي إلى Binance.
2. نطاق الأوامر المستقبلي المسموح حصراً (Spot Only):
   - شراء وبيع فوري فقط (BUY / SELL)
   - أنواع الأوامر الفورية المعتمدة: LIMIT, MARKET, STOP_LOSS_LIMIT
   - إلغاء الأوامر الفورية ومطابقة حالة الأمر (Order Reconciliation)
3. الحظر المعماري القاطع (HTTP 403 PROHIBITED_NON_SPOT_OPERATION):
   - العقود الآجلة (Futures: UM / CM / /fapi / /dapi)
   - التداول بالهامش (Margin: Cross / Isolated / /sapi/v1/margin)
   - الرافعة المالية (Leverage > 1x) والاقتراض (Borrowing / sideEffectType != NO_SIDE_EFFECT)
   - السحوبات المالية (Withdrawals) والتحويلات الخارجية أو الشاملة (External / Universal Transfers)
   - التصعيد الذاتي للصلاحيات من قبل أي وكيل ذكاء اصطناعي (Autonomous Permission Escalation)
4. معمارية البوابات الثماني لاعتماد المالك المستقبلي (8-Gate LIVE_SPOT Authorization Workflow).
"""

from __future__ import annotations

import json
import time
from typing import Any, Final, Literal
import uuid

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.binance_personal_account import (
    PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR,
    SAR_PER_USD_PEG,
    ensure_binance_personal_tables,
    get_personal_binance_overview,
    require_owner_biometric_for_binance,
)
from app.database import append_audit_log, db_session, utc_now_iso
from app.market_engine import market_engine
from app.safety_gateway import get_system_status
from app.security import get_client_identifier, require_authenticated_session_or_secret, security_telemetry
from app.webauthn_passkeys import list_registered_passkeys, verify_step_up_token

# الثوابت غير القابلة للتجاوز في هذا الإصدار
RELEASE_EXECUTION_LOCKED_TO_PAPER: Final[bool] = True
RELEASE_TRADING_MODE: Final[str] = "PAPER"
RELEASE_LIVE_AUTHORIZED: Final[bool] = False

ALLOWED_SPOT_SIDES: frozenset[str] = frozenset({"BUY", "SELL"})
ALLOWED_SPOT_ORDER_TYPES: frozenset[str] = frozenset({"LIMIT", "MARKET", "STOP_LOSS_LIMIT"})

PROHIBITED_OPERATION_CATEGORIES: tuple[str, ...] = (
    "FUTURES_TRADING",
    "MARGIN_TRADING",
    "LEVERAGE_ABOVE_1X",
    "BORROWING_OR_MARGIN_LOAN",
    "CRYPTO_OR_FIAT_WITHDRAWALS",
    "EXTERNAL_OR_UNIVERSAL_TRANSFERS",
    "AUTONOMOUS_PERMISSION_ESCALATION",
)

spot_execution_router = APIRouter(
    prefix="/api/binance/spot-execution",
    tags=["Future Spot Execution Preparation (Disabled & Locked to PAPER)"],
)


# ==============================================================================
# 1. Database Schema for Owner LIVE_SPOT Limits & Dry-Run Audit Log
# ==============================================================================


def ensure_spot_execution_tables() -> None:
    """تهيئة جدول حدود المالك المستقبلية للتداول الفوري مع الإبقاء على التنفيذ الحقيقي مقفلاً على PAPER."""
    now = utc_now_iso()
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS binance_spot_owner_policy (
                policy_id TEXT PRIMARY KEY,
                owner_configured INTEGER NOT NULL DEFAULT 0,
                jurisdiction_eligibility_confirmed INTEGER NOT NULL DEFAULT 0,
                jurisdiction_country_code TEXT NOT NULL DEFAULT 'SA',
                max_single_order_sar REAL NOT NULL DEFAULT 750.0,
                max_daily_spot_sar REAL NOT NULL DEFAULT 1500.0,
                max_monthly_spot_sar REAL NOT NULL DEFAULT 2125.0,
                max_single_asset_exposure_pct REAL NOT NULL DEFAULT 45.0,
                require_biometric_per_order INTEGER NOT NULL DEFAULT 1,
                allowed_spot_symbols_json TEXT NOT NULL DEFAULT '["BTCUSDT","ETHUSDT","SOLUSDT"]',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS binance_spot_dry_run_log (
                dry_run_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                estimated_notional_usd REAL NOT NULL,
                estimated_notional_sar REAL NOT NULL,
                passed_validation INTEGER NOT NULL,
                rejection_code TEXT NOT NULL DEFAULT '',
                real_order_submitted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        existing = conn.execute(
            "SELECT policy_id FROM binance_spot_owner_policy WHERE policy_id = 'owner-live-spot-policy'"
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO binance_spot_owner_policy (
                    policy_id, owner_configured, jurisdiction_eligibility_confirmed, jurisdiction_country_code,
                    max_single_order_sar, max_daily_spot_sar, max_monthly_spot_sar, max_single_asset_exposure_pct,
                    require_biometric_per_order, allowed_spot_symbols_json, updated_at
                ) VALUES ('owner-live-spot-policy', 0, 0, 'SA', 750.0, 1500.0, ?, 45.0, 1, '["BTCUSDT","ETHUSDT","SOLUSDT"]', ?)
                """,
                (PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR, now),
            )


def get_owner_spot_policy() -> dict[str, Any]:
    """استرجاع سياسة حدود المخاطر والتعرض الفوري التي يحددها المالك."""
    ensure_spot_execution_tables()
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM binance_spot_owner_policy WHERE policy_id = 'owner-live-spot-policy'"
        ).fetchone()
    assert row is not None
    rd = dict(row)
    return {
        "ownerConfigured": bool(rd["owner_configured"]),
        "jurisdictionEligibilityConfirmed": bool(rd["jurisdiction_eligibility_confirmed"]),
        "jurisdictionCountryCode": str(rd["jurisdiction_country_code"]),
        "maxSingleOrderSar": float(rd["max_single_order_sar"]),
        "maxSingleOrderUsd": round(float(rd["max_single_order_sar"]) / SAR_PER_USD_PEG, 2),
        "maxDailySpotSar": float(rd["max_daily_spot_sar"]),
        "maxMonthlySpotSar": float(rd["max_monthly_spot_sar"]),
        "maxMonthlySpotUsd": round(float(rd["max_monthly_spot_sar"]) / SAR_PER_USD_PEG, 2),
        "maxSingleAssetExposurePct": float(rd["max_single_asset_exposure_pct"]),
        "requireBiometricPerOrder": bool(rd["require_biometric_per_order"]),
        "allowedSpotSymbols": json.loads(str(rd["allowed_spot_symbols_json"] or '["BTCUSDT","ETHUSDT","SOLUSDT"]')),
        "updatedAt": rd["updated_at"],
    }


# ==============================================================================
# 2. Architectural Prohibition Enforcement (Futures / Margin / Leverage / Withdrawals)
# ==============================================================================


def enforce_spot_only_prohibitions(payload: dict[str, Any], actor_source: str = "API_REQUEST") -> None:
    """
    رفض معماري قاطع لأي محاولة لتمرير معلمات عقود آجلة، هامش، رافعة مالية، اقتراض، سحب، تحويل، أو تصعيد ذاتي.
    """
    market_type = str(payload.get("marketType") or payload.get("productType") or "SPOT").strip().upper()
    operation = str(payload.get("operation") or "SPOT_ORDER").strip().upper()
    leverage = float(payload.get("leverage") or 1.0)
    is_isolated = bool(payload.get("isIsolated", False))
    margin_borrow = bool(payload.get("autoBorrow", False) or payload.get("borrowAmount", 0))
    side_effect = str(payload.get("sideEffectType") or "NO_SIDE_EFFECT").strip().upper()
    autonomous_escalation = bool(payload.get("autonomousEscalation", False)) or actor_source.upper() == "AUTONOMOUS_AGENT"

    reasons: list[str] = []
    if autonomous_escalation or operation in {"ESCALATE_PERMISSIONS", "ENABLE_LIVE_AUTONOMOUSLY"}:
        reasons.append("AUTONOMOUS_PERMISSION_ESCALATION_FORBIDDEN")
    if market_type != "SPOT" or "FUTURES" in operation or "MARGIN" in operation:
        reasons.append(f"NON_SPOT_MARKET_FORBIDDEN:{market_type}")
    if leverage > 1.0001 or leverage < 1.0:
        reasons.append(f"LEVERAGE_PROHIBITED:{leverage}x")
    if is_isolated or margin_borrow or side_effect != "NO_SIDE_EFFECT":
        reasons.append(f"MARGIN_OR_BORROWING_PROHIBITED:{side_effect}")
    if operation in {"WITHDRAW", "WITHDRAWAL", "CAPITAL_WITHDRAW"} or payload.get("withdrawAddress"):
        reasons.append("WITHDRAWALS_ARCHITECTURALLY_PROHIBITED")
    if operation in {"TRANSFER", "INTERNAL_TRANSFER", "UNIVERSAL_TRANSFER"} or payload.get("transferTarget"):
        reasons.append("EXTERNAL_OR_UNIVERSAL_TRANSFERS_PROHIBITED")

    if reasons:
        security_telemetry.emit_event(
            "LIVE_EXECUTION_BLOCKED",
            severity="CRITICAL",
            details={"reason": "PROHIBITED_NON_SPOT_OPERATION", "violations": reasons, "source": actor_source},
        )
        with db_session() as conn:
            append_audit_log(
                actor="SPOT_SECURITY_GATE",
                source="SAFETY_GATEWAY",
                action="PROHIBITED_NON_SPOT_OPERATION_BLOCKED",
                severity="CRITICAL",
                details_ar=f"رفض معماري قاطع لعملية محظورة خارج نطاق الفوري (Spot): {', '.join(reasons)}.",
                details_en=f"Hard architectural block on prohibited non-Spot operation: {', '.join(reasons)}.",
                conn=conn,
            )
        raise HTTPException(
            status_code=403,
            detail=f"PROHIBITED_NON_SPOT_OPERATION: {', '.join(reasons)}",
        )


# ==============================================================================
# 3. 8-Gate LIVE_SPOT Owner Approval Evaluator
# ==============================================================================


def evaluate_live_spot_authorization_gates(request: Request | None = None) -> dict[str, Any]:
    """
    تقييم البوابات الثماني الإلزامية لمسار اعتماد المالك المستقبلي (LIVE_SPOT):
    البوابة الثامنة تظل مقفلة دائماً (passed=False) في هذا الإصدار لضمان عدم إرسال أي أمر تداول حقيقي.
    """
    ensure_binance_personal_tables()
    ensure_spot_execution_tables()

    overview = get_personal_binance_overview()
    policy = get_owner_spot_policy()
    sys_status = get_system_status()
    active_passkeys = list_registered_passkeys(include_revoked=False)

    ro_slot = overview["credentialSlots"]["READ_ONLY_MONITORING"]
    exec_slot = overview["credentialSlots"]["FUTURE_SPOT_EXECUTION"]

    # البوابة 1: اتصال رسمي موثق بـ Binance
    g1_passed = bool(
        (ro_slot.get("configured") and ro_slot.get("status") == "VERIFIED_READ_ONLY")
        or (exec_slot.get("configured") and exec_slot.get("status") == "VERIFIED_SPOT_RESTRICTED")
    )

    # البوابة 2: مفتاح خاص بالتداول الفوري فقط مع تعطيل السحب والهامش والعقود الآجلة والتحويلات
    exec_audit = exec_slot.get("permissionAudit") or {}
    exec_scopes = exec_audit.get("scopes") or {}
    g2_passed = bool(
        exec_slot.get("configured")
        and exec_slot.get("status") == "VERIFIED_SPOT_RESTRICTED"
        and exec_scopes.get("enableSpotTrading") is True
        and exec_scopes.get("enableWithdrawals") is False
        and exec_scopes.get("enableMargin") is False
        and exec_scopes.get("enableFutures") is False
        and exec_scopes.get("enableInternalOrUniversalTransfer") is False
    )

    # البوابة 3: تأكيد الأهلية القانونية والنطاق الجغرافي المدعوم
    g3_passed = bool(policy["jurisdictionEligibilityConfirmed"])

    # البوابة 4: استقرار البنية التحتية وتقييد عناوين IP الموثوقة على Binance
    active_slot_for_ip = exec_slot if exec_slot.get("configured") else ro_slot
    trusted_ips = active_slot_for_ip.get("trustedIps") or []
    ip_restrict_binance = bool((active_slot_for_ip.get("permissionAudit") or {}).get("ipRestrictEnabledOnBinance", False))
    g4_passed = bool(
        sys_status.safetyChecks.auditTrailHealthy
        and sys_status.safetyChecks.positionLimitsActive
        and len(trusted_ips) > 0
        and ip_restrict_binance
    )

    # البوابة 5: جاهزية محرك المخاطر وعدم تفعيل مفتاح الطوارئ (Kill Switch)
    g5_passed = bool(
        not sys_status.killSwitchActive
        and sys_status.safetyChecks.riskEngineVerified
        and sys_status.safetyChecks.killSwitchReady
    )

    # البوابة 6: ضبط حدود المبلغ والتعرض الشهري من قبل المالك
    g6_passed = bool(
        policy["ownerConfigured"]
        and 0 < policy["maxSingleOrderSar"] <= policy["maxMonthlySpotSar"]
        and len(policy["allowedSpotSymbols"]) > 0
    )

    # البوابة 7: مصادقة بيومترية حديثة عبر WebAuthn Passkey (Face ID / Touch ID -> X-Step-Up-Token)
    step_up_claims = None
    if request is not None:
        tok = (request.headers.get("X-Step-Up-Token") or "").strip()
        if tok:
            step_up_claims = verify_step_up_token(tok)
    g7_passed = bool(len(active_passkeys) > 0 and step_up_claims is not None)

    # البوابة 8: قفل الإصدار الدائم لمنع التداول الحقيقي في هذه المرحلة
    g8_passed = not RELEASE_EXECUTION_LOCKED_TO_PAPER  # دائماً False في هذا الإصدار

    gates = [
        {
            "gateNumber": 1,
            "gateId": "VERIFIED_OFFICIAL_BINANCE_CONNECTION",
            "titleEn": "Verified Official Binance API Connection",
            "titleAr": "اتصال رسمي موثق بواجهة Binance API",
            "passed": g1_passed,
            "detailEn": "Verified via signed official Binance API check." if g1_passed else "Pending verified owner API key setup.",
        },
        {
            "gateNumber": 2,
            "gateId": "VERIFIED_SPOT_ONLY_PERMISSIONS",
            "titleEn": "Verified Spot-Only API Scope (Withdrawals/Margin/Futures Disabled)",
            "titleAr": "التحقق من اقتصار الصلاحيات على التداول الفوري مع تعطيل السحب والهامش والعقود الآجلة",
            "passed": g2_passed,
            "detailEn": (
                "Dedicated Spot execution key verified with withdrawals, margin, futures, and transfers disabled."
                if g2_passed
                else "Dedicated FUTURE_SPOT_EXECUTION key not yet verified.",
            )[0]
            if isinstance(
                (
                    "Dedicated Spot execution key verified with withdrawals, margin, futures, and transfers disabled."
                    if g2_passed
                    else "Dedicated FUTURE_SPOT_EXECUTION key not yet verified."
                ),
                tuple,
            )
            else (
                "Dedicated Spot execution key verified with withdrawals, margin, futures, and transfers disabled."
                if g2_passed
                else "Dedicated FUTURE_SPOT_EXECUTION key not yet verified."
            ),
        },
        {
            "gateNumber": 3,
            "gateId": "SUPPORTED_JURISDICTION_AND_ELIGIBILITY",
            "titleEn": "Supported Jurisdiction & Personal Spot Account Eligibility",
            "titleAr": "أهلية الحساب الشخصي والتوافق التنظيمي للنطاق الجغرافي",
            "passed": g3_passed,
            "detailEn": f"Confirmed ({policy['jurisdictionCountryCode']})." if g3_passed else "Owner confirmation pending.",
        },
        {
            "gateNumber": 4,
            "gateId": "STABLE_INFRASTRUCTURE_AND_IP_ALLOWLIST",
            "titleEn": "Verified Infrastructure Health & Trusted Static IP Allowlist",
            "titleAr": "استقرار البنية التحتية وتفعيل قائمة عناوين IP الثابتة الموثوقة",
            "passed": g4_passed,
            "detailEn": "DB, audit trail, and Binance IP allowlist verified." if g4_passed else "Requires static server IP allowlist on Binance API key.",
        },
        {
            "gateNumber": 5,
            "gateId": "RISK_ENGINE_AND_KILL_SWITCH_CLEAR",
            "titleEn": "Deterministic Risk Engine Healthy & Kill Switch Disarmed",
            "titleAr": "سلامة محرك المخاطر الحتمي وعدم تفعيل مفتاح الطوارئ",
            "passed": g5_passed,
            "detailEn": "Deterministic risk engine ready and Kill Switch inactive." if g5_passed else "Kill Switch active or risk subsystem degraded.",
        },
        {
            "gateNumber": 6,
            "gateId": "OWNER_MONETARY_AND_EXPOSURE_LIMITS",
            "titleEn": "Owner-Configured SAR Monetary & Asset Exposure Caps",
            "titleAr": "اعتماد المالك لسقوف المبالغ بالريال وحدود التركز للأصول",
            "passed": g6_passed,
            "detailEn": (
                f"Configured: max order SAR {policy['maxSingleOrderSar']:,.0f}, monthly cap SAR {policy['maxMonthlySpotSar']:,.0f}."
                if g6_passed
                else "Owner has not explicitly saved LIVE_SPOT monetary caps yet."
            ),
        },
        {
            "gateNumber": 7,
            "gateId": "WEBAUTHN_BIOMETRIC_STEP_UP_VERIFIED",
            "titleEn": "Fresh Face ID / Touch ID WebAuthn Biometric Step-Up",
            "titleAr": "مصادقة بيومترية فورية عبر Face ID / Touch ID (WebAuthn Passkey)",
            "passed": g7_passed,
            "detailEn": "Fresh WebAuthn X-Step-Up-Token verified." if g7_passed else "Requires enrolled Passkey + fresh X-Step-Up-Token.",
        },
        {
            "gateNumber": 8,
            "gateId": "OWNER_EXPLICIT_PRODUCTION_RELEASE_LOCK",
            "titleEn": "Permanent Release Safety Lock (Locked to PAPER Mode)",
            "titleAr": "قفل الأمان المعماري للإصدار (التنفيذ مقفل دائماً على PAPER)",
            "passed": g8_passed,
            "detailEn": "LOCKED BY DESIGN: Real Binance order execution is disabled in v1.3.0-binance-personal-guard; tradingMode remains PAPER.",
        },
    ]

    all_passed = all(g["passed"] for g in gates)
    return {
        "workflowName": "LIVE_SPOT",
        "tradingMode": RELEASE_TRADING_MODE,
        "liveAuthorized": RELEASE_LIVE_AUTHORIZED and all_passed,
        "executionLockedToPaper": RELEASE_EXECUTION_LOCKED_TO_PAPER,
        "realOrdersPermitted": False,
        "passedGatesCount": sum(1 for g in gates if g["passed"]),
        "totalGatesCount": 8,
        "gates": gates,
        "allowedSpotCapabilities": {
            "sides": sorted(ALLOWED_SPOT_SIDES),
            "orderTypes": sorted(ALLOWED_SPOT_ORDER_TYPES),
            "supportsOrderCancellation": True,
            "supportsOrderStatusReconciliation": True,
        },
        "prohibitedOperations": list(PROHIBITED_OPERATION_CATEGORIES),
        "ownerPolicy": policy,
    }


# ==============================================================================
# 4. Isolated BinanceSpotExecutionAdapter (Dry-Run Validation + Hard Execution Block)
# ==============================================================================


class BinanceSpotExecutionAdapter:
    """محول التداول الفوري المعزول — يتحقق من الأوامر دون إرسالها ويمنع التنفيذ الحقيقي طوال قفل PAPER."""

    @staticmethod
    def dry_run_validate_order(raw_order: dict[str, Any]) -> dict[str, Any]:
        """التحقق الجاف (Offline Dry-Run) من أمر فوري مقترح مقابل قيود Spot وحدود المالك ومحرك المخاطر دون أي اتصال شبكي."""
        ensure_spot_execution_tables()
        enforce_spot_only_prohibitions(raw_order, actor_source=str(raw_order.get("source", "DRY_RUN")))

        symbol = str(raw_order.get("symbol", "")).strip().upper()
        side = str(raw_order.get("side", "")).strip().upper()
        order_type = str(raw_order.get("orderType") or raw_order.get("type") or "LIMIT").strip().upper()
        quantity = float(raw_order.get("quantity") or 0.0)
        limit_price = float(raw_order.get("price") or 0.0)
        stop_price = float(raw_order.get("stopPrice") or 0.0)

        if side not in ALLOWED_SPOT_SIDES:
            raise HTTPException(status_code=422, detail=f"Unsupported Spot side '{side}'; allowed: BUY, SELL.")
        if order_type not in ALLOWED_SPOT_ORDER_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported Spot orderType '{order_type}'; allowed: LIMIT, MARKET, STOP_LOSS_LIMIT.",
            )
        if quantity <= 0:
            raise HTTPException(status_code=422, detail="Spot order quantity must be strictly positive.")
        if order_type in {"LIMIT", "STOP_LOSS_LIMIT"} and limit_price <= 0:
            raise HTTPException(status_code=422, detail=f"{order_type} requires a positive limit price.")
        if order_type == "STOP_LOSS_LIMIT" and stop_price <= 0:
            raise HTTPException(status_code=422, detail="STOP_LOSS_LIMIT requires a positive stopPrice.")

        policy = get_owner_spot_policy()
        sys_status = get_system_status()
        overview = get_personal_binance_overview()

        ref_price_usd = limit_price
        if ref_price_usd <= 0:
            base_coin = symbol[:-4] if symbol.endswith("USDT") else symbol
            for ma in market_engine.get_assets():
                if ma.symbol.split("/")[0].replace("USDT", "").upper() == base_coin:
                    ref_price_usd = float(ma.price)
                    break
        if ref_price_usd <= 0:
            ref_price_usd = 100.0

        notional_usd = round(quantity * ref_price_usd, 2)
        notional_sar = round(notional_usd * SAR_PER_USD_PEG, 2)

        rejections: list[str] = []
        if sys_status.killSwitchActive:
            rejections.append("KILL_SWITCH_ACTIVE")
        if symbol not in [s.upper() for s in policy["allowedSpotSymbols"]]:
            rejections.append(f"SYMBOL_NOT_IN_OWNER_ALLOWLIST:{symbol}")
        if notional_sar > policy["maxSingleOrderSar"] + 0.01:
            rejections.append(
                f"EXCEEDS_MAX_SINGLE_ORDER_SAR:{notional_sar:.2f}>{policy['maxSingleOrderSar']:.2f}"
            )
        monthly_used_sar = float(overview["monthlyInvestmentBudgetTracking"]["currentMonthSpotPurchasesSar"])
        if side == "BUY" and (monthly_used_sar + notional_sar) > policy["maxMonthlySpotSar"] + 0.01:
            rejections.append(
                f"EXCEEDS_MONTHLY_SPOT_CAP_SAR:{monthly_used_sar + notional_sar:.2f}>{policy['maxMonthlySpotSar']:.2f}"
            )
        if notional_usd < 5.0:
            rejections.append("BELOW_BINANCE_MIN_NOTIONAL_5_USDT")

        passed = len(rejections) == 0
        dry_id = f"dry_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO binance_spot_dry_run_log (
                    dry_run_id, symbol, side, order_type, quantity, estimated_notional_usd,
                    estimated_notional_sar, passed_validation, rejection_code, real_order_submitted, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    dry_id,
                    symbol,
                    side,
                    order_type,
                    quantity,
                    notional_usd,
                    notional_sar,
                    int(passed),
                    ",".join(rejections),
                    now,
                ),
            )

        return {
            "dryRunId": dry_id,
            "passedValidation": passed,
            "rejections": rejections,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "quantity": quantity,
            "estimatedNotionalUsd": notional_usd,
            "estimatedNotionalSar": notional_sar,
            "realOrderSubmitted": False,
            "tradingMode": RELEASE_TRADING_MODE,
            "liveAuthorized": RELEASE_LIVE_AUTHORIZED,
            "executionLockedToPaper": RELEASE_EXECUTION_LOCKED_TO_PAPER,
        }

    @staticmethod
    def submit_spot_order(raw_order: dict[str, Any], request: Request | None = None) -> dict[str, Any]:
        """رفض حتمي لإرسال أي أمر حقيقي إلى Binance طالما قفل الإصدار على PAPER مفعّل."""
        enforce_spot_only_prohibitions(raw_order, actor_source=str(raw_order.get("source", "SUBMIT_ATTEMPT")))
        gates = evaluate_live_spot_authorization_gates(request)
        security_telemetry.emit_event(
            "LIVE_EXECUTION_BLOCKED",
            severity="CRITICAL",
            details={
                "reason": "LIVE_SPOT_EXECUTION_LOCKED_TO_PAPER",
                "passedGates": gates["passedGatesCount"],
                "symbol": str(raw_order.get("symbol", "")),
            },
        )
        with db_session() as conn:
            append_audit_log(
                actor="SPOT_SECURITY_GATE",
                source="SAFETY_GATEWAY",
                action="LIVE_SPOT_ORDER_SUBMISSION_BLOCKED",
                severity="CRITICAL",
                details_ar="تم حظر محاولة إرسال أمر فوري حقيقي إلى Binance: التنفيذ مقفل معمارياً على وضع PAPER.",
                details_en="Blocked live Binance Spot order submission attempt: executionLockedToPaper=True (tradingMode=PAPER).",
                conn=conn,
            )
        raise HTTPException(
            status_code=403,
            detail=(
                "LIVE_SPOT_EXECUTION_LOCKED_TO_PAPER: Real-money Binance order submission is permanently disabled "
                "in this release (tradingMode=PAPER, liveAuthorized=False). Zero orders sent."
            ),
        )

    @staticmethod
    def cancel_spot_order(symbol: str, order_id: str, request: Request | None = None) -> dict[str, Any]:
        """رفض حتمي لأي عملية إلغاء كتابية على حساب حقيقي طالما قفل PAPER مفعّل."""
        _ = (symbol, order_id, request)
        security_telemetry.emit_event(
            "LIVE_EXECUTION_BLOCKED",
            severity="WARNING",
            details={"reason": "LIVE_SPOT_CANCEL_LOCKED_TO_PAPER", "symbol": symbol},
        )
        raise HTTPException(
            status_code=403,
            detail="LIVE_SPOT_EXECUTION_LOCKED_TO_PAPER: Live order cancellation/mutation is disabled while locked to PAPER.",
        )

    @staticmethod
    def reconcile_spot_order_status(symbol: str, order_id: str) -> dict[str, Any]:
        """مطابقة حالة أمر فوري من السجل المحلي المتزامن بالقراءة فقط دون تنفيذ أي عملية كتابية."""
        ensure_binance_personal_tables()
        uid = f"{symbol.strip().upper()}:{order_id.strip()}"
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM binance_personal_orders WHERE order_uid = ?",
                (uid,),
            ).fetchone()
            trades = conn.execute(
                "SELECT * FROM binance_personal_trades WHERE symbol = ? AND binance_order_id = ?",
                (symbol.strip().upper(), order_id.strip()),
            ).fetchall()

        if row is None:
            return {
                "found": False,
                "symbol": symbol.strip().upper(),
                "orderId": order_id.strip(),
                "reconciliationStatus": "ORDER_NOT_IN_SYNCED_LEDGER",
            }

        rd = dict(row)
        summed_trade_qty = round(sum(float(t["qty"]) for t in trades), 8)
        reported_exec_qty = round(float(rd["executed_qty"]), 8)
        qty_matched = abs(summed_trade_qty - reported_exec_qty) <= 1e-6 or (len(trades) == 0 and reported_exec_qty == 0.0)
        return {
            "found": True,
            "symbol": rd["symbol"],
            "orderId": rd["binance_order_id"],
            "orderStatus": rd["status"],
            "reportedExecutedQty": reported_exec_qty,
            "summedSyncedFillsQty": summed_trade_qty,
            "matchedTradeCount": len(trades),
            "reconciliationStatus": "RECONCILED_EXACT" if qty_matched else "FILLS_DELTA_DETECTED",
        }


# ==============================================================================
# 5. Request Schemas & FastAPI Endpoints (/api/binance/spot-execution/*)
# ==============================================================================


class OwnerSpotPolicyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jurisdictionEligibilityConfirmed: bool = True
    jurisdictionCountryCode: str = Field(default="SA", min_length=2, max_length=6)
    maxSingleOrderSar: float = Field(default=750.0, gt=0, le=50000.0)
    maxDailySpotSar: float = Field(default=1500.0, gt=0, le=100000.0)
    maxMonthlySpotSar: float = Field(default=2125.0, gt=0, le=200000.0)
    maxSingleAssetExposurePct: float = Field(default=45.0, gt=1.0, le=100.0)
    requireBiometricPerOrder: bool = True
    allowedSpotSymbols: list[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    adminSecret: str | None = None


@spot_execution_router.get("/readiness")
def api_get_live_spot_readiness(request: Request) -> dict[str, Any]:
    """استرجاع تقييم البوابات الثماني لـ LIVE_SPOT وحالة قفل التداول الورقي الدائم."""
    return evaluate_live_spot_authorization_gates(request)


@spot_execution_router.put("/limits")
async def api_update_owner_spot_limits(
    request: Request,
    req: OwnerSpotPolicyUpdateRequest,
) -> dict[str, Any]:
    """تحديث سقوف المبالغ والتعرض لـ LIVE_SPOT بعد مصادقة المالك والتصعيد البيومتري (مع بقاء التنفيذ مقفلاً على PAPER)."""
    auth_info = require_owner_biometric_for_binance(
        request,
        req.adminSecret,
        action_label="BINANCE_LIVE_SPOT_LIMITS_UPDATE",
    )
    if req.maxSingleOrderSar > req.maxMonthlySpotSar + 0.01:
        raise HTTPException(
            status_code=422,
            detail="maxSingleOrderSar cannot exceed maxMonthlySpotSar.",
        )

    ensure_spot_execution_tables()
    clean_syms = [s.strip().upper() for s in req.allowedSpotSymbols if s.strip().isalnum()][:12]
    if not clean_syms:
        raise HTTPException(status_code=422, detail="At least one allowed Spot symbol is required.")

    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE binance_spot_owner_policy
            SET owner_configured = 1,
                jurisdiction_eligibility_confirmed = ?,
                jurisdiction_country_code = ?,
                max_single_order_sar = ?,
                max_daily_spot_sar = ?,
                max_monthly_spot_sar = ?,
                max_single_asset_exposure_pct = ?,
                require_biometric_per_order = ?,
                allowed_spot_symbols_json = ?,
                updated_at = ?
            WHERE policy_id = 'owner-live-spot-policy'
            """,
            (
                int(req.jurisdictionEligibilityConfirmed),
                req.jurisdictionCountryCode.strip().upper(),
                round(req.maxSingleOrderSar, 2),
                round(req.maxDailySpotSar, 2),
                round(req.maxMonthlySpotSar, 2),
                round(req.maxSingleAssetExposurePct, 2),
                int(req.requireBiometricPerOrder),
                json.dumps(clean_syms),
                now,
            ),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="SPOT_POLICY_GUARD",
            action="OWNER_LIVE_SPOT_LIMITS_SAVED",
            severity="INFO",
            details_ar=(
                f"حفظ المالك حدود الإعداد المستقبلي لـ LIVE_SPOT (أقصى أمر {req.maxSingleOrderSar:,.0f} ريال، "
                f"أقصى شهر {req.maxMonthlySpotSar:,.0f} ريال) — التنفيذ الحقيقي مقفل على PAPER."
            ),
            details_en=(
                f"Saved owner LIVE_SPOT risk caps (maxOrder=SAR {req.maxSingleOrderSar:,.0f}, "
                f"maxMonthly=SAR {req.maxMonthlySpotSar:,.0f}); execution remains locked to PAPER."
            ),
            conn=conn,
        )

    readiness = evaluate_live_spot_authorization_gates(request)
    readiness["authorizedVia"] = auth_info["authMethod"]
    return readiness


@spot_execution_router.post("/dry-run")
async def api_dry_run_spot_order(
    request: Request,
    raw_order: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """تشغيل تحقق جاف (Dry-Run) لأمر فوري مقترح دون إرسال أي أمر حقيقي إلى Binance."""
    require_authenticated_session_or_secret(
        request,
        raw_order.get("adminSecret"),
        action_label="BINANCE_SPOT_DRY_RUN",
    )
    return BinanceSpotExecutionAdapter.dry_run_validate_order(raw_order)


@spot_execution_router.post("/submit")
async def api_submit_live_spot_order_locked(
    request: Request,
    raw_order: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """نقطة نهاية التنفيذ المحمية — ترفض دائماً إرسال أي أمر حقيقي في هذا الإصدار وتتحقق من الحظر المعماري."""
    return BinanceSpotExecutionAdapter.submit_spot_order(raw_order, request)


@spot_execution_router.delete("/order")
async def api_cancel_live_spot_order_locked(
    request: Request,
    symbol: str,
    orderId: str,
) -> dict[str, Any]:
    """نقطة نهاية الإلغاء المحمية — مقفلة على PAPER لمنع أي تعديل على حساب حقيقي."""
    return BinanceSpotExecutionAdapter.cancel_spot_order(symbol, orderId, request)


@spot_execution_router.get("/reconcile/{symbol}/{order_id}")
def api_reconcile_synced_spot_order(symbol: str, order_id: str) -> dict[str, Any]:
    """مطابقة حالة أمر فوري مقابل سجل الصفقات المتزامن بالقراءة فقط."""
    return BinanceSpotExecutionAdapter.reconcile_spot_order_status(symbol, order_id)
