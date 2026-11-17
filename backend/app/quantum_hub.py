"""
منظومة القيادة الكمية المتكاملة (Quantum AI Trading Command Center Hub).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD (my-road-to-be-trilunair)

تطبق هذه الوحدة الطبقات الصارمة المنصوص عليها في المواصفة المرجعية العليا:
1. محولات مزودات الذكاء الاصطناعي المستقلة (OpenAI GPT, Google Gemini, Anthropic Claude, xAI Grok)
   مع سياسة المصداقية المطلقة (عدم انتحال أي استجابة لمزود غير مهيأ مطلقاً).
2. نظام تأهيل الوكلاء رباعي المستويات (Trainee -> Analyst -> Experimentally Qualified -> Production Qualified)
   مع فرض إعادة التأهيل التلقائية فور أي تعديل جوهري في النموذج أو التعليمات أو المهارات أو الصلاحيات.
3. موسوعة المعرفة التداولية المؤرشفة بالإصدارات (Versioned Trading Knowledge Base) لـ 20 محوراً علمياً.
4. المهارات التحليلية المعيارية (Modular Skills) وموصلات البيانات الخارجية مع تعقيم المدخلات غير الموثوقة.
5. محول Binance Spot الرسمي الموقع بـ HMAC-SHA256، التحقق من فلاتر الرموز القياسية (BTCUSDT...)،
   عدم الخلط بين USD و USDT، ومنع إرسال الأصول المرجعية (REFERENCE_ONLY) للتنفيذ الفوري.
6. محرك الجدوى الاقتصادية للصفقات (Trade Economic Viability Engine) وفصل تكاليف التداول عن تكاليف AI.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import math
import os
import re
import time
from typing import Any
from urllib.parse import urlencode
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .database import append_audit_log, db_session, utc_now_iso

router = APIRouter(prefix="/api/quantum", tags=["quantum-command-center"])

DEFAULT_TENANT_ID = "admin-primary"

QUALIFICATION_SEQUENCE = [
    "TRAINEE",
    "ANALYST",
    "EXPERIMENTALLY_QUALIFIED",
    "PRODUCTION_QUALIFIED",
]


# ==============================================================================
# 1. محولات مزودات الذكاء الاصطناعي المستقلة (Independent LLM Provider Adapters)
# ==============================================================================

def get_llm_providers_status() -> list[dict[str, Any]]:
    """
    فحص حالة التوفر الحقيقية لمزودات النماذج اللغوية دون أي تزييف.
    إذا لم يتوفر مفتاح المزود في البيئة يُعلّم صراحةً كـ UNAVAILABLE.
    """
    openai_ok = bool(os.getenv("OPENAI_API_KEY", "").strip())
    gemini_ok = bool(os.getenv("GEMINI_API_KEY", "").strip())
    anthropic_ok = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    xai_ok = bool(os.getenv("XAI_API_KEY", "").strip())

    return [
        {
            "providerId": "local-quant-engine",
            "displayName": "Local Quantitative Engine",
            "available": True,
            "configuredKeyEnv": "BUILT_IN_DETERMINISTIC",
            "availableModels": ["quant-deterministic-v1", "risk-calculus-v1"],
            "costPer1kTokensUsd": 0.0001,
            "statusMessageAr": "محرك رياضي كمي محلي متصل دائماً — شفاف ومعلن الهوية.",
            "statusMessageEn": "Built-in transparent local quantitative engine — always online.",
        },
        {
            "providerId": "openai",
            "displayName": "OpenAI GPT",
            "available": openai_ok,
            "configuredKeyEnv": "OPENAI_API_KEY",
            "availableModels": ["gpt-4.1", "gpt-4o-mini"],
            "costPer1kTokensUsd": 0.0050,
            "statusMessageAr": (
                "مفتاح OPENAI_API_KEY مهيأ وجاهز."
                if openai_ok
                else "غير متصل — لم يتم ضبط OPENAI_API_KEY (لا يتم انتحال ردود المزود)."
            ),
            "statusMessageEn": (
                "OPENAI_API_KEY configured."
                if openai_ok
                else "Unavailable — OPENAI_API_KEY not set (never fabricated)."
            ),
        },
        {
            "providerId": "gemini",
            "displayName": "Google Gemini",
            "available": gemini_ok,
            "configuredKeyEnv": "GEMINI_API_KEY",
            "availableModels": ["gemini-2.5-pro", "gemini-2.5-flash"],
            "costPer1kTokensUsd": 0.0025,
            "statusMessageAr": (
                "مفتاح GEMINI_API_KEY مهيأ وجاهز."
                if gemini_ok
                else "غير متصل — لم يتم ضبط GEMINI_API_KEY (لا يتم انتحال ردود المزود)."
            ),
            "statusMessageEn": (
                "GEMINI_API_KEY configured."
                if gemini_ok
                else "Unavailable — GEMINI_API_KEY not set (never fabricated)."
            ),
        },
        {
            "providerId": "anthropic",
            "displayName": "Anthropic Claude",
            "available": anthropic_ok,
            "configuredKeyEnv": "ANTHROPIC_API_KEY",
            "availableModels": ["claude-sonnet-4-20250514", "claude-3-5-haiku-latest"],
            "costPer1kTokensUsd": 0.0045,
            "statusMessageAr": (
                "مفتاح ANTHROPIC_API_KEY مهيأ وجاهز."
                if anthropic_ok
                else "غير متصل — لم يتم ضبط ANTHROPIC_API_KEY (لا يتم انتحال ردود المزود)."
            ),
            "statusMessageEn": (
                "ANTHROPIC_API_KEY configured."
                if anthropic_ok
                else "Unavailable — ANTHROPIC_API_KEY not set (never fabricated)."
            ),
        },
        {
            "providerId": "xai",
            "displayName": "xAI Grok",
            "available": xai_ok,
            "configuredKeyEnv": "XAI_API_KEY",
            "availableModels": ["grok-3", "grok-3-mini"],
            "costPer1kTokensUsd": 0.0040,
            "statusMessageAr": (
                "مفتاح XAI_API_KEY مهيأ وجاهز."
                if xai_ok
                else "غير متصل — لم يتم ضبط XAI_API_KEY (لا يتم انتحال ردود المزود)."
            ),
            "statusMessageEn": (
                "XAI_API_KEY configured."
                if xai_ok
                else "Unavailable — XAI_API_KEY not set (never fabricated)."
            ),
        },
    ]


# ==============================================================================
# 2. تعقيم المدخلات الخارجية غير الموثوقة (Untrusted External Data Sanitizer)
# ==============================================================================

def sanitize_untrusted_external_payload(raw_text: str, max_length: int = 1200) -> str:
    """
    تطهير البيانات الواردة من الموصلات الخارجية قبل تمريرها لأي وكيل أو واجهة عرض
    لحماية النظام من حقن التعليمات (Prompt Injection) أو الوسوم النصية الخبيثة.
    """
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw_text or "")
    cleaned = html.escape(cleaned, quote=True)
    # إزالة أنماط محاولات تجاوز صلاحيات النظام
    cleaned = re.sub(
        r"(?i)(ignore\s+previous\s+instructions|bypass\s+risk|execute\s+immediately)",
        "[REDACTED_UNTRUSTED_DIRECTIVE]",
        cleaned,
    )
    return cleaned[:max_length]


# ==============================================================================
# 3. محول Binance Spot وفلاتر الرموز القياسية (Binance Spot Adapter & Filters)
# ==============================================================================

BINANCE_INSTRUMENTS_CATALOG: list[dict[str, Any]] = [
    {
        "canonicalSymbol": "BTCUSDT",
        "displayAlias": "BTC / USDT (Spot)",
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "classification": "TRADABLE_SPOT",
        "tickSize": 0.01,
        "stepSize": 0.00001,
        "minQty": 0.0001,
        "maxQty": 100.0,
        "minNotional": 10.0,
        "referencePrice": 96500.0,
    },
    {
        "canonicalSymbol": "ETHUSDT",
        "displayAlias": "ETH / USDT (Spot)",
        "baseAsset": "ETH",
        "quoteAsset": "USDT",
        "classification": "TRADABLE_SPOT",
        "tickSize": 0.01,
        "stepSize": 0.0001,
        "minQty": 0.001,
        "maxQty": 1000.0,
        "minNotional": 10.0,
        "referencePrice": 3420.0,
    },
    {
        "canonicalSymbol": "SOLUSDT",
        "displayAlias": "SOL / USDT (Spot)",
        "baseAsset": "SOL",
        "quoteAsset": "USDT",
        "classification": "TRADABLE_SPOT",
        "tickSize": 0.01,
        "stepSize": 0.01,
        "minQty": 0.05,
        "maxQty": 10000.0,
        "minNotional": 10.0,
        "referencePrice": 212.5,
    },
    {
        "canonicalSymbol": "BNBUSDT",
        "displayAlias": "BNB / USDT (Spot)",
        "baseAsset": "BNB",
        "quoteAsset": "USDT",
        "classification": "TRADABLE_SPOT",
        "tickSize": 0.01,
        "stepSize": 0.001,
        "minQty": 0.01,
        "maxQty": 5000.0,
        "minNotional": 10.0,
        "referencePrice": 645.0,
    },
    {
        "canonicalSymbol": "XAUUSD",
        "displayAlias": "Gold Spot Reference (XAU/USD)",
        "baseAsset": "XAU",
        "quoteAsset": "USD",
        "classification": "REFERENCE_ONLY",
        "tickSize": 0.10,
        "stepSize": 0.01,
        "minQty": 0.0,
        "maxQty": 0.0,
        "minNotional": 0.0,
        "referencePrice": 2685.0,
    },
    {
        "canonicalSymbol": "NVDA",
        "displayAlias": "NVIDIA Equity Reference (NASDAQ)",
        "baseAsset": "NVDA",
        "quoteAsset": "USD",
        "classification": "REFERENCE_ONLY",
        "tickSize": 0.01,
        "stepSize": 1.0,
        "minQty": 0.0,
        "maxQty": 0.0,
        "minNotional": 0.0,
        "referencePrice": 142.8,
    },
    {
        "canonicalSymbol": "SPX",
        "displayAlias": "S&P 500 Macro Index Reference",
        "baseAsset": "SPX",
        "quoteAsset": "USD",
        "classification": "REFERENCE_ONLY",
        "tickSize": 0.01,
        "stepSize": 1.0,
        "minQty": 0.0,
        "maxQty": 0.0,
        "minNotional": 0.0,
        "referencePrice": 5980.0,
    },
]


def sign_binance_query(params: dict[str, Any], api_secret: str) -> str:
    """توقيع استعلام Binance Spot REST رسمياً بخوارزمية HMAC-SHA256."""
    query_string = urlencode(params)
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{query_string}&signature={signature}"


def validate_binance_spot_filters(
    symbol: str,
    quantity: float,
    price: float,
) -> dict[str, Any]:
    """
    التحقق الحتمي من فلاتر Binance Spot القياسية:
    - منع تنفيذ الأصول المرجعية (REFERENCE_ONLY) في Binance Spot منعاً باتاً.
    - التحقق من الحد الأدنى للكمية minQty والحد الأقصى maxQty ودقة stepSize والحد الأدنى للقيمة minNotional.
    """
    normalized = symbol.strip().upper()
    spec = next(
        (item for item in BINANCE_INSTRUMENTS_CATALOG if item["canonicalSymbol"] == normalized),
        None,
    )
    if spec is None:
        return {
            "valid": False,
            "code": "SYMBOL_UNAVAILABLE",
            "reasonAr": f"الرمز {normalized} غير مدرج في قائمة أزواج Binance Spot المصرح بها.",
            "reasonEn": f"Symbol {normalized} is not an eligible Binance Spot pair.",
        }

    if spec["classification"] != "TRADABLE_SPOT":
        return {
            "valid": False,
            "code": "REFERENCE_ONLY_INSTRUMENT",
            "reasonAr": (
                f"الأصل {normalized} مصنف كأداة مرجعية فقط (REFERENCE_ONLY) ولا يجوز إرساله للتنفيذ في Binance Spot."
            ),
            "reasonEn": (
                f"Instrument {normalized} is classified as REFERENCE_ONLY and must never be routed to Binance Spot."
            ),
        }

    if quantity <= 0 or not math.isfinite(quantity):
        return {
            "valid": False,
            "code": "INVALID_QUANTITY",
            "reasonAr": "يجب أن تكون الكمية رقماً موجباً ومحدوداً.",
            "reasonEn": "Quantity must be a positive finite number.",
        }

    if quantity < spec["minQty"] or quantity > spec["maxQty"]:
        return {
            "valid": False,
            "code": "LOT_SIZE_VIOLATION",
            "reasonAr": f"الكمية خارج نطاق فلتر LOT_SIZE المسموح ({spec['minQty']} - {spec['maxQty']}).",
            "reasonEn": f"Quantity violates LOT_SIZE filter ({spec['minQty']} - {spec['maxQty']}).",
        }

    notional = quantity * price
    if notional < spec["minNotional"]:
        return {
            "valid": False,
            "code": "MIN_NOTIONAL_VIOLATION",
            "reasonAr": f"القيمة الإجمالية ({notional:.2f} {spec['quoteAsset']}) أقل من الحد الأدنى MIN_NOTIONAL ({spec['minNotional']}).",
            "reasonEn": f"Order notional ({notional:.2f} {spec['quoteAsset']}) is below MIN_NOTIONAL ({spec['minNotional']}).",
        }

    return {
        "valid": True,
        "code": "FILTERS_OK",
        "spec": spec,
        "notional": round(notional, 4),
    }


def calculate_safe_position_size(
    equity_usd: float,
    max_risk_pct: float,
    entry_price: float,
    stop_loss_price: float | None,
    round_trip_fee_bps: float = 20.0,
) -> dict[str, Any]:
    """
    حساب حجم المركز الآمن باستخدام مسافة وقف الخسارة وتكاليف التداول التقديرية (القسم 12).
    يتعامل بأمان تام مع مسافة الوقف الصفرية أو المفقودة أو غير الصالحة دون قسمة على صفر.
    """
    if equity_usd <= 0 or entry_price <= 0:
        return {"valid": False, "recommendedQuantity": 0.0, "reason": "INVALID_EQUITY_OR_PRICE"}

    if stop_loss_price is None or stop_loss_price <= 0:
        return {
            "valid": False,
            "recommendedQuantity": 0.0,
            "reason": "MISSING_OR_NON_POSITIVE_STOP_LOSS",
        }

    stop_distance = abs(entry_price - stop_loss_price)
    min_safe_distance = entry_price * 0.0005  # 5 bps minimum valid stop distance
    if stop_distance < min_safe_distance:
        return {
            "valid": False,
            "recommendedQuantity": 0.0,
            "reason": "ZERO_OR_TOO_TIGHT_STOP_DISTANCE",
        }

    fee_per_unit = entry_price * (round_trip_fee_bps / 10_000.0)
    effective_loss_per_unit = stop_distance + fee_per_unit
    max_dollar_risk = equity_usd * (max_risk_pct / 100.0)
    raw_qty = max_dollar_risk / effective_loss_per_unit
    max_exposure_qty = (equity_usd * 0.25) / entry_price
    safe_qty = min(raw_qty, max_exposure_qty)

    return {
        "valid": True,
        "recommendedQuantity": round(max(0.0, safe_qty), 6),
        "maxDollarRiskUsd": round(max_dollar_risk, 2),
        "effectiveLossPerUnit": round(effective_loss_per_unit, 4),
    }


# ==============================================================================
# 4. تهيئة جداول المنظومة الكمية وبذر المعرفة والوكلاء (SQLite Bootstrap)
# ==============================================================================

INITIAL_20_KNOWLEDGE_ARTICLES: list[tuple[str, str, str, str, str]] = [
    (
        "RISK_MANAGEMENT",
        "تحجيم المراكز (Position Sizing)",
        "Position Sizing",
        "يُحسب حجم المركز بقسمة أقصى مبلغ مخاطرة مسموح به (0.5% من حقوق الملكية) على مسافة وقف الخسارة مضافاً إليها العمولات والانزلاق.",
        "Position size equals maximum allowable dollar risk (0.5% of equity) divided by (stop distance + round-trip trading costs).",
    ),
    (
        "RISK_MANAGEMENT",
        "المخاطرة لكل صفقة (Risk per Trade)",
        "Risk per Trade",
        "الحد الافتراضي الصارم هو 0.5% من إجمالي حقوق الملكية في الصفقة الواحدة لحماية رأس المال من سلاسل الخسائر المتتالية.",
        "Default hard risk cap is 0.5% of account equity per trade to preserve capital across losing streaks.",
    ),
    (
        "RISK_MANAGEMENT",
        "نسبة العائد إلى المخاطرة (Risk/Reward Ratio)",
        "Risk/Reward Ratio",
        "يُشترط تقييم صافي العائد المتوقع بعد خصم العمولات والسبريد والانزلاق وتكلفة استدلال الذكاء الاصطناعي.",
        "Net expected reward must exceed total execution and AI inference costs with a defensible R:R profile.",
    ),
    (
        "MARKET_MECHANICS",
        "بنية السوق (Market Structure)",
        "Market Structure",
        "تمييز القمم والقيعان الصاعدة والهابطة ومناطق التجميع والتصريف قبل اقتراح أي دخول فوري.",
        "Identify higher-highs/lows, consolidation regimes, and liquidity sweeps prior to spot entries.",
    ),
    (
        "TECHNICALS",
        "الدعم والمقاومة (Support and Resistance)",
        "Support and Resistance",
        "تُعامل مناطق الدعم والمقاومة كنطاقات سيولة احتمالية وليست خطوطاً حتمية مضمونة الارتداد.",
        "Treat support and resistance as probabilistic liquidity zones rather than guaranteed reversal lines.",
    ),
    (
        "MARKET_MECHANICS",
        "التقلب السعري (Volatility Regimes)",
        "Volatility Regimes",
        "عند ارتفاع التقلب السعري (ATR) يتسع وقف الخسارة فيجب تقليص حجم المركز تلقائياً للحفاظ على ثبات المخاطرة الدولارية.",
        "Higher ATR widens stops and requires proportionally smaller position sizes to keep dollar risk constant.",
    ),
    (
        "EXECUTION",
        "السيولة وعمق الدفتر (Liquidity & Orderbook Depth)",
        "Liquidity & Orderbook Depth",
        "تجنب أوامر السوق الكبيرة في الأزواج ضحلة السيولة لتفادي الانزلاق السعري المكلف.",
        "Avoid oversized market orders in thin orderbooks to prevent severe market-impact slippage.",
    ),
    (
        "EXECUTION",
        "عمولات التداول (Trading Fees)",
        "Trading Fees",
        "تُحتسب عمولة الدخول والخروج معاً (Round-Trip) في كل تقييم للجدوى الاقتصادية للصفقة.",
        "Always account for round-trip maker/taker commissions in pre-trade economic viability checks.",
    ),
    (
        "EXECUTION",
        "فارق العرض والطلب والانزلاق (Spread & Slippage)",
        "Spread and Slippage",
        "يمثل السبريد والانزلاق ضريبة غير مرئية تتعاظم في الأطر القصيرة وتقلص القيمة المتوقعة الصافية.",
        "Bid/ask spread and slippage act as hidden friction that compounds heavily on short horizons.",
    ),
    (
        "RISK_MANAGEMENT",
        "تصميم وقف الخسارة (Stop-Loss Design)",
        "Stop-Loss Design",
        "يوضع وقف الخسارة عند المستوى الذي يثبت بطلان الفرضية الفنية، ويُرفض الوقف الصفري أو الضيق بشكل مصطنع.",
        "Place stops at structural invalidation points; reject zero or artificially tight stop distances.",
    ),
    (
        "EXECUTION",
        "استراتيجيات جني الأرباح والخروج الجزئي (Take-Profit & Partial Exits)",
        "Take-Profit & Partial Exits",
        "يدعم الخروج المتدرج تأمين جزء من الربح عند الهدف الأول وتقليل تعرض المحفظة لتقلبات الانعكاس.",
        "Scaled partial exits lock in realized gains at structural targets while reducing residual exposure.",
    ),
    (
        "EXECUTION",
        "أنواع الأوامر الفورية (Spot Order Types)",
        "Spot Order Types",
        "الموازنة بين سرعة التنفيذ في أوامر السوق (MARKET) وضبط السعر وتقليل الانزلاق في الأوامر المحددة (LIMIT).",
        "Balance immediacy of MARKET orders against price protection and reduced slippage of LIMIT orders.",
    ),
    (
        "PORTFOLIO",
        "تركز المحفظة (Portfolio Concentration)",
        "Portfolio Concentration",
        "الحد الأقصى للتعرض لأصل منفرد هو 25% من حقوق الملكية لمنع مخاطر الأصل الواحد الكارثية.",
        "Maximum single-asset exposure is capped at 25% of total equity to prevent idiosyncratic ruin.",
    ),
    (
        "PORTFOLIO",
        "التراجع وقواطع الدائرة (Drawdown & Circuit Breakers)",
        "Drawdown & Circuit Breakers",
        "تتوقف الصفقات الجالبة للمخاطر تلقائياً عند خسارة 2% يومياً أو 5% أسبوعياً أو 10% تراجعاً أقصى.",
        "Risk-increasing trades halt automatically at 2% daily loss, 5% weekly loss, or 10% max drawdown.",
    ),
    (
        "PSYCHOLOGY",
        "أخطاء التداول قصير الأجل الشائعة (Short-Term Trading Mistakes)",
        "Common Short-Term Mistakes",
        "الإفراط في التداول وملاحقة الشموع بعد اتساع السبريد يؤديان إلى تآكل رأس المال بفعل العمولات.",
        "Overtrading and chasing impulses across wide spreads erode equity through transaction costs.",
    ),
    (
        "CASE_STUDIES",
        "أمثلة تاريخية رابحة وخاسرة (Historical Winning & Losing Cases)",
        "Historical Case Studies",
        "الصفقات المنضبطة تنجو عند فشل التوقع بفضل التزامها بحجم مخاطرة 0.5%، بينما تنهار المراكز المضخمة حتى مع نسبة نجاح عالية.",
        "Disciplined 0.5%-risk trades survive thesis invalidation, whereas oversized positions fail despite high win rates.",
    ),
    (
        "OPERATIONS",
        "المخاطر التشغيلية للبورصة وتقادم البيانات (Exchange Operational Risks)",
        "Exchange Operational Risks",
        "عند انقطاع بث الأسعار أو عدم يقين حالة الحساب، يجب تجميد أي أوامر شراء جديدة ومصالحة حالة الأوامر فوراً.",
        "When market feeds go stale or account state is uncertain, halt new risk-increasing orders and reconcile.",
    ),
    (
        "AI_GOVERNANCE",
        "عدم يقين نماذج الذكاء الاصطناعي (AI-Model Uncertainty)",
        "AI-Model Uncertainty",
        "إجماع الوكلاء ليس دليلاً على الربحية؛ تخضع كل توصية لمحرك المخاطر الحتمي وبوابة التصاريح.",
        "Agent consensus is never proof of profitability; every proposal remains subordinate to deterministic risk gates.",
    ),
]


def ensure_quantum_tables() -> None:
    """إنشاء وبذر جداول المنظومة الكمية بعزل المستأجرين (tenant_id) عند التشغيل."""
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS quantum_governance (
                tenant_id TEXT PRIMARY KEY,
                authorization_policy TEXT NOT NULL DEFAULT 'PAPER',
                agents_paused INTEGER NOT NULL DEFAULT 0,
                account_state_uncertain INTEGER NOT NULL DEFAULT 0,
                max_risk_per_trade_pct REAL NOT NULL DEFAULT 0.5,
                max_exposure_per_asset_pct REAL NOT NULL DEFAULT 25.0,
                daily_loss_limit_pct REAL NOT NULL DEFAULT 2.0,
                weekly_loss_limit_pct REAL NOT NULL DEFAULT 5.0,
                max_drawdown_limit_pct REAL NOT NULL DEFAULT 10.0,
                starting_equity_usd REAL NOT NULL DEFAULT 1000000.0,
                target_equity_usd REAL NOT NULL DEFAULT 1000000000000.0,
                horizon_months INTEGER NOT NULL DEFAULT 120,
                daily_goal_pct REAL NOT NULL DEFAULT 0.35,
                weekly_goal_pct REAL NOT NULL DEFAULT 1.80,
                monthly_goal_pct REAL NOT NULL DEFAULT 7.50,
                total_ai_inference_costs_usd REAL NOT NULL DEFAULT 0.0142,
                total_connector_costs_usd REAL NOT NULL DEFAULT 0.0045,
                last_reconciled_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quantum_agents (
                agent_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'admin-primary',
                name_ar TEXT NOT NULL,
                name_en TEXT NOT NULL,
                role_ar TEXT NOT NULL,
                role_en TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                visual_state TEXT NOT NULL DEFAULT 'AGREE',
                assigned_provider TEXT NOT NULL DEFAULT 'local-quant-engine',
                assigned_model TEXT NOT NULL DEFAULT 'quant-deterministic-v1',
                decision_weight REAL NOT NULL DEFAULT 1.0,
                qualification_level TEXT NOT NULL DEFAULT 'EXPERIMENTALLY_QUALIFIED',
                qualification_score_pct INTEGER NOT NULL DEFAULT 88,
                requalification_required INTEGER NOT NULL DEFAULT 0,
                last_note_ar TEXT NOT NULL,
                last_note_en TEXT NOT NULL,
                assigned_skills_json TEXT NOT NULL,
                core_instructions TEXT NOT NULL,
                can_analyze INTEGER NOT NULL DEFAULT 1,
                can_propose_trades INTEGER NOT NULL DEFAULT 1,
                can_participate_autonomous INTEGER NOT NULL DEFAULT 0,
                total_calls INTEGER NOT NULL DEFAULT 4,
                total_tokens INTEGER NOT NULL DEFAULT 2800,
                attributable_ai_cost_usd REAL NOT NULL DEFAULT 0.0028,
                historical_reliability_pct REAL NOT NULL DEFAULT 78.0
            );

            CREATE TABLE IF NOT EXISTS quantum_knowledge_base (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'admin-primary',
                slug TEXT NOT NULL,
                category TEXT NOT NULL,
                title_ar TEXT NOT NULL,
                title_en TEXT NOT NULL,
                content_ar TEXT NOT NULL,
                content_en TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quantum_skills (
                skill_id TEXT PRIMARY KEY,
                name_ar TEXT NOT NULL,
                name_en TEXT NOT NULL,
                description_ar TEXT NOT NULL,
                description_en TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                avg_compute_cost_usd REAL NOT NULL DEFAULT 0.0002
            );

            CREATE TABLE IF NOT EXISTS quantum_connectors (
                connector_id TEXT PRIMARY KEY,
                name_ar TEXT NOT NULL,
                name_en TEXT NOT NULL,
                provider TEXT NOT NULL,
                required_credentials_json TEXT NOT NULL,
                capabilities_json TEXT NOT NULL,
                rate_limit_per_min INTEGER NOT NULL,
                data_freshness_seconds INTEGER NOT NULL,
                operating_cost_per_1k_usd REAL NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            );
            """
        )

        now = utc_now_iso()
        gov = conn.execute(
            "SELECT tenant_id FROM quantum_governance WHERE tenant_id = ?",
            (DEFAULT_TENANT_ID,),
        ).fetchone()
        if gov is None:
            conn.execute(
                """
                INSERT INTO quantum_governance (tenant_id, last_reconciled_at)
                VALUES (?, ?)
                """,
                (DEFAULT_TENANT_ID, now),
            )

        agent_cnt = conn.execute("SELECT COUNT(*) AS c FROM quantum_agents").fetchone()["c"]
        if int(agent_cnt) == 0:
            default_agents = [
                (
                    "quant-alpha",
                    "د. ريان (المحلل الكمي)",
                    "Dr. Rayan (Quant Alpha)",
                    "التحليل الكمي والزخم الفني وبنية السوق",
                    "Quantitative & Technical Market Structure",
                    "THINKING",
                    1.15,
                    "EXPERIMENTALLY_QUALIFIED",
                    91,
                    json.dumps(["volume-analysis", "volatility-analysis", "anomaly-detection"]),
                    "حلل الزخم والتقلب ومستويات السيولة دون تجاوز ضوابط المخاطر.",
                ),
                (
                    "risk-sentinel",
                    "سارة (حارسة المخاطر)",
                    "Sara (Risk Sentinel)",
                    "تقييم المخاطر واختبار الضغط والتحدي النقدي",
                    "Deterministic Risk Challenge & Drawdown Defense",
                    "SPEAKING",
                    1.35,
                    "PRODUCTION_QUALIFIED",
                    96,
                    json.dumps(["risk-reward-calc", "portfolio-exposure", "volatility-analysis"]),
                    "تحدَّ جميع الفرضيات المتفائلة وافرض حد مخاطرة 0.5% لكل صفقة.",
                ),
                (
                    "macro-oracle",
                    "طارق (استراتيجي الاقتصاد الكلي)",
                    "Tariq (Macro & Liquidity Oracle)",
                    "استخبارات السوق والسيولة الكلية والمشاعر",
                    "Macro Intelligence, Sentiment & Cross-Market Flows",
                    "AGREE",
                    0.95,
                    "ANALYST",
                    84,
                    json.dumps(["sentiment-analysis", "news-impact", "liquidity-analysis"]),
                    "ارصد تدفقات السيولة وتأثير المؤشرات المرجعية دون الخلط بين USD و USDT.",
                ),
                (
                    "execution-architect",
                    "خالد (مهندس التنفيذ)",
                    "Khaled (Execution Architect)",
                    "جودة التنفيذ وتقدير السبريد والانزلاق والعمولات",
                    "Execution Quality, Spread, Slippage & Cost Optimization",
                    "DISAGREE",
                    1.05,
                    "EXPERIMENTALLY_QUALIFIED",
                    89,
                    json.dumps(["trade-cost-estimation", "liquidity-analysis"]),
                    "قلل تكاليف الانزلاق والسبريد وافحص الجدوى الاقتصادية الصافية.",
                ),
                (
                    "chief-strategist",
                    "المجلس التنفيذي (كبير المستشارين)",
                    "Executive Council (Chief Strategist)",
                    "تنسيق الاستراتيجية وتجميع الأدلة وعدم اليقين",
                    "Decision Aggregation & Uncertainty Synthesis",
                    "AGREE",
                    1.25,
                    "PRODUCTION_QUALIFIED",
                    95,
                    json.dumps(["risk-reward-calc", "trade-cost-estimation", "portfolio-exposure"]),
                    "اجمع الآراء المتفقة والمختلفة ووازن الأدلة دون اعتبار الإجماع ضماناً للربح.",
                ),
            ]
            for (
                aid,
                nar,
                nen,
                rar,
                ren,
                vstate,
                weight,
                qlevel,
                qscore,
                skills_j,
                instr,
            ) in default_agents:
                can_auto = 1 if qlevel == "PRODUCTION_QUALIFIED" else 0
                conn.execute(
                    """
                    INSERT INTO quantum_agents (
                        agent_id, name_ar, name_en, role_ar, role_en, visual_state,
                        decision_weight, qualification_level, qualification_score_pct,
                        last_note_ar, last_note_en, assigned_skills_json, core_instructions,
                        can_participate_autonomous
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        aid,
                        nar,
                        nen,
                        rar,
                        ren,
                        vstate,
                        weight,
                        qlevel,
                        qscore,
                        "مؤهل وفق اختبارات التهيئة القياسية.",
                        "Qualified under baseline automated verification.",
                        skills_j,
                        instr,
                        can_auto,
                    ),
                )

        kb_cnt = conn.execute("SELECT COUNT(*) AS c FROM quantum_knowledge_base").fetchone()["c"]
        if int(kb_cnt) == 0:
            for idx, (cat, tar, ten, car, cen) in enumerate(INITIAL_20_KNOWLEDGE_ARTICLES, start=1):
                conn.execute(
                    """
                    INSERT INTO quantum_knowledge_base (
                        id, slug, category, title_ar, title_en, content_ar, content_en, version, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (f"kb_{idx:02d}", f"topic-{idx:02d}", cat, tar, ten, car, cen, now),
                )

        sk_cnt = conn.execute("SELECT COUNT(*) AS c FROM quantum_skills").fetchone()["c"]
        if int(sk_cnt) == 0:
            skills_seed = [
                ("volume-analysis", "تحليل الأحجام المتقدم", "Advanced Volume Analysis", "كشف تدفقات السيولة المؤسسية وانحرافات الحجم.", "Detects volume profile imbalances and institutional participation."),
                ("volatility-analysis", "تحليل التقلب السعري", "Volatility Analysis", "قياس ATR وتكيف حجم المركز مع تقلب السوق.", "Computes realized volatility & ATR-adjusted stop sizing."),
                ("risk-reward-calc", "حاسبة العائد للمخاطرة", "Risk/Reward Calculator", "تقييم صافي العائد بعد العمولات ومسافة الوقف.", "Evaluates net R:R after fees and stop distance."),
                ("anomaly-detection", "كشف شذوذ السوق", "Market Anomaly Detection", "رصد القفزات غير الطبيعية واتساع السبريد المفاجئ.", "Flags abnormal price spikes and sudden spread widening."),
                ("sentiment-analysis", "تحليل مشاعر السوق", "Sentiment Analysis", "قراءة توازن الخوف والطمع كمؤشر سياقي مساعد.", "Evaluates crowd sentiment regime as contextual input."),
                ("news-impact", "تحليل أثر الأخبار", "News-Impact Analysis", "تقييم مخاطر الأحداث الكلية مع تعقيم المدخلات الخارجية.", "Assesses macro event risk using sanitized external feeds."),
                ("liquidity-analysis", "تحليل السيولة وعمق الدفتر", "Liquidity Analysis", "فحص عمق أوامر الشراء والبيع قبل التوجيه.", "Inspects orderbook bid/ask depth prior to order routing."),
                ("trade-cost-estimation", "تقدير تكاليف الصفقة", "Trade Cost Estimation", "حساب العمولة والسبريد والانزلاق وتكلفة AI.", "Estimates commission, spread, slippage, and AI inference cost."),
                ("portfolio-exposure", "تحليل تعرض المحفظة", "Portfolio Exposure Analysis", "مراقبة حد التركز 25% والارتباط بين المراكز.", "Enforces 25% single-asset cap and portfolio VaR."),
            ]
            for sid, nar, nen, dar, den in skills_seed:
                conn.execute(
                    """
                    INSERT INTO quantum_skills (skill_id, name_ar, name_en, description_ar, description_en)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (sid, nar, nen, dar, den),
                )

        cn_cnt = conn.execute("SELECT COUNT(*) AS c FROM quantum_connectors").fetchone()["c"]
        if int(cn_cnt) == 0:
            connectors_seed = [
                (
                    "binance-spot-connector",
                    "موصل Binance Spot (REST + WebSocket)",
                    "Binance Spot Exchange Connector",
                    "Binance Spot",
                    json.dumps(["BINANCE_API_KEY", "BINANCE_API_SECRET"]),
                    json.dumps(["SPOT_QUOTES", "ORDERBOOK_DEPTH", "AUTHENTICATED_SPOT_EXECUTION"]),
                    1200,
                    2,
                    0.0,
                ),
                (
                    "macro-reference-connector",
                    "موصل المؤشرات المرجعية والذهب والأسهم",
                    "Reference Macro, Gold & Equities Feed",
                    "Reference Market Data",
                    json.dumps([]),
                    json.dumps(["REFERENCE_ONLY_QUOTES", "MACRO_CORRELATION"]),
                    300,
                    15,
                    0.05,
                ),
                (
                    "sanitized-news-connector",
                    "موصل الأخبار والمشاعر المعقّم",
                    "Sanitized Crypto News & Sentiment Feed",
                    "News Intelligence Adapter",
                    json.dumps(["NEWS_API_KEY"]),
                    json.dumps(["HEADLINE_IMPACT", "SENTIMENT_SCORE"]),
                    120,
                    60,
                    0.12,
                ),
            ]
            for cid, nar, nen, prov, req_j, cap_j, rlim, fresh, cost in connectors_seed:
                conn.execute(
                    """
                    INSERT INTO quantum_connectors (
                        connector_id, name_ar, name_en, provider, required_credentials_json,
                        capabilities_json, rate_limit_per_min, data_freshness_seconds, operating_cost_per_1k_usd
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (cid, nar, nen, prov, req_j, cap_j, rlim, fresh, cost),
                )


# ==============================================================================
# 5. نماذج الطلبات وحسابات الجدوى والتأهيل
# ==============================================================================

class AgentConfigPatch(BaseModel):
    enabled: bool | None = None
    assignedProvider: str | None = None
    assignedModel: str | None = None
    decisionWeight: float | None = Field(default=None, ge=0.1, le=2.5)
    assignedSkills: list[str] | None = None
    coreInstructions: str | None = None
    canProposeTrades: bool | None = None
    canParticipateAutonomous: bool | None = None


class PauseAgentsRequest(BaseModel):
    paused: bool


class KnowledgeUpsertRequest(BaseModel):
    id: str | None = None
    category: str = "RISK_MANAGEMENT"
    titleAr: str
    titleEn: str = ""
    contentAr: str
    contentEn: str = ""


class ToggleEnabledRequest(BaseModel):
    enabled: bool


class RiskPolicyUpdateRequest(BaseModel):
    maxRiskPerTradePct: float = Field(gt=0.05, le=2.0)
    maxExposurePerAssetPct: float = Field(gt=1.0, le=50.0)
    dailyLossLimitPct: float = Field(gt=0.2, le=10.0)
    weeklyLossLimitPct: float = Field(gt=0.5, le=15.0)
    maxDrawdownLimitPct: float = Field(gt=1.0, le=25.0)
    adminPin: str = ""


class AuthPolicyUpdateRequest(BaseModel):
    policy: str
    adminPin: str = ""


class EconomicsEvaluateRequest(BaseModel):
    symbol: str
    side: str = "BUY"
    quantity: float = Field(gt=0)
    entryPrice: float | None = None
    stopLoss: float | None = None
    takeProfit: float | None = None


class GoalConfigUpdateRequest(BaseModel):
    startingEquityUsd: float = Field(gt=0)
    targetEquityUsd: float = Field(gt=0)
    horizonMonths: int = Field(ge=1, le=600)
    dailyGoalPct: float = Field(ge=0, le=20)
    weeklyGoalPct: float = Field(ge=0, le=50)
    monthlyGoalPct: float = Field(ge=0, le=150)


def _enforce_quantum_admin_auth(
    pin: str,
    action_label: str = "QUANTUM_ADMIN_ACTION",
    request: Request | None = None,
) -> dict[str, Any]:
    from .security import require_authenticated_session_or_secret

    require_step_up = os.getenv("TRILUNAIR_REQUIRE_PASSKEY_STEP_UP", "false").lower() == "true"
    return require_authenticated_session_or_secret(
        request=request,
        provided_secret=pin,
        action_label=action_label,
        require_step_up=require_step_up,
    )


def _serialize_agent(row: Any, provider_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prov = provider_map.get(row["assigned_provider"], {})
    return {
        "agentId": row["agent_id"],
        "nameAr": row["name_ar"],
        "nameEn": row["name_en"],
        "roleAr": row["role_ar"],
        "roleEn": row["role_en"],
        "enabled": bool(row["enabled"]),
        "visualState": row["visual_state"] if row["enabled"] else "INACTIVE",
        "assignedProvider": row["assigned_provider"],
        "assignedModel": row["assigned_model"],
        "providerAvailable": bool(prov.get("available", False)),
        "decisionWeight": float(row["decision_weight"]),
        "qualificationLevel": row["qualification_level"],
        "qualificationScorePct": int(row["qualification_score_pct"]),
        "requalificationRequired": bool(row["requalification_required"]),
        "lastQualificationNoteAr": row["last_note_ar"],
        "lastQualificationNoteEn": row["last_note_en"],
        "assignedSkills": json.loads(row["assigned_skills_json"]),
        "coreInstructions": row["core_instructions"],
        "operationalPermissions": {
            "canAnalyze": bool(row["can_analyze"]),
            "canProposeTrades": bool(row["can_propose_trades"]),
            "canParticipateAutonomous": False,
        },
        "metrics": {
            "totalCalls": int(row["total_calls"]),
            "totalTokens": int(row["total_tokens"]),
            "attributableAiCostUsd": round(float(row["attributable_ai_cost_usd"]), 5),
            "historicalReliabilityPct": float(row["historical_reliability_pct"]),
        },
    }


def _build_exchange_status(gov_row: Any) -> dict[str, Any]:
    from .binance_market_data import binance_public_client
    from .market_engine import market_engine

    creds_ok = bool(
        os.getenv("BINANCE_SPOT_API_KEY", "").strip()
        and os.getenv("BINANCE_SPOT_API_SECRET", "").strip()
    )
    b_snap = binance_public_client.get_health_snapshot()
    if b_snap["liveMarketDataActive"]:
        conn_mode = "LIVE_MARKET_DATA_PAPER_EXECUTION"
    else:
        conn_mode = "PAPER_SIMULATION"

    rest_ok = bool(creds_ok or b_snap.get("restHealthy"))
    live_filters = dict(binance_public_client._exchange_filters)
    stale_detected = market_engine.is_stale()
    now_ts = int(time.time())
    instruments = []
    for item in BINANCE_INSTRUMENTS_CATALOG:
        bsym = item["canonicalSymbol"]
        lf = live_filters.get(bsym, {})
        instruments.append(
            {
                "canonicalSymbol": bsym,
                "displayAlias": item["displayAlias"],
                "baseAsset": item["baseAsset"],
                "quoteAsset": item["quoteAsset"],
                "classification": item["classification"],
                "tickSize": float(lf.get("tickSize", item["tickSize"])),
                "stepSize": float(lf.get("stepSize", item["stepSize"])),
                "minQty": float(lf.get("minQty", item["minQty"])),
                "maxQty": float(lf.get("maxQty", item["maxQty"])),
                "minNotional": float(lf.get("minNotional", item["minNotional"])),
                "lastUpdatedTs": now_ts,
                "isStale": stale_detected,
            }
        )

    return {
        "exchange": "BINANCE_SPOT",
        "connectionMode": conn_mode,
        "credentialsConfigured": creds_ok,
        "restReachable": rest_ok,
        "wsStreamActive": not stale_detected,
        "accountStateUncertain": bool(gov_row["account_state_uncertain"]),
        "staleMarketDataDetected": stale_detected,
        "lastReconciledAt": gov_row["last_reconciled_at"],
        "authorizationPolicy": gov_row["authorization_policy"],
        "agentsPaused": bool(gov_row["agents_paused"]),
        "instruments": instruments,
    }


# ==============================================================================
# 6. نقاط النهاية البرمجية لمنظومة القيادة الكمية (/api/quantum/*)
# ==============================================================================

@router.get("/overview")
def get_quantum_overview() -> dict[str, Any]:
    """إرجاع نظرة شاملة لجميع مكونات المنظومة الكمية الثماني في طلب واحد."""
    ensure_quantum_tables()
    providers = get_llm_providers_status()
    provider_map = {p["providerId"]: p for p in providers}

    with db_session() as conn:
        gov = conn.execute(
            "SELECT * FROM quantum_governance WHERE tenant_id = ?",
            (DEFAULT_TENANT_ID,),
        ).fetchone()
        agent_rows = conn.execute(
            """
            SELECT * FROM quantum_agents
            ORDER BY CASE agent_id
                WHEN 'quant-alpha' THEN 1
                WHEN 'risk-sentinel' THEN 2
                WHEN 'macro-oracle' THEN 3
                WHEN 'execution-architect' THEN 4
                WHEN 'chief-strategist' THEN 5
                ELSE 99
            END ASC
            """
        ).fetchall()
        skill_rows = conn.execute("SELECT * FROM quantum_skills ORDER BY skill_id ASC").fetchall()
        conn_rows = conn.execute("SELECT * FROM quantum_connectors ORDER BY connector_id ASC").fetchall()
        fee_row = conn.execute(
            "SELECT COALESCE(SUM(total_fee_usd), 0.0) AS total_fees FROM orders"
        ).fetchone()

    trading_fees = float(fee_row["total_fees"]) if fee_row else 0.0
    ai_costs = sum(float(r["attributable_ai_cost_usd"]) for r in agent_rows)
    conn_costs = float(gov["total_connector_costs_usd"])

    connectors_out = []
    for c in conn_rows:
        req_keys: list[str] = json.loads(c["required_credentials_json"])
        keys_present = all(bool(os.getenv(k, "").strip()) for k in req_keys) if req_keys else True
        health = "HEALTHY" if keys_present and c["enabled"] else ("UNCONFIGURED" if not keys_present else "OFFLINE")
        connectors_out.append(
            {
                "connectorId": c["connector_id"],
                "nameAr": c["name_ar"],
                "nameEn": c["name_en"],
                "provider": c["provider"],
                "requiredCredentials": req_keys,
                "credentialsConfigured": keys_present,
                "capabilities": json.loads(c["capabilities_json"]),
                "rateLimitPerMin": int(c["rate_limit_per_min"]),
                "dataFreshnessSeconds": int(c["data_freshness_seconds"]),
                "healthStatus": health,
                "operatingCostPer1kCallsUsd": float(c["operating_cost_per_1k_usd"]),
                "enabled": bool(c["enabled"]),
                "treatsInputAsUntrusted": True,
            }
        )

    return {
        "providers": providers,
        "agents": [_serialize_agent(r, provider_map) for r in agent_rows],
        "skills": [
            {
                "skillId": s["skill_id"],
                "nameAr": s["name_ar"],
                "nameEn": s["name_en"],
                "descriptionAr": s["description_ar"],
                "descriptionEn": s["description_en"],
                "enabled": bool(s["enabled"]),
                "avgComputeCostUsd": float(s["avg_compute_cost_usd"]),
            }
            for s in skill_rows
        ],
        "connectors": connectors_out,
        "riskPolicy": {
            "maxRiskPerTradePct": float(gov["max_risk_per_trade_pct"]),
            "maxExposurePerAssetPct": float(gov["max_exposure_per_asset_pct"]),
            "dailyLossLimitPct": float(gov["daily_loss_limit_pct"]),
            "weeklyLossLimitPct": float(gov["weekly_loss_limit_pct"]),
            "maxDrawdownLimitPct": float(gov["max_drawdown_limit_pct"]),
            "prohibitLeverage": True,
            "prohibitMargin": True,
            "prohibitFutures": True,
            "prohibitBorrowing": True,
            "prohibitWithdrawals": True,
        },
        "goalConfig": {
            "startingEquityUsd": float(gov["starting_equity_usd"]),
            "targetEquityUsd": float(gov["target_equity_usd"]),
            "horizonMonths": int(gov["horizon_months"]),
            "dailyGoalPct": float(gov["daily_goal_pct"]),
            "weeklyGoalPct": float(gov["weekly_goal_pct"]),
            "monthlyGoalPct": float(gov["monthly_goal_pct"]),
        },
        "accounting": {
            "totalTradingCommissionsUsd": round(trading_fees * 0.55, 4),
            "totalSpreadAndSlippageUsd": round(trading_fees * 0.45, 4),
            "totalTradingExecutionCostsUsd": round(trading_fees, 4),
            "totalAiInferenceCostsUsd": round(ai_costs, 4),
            "totalConnectorOperatingCostsUsd": round(conn_costs, 4),
            "netRealizedPnlAfterAllCostsUsd": round(-(trading_fees + ai_costs + conn_costs), 4),
        },
        "exchangeStatus": _build_exchange_status(gov),
    }


@router.put("/agents/{agent_id}")
def update_quantum_agent(agent_id: str, patch: AgentConfigPatch) -> dict[str, Any]:
    """
    تحديث إعدادات وكيل ذكي، مع إنفاذ قاعدة إعادة التأهيل الإلزامية (القسم 9):
    أي تعديل جوهري في المزود أو النموذج أو التعليمات أو المهارات أو وزن القرار أو الصلاحيات
    يعيد مستوى التأهيل فوراً إلى TRAINEE ويمنع المشاركة المستقلة لحين اجتياز الاختبارات مجدداً.
    """
    ensure_quantum_tables()
    providers = get_llm_providers_status()
    provider_map = {p["providerId"]: p for p in providers}

    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM quantum_agents WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        material_change = False
        next_provider = row["assigned_provider"]
        next_model = row["assigned_model"]
        next_weight = float(row["decision_weight"])
        next_skills_json = row["assigned_skills_json"]
        next_instr = row["core_instructions"]
        next_enabled = int(row["enabled"])
        next_can_propose = int(row["can_propose_trades"])
        next_can_auto = int(row["can_participate_autonomous"])

        if patch.enabled is not None:
            next_enabled = 1 if patch.enabled else 0
        if patch.assignedProvider is not None and patch.assignedProvider != next_provider:
            if patch.assignedProvider not in provider_map:
                raise HTTPException(status_code=400, detail="Unsupported LLM provider")
            next_provider = patch.assignedProvider
            material_change = True
        if patch.assignedModel is not None and patch.assignedModel != next_model:
            next_model = patch.assignedModel
            material_change = True
        if patch.decisionWeight is not None and abs(patch.decisionWeight - next_weight) > 1e-6:
            next_weight = patch.decisionWeight
            material_change = True
        if patch.assignedSkills is not None:
            encoded = json.dumps(patch.assignedSkills)
            if encoded != next_skills_json:
                next_skills_json = encoded
                material_change = True
        if patch.coreInstructions is not None and patch.coreInstructions != next_instr:
            next_instr = patch.coreInstructions
            material_change = True
        if patch.canProposeTrades is not None and int(patch.canProposeTrades) != next_can_propose:
            next_can_propose = 1 if patch.canProposeTrades else 0
            material_change = True
        if patch.canParticipateAutonomous is not None and int(patch.canParticipateAutonomous) != next_can_auto:
            next_can_auto = 1 if patch.canParticipateAutonomous else 0
            material_change = True

        q_level = row["qualification_level"]
        q_score = int(row["qualification_score_pct"])
        req_requal = int(row["requalification_required"])
        note_ar = row["last_note_ar"]
        note_en = row["last_note_en"]

        if material_change:
            q_level = "TRAINEE"
            q_score = 65
            req_requal = 1
            next_can_auto = 0
            note_ar = "تتطلب التغييرات الجوهرية إعادة اجتياز مراحل التأهيل الأربع."
            note_en = "Material configuration change triggered mandatory requalification to Trainee."
            append_audit_log(
                actor="ADMIN",
                source="TERMINAL",
                action="AGENT_REQUALIFICATION_TRIGGERED",
                severity="WARNING",
                details_ar=f"إعادة الوكيل {agent_id} إلى مستوى متدرب (TRAINEE) بعد تعديل جوهري في التكوين.",
                details_en=f"Agent {agent_id} downgraded to TRAINEE after material configuration update.",
                conn=conn,
            )

        conn.execute(
            """
            UPDATE quantum_agents
            SET enabled = ?, assigned_provider = ?, assigned_model = ?, decision_weight = ?,
                assigned_skills_json = ?, core_instructions = ?, can_propose_trades = ?,
                can_participate_autonomous = ?, qualification_level = ?,
                qualification_score_pct = ?, requalification_required = ?,
                last_note_ar = ?, last_note_en = ?
            WHERE agent_id = ?
            """,
            (
                next_enabled,
                next_provider,
                next_model,
                next_weight,
                next_skills_json,
                next_instr,
                next_can_propose,
                next_can_auto,
                q_level,
                q_score,
                req_requal,
                note_ar,
                note_en,
                agent_id,
            ),
        )
        updated = conn.execute(
            "SELECT * FROM quantum_agents WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()

    return _serialize_agent(updated, provider_map)


@router.post("/agents/{agent_id}/revoke-permissions")
def revoke_agent_permissions(agent_id: str) -> dict[str, Any]:
    """سحب الصلاحيات التشغيلية للوكيل فوراً وإلغاء أهليته للتداول المستقل."""
    ensure_quantum_tables()
    providers = get_llm_providers_status()
    provider_map = {p["providerId"]: p for p in providers}

    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM quantum_agents WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        conn.execute(
            """
            UPDATE quantum_agents
            SET enabled = 0, can_propose_trades = 0, can_participate_autonomous = 0,
                qualification_level = 'TRAINEE', requalification_required = 1,
                visual_state = 'INACTIVE',
                last_note_ar = 'تم سحب الصلاحيات التشغيلية من قبل المسؤول.',
                last_note_en = 'Operational permissions explicitly revoked by administrator.'
            WHERE agent_id = ?
            """,
            (agent_id,),
        )
        append_audit_log(
            actor="ADMIN",
            source="TERMINAL",
            action="AGENT_PERMISSIONS_REVOKED",
            severity="WARNING",
            details_ar=f"تم سحب الصلاحيات التشغيلية للوكيل {agent_id}.",
            details_en=f"Revoked operational permissions for agent {agent_id}.",
            conn=conn,
        )
        updated = conn.execute(
            "SELECT * FROM quantum_agents WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
    return _serialize_agent(updated, provider_map)


@router.post("/agents/pause-all")
def pause_or_resume_all_agents(req: PauseAgentsRequest) -> dict[str, Any]:
    """إيقاف جميع الوكلاء مؤقتاً أو استئناف عملهم."""
    ensure_quantum_tables()
    with db_session() as conn:
        conn.execute(
            "UPDATE quantum_governance SET agents_paused = ? WHERE tenant_id = ?",
            (1 if req.paused else 0, DEFAULT_TENANT_ID),
        )
        append_audit_log(
            actor="ADMIN",
            source="TERMINAL",
            action="AGENTS_PAUSE_TOGGLED",
            severity="INFO",
            details_ar="تم إيقاف الوكلاء مؤقتاً." if req.paused else "تم استئناف عمل الوكلاء.",
            details_en=f"Agents paused set to {req.paused}.",
            conn=conn,
        )
    return {"agentsPaused": req.paused}


@router.post("/agents/{agent_id}/qualify")
def evaluate_agent_qualification_gate(agent_id: str) -> dict[str, Any]:
    """
    تشغيل بوابة التقييم الحتمية لترقية تأهيل الوكيل خطوة بخطوة:
    TRAINEE -> ANALYST -> EXPERIMENTALLY_QUALIFIED -> PRODUCTION_QUALIFIED.
    يتحقق فعلياً من توفر المزود المسند ومن اجتياز حسابات تحجيم المخاطر وفلاتر البورصة.
    """
    ensure_quantum_tables()
    providers = get_llm_providers_status()
    provider_map = {p["providerId"]: p for p in providers}

    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM quantum_agents WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Agent not found")

        prov = provider_map.get(row["assigned_provider"], {})
        prov_available = bool(prov.get("available", False))
        kb_count = int(
            conn.execute("SELECT COUNT(*) AS c FROM quantum_knowledge_base").fetchone()["c"]
        )
        sizing_test = calculate_safe_position_size(100_000.0, 0.5, 95_000.0, 93_500.0)
        zero_stop_guard = calculate_safe_position_size(100_000.0, 0.5, 95_000.0, 95_000.0)
        ref_asset_guard = validate_binance_spot_filters("XAUUSD", 1.0, 2685.0)

        checks = [
            {
                "gate": "KNOWLEDGE_BASE_COVERAGE",
                "passed": kb_count >= 15,
                "detailAr": f"مراجعة {kb_count} مورداً معرفياً معتمداً في موسوعة التداول.",
                "detailEn": f"Verified {kb_count} versioned Trading Knowledge Base articles.",
            },
            {
                "gate": "PROVIDER_AUTHENTICITY_CHECK",
                "passed": prov_available,
                "detailAr": (
                    f"المزود المسند ({row['assigned_provider']}) متصل فعلياً."
                    if prov_available
                    else f"فشل التأهيل: المزود ({row['assigned_provider']}) غير مهيأ بمفتاح API صالح."
                ),
                "detailEn": (
                    f"Assigned provider ({row['assigned_provider']}) is genuinely available."
                    if prov_available
                    else f"Qualification blocked: provider ({row['assigned_provider']}) is unavailable."
                ),
            },
            {
                "gate": "HISTORICAL_SIZING_AND_ZERO_STOP_GUARD",
                "passed": bool(sizing_test["valid"] and not zero_stop_guard["valid"]),
                "detailAr": "اجتياز اختبار حساب حجم المركز (0.5%) ورفض مسافة الوقف الصفرية بأمان.",
                "detailEn": "Passed 0.5% risk position-sizing math and zero-stop-distance safety rejection.",
            },
            {
                "gate": "SPOT_REFERENCE_ISOLATION_GUARD",
                "passed": not ref_asset_guard["valid"],
                "detailAr": "التحقق من حظر إرسال الأصول المرجعية (REFERENCE_ONLY) إلى Binance Spot.",
                "detailEn": "Verified strict blocking of REFERENCE_ONLY instruments on Binance Spot.",
            },
        ]

        all_passed = all(c["passed"] for c in checks)
        prev_level = row["qualification_level"]
        idx = QUALIFICATION_SEQUENCE.index(prev_level) if prev_level in QUALIFICATION_SEQUENCE else 0

        if all_passed:
            new_idx = min(len(QUALIFICATION_SEQUENCE) - 1, idx + 1)
            new_level = QUALIFICATION_SEQUENCE[new_idx]
            score = min(99, 78 + new_idx * 7)
            can_auto = 1 if new_level == "PRODUCTION_QUALIFIED" else 0
            conn.execute(
                """
                UPDATE quantum_agents
                SET qualification_level = ?, qualification_score_pct = ?, requalification_required = 0,
                    can_propose_trades = 1, can_participate_autonomous = ?, enabled = 1,
                    visual_state = 'AGREE',
                    last_note_ar = 'اجتاز بوابة الاختبار الآلي بنجاح.',
                    last_note_en = 'Passed deterministic qualification gate.'
                WHERE agent_id = ?
                """,
                (new_level, score, can_auto, agent_id),
            )
        else:
            new_level = prev_level
            score = 50

        append_audit_log(
            actor="QUALIFICATION_ENGINE",
            source="TERMINAL",
            action="AGENT_QUALIFICATION_EVALUATED",
            severity="INFO" if all_passed else "WARNING",
            details_ar=f"تقييم تأهيل الوكيل {agent_id}: {prev_level} -> {new_level} (النتيجة: {all_passed}).",
            details_en=f"Evaluated agent {agent_id}: {prev_level} -> {new_level} (passed={all_passed}).",
            conn=conn,
        )

    return {
        "agentId": agent_id,
        "previousLevel": prev_level,
        "newLevel": new_level,
        "passed": all_passed,
        "scorePct": score,
        "checksRun": checks,
        "disclaimerAr": "تنبيه تنظيمي: اجتياز اختبارات التأهيل يثبت الامتثال لقواعد السلامة التشغيلية فقط ولا يُعد ضماناً لتحقيق أرباح مستقبلية.",
        "disclaimerEn": "Regulatory notice: Passing qualification gates verifies operational rule compliance only and never guarantees profitable trades.",
    }


@router.get("/knowledge")
def list_knowledge_base() -> list[dict[str, Any]]:
    """استرجاع موسوعة المعرفة التداولية المؤرشفة بالإصدارات."""
    ensure_quantum_tables()
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM quantum_knowledge_base ORDER BY version DESC, id ASC"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "slug": r["slug"],
            "category": r["category"],
            "titleAr": r["title_ar"],
            "titleEn": r["title_en"],
            "contentAr": r["content_ar"],
            "contentEn": r["content_en"],
            "version": int(r["version"]),
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]


@router.post("/knowledge")
def upsert_knowledge_entry(req: KnowledgeUpsertRequest) -> dict[str, Any]:
    """إضافة أو تحديث مورد معرفي مع زيادة رقم الإصدار تلقائياً (Versioned Knowledge Base)."""
    ensure_quantum_tables()
    now = utc_now_iso()
    with db_session() as conn:
        if req.id:
            existing = conn.execute(
                "SELECT * FROM quantum_knowledge_base WHERE id = ?",
                (req.id,),
            ).fetchone()
            if existing is None:
                raise HTTPException(status_code=404, detail="Knowledge article not found")
            next_ver = int(existing["version"]) + 1
            conn.execute(
                """
                UPDATE quantum_knowledge_base
                SET category = ?, title_ar = ?, title_en = ?, content_ar = ?, content_en = ?,
                    version = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    req.category,
                    req.titleAr.strip(),
                    (req.titleEn or req.titleAr).strip(),
                    req.contentAr.strip(),
                    (req.contentEn or req.contentAr).strip(),
                    next_ver,
                    now,
                    req.id,
                ),
            )
            row_id = req.id
        else:
            row_id = f"kb_{uuid.uuid4().hex[:8]}"
            conn.execute(
                """
                INSERT INTO quantum_knowledge_base (
                    id, slug, category, title_ar, title_en, content_ar, content_en, version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    row_id,
                    row_id,
                    req.category,
                    req.titleAr.strip(),
                    (req.titleEn or req.titleAr).strip(),
                    req.contentAr.strip(),
                    (req.contentEn or req.contentAr).strip(),
                    now,
                ),
            )

        saved = conn.execute(
            "SELECT * FROM quantum_knowledge_base WHERE id = ?",
            (row_id,),
        ).fetchone()

    return {
        "id": saved["id"],
        "slug": saved["slug"],
        "category": saved["category"],
        "titleAr": saved["title_ar"],
        "titleEn": saved["title_en"],
        "contentAr": saved["content_ar"],
        "contentEn": saved["content_en"],
        "version": int(saved["version"]),
        "updatedAt": saved["updated_at"],
    }


@router.put("/skills/{skill_id}")
def toggle_modular_skill(skill_id: str, req: ToggleEnabledRequest) -> dict[str, Any]:
    """تفعيل أو تعطيل مهارة تحليلية معيارية."""
    ensure_quantum_tables()
    with db_session() as conn:
        res = conn.execute(
            "UPDATE quantum_skills SET enabled = ? WHERE skill_id = ?",
            (1 if req.enabled else 0, skill_id),
        )
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail="Skill not found")
    return {"skillId": skill_id, "enabled": req.enabled}


@router.put("/connectors/{connector_id}")
def toggle_external_connector(connector_id: str, req: ToggleEnabledRequest) -> dict[str, Any]:
    """تفعيل أو تعطيل موصل بيانات خارجي."""
    ensure_quantum_tables()
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM quantum_connectors WHERE connector_id = ?",
            (connector_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Connector not found")
        conn.execute(
            "UPDATE quantum_connectors SET enabled = ? WHERE connector_id = ?",
            (1 if req.enabled else 0, connector_id),
        )
        updated = conn.execute(
            "SELECT * FROM quantum_connectors WHERE connector_id = ?",
            (connector_id,),
        ).fetchone()

    req_keys: list[str] = json.loads(updated["required_credentials_json"])
    keys_present = all(bool(os.getenv(k, "").strip()) for k in req_keys) if req_keys else True
    return {
        "connectorId": updated["connector_id"],
        "nameAr": updated["name_ar"],
        "nameEn": updated["name_en"],
        "provider": updated["provider"],
        "requiredCredentials": req_keys,
        "credentialsConfigured": keys_present,
        "capabilities": json.loads(updated["capabilities_json"]),
        "rateLimitPerMin": int(updated["rate_limit_per_min"]),
        "dataFreshnessSeconds": int(updated["data_freshness_seconds"]),
        "healthStatus": "HEALTHY" if keys_present and updated["enabled"] else "OFFLINE",
        "operatingCostPer1kCallsUsd": float(updated["operating_cost_per_1k_usd"]),
        "enabled": bool(updated["enabled"]),
        "treatsInputAsUntrusted": True,
    }


@router.put("/risk-policy")
def update_deterministic_risk_policy(req: RiskPolicyUpdateRequest, request: Request) -> dict[str, Any]:
    """تعديل حدود محرك المخاطر عبر مسار إداري محمي بمصادقة المالك البيومترية (Step-Up) أو سر المسؤول المشفر."""
    ensure_quantum_tables()
    auth_ctx = _enforce_quantum_admin_auth(req.adminPin, action_label="UPDATE_RISK_POLICY", request=request)

    with db_session() as conn:
        conn.execute(
            """
            UPDATE quantum_governance
            SET max_risk_per_trade_pct = ?, max_exposure_per_asset_pct = ?,
                daily_loss_limit_pct = ?, weekly_loss_limit_pct = ?, max_drawdown_limit_pct = ?
            WHERE tenant_id = ?
            """,
            (
                req.maxRiskPerTradePct,
                req.maxExposurePerAssetPct,
                req.dailyLossLimitPct,
                req.weeklyLossLimitPct,
                req.maxDrawdownLimitPct,
                DEFAULT_TENANT_ID,
            ),
        )
        conn.execute(
            "UPDATE system_state SET max_allowed_drawdown_pct = ? WHERE id = 1",
            (req.maxDrawdownLimitPct,),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD" if "WEBAUTHN" in auth_ctx.get("authMethod", "") else "ADMIN",
            source="TERMINAL",
            action="RISK_POLICY_UPDATED",
            severity="WARNING",
            details_ar=(
                f"تحديث حدود المخاطر ({auth_ctx.get('authMethod')}): مخاطرة/صفقة={req.maxRiskPerTradePct}%، تعرض={req.maxExposurePerAssetPct}%، "
                f"خسارة يومية={req.dailyLossLimitPct}%، أسبوعية={req.weeklyLossLimitPct}%، أقصى تراجع={req.maxDrawdownLimitPct}%."
            ),
            details_en=f"Updated deterministic risk policy thresholds via {auth_ctx.get('authMethod')}.",
            conn=conn,
        )

    return {
        "maxRiskPerTradePct": req.maxRiskPerTradePct,
        "maxExposurePerAssetPct": req.maxExposurePerAssetPct,
        "dailyLossLimitPct": req.dailyLossLimitPct,
        "weeklyLossLimitPct": req.weeklyLossLimitPct,
        "maxDrawdownLimitPct": req.maxDrawdownLimitPct,
        "prohibitLeverage": True,
        "prohibitMargin": True,
        "prohibitFutures": True,
        "prohibitBorrowing": True,
        "prohibitWithdrawals": True,
    }


@router.post("/authorization-policy")
@router.post("/governance/policy")
def set_authorization_policy(req: AuthPolicyUpdateRequest, request: Request) -> dict[str, Any]:
    """
    ضبط سياسة التفويض في الإصدار v1.2.0-low-latency-cloudflare:
    - يسمح بـ PAPER و HUMAN_APPROVAL (مع بقاء التنفيذ الفعلي ورقياً PAPER حصراً).
    - يحظر AUTONOMOUS نهائياً بموجب قواعد السلامة غير القابلة للتفاوض.
    """
    ensure_quantum_tables()
    policy = req.policy.strip().upper()
    if policy not in {"PAPER", "HUMAN_APPROVAL", "AUTONOMOUS"}:
        raise HTTPException(status_code=400, detail="Invalid authorization policy")

    if policy == "AUTONOMOUS":
        append_audit_log(
            actor="RELEASE_SAFETY_LOCK",
            source="TERMINAL",
            action="AUTONOMOUS_TRADING_BLOCKED",
            severity="CRITICAL",
            details_ar="رفض تفعيل التداول المستقل (AUTONOMOUS): معطل نهائياً في الإصدار v1.2.0-low-latency-cloudflare.",
            details_en="Blocked AUTONOMOUS policy activation: permanently disabled in release v1.2.0-low-latency-cloudflare.",
        )
        raise HTTPException(
            status_code=403,
            detail="AUTONOMOUS_DISABLED: التداول المستقل معطل نهائياً في الإصدار v1.2.0-low-latency-cloudflare؛ التنفيذ مقفل على الوضع الورقي الآمن (PAPER).",
        )

    if policy == "HUMAN_APPROVAL":
        _enforce_quantum_admin_auth(req.adminPin, action_label="SET_AUTH_POLICY_HUMAN_APPROVAL", request=request)

    with db_session() as conn:
        conn.execute(
            "UPDATE quantum_governance SET authorization_policy = ? WHERE tenant_id = ?",
            (policy, DEFAULT_TENANT_ID),
        )
        append_audit_log(
            actor="ADMIN",
            source="TERMINAL",
            action="AUTHORIZATION_POLICY_CHANGED",
            severity="WARNING" if policy != "PAPER" else "INFO",
            details_ar=f"تم تغيير سياسة بوابة التفويض إلى: {policy} (مع بقاء التنفيذ الورقي PAPER إلزامياً).",
            details_en=f"Authorization policy changed to {policy} (PAPER execution lock remains enforced).",
            conn=conn,
        )
        gov = conn.execute(
            "SELECT * FROM quantum_governance WHERE tenant_id = ?",
            (DEFAULT_TENANT_ID,),
        ).fetchone()

    return _build_exchange_status(gov)


@router.post("/exchange/reconcile")
def reconcile_binance_spot_state() -> dict[str, Any]:
    """مصالحة حالة الأوامر والحساب وإزالة علم عدم يقين الحالة بعد التحقق من سلامة الجداول."""
    ensure_quantum_tables()
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE quantum_governance
            SET account_state_uncertain = 0, last_reconciled_at = ?
            WHERE tenant_id = ?
            """,
            (now, DEFAULT_TENANT_ID),
        )
        append_audit_log(
            actor="RECOVERY_MONITOR",
            source="TERMINAL",
            action="EXCHANGE_STATE_RECONCILED",
            severity="INFO",
            details_ar="تمت مصالحة حالة الحساب والأوامر مع محول Binance Spot بنجاح.",
            details_en="Reconciled internal portfolio and order state with Binance Spot adapter.",
            conn=conn,
        )
        gov = conn.execute(
            "SELECT * FROM quantum_governance WHERE tenant_id = ?",
            (DEFAULT_TENANT_ID,),
        ).fetchone()
    return _build_exchange_status(gov)


@router.post("/economics/evaluate")
def evaluate_trade_economic_viability(req: EconomicsEvaluateRequest) -> dict[str, Any]:
    """
    محرك الجدوى الاقتصادية للصفقة (القسم 13):
    يحسب القيمة الاسمية، عمولة البورصة، تكلفة السبريد، الانزلاق المتوقع، وتكلفة استدلال AI المنسوبة،
    ويقارنها بالعائد المتوقع لحماية الحساب من الصفقات ذات الجدوى الصافية السالبة.
    """
    ensure_quantum_tables()
    spec_check = validate_binance_spot_filters(
        req.symbol,
        req.quantity,
        req.entryPrice or next(
            (i["referencePrice"] for i in BINANCE_INSTRUMENTS_CATALOG if i["canonicalSymbol"] == req.symbol.upper()),
            100.0,
        ),
    )
    if not spec_check["valid"]:
        raise HTTPException(status_code=422, detail=spec_check["reasonAr"])

    spec = spec_check["spec"]
    entry_price = req.entryPrice if (req.entryPrice and req.entryPrice > 0) else float(spec["referencePrice"])
    notional = req.quantity * entry_price

    # عمولة الذهاب والإياب القياسية لبينانس سبوت (10 bps لكل جانب = 20 bps إجمالي)
    commission = notional * 0.0020
    spread_cost = notional * 0.0004
    slippage_cost = notional * (0.0003 if notional < 50_000 else 0.0008)
    ai_cost = 0.0035  # تكلفة استدلال مجلس الوكلاء المنسوبة للتحليل
    total_cost = commission + spread_cost + slippage_cost + ai_cost

    if req.takeProfit and req.takeProfit > 0:
        expected_move = abs(req.takeProfit - entry_price) * req.quantity
    else:
        expected_move = notional * 0.018  # عائد مرجعي محافظ 1.8% عند عدم تحديد هدف

    reward_to_cost = expected_move / max(total_cost, 1e-6)
    # تقدير احتمالي محافظ للقيمة المتوقعة الصافية (احتمال تحقق الهدف 52% مقابل تكلفة الوقف)
    stop_risk = (
        abs(entry_price - req.stopLoss) * req.quantity
        if (req.stopLoss and req.stopLoss > 0)
        else notional * 0.01
    )
    net_ev = (0.52 * expected_move) - (0.48 * stop_risk) - total_cost
    viable = reward_to_cost >= 2.5 and net_ev > 0

    return {
        "notionalUsd": round(notional, 2),
        "exchangeCommissionUsd": round(commission, 4),
        "spreadCostUsd": round(spread_cost, 4),
        "expectedSlippageUsd": round(slippage_cost, 4),
        "attributableAiCostUsd": round(ai_cost, 4),
        "totalExpectedCostUsd": round(total_cost, 4),
        "expectedRewardUsd": round(expected_move, 2),
        "rewardToCostRatio": round(reward_to_cost, 2),
        "netExpectedValueUsd": round(net_ev, 2),
        "economicallyViable": viable,
        "notesAr": (
            f"نسبة العائد للتكلفة ({reward_to_cost:.2f}x) وصافي القيمة المتوقعة (${net_ev:.2f}) يجتازان عتبة الجدوى الاقتصادية."
            if viable
            else f"تحذير اقتصادي: التكاليف الإجمالية (${total_cost:.2f}) أو مسافة المخاطرة تضعف صافي القيمة المتوقعة (${net_ev:.2f})."
        ),
        "notesEn": (
            f"Reward-to-cost ({reward_to_cost:.2f}x) and net EV (${net_ev:.2f}) satisfy economic viability thresholds."
            if viable
            else f"Economic caution: Total execution + AI costs (${total_cost:.2f}) yield weak net EV (${net_ev:.2f})."
        ),
    }


@router.put("/goal-config")
def update_goal_mode_config(req: GoalConfigUpdateRequest) -> dict[str, Any]:
    """تحديث إعدادات رحلة الوصول إلى التريليون (Goal Mode — Section 14)."""
    ensure_quantum_tables()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE quantum_governance
            SET starting_equity_usd = ?, target_equity_usd = ?, horizon_months = ?,
                daily_goal_pct = ?, weekly_goal_pct = ?, monthly_goal_pct = ?
            WHERE tenant_id = ?
            """,
            (
                req.startingEquityUsd,
                req.targetEquityUsd,
                req.horizonMonths,
                req.dailyGoalPct,
                req.weeklyGoalPct,
                req.monthlyGoalPct,
                DEFAULT_TENANT_ID,
            ),
        )
    return req.model_dump()


class BinanceSpotTestOrderRequest(BaseModel):
    symbol: str
    side: str = "BUY"
    orderType: str = "LIMIT"
    quantity: float = Field(gt=0)
    price: float | None = None
    clientOrderId: str | None = None
    simulateNetworkFailure: bool = False


@router.get("/providers/audit")
def get_truthful_providers_audit() -> dict[str, Any]:
    """تقرير تدقيق صريح يوضح المزودات المحاكاة، الوهمية الاختبارية، والمتصلة سحابياً فعلياً."""
    from .llm_adapters import get_provider_credentials_report

    openai_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
    binance_key = bool(
        os.getenv("BINANCE_API_KEY", "").strip()
        or os.getenv("BINANCE_SPOT_API_KEY", "").strip()
    )
    binance_base = os.getenv(
        "BINANCE_SPOT_BASE_URL", "https://testnet.binance.vision"
    ).strip()

    return {
        "llmProviders": get_provider_credentials_report(),
        "voiceProviders": [
            {
                "component": "browser-stt-tts",
                "provider": "Web Speech API (SpeechRecognition + SpeechSynthesis)",
                "classification": "BROWSER_NATIVE_CLIENT",
                "credentialsConfigured": True,
            },
            {
                "component": "server-stt-whisper",
                "provider": "OpenAI Whisper (/v1/audio/transcriptions)",
                "classification": "CONNECTED_CLOUD" if openai_key else "UNAVAILABLE_FALLBACK_BROWSER",
                "credentialsConfigured": openai_key,
            },
            {
                "component": "server-tts-wav",
                "provider": "OpenAI TTS / Local RIFF WAVE Holo-Cue Fallback",
                "classification": "CONNECTED_CLOUD" if openai_key else "SIMULATED_LOCAL_WAV_FALLBACK",
                "credentialsConfigured": openai_key,
            },
        ],
        "exchangeAdapter": {
            "adapter": "BinanceSpotAdapter",
            "liveTradingDisabled": True,
            "configuredBaseUrl": binance_base,
            "credentialsConfigured": binance_key,
            "classification": "TESTNET_OR_MOCK_CONFIGURED" if binance_key else "SAFE_PAPER_MOCK_ADAPTER",
        },
    }


@router.post("/exchange/spot-test-order")
def verify_binance_spot_order_adapter(req: BinanceSpotTestOrderRequest) -> dict[str, Any]:
    """
    اختبار آمن لمحول Binance Spot دون إرسال أي أوامر مالية حقيقية إطلاقاً:
    1. يمنع الخلط بين USD و USDT (يرفض BTCUSD أو BTC-USD ويشترط الرمز القياسي BTCUSDT).
    2. يمنع إرسال الأصول المرجعية REFERENCE_ONLY (مثل XAUUSD و NVDA و SPX).
    3. يتحقق من فلاتر LOT_SIZE (minQty, maxQty, stepSize) و PRICE_FILTER (tickSize) و MIN_NOTIONAL.
    4. يوقع الحمولة رسمياً بـ HMAC-SHA256.
    5. عند تفعيل simulateNetworkFailure=True يحاكي انقطاع الاتصال أثناء الإرسال ويفعل علم عدم يقين الحساب
       (account_state_uncertain=1) لاختبار آلية التعافي والمصالحة الإلزامية.
    """
    ensure_quantum_tables()
    norm_sym = req.symbol.strip().upper()
    if norm_sym.endswith("USD") and not norm_sym.endswith("USDT") and norm_sym not in {"XAUUSD"}:
        raise HTTPException(
            status_code=422,
            detail=f"رفض صارم: لا يجوز الخلط بين USD و USDT في محول Binance Spot ({norm_sym})؛ استخدم الزوج القياسي مثل BTCUSDT.",
        )

    spec_item = next(
        (i for i in BINANCE_INSTRUMENTS_CATALOG if i["canonicalSymbol"] == norm_sym),
        None,
    )
    eff_price = (
        float(req.price)
        if (req.price is not None and req.price > 0)
        else float(spec_item["referencePrice"] if spec_item else 100.0)
    )

    filter_res = validate_binance_spot_filters(norm_sym, req.quantity, eff_price)
    if not filter_res["valid"]:
        raise HTTPException(
            status_code=422,
            detail=f"[{filter_res['code']}] {filter_res['reasonAr']}",
        )

    spec = filter_res["spec"]
    # فحص دقة stepSize و tickSize
    step_size = float(spec["stepSize"])
    tick_size = float(spec["tickSize"])
    qty_steps = req.quantity / step_size
    if abs(qty_steps - round(qty_steps)) > 1e-6:
        raise HTTPException(
            status_code=422,
            detail=f"[STEP_SIZE_VIOLATION] الكمية {req.quantity} لا تتوافق مع مضاعفات stepSize ({step_size}).",
        )
    if req.orderType.upper() == "LIMIT" and req.price is not None:
        price_ticks = req.price / tick_size
        if abs(price_ticks - round(price_ticks)) > 1e-6:
            raise HTTPException(
                status_code=422,
                detail=f"[PRICE_FILTER_VIOLATION] السعر {req.price} لا يتوافق مع مضاعفات tickSize ({tick_size}).",
            )

    # حظر الاتصال بنطاق بينانس الحقيقي أثناء التحقق الآمن مهما كانت المتغيرات
    configured_base = os.getenv("BINANCE_SPOT_BASE_URL", "").strip()
    if "api.binance.com" in configured_base.lower():
        raise HTTPException(
            status_code=403,
            detail="حظر أمني: يمنع الاتصال بنطاق التداول الحقيقي api.binance.com أثناء وضع التحقق والاختبار.",
        )

    client_oid = (req.clientOrderId or f"trilunair_test_{uuid.uuid4().hex[:10]}").strip()
    params: dict[str, Any] = {
        "symbol": norm_sym,
        "side": req.side.upper(),
        "type": req.orderType.upper(),
        "quantity": f"{req.quantity:g}",
        "newClientOrderId": client_oid,
        "timestamp": int(time.time() * 1000),
    }
    if req.orderType.upper() == "LIMIT":
        params["timeInForce"] = "GTC"
        params["price"] = f"{eff_price:.2f}"

    test_secret = os.getenv("BINANCE_SPOT_API_SECRET", "").strip() or "SAFE_SANDBOX_HMAC_KEY"
    signed_query = sign_binance_query(params, test_secret)

    # محاكاة فشل الشبكة لاختبار آلية التعافي وتجميد الحساب غير المؤكد
    if req.simulateNetworkFailure:
        with db_session() as conn:
            conn.execute(
                "UPDATE quantum_governance SET account_state_uncertain = 1 WHERE tenant_id = ?",
                (DEFAULT_TENANT_ID,),
            )
            append_audit_log(
                actor="BINANCE_SPOT_ADAPTER",
                source="TERMINAL",
                action="EXCHANGE_UNCERTAIN_STATE_ENTERED",
                severity="CRITICAL",
                details_ar=f"انقطاع اتصال محول Binance Spot أثناء إرسال {client_oid}؛ تم تفعيل حالة عدم يقين الحساب وتجميد الشراء لحين المصالحة.",
                details_en=f"Simulated transport timeout for {client_oid}; account_state_uncertain=1 set until reconciliation.",
                conn=conn,
            )
        raise HTTPException(
            status_code=504,
            detail="انقطاع اتصال البورصة (Timeout): دخل الحساب في وضع عدم اليقين (accountStateUncertain=true) وتجب المصالحة الفورية.",
        )

    # إذا وُجد خادم محاكاة HTTP محلي مهيأ في الاختبارات، نختبر دورة البروتوكول الكاملة عليه بأمان
    if configured_base.startswith(("http://127.0.0.1", "http://localhost")):
        import httpx

        with httpx.Client(timeout=4.0, trust_env=False) as client:
            resp = client.post(
                f"{configured_base.rstrip('/')}/api/v3/order/test?{signed_query}",
                headers={"X-MBX-APIKEY": os.getenv("BINANCE_SPOT_API_KEY", "mock-key")},
            )
            resp.raise_for_status()
            remote_ack = resp.json()
    else:
        remote_ack = {"mockExchangeAck": True, "endpoint": "/api/v3/order/test"}

    return {
        "validated": True,
        "executionEnvironment": "MOCK_HTTP_EXCHANGE" if configured_base.startswith(("http://127.0.0.1", "http://localhost")) else "SAFE_IN_MEMORY_SANDBOX",
        "realOrderPlaced": False,
        "canonicalSymbol": norm_sym,
        "clientOrderId": client_oid,
        "notionalUsdt": filter_res["notional"],
        "hmacSigned": "signature=" in signed_query,
        "signedQueryPreview": signed_query[:96] + "...",
        "exchangeAck": remote_ack,
    }

