"""
مجلس الوكلاء الخمسة المتخصصين وغرفة معالجة الأوامر الصوتية والنصية (AI Agents Council).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

يضم المجلس خمسة وكلاء متخصصين يعملون بتكامل حتمي مع محرك السوق ومحرك المخاطر:
1. quant-alpha (د. ريان — المحلل الكمي والزخم السعري)
2. risk-sentinel (سارة — حارسة المخاطر وحماية رأس المال)
3. macro-oracle (طارق — استراتيجي السيولة والاقتصاد الكلي)
4. execution-architect (خالد — مهندس التنفيذ وتكاليف الميكروستركشر)
5. chief-strategist (المجلس التنفيذي — كبير المستشارين لرحلة التريليون)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Final
import uuid

from fastapi import HTTPException
import httpx

from app.database import append_audit_log, db_session, utc_now_iso
from app.market_engine import market_engine
from app.models import (
    AgentDeliberationItem,
    AgentMeetingResult,
    AgentProfile,
    AgentStance,
    AiCommandRequest,
    AiCommandResponse,
    ChatMessageRecord,
    CommandSource,
    Language,
    MeetingConsensus,
    MeetingEvidenceAndUncertainty,
    MeetingFinalRecommendation,
    TradeProposalEvaluation,
    TradeProposalInput,
    UiCommandAction,
)
from app.safety_gateway import (
    DeterministicRiskEngine,
    get_portfolio_snapshot,
    get_system_status,
    propose_order,
)
from app.themes_service import apply_quick_theme_patch, get_custom_themes

AGENTS_REGISTRY: Final[list[AgentProfile]] = [
    AgentProfile(
        agentId="quant-alpha",
        nameAr="د. ريان — المحلل الكمي",
        nameEn="Dr. Rayan — Quant Alpha",
        roleAr="تحليل الزخم السعري والنماذج الإحصائية",
        roleEn="Quantitative Momentum & Statistical Signals",
        specialtyAr="تفكيك السلاسل الزمنية، مستويات الدعم والمقاومة، وكفاءة العائد للمخاطرة.",
        specialtyEn="Time-series decomposition, support/resistance geometry, and Sharpe dynamics.",
        status="ONLINE",
        accentToken="accentPrimary",
    ),
    AgentProfile(
        agentId="risk-sentinel",
        nameAr="سارة — حارسة المخاطر",
        nameEn="Sarah — Risk Sentinel",
        roleAr="حوكمة المخاطر والتركز وحماية رأس المال",
        roleEn="VaR Governance, Concentration & Drawdown Control",
        specialtyAr="مراقبة القيمة المعرضة للمخاطر (VaR 95%)، التراجع اليومي، ومنع التركز المفرط.",
        specialtyEn="Monitoring 95% VaR, daily drawdown caps, and position sizing discipline.",
        status="ONLINE",
        accentToken="danger",
    ),
    AgentProfile(
        agentId="macro-oracle",
        nameAr="طارق — استراتيجي السيولة والاقتصاد الكلي",
        nameEn="Tariq — Macro & Liquidity Oracle",
        roleAr="تحليل التدفقات المؤسسية والارتباطات الكلية",
        roleEn="Institutional Flows & Cross-Asset Macro Regime",
        specialtyAr="قراءة سيولة الأسواق العالمية، تحوط الذهب، ودورات قطاع الذكاء الاصطناعي والطاقة.",
        specialtyEn="Tracking global liquidity regimes, gold safe-haven flows, AI equities, and energy.",
        status="ONLINE",
        accentToken="accentTertiary",
    ),
    AgentProfile(
        agentId="execution-architect",
        nameAr="خالد — مهندس التنفيذ وتكاليف التداول",
        nameEn="Khalid — Execution Architect",
        roleAr="هندسة التنفيذ وتقليل السبريد والانزلاق السعري",
        roleEn="Orderbook Microstructure & Slippage Optimization",
        specialtyAr="تحليل عمق دفتر الأوامر وتقدير تكاليف التنفيذ بنقاط الأساس (bps) واختيار نوع الأمر.",
        specialtyEn="Orderbook depth imbalance analysis, bps cost minimization, and limit vs market routing.",
        status="ONLINE",
        accentToken="success",
    ),
    AgentProfile(
        agentId="chief-strategist",
        nameAr="المجلس التنفيذي — كبير المستشارين",
        nameEn="Chief Strategist — Executive Council",
        roleAr="التركيب التنفيذي والتوصية المجمعة لرحلة التريليون",
        roleEn="Executive Synthesis & Trilunair Capital Allocation",
        specialtyAr="الموازنة بين آراء الوكلاء الأربعة لإصدار توصية تنفيذية منضبطة تحمي المسار التراكمي.",
        specialtyEn="Synthesizing specialist views into an actionable, risk-governed allocation verdict.",
        status="ONLINE",
        accentToken="accentSecondary",
    ),
]

ARABIC_DIGITS_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")


def normalize_digits(text: str) -> str:
    """تحويل الأرقام العربية الشرقية والفواصل العشرية العربية إلى صيغة قياسية قابلة للتحليل."""
    return text.translate(ARABIC_DIGITS_MAP)


def get_agents() -> list[AgentProfile]:
    """استرجاع قائمة الوكلاء الخمسة المتخصصين وحالتهم التشغيلية."""
    return [a.model_copy(deep=True) for a in AGENTS_REGISTRY]


def get_chat_history(limit: int = 80) -> dict[str, Any]:
    """استرجاع سجل رسائل المحادثة وآخر اجتماع لمجلس الوكلاء من SQLite."""
    with db_session() as conn:
        msg_rows = conn.execute(
            "SELECT message_json FROM chat_messages ORDER BY seq ASC LIMIT ?",
            (limit,),
        ).fetchall()
        latest_meeting_row = conn.execute(
            "SELECT meeting_json FROM agent_meetings ORDER BY seq DESC LIMIT 1"
        ).fetchone()

    messages = [ChatMessageRecord(**json.loads(r["message_json"])) for r in msg_rows]
    latest_meeting = (
        AgentMeetingResult(**json.loads(latest_meeting_row["meeting_json"]))
        if latest_meeting_row
        else None
    )
    return {"messages": messages, "latestMeeting": latest_meeting}


def clear_chat_history() -> dict[str, bool]:
    """مسح سجل المحادثات عند طلب المستخدم مع الاحتفاظ بسجل التدقيق الأمني المستقل."""
    with db_session() as conn:
        conn.execute("DELETE FROM chat_messages")
        append_audit_log(
            actor="AI_COUNCIL",
            source="TERMINAL",
            action="CLEAR_CHAT_HISTORY",
            severity="INFO",
            details_ar="تم مسح سجل المحادثة في غرفة الأوامر بناءً على طلب المستخدم.",
            details_en="Cleared command room chat history upon user request.",
            conn=conn,
        )
    return {"cleared": True}


def convene_meeting(
    symbol: str,
    horizon: str = "1h",
    language: Language = "ar",
    topic_ar: str | None = None,
    topic_en: str | None = None,
    proposed_qty: float | None = None,
    proposed_side: str | None = None,
) -> AgentMeetingResult:
    """
    عقد اجتماع طاولة مستديرة كامل للوكلاء الخمسة حول أصل مالي محدد.
    يولّد مداخلات مستقلة لكل وكيل مع نقاط اتفاق واختلاف حقيقية مبنية على بيانات السوق والمحفظة،
    بالإضافة إلى حساب التكاليف وتقييم المخاطر عبر محرك المخاطر الحتمي.
    """
    canonical_symbol = market_engine.resolve_symbol(symbol)
    if not canonical_symbol:
        raise HTTPException(
            status_code=400,
            detail=f"رمز الأصل غير معروف لعقد الاجتماع: {symbol}",
        )

    asset = market_engine.get_asset(canonical_symbol)
    assert asset is not None
    tf = horizon if horizon in ("5m", "15m", "1h", "4h") else "1h"
    candles_data = market_engine.get_candles(canonical_symbol, timeframe=tf, limit=60)
    assert candles_data is not None

    portfolio = get_portfolio_snapshot()
    sys_status = get_system_status()

    # استخراج مؤشرات فنية وميكروستركشر حقيقية من الشموع ودفتر الأوامر
    closes = [c.close for c in candles_data.candles]
    sma20 = sum(closes[-20:]) / min(20, len(closes))
    trend_vs_sma_pct = round(((asset.price - sma20) / sma20) * 100.0, 2)
    dist_to_res_pct = round(
        ((candles_data.resistanceLevel - asset.price) / asset.price) * 100.0, 2
    )
    dist_to_sup_pct = round(
        ((asset.price - candles_data.supportLevel) / asset.price) * 100.0, 2
    )

    total_bid_depth = sum(b.size for b in candles_data.bids)
    total_ask_depth = max(1e-6, sum(a.size for a in candles_data.asks))
    ob_imbalance = round(total_bid_depth / total_ask_depth, 2)

    # تحديد حجم الصفقة المرجعي للفحص الحتمي (إما المقترح من المستخدم أو 2% معيارية من حقوق الملكية)
    default_notional = max(1000.0, portfolio.totalEquity * 0.02)
    decimals = 4 if asset.price > 1000 else (2 if asset.price > 50 else 0)
    benchmark_qty = round(default_notional / asset.price, decimals) or 1.0
    eval_qty = float(proposed_qty) if (proposed_qty and proposed_qty > 0) else benchmark_qty
    eval_side = (
        proposed_side
        if proposed_side in ("BUY", "SELL")
        else ("BUY" if asset.change24hPct >= -0.5 else "BUY")
    )

    sim_proposal = TradeProposalInput(
        symbol=asset.symbol,
        side=eval_side,  # type: ignore[arg-type]
        orderType="MARKET",
        quantity=eval_qty,
        source="TEXT",
        rationale="تقييم معياري لقاعة اجتماع الوكلاء",
    )
    _, estimated_costs, risk_assessment = DeterministicRiskEngine.evaluate(
        proposal=sim_proposal,
        asset=asset,
        portfolio=portfolio,
        kill_switch_active=sys_status.killSwitchActive,
    )

    # 1. مداخلة د. ريان (المحلل الكمي - Quant Alpha)
    sharpe_proxy = round(asset.change24hPct / max(0.4, asset.volatilityPct), 2)
    if asset.change24hPct >= 1.2 and trend_vs_sma_pct >= -0.5:
        quant_stance: AgentStance = "BUY"
        quant_conf = min(91, 72 + int(abs(sharpe_proxy) * 8))
        quant_status = "AGREE"
    elif asset.change24hPct <= -1.5:
        quant_stance = "SELL"
        quant_conf = 76
        quant_status = "DISSENT"
    else:
        quant_stance = "HOLD"
        quant_conf = 69
        quant_status = "READY"

    quant_item = AgentDeliberationItem(
        agentId="quant-alpha",
        nameAr="د. ريان — المحلل الكمي",
        nameEn="Dr. Rayan — Quant Alpha",
        roleAr="تحليل الزخم السعري والنماذج الإحصائية",
        roleEn="Quantitative Momentum & Statistical Signals",
        status=quant_status,  # type: ignore[arg-type]
        stance=quant_stance,
        confidence=quant_conf,
        summaryAr=(
            f"يتداول {asset.symbol} عند ${asset.price:,.2f} بتغير يومي {asset.change24hPct:+.2f}% "
            f"وانحراف {trend_vs_sma_pct:+.2f}% عن متوسط 20 شمعة ({tf}). الدعم عند ${candles_data.supportLevel:,.2f} "
            f"والمقاومة عند ${candles_data.resistanceLevel:,.2f} (هامش صعود {dist_to_res_pct:.2f}%)."
        ),
        summaryEn=(
            f"{asset.symbol} trades at ${asset.price:,.2f} ({asset.change24hPct:+.2f}% 24h) with "
            f"{trend_vs_sma_pct:+.2f}% deviation vs 20-period SMA ({tf}). Support sits at ${candles_data.supportLevel:,.2f} "
            f"and resistance at ${candles_data.resistanceLevel:,.2f} ({dist_to_res_pct:.2f}% upside room)."
        ),
        keyMetricLabelAr="معامل الزخم / التقلب",
        keyMetricLabelEn="Momentum / Vol Ratio",
        keyMetricValue=f"{sharpe_proxy:+.2f}x",
    )

    # 2. مداخلة سارة (حارسة المخاطر - Risk Sentinel) — توفر تدقيقاً صارماً واختلافاً بناءً عند ارتفاع التقلب أو الحجم
    high_vol_or_conc = (
        asset.volatilityPct >= 2.8
        or risk_assessment.postTradeConcentrationPct >= 12.0
        or not risk_assessment.passed
    )
    if not risk_assessment.passed:
        risk_stance: AgentStance = "CAUTION"
        risk_status = "DISSENT"
        risk_conf = 95
        risk_summary_ar = (
            f"تحذير حتمي: المقترح بحجم {eval_qty:g} {asset.symbol} لم يجتز ضوابط المخاطر "
            f"({len(risk_assessment.violations)} مخالفة). التركز المتوقع {risk_assessment.postTradeConcentrationPct:.2f}% "
            f"وتأثير VaR اليومي ${risk_assessment.varImpactUsd:,.2f}. أوصي بتقليص الحجم فوراً."
        )
        risk_summary_en = (
            f"Deterministic alert: {eval_qty:g} {asset.symbol} failed risk controls "
            f"({len(risk_assessment.violations)} violation(s)). Post-trade concentration reaches {risk_assessment.postTradeConcentrationPct:.2f}% "
            f"with ${risk_assessment.varImpactUsd:,.2f} 95% VaR impact. Immediate downsizing required."
        )
    elif high_vol_or_conc:
        risk_stance = "CAUTION"
        risk_status = "CAUTION"
        risk_conf = 84
        risk_summary_ar = (
            f"رغم إيجابية الزخم، يبلغ التقلب اليومي {asset.volatilityPct:.2f}% وتأثير المخاطرة VaR 95% "
            f"نحو ${risk_assessment.varImpactUsd:,.2f} مع تركز بعد الصفقة {risk_assessment.postTradeConcentrationPct:.2f}%. "
            f"أختلف مع التوسع المفرط وأوصي بتدرج الدخول مع وقف خسارة عند ${candles_data.supportLevel:,.2f}."
        )
        risk_summary_en = (
            f"Despite constructive momentum, daily volatility is {asset.volatilityPct:.2f}% with "
            f"${risk_assessment.varImpactUsd:,.2f} VaR impact and {risk_assessment.postTradeConcentrationPct:.2f}% post-trade weight. "
            f"I dissent against aggressive sizing; scale in gradually with a hard stop near ${candles_data.supportLevel:,.2f}."
        )
    else:
        risk_stance = "BUY" if quant_stance == "BUY" else "HOLD"
        risk_status = "AGREE"
        risk_conf = 82
        risk_summary_ar = (
            f"جميع الضوابط الخمسة لمحرك المخاطر سليمة؛ التركز بعد الصفقة {risk_assessment.postTradeConcentrationPct:.2f}% "
            f"(أقل بكثير من سقف 35%) وتراجع المحفظة الحالي {portfolio.currentDrawdownPct:.2f}%."
        )
        risk_summary_en = (
            f"All 5 deterministic risk checks pass cleanly; post-trade concentration is {risk_assessment.postTradeConcentrationPct:.2f}% "
            f"(well below 35% cap) and portfolio drawdown stands at {portfolio.currentDrawdownPct:.2f}%."
        )

    risk_item = AgentDeliberationItem(
        agentId="risk-sentinel",
        nameAr="سارة — حارسة المخاطر",
        nameEn="Sarah — Risk Sentinel",
        roleAr="حوكمة المخاطر والتركز وحماية رأس المال",
        roleEn="VaR Governance, Concentration & Drawdown Control",
        status=risk_status,  # type: ignore[arg-type]
        stance=risk_stance,
        confidence=risk_conf,
        summaryAr=risk_summary_ar,
        summaryEn=risk_summary_en,
        keyMetricLabelAr="درجة المخاطرة / التركّز",
        keyMetricLabelEn="Risk Score / Weight",
        keyMetricValue=f"{risk_assessment.riskScore}/100 ({risk_assessment.postTradeConcentrationPct:.1f}%)",
    )

    # 3. مداخلة طارق (استراتيجي السيولة والاقتصاد الكلي - Macro Oracle)
    vol_bn = asset.volume24hUsd / 1_000_000_000.0
    if ob_imbalance >= 0.98 and asset.change24hPct >= 0.4:
        macro_stance: AgentStance = "BUY"
        macro_status = "AGREE"
        macro_conf = 79
    else:
        macro_stance = "HOLD"
        macro_status = "READY"
        macro_conf = 73

    macro_item = AgentDeliberationItem(
        agentId="macro-oracle",
        nameAr="طارق — استراتيجي السيولة والاقتصاد الكلي",
        nameEn="Tariq — Macro & Liquidity Oracle",
        roleAr="تحليل التدفقات المؤسسية والارتباطات الكلية",
        roleEn="Institutional Flows & Cross-Asset Macro Regime",
        status=macro_status,  # type: ignore[arg-type]
        stance=macro_stance,
        confidence=macro_conf,
        summaryAr=(
            f"حجم التداول خلال 24 ساعة يبلغ ${vol_bn:,.2f}B مع نسبة توازن طلبات الشراء إلى البيع {ob_imbalance:.2f}x. "
            f"البيئة الكلية تدعم تنويع المحفظة بين أصول النمو والسيولة النقدية الاحتياطية (${portfolio.cashBalance:,.0f})."
        ),
        summaryEn=(
            f"24h institutional turnover stands at ${vol_bn:,.2f}B with an orderbook bid/ask ratio of {ob_imbalance:.2f}x. "
            f"Macro liquidity favors balanced allocation alongside our ${portfolio.cashBalance:,.0f} cash reserve."
        ),
        keyMetricLabelAr="سيولة 24 ساعة / عمق السوق",
        keyMetricLabelEn="24h Volume / OB Ratio",
        keyMetricValue=f"${vol_bn:,.2f}B ({ob_imbalance:.2f}x)",
    )

    # 4. مداخلة خالد (مهندس التنفيذ وتكاليف التداول - Execution Architect)
    prefer_limit = estimated_costs.costBps >= 8.5 or asset.spreadBps >= 3.5
    exec_stance: AgentStance = "CAUTION" if prefer_limit else ("BUY" if quant_stance == "BUY" else "HOLD")
    exec_status = "DISSENT" if prefer_limit and quant_stance == "BUY" else "AGREE"
    exec_item = AgentDeliberationItem(
        agentId="execution-architect",
        nameAr="خالد — مهندس التنفيذ وتكاليف التداول",
        nameEn="Khalid — Execution Architect",
        roleAr="هندسة التنفيذ وتقليل السبريد والانزلاق السعري",
        roleEn="Orderbook Microstructure & Slippage Optimization",
        status=exec_status,  # type: ignore[arg-type]
        stance=exec_stance,
        confidence=86,
        summaryAr=(
            f"السبريد الحالي {asset.spreadBps:.1f} bps والتكلفة الكلية المقدرة لأمر السوق تبلغ "
            f"${estimated_costs.totalEstimatedCostUsd:,.2f} ({estimated_costs.costBps:.2f} bps). "
            + (
                f"أتحفظ على التنفيذ بسعر السوق المباشر وأوصي بأمر محدد (LIMIT) قرب ${asset.price * 0.9985:,.2f} لتوفير الانزلاق السعري."
                if prefer_limit
                else "عمق الدفتر يسمح بتنفيذ سلس منخفض الانزلاق السعري."
            )
        ),
        summaryEn=(
            f"Current spread is {asset.spreadBps:.1f} bps and estimated market execution friction is "
            f"${estimated_costs.totalEstimatedCostUsd:,.2f} ({estimated_costs.costBps:.2f} bps). "
            + (
                f"I dissent on aggressive market sweeping; use a passive LIMIT order near ${asset.price * 0.9985:,.2f} to capture spread."
                if prefer_limit
                else "Orderbook depth supports clean, low-slippage execution."
            )
        ),
        keyMetricLabelAr="إجمالي تكلفة التنفيذ",
        keyMetricLabelEn="Total Execution Friction",
        keyMetricValue=f"{estimated_costs.costBps:.1f} bps (${estimated_costs.totalEstimatedCostUsd:,.2f})",
    )

    # 5. مداخلة المجلس التنفيذي (كبير المستشارين - Chief Strategist)
    safe_suggested_qty = (
        benchmark_qty if not risk_assessment.passed else eval_qty
    )
    if not risk_assessment.passed or sys_status.killSwitchActive:
        final_stance: AgentStance = "CAUTION"
        final_conf = 90
    elif quant_stance == "BUY" and macro_stance == "BUY":
        final_stance = "BUY"
        final_conf = 81 if not high_vol_or_conc else 76
    elif quant_stance == "SELL":
        final_stance = "SELL"
        final_conf = 74
    else:
        final_stance = "HOLD"
        final_conf = 75

    chief_item = AgentDeliberationItem(
        agentId="chief-strategist",
        nameAr="المجلس التنفيذي — كبير المستشارين",
        nameEn="Chief Strategist — Executive Council",
        roleAr="التركيب التنفيذي والتوصية المجمعة لرحلة التريليون",
        roleEn="Executive Synthesis & Trilunair Capital Allocation",
        status="READY",
        stance=final_stance,
        confidence=final_conf,
        summaryAr=(
            f"الخلاصة التنفيذية لـ {asset.symbol}: التوجه المجمع هو «{final_stance}» بثقة {final_conf}% "
            f"مع الالتزام بحجم منضبط ({safe_suggested_qty:g} وحدة) ومراعاة توصية مهندس التنفيذ وحارسة المخاطر."
        ),
        summaryEn=(
            f"Executive verdict on {asset.symbol}: Council stance is '{final_stance}' ({final_conf}% confidence) "
            f"with disciplined sizing ({safe_suggested_qty:g} units), integrating risk and microstructure guardrails."
        ),
        keyMetricLabelAr="الحجم الاستراتيجي المقترح",
        keyMetricLabelEn="Suggested Disciplined Size",
        keyMetricValue=f"{safe_suggested_qty:g} {asset.symbol}",
    )

    agent_responses = [quant_item, risk_item, macro_item, exec_item, chief_item]

    # بناء مصفوفات التوافق والاختلاف بشفافية كاملة
    agreement_score = 84 if (not high_vol_or_conc and not prefer_limit and risk_assessment.passed) else (62 if not risk_assessment.passed else 74)
    agreements_ar = [
        f"اتفاق جماعي على أن مستوى الدعم المحوري للأصل {asset.symbol} يقع عند ${candles_data.supportLevel:,.2f} والمقاومة عند ${candles_data.resistanceLevel:,.2f}.",
        f"توافق على متانة السيولة النقدية في المحفظة (${portfolio.cashBalance:,.2f}) وانضباط التراجع اليومي ({portfolio.currentDrawdownPct:.2f}% < 5.0%).",
    ]
    agreements_en = [
        f"Unanimous agreement on key technical structure: support at ${candles_data.supportLevel:,.2f} and resistance at ${candles_data.resistanceLevel:,.2f}.",
        f"Consensus on strong portfolio cash buffer (${portfolio.cashBalance:,.2f}) and controlled drawdown ({portfolio.currentDrawdownPct:.2f}% < 5.0%).",
    ]

    disagreements_ar = []
    disagreements_en = []
    if high_vol_or_conc or not risk_assessment.passed:
        disagreements_ar.append(
            f"تباين بين المحلل الكمي وحارسة المخاطر: سارة تفرض سقفاً تحوطياً صارماً بسبب تقلب {asset.volatilityPct:.2f}% وتأثير VaR البالغ ${risk_assessment.varImpactUsd:,.2f}."
        )
        disagreements_en.append(
            f"Quant vs. Risk divergence: Risk Sentinel enforces tighter sizing due to {asset.volatilityPct:.2f}% volatility and ${risk_assessment.varImpactUsd:,.2f} VaR impact."
        )
    if prefer_limit:
        disagreements_ar.append(
            f"تحفظ تكتيكي من مهندس التنفيذ خالد: يوصي بأمر محدد (LIMIT) بدلاً من أمر السوق لتفادي تكلفة {estimated_costs.costBps:.1f} نقطة أساس."
        )
        disagreements_en.append(
            f"Tactical execution dissent: Execution Architect favors passive LIMIT placement over MARKET sweep to save {estimated_costs.costBps:.1f} bps."
        )
    if not disagreements_ar:
        disagreements_ar.append(
            "تفاوت طفيف في توقيت جني الأرباح بين الهدف الكمي القريب والاحتفاظ الكلي متوسط الأجل."
        )
        disagreements_en.append(
            "Minor horizon divergence between short-term quantitative target profit-taking and medium-term macro holding."
        )

    # الأدلة الكمية وعوامل عدم اليقين
    uncertainty_score = min(85, max(18, int(round(asset.volatilityPct * 9.5 + (15 if not risk_assessment.passed else 0)))))
    evidence_ar = [
        f"السعر الفوري ${asset.price:,.2f} ({asset.change24hPct:+.2f}% خلال 24 ساعة) بحجم تداول مؤسسي ${vol_bn:,.2f} مليار دولار.",
        f"نسبة عمق طلبات الشراء إلى البيع في دفتر الأوامر تبلغ {ob_imbalance:.2f}x مع سبريد {asset.spreadBps:.1f} bps.",
        f"نتيجة فحص محرك المخاطر الحتمي: {'اجتياز كامل (5/5)' if risk_assessment.passed else f'رفض رقابي ({len(risk_assessment.violations)} مخالفة)'}.",
    ]
    evidence_en = [
        f"Spot price ${asset.price:,.2f} ({asset.change24hPct:+.2f}% 24h) backed by ${vol_bn:,.2f}B 24h volume.",
        f"Orderbook bid-to-ask depth imbalance at {ob_imbalance:.2f}x with {asset.spreadBps:.1f} bps bid-ask spread.",
        f"Deterministic Risk Engine audit: {'5/5 checks passed' if risk_assessment.passed else f'Rejected ({len(risk_assessment.violations)} violation(s))'}.",
    ]

    uncertainties_ar = [
        f"احتمال اتساع الانزلاق السعري في حال اختراق نطاق التقلب اليومي ({asset.volatilityPct:.2f}%) خلال الأخبار الكلية.",
        f"حساسية الزخم عند الاقتراب من منطقة المقاومة ${candles_data.resistanceLevel:,.2f} (مسافة {dist_to_res_pct:.2f}%).",
    ]
    uncertainties_en = [
        f"Potential slippage expansion if intraday volatility ({asset.volatilityPct:.2f}%) spikes on macro data releases.",
        f"Momentum sensitivity near overhead resistance at ${candles_data.resistanceLevel:,.2f} ({dist_to_res_pct:.2f}% away).",
    ]

    headline_ar = (
        f"توصية المجلس لـ {asset.nameAr} ({asset.symbol}): {final_stance} — ثقة {final_conf}%"
    )
    headline_en = (
        f"Council Verdict for {asset.nameEn} ({asset.symbol}): {final_stance} — {final_conf}% Confidence"
    )
    actionable_ar = (
        f"الحجم المنضبط المقترح: {safe_suggested_qty:g} {asset.symbol} (بتكلفة تقديرية ${estimated_costs.totalEstimatedCostUsd:,.2f} / {estimated_costs.costBps:.1f} bps)، "
        f"مع مراقبة الدعم ${candles_data.supportLevel:,.2f} والمقاومة ${candles_data.resistanceLevel:,.2f}. "
        "أي تنفيذ يتطلب مراجعة مقترح الصفقة والتوقيع الصريح عبر بوابة التصاريح."
    )
    actionable_en = (
        f"Suggested disciplined size: {safe_suggested_qty:g} {asset.symbol} (est. cost ${estimated_costs.totalEstimatedCostUsd:,.2f} / {estimated_costs.costBps:.1f} bps), "
        f"watching support at ${candles_data.supportLevel:,.2f} and resistance at ${candles_data.resistanceLevel:,.2f}. "
        "Any execution requires explicit user authorization in the order ticket."
    )

    meeting_id = f"mtg_{uuid.uuid4().hex[:12]}"
    created_at = utc_now_iso()

    result = AgentMeetingResult(
        meetingId=meeting_id,
        topicAr=topic_ar or f"اجتماع الطاولة المستديرة لتحليل {asset.nameAr} ({asset.symbol})",
        topicEn=topic_en or f"Executive Council Roundtable on {asset.nameEn} ({asset.symbol})",
        symbol=asset.symbol,
        timestamp=created_at,
        agentResponses=agent_responses,
        consensus=MeetingConsensus(
            agreementScorePct=agreement_score,
            agreementsAr=agreements_ar,
            agreementsEn=agreements_en,
            disagreementsAr=disagreements_ar,
            disagreementsEn=disagreements_en,
        ),
        evidenceAndUncertainty=MeetingEvidenceAndUncertainty(
            uncertaintyScorePct=uncertainty_score,
            evidenceAr=evidence_ar,
            evidenceEn=evidence_en,
            uncertaintiesAr=uncertainties_ar,
            uncertaintiesEn=uncertainties_en,
        ),
        estimatedCosts=estimated_costs,
        riskAssessment=risk_assessment,
        finalRecommendation=MeetingFinalRecommendation(
            stance=final_stance,
            confidence=final_conf,
            headlineAr=headline_ar,
            headlineEn=headline_en,
            actionableSummaryAr=actionable_ar,
            actionableSummaryEn=actionable_en,
            suggestedQuantity=safe_suggested_qty,
        ),
    )

    with db_session() as conn:
        conn.execute(
            "INSERT INTO agent_meetings (meeting_id, symbol, meeting_json, created_at) VALUES (?, ?, ?, ?)",
            (
                meeting_id,
                asset.symbol,
                json.dumps(result.model_dump(), ensure_ascii=False),
                created_at,
            ),
        )

    return result


def _detect_ui_action(norm_text: str) -> tuple[UiCommandAction | None, str, str]:
    """اكتشاف أوامر تغيير السمات أو إعدادات العرض أو التنقل بين شاشات لوحة التحكم."""
    lower = norm_text.lower()

    # 1. تبديل السمة الهولوغرامية (5 سمات أساسية + السمات المخصصة)
    theme_triggers = [
        ("royal-gold", ["royal gold", "royal-gold", "الملكي الذهبي", "ملكي ذهبي", "السمة الذهبية", "الوضع الذهبي"]),
        ("quantum-cyan", ["quantum cyan", "quantum-cyan", "السيان الكمي", "سيان كمي", "سمة السيان", "السيان"]),
        ("nebula-purple", ["nebula purple", "nebula-purple", "سديم الأرجوان", "الأرجواني", "الارجواني", "البنفسجي", "سمة الأرجوان"]),
        ("emerald-matrix", ["emerald matrix", "emerald-matrix", "المصفوفة الزمردية", "الزمردية", "الزمرد", "مصفوفة الزمرد"]),
        ("arctic-platinum", ["arctic platinum", "arctic-platinum", "البلاتين القطبي", "البلاتينية", "البلاتين", "القطبي"]),
    ]

    theme_context_words = ["theme", "سمة", "السمة", "ثيم", "لون", "واجهة", "مظهر", "حول", "غير", "فعل", "تفعيل", "switch", "activate", "set"]
    has_theme_intent = any(w in lower for w in theme_context_words)

    for theme_id, keywords in theme_triggers:
        if any(kw in lower for kw in keywords) and (has_theme_intent or "-" in lower or len(keywords[0]) > 6):
            apply_quick_theme_patch(theme_id=theme_id)
            return (
                UiCommandAction(type="SWITCH_THEME", payload={"themeId": theme_id}),
                f"تم تطبيق السمة الهولوغرامية «{theme_id}» وحفظها في قاعدة البيانات المستديمة.",
                f"Activated holographic theme '{theme_id}' and persisted it to SQLite.",
            )

    for custom_t in get_custom_themes():
        if custom_t.nameAr.lower() in lower or custom_t.nameEn.lower() in lower or custom_t.id.lower() in lower:
            apply_quick_theme_patch(theme_id=custom_t.id)
            return (
                UiCommandAction(type="SWITCH_THEME", payload={"themeId": custom_t.id}),
                f"تم التبديل إلى السمة المخصصة «{custom_t.nameAr}».",
                f"Switched to custom theme '{custom_t.nameEn}'.",
            )

    negation = any(neg in lower for neg in ["إلغاء", "الغاء", "أوقف", "إيقاف", "ايقاف", "تعطيل", "disable", "turn off", "off"])

    # 2. وضع الطاقة المنخفضة (Low Power Mode)
    if any(k in lower for k in ["low power", "طاقة منخفضة", "الطاقة المنخفضة", "منخفض الطاقة", "توفير الطاقة"]):
        enabled = not negation
        apply_quick_theme_patch(low_power=enabled)
        return (
            UiCommandAction(
                type="SET_LOW_POWER",
                payload={"enabled": enabled, "lowPowerMode": enabled},
            ),
            f"تم {'تفعيل' if enabled else 'إيقاف'} وضع الطاقة المنخفضة لحماية موارد المعالج الرسومي.",
            f"{'Enabled' if enabled else 'Disabled'} Low Power Mode for GPU efficiency.",
        )

    # 3. وضع التباين العالي (High Contrast)
    if any(k in lower for k in ["high contrast", "تباين عالي", "التباين العالي", "تباين مرتفع"]):
        enabled = not negation
        apply_quick_theme_patch(high_contrast=enabled)
        return (
            UiCommandAction(
                type="SET_HIGH_CONTRAST",
                payload={"enabled": enabled, "highContrast": enabled},
            ),
            f"تم {'تفعيل' if enabled else 'إيقاف'} وضع التباين العالي لوضوح بصري فائق.",
            f"{'Enabled' if enabled else 'Disabled'} High Contrast accessibility mode.",
        )

    # 4. تقليل أو إيقاف الحركة (Motion Disabled)
    if any(
        k in lower
        for k in [
            "disable motion",
            "reduce motion",
            "enable motion",
            "إيقاف الحركة",
            "ايقاف الحركة",
            "تعطيل الحركة",
            "تقليل الحركة",
            "بدون حركة",
            "تفعيل الحركة",
        ]
    ):
        enable_motion = any(k in lower for k in ["enable motion", "تفعيل الحركة", "تشغيل الحركة"])
        motion_disabled = not enable_motion
        apply_quick_theme_patch(motion_disabled=motion_disabled)
        return (
            UiCommandAction(
                type="SET_MOTION_DISABLED",
                payload={"enabled": motion_disabled, "motionDisabled": motion_disabled},
            ),
            f"تم {'تعطيل المؤثرات الحركية' if motion_disabled else 'إعادة تفعيل المؤثرات الحركية'} في الواجهة.",
            f"{'Disabled' if motion_disabled else 'Re-enabled'} holographic motion animations.",
        )

    # 5. التنقل بين الشاشات (Navigate View)
    nav_verbs = ["انتقل", "افتح", "اعرض شاشة", "اعرض صفحة", "اذهب", "navigate", "open screen", "go to", "switch screen"]
    if any(v in lower for v in nav_verbs):
        if any(k in lower for k in ["حوكمة", "تصاريح", "أمان", "governance", "safety", "audit"]):
            return (
                UiCommandAction(type="NAVIGATE_VIEW", payload={"screen": "governance", "view": "governance"}),
                "تم الانتقال إلى شاشة الحوكمة وبوابة التصاريح الأمنية.",
                "Navigated to the Governance & Safety Authorization screen.",
            )
        if any(k in lower for k in ["استوديو السمات", "شاشة السمات", "صفحة السمات", "themes", "theme studio"]):
            return (
                UiCommandAction(type="NAVIGATE_VIEW", payload={"screen": "themes", "view": "themes"}),
                "تم الانتقال إلى استوديو تخصيص السمات الهولوغرامية.",
                "Navigated to the Holographic Theme Studio.",
            )
        if any(k in lower for k in ["شاشة المحفظة", "تبويب المحفظة", "portfolio screen", "go to portfolio", "open portfolio", "انتقل إلى المحفظة", "افتح المحفظة"]):
            return (
                UiCommandAction(type="NAVIGATE_VIEW", payload={"screen": "portfolio", "view": "portfolio"}),
                "تم الانتقال إلى شاشة المحفظة وإدارة المراكز والمخاطر.",
                "Navigated to the Portfolio & Risk Analytics screen.",
            )
        if any(k in lower for k in ["مركز القيادة", "شاشة التداول", "terminal", "command center"]):
            return (
                UiCommandAction(type="NAVIGATE_VIEW", payload={"screen": "terminal", "view": "terminal"}),
                "تم الانتقال إلى شاشة مركز القيادة والتداول الرئيسية.",
                "Navigated to the main Holographic Trading Terminal.",
            )

    return None, "", ""


def _extract_trade_proposal_intent(
    norm_text: str, source: CommandSource
) -> TradeProposalInput | None:
    """
    استخراج نية إنشاء مقترح صفقة مهيكل من جملة عربية أو إنجليزية.
    لا تنفذ هذه الدالة أي صفقة إطلاقاً، بل تُخرج مدخلات مهيكلة تمر عبر CommandValidator و DeterministicRiskEngine.
    """
    lower = norm_text.lower()

    buy_keywords = ["اشتر", "اشتري", "شراء", "buy", "purchase", "long"]
    sell_keywords = ["بيع", "بع", "sell", "short"]

    side: str | None = None
    trigger_pos = -1

    # فحص موضع فعل الشراء أو البيع بدقة
    for kw in buy_keywords:
        m = re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", lower) if kw.isascii() else re.search(re.escape(kw), lower)
        if m and (trigger_pos == -1 or m.start() < trigger_pos):
            side = "BUY"
            trigger_pos = m.start()

    for kw in sell_keywords:
        m = re.search(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", lower) if kw.isascii() else re.search(re.escape(kw), lower)
        if m and (trigger_pos == -1 or m.start() < trigger_pos):
            side = "SELL"
            trigger_pos = m.start()

    if side is None:
        return None

    # التركيز على المقطع النصي المحيط بأمر التداول لاستخراج الكمية والأصل بدقة حتى في الجمل المركبة
    trade_clause = norm_text[trigger_pos:]
    clause_symbols = market_engine.extract_symbols_from_text(trade_clause)
    all_symbols = market_engine.extract_symbols_from_text(norm_text)
    target_symbol = clause_symbols[0] if clause_symbols else (all_symbols[-1] if all_symbols else None)
    if not target_symbol:
        return None

    # البحث عن سعر محدد اختياري (LIMIT) مثل: "بسعر محدد 95000" أو "limit 95000" أو "at 95000"
    limit_price: float | None = None
    limit_match = re.search(
        r"(?:بسعر محدد|أمر محدد|سعر محدد|limit(?:\s+price)?|at\s+price|@)\s*\$?([0-9]+(?:\.[0-9]+)?)",
        trade_clause.lower(),
    )
    clause_for_qty = trade_clause
    if limit_match:
        limit_price = float(limit_match.group(1))
        # إزالة نص السعر المحدد حتى لا يختلط مع الكمية
        clause_for_qty = (
            trade_clause[: limit_match.start()] + " " + trade_clause[limit_match.end() :]
        )

    # استخراج أول رقم موجب يمثل الكمية داخل جملة الصفقة
    qty_match = re.search(r"(?<![a-zA-Z0-9])([0-9]+(?:\.[0-9]+)?)(?![a-zA-Z0-9])", clause_for_qty)
    if qty_match:
        quantity = float(qty_match.group(1))
    else:
        # إذا لم يحدد المستخدم رقماً صريحاً، نختار وحدة معيارية آمنة (مثلاً 0.1 BTC أو 10 أسهم)
        asset_obj = market_engine.get_asset(target_symbol)
        quantity = 0.1 if (asset_obj and asset_obj.price > 1000) else 10.0

    order_type = "LIMIT" if (limit_price is not None and limit_price > 0) else "MARKET"

    return TradeProposalInput(
        symbol=target_symbol,
        side=side,  # type: ignore[arg-type]
        orderType=order_type,  # type: ignore[arg-type]
        quantity=quantity,
        limitPrice=limit_price,
        source=source,
        rationale=norm_text.strip()[:240],
    )


def _try_optional_cloud_enrichment(
    prompt_context: str, language: Language
) -> str | None:
    """
    إثراء لغوي اختياري عبر مزود سحابي (OpenAI أو Gemini) في حال ضبط مفتاح البيئة فقط،
    مع مهلة زمنية قصيرة جداً وعدم التأثير نهائياً على الحسابات أو ضوابط المخاطر الحتمية.
    """
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are the concise Executive Financial Strategist for Dr. MaJoOoOoOoD. "
                                "Provide a 2-sentence institutional insight strictly grounded in the provided metrics without claiming trade execution."
                            ),
                        },
                        {"role": "user", "content": prompt_context},
                    ],
                    "max_tokens": 140,
                    "temperature": 0.2,
                },
                timeout=3.5,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None
    return None


def process_ai_command(req: AiCommandRequest) -> AiCommandResponse:
    """
    المعالج الموحد للأوامر الصوتية (VOICE) والنصية (TEXT).
    يدعم الأوامر الفردية والمركبة بالعربية والإنجليزية:
    - تغيير السمات وإعدادات العرض والتنقل (uiAction)
    - إعداد مقترحات الصفقات المهيكلة وفحصها حتمياً دون تنفيذ تلقائي (tradeProposalEvaluation)
    - مقارنة الأصول المتعددة (Compare)
    - شرح أداء المحفظة ومسار التريليون (Portfolio & Trilunair Roadmap)
    - عقد اجتماع مجلس الوكلاء الشامل (AgentMeetingResult)
    """
    raw_msg = (req.message or "").strip()
    if not raw_msg:
        raise HTTPException(status_code=400, detail="نص الأمر لا يمكن أن يكون فارغاً.")

    norm_msg = normalize_digits(raw_msg)
    lower_msg = norm_msg.lower()
    now_user = utc_now_iso()

    # توثيق الأمر الصوتي أو النصي في سجل التدقيق الأمني
    append_audit_log(
        actor="USER_COMMAND",
        source=req.source,
        action="AI_COMMAND_RECEIVED",
        severity="INFO",
        details_ar=f"تم استلام أمر ({req.source}) باللغة ({req.language}): «{raw_msg[:140]}»",
        details_en=f"Received {req.source} command ({req.language}): '{raw_msg[:140]}'",
    )

    user_record = ChatMessageRecord(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        role="user",
        senderNameAr="د. ماجد (قائد المركز)",
        senderNameEn="Dr. MaJoOoOoOoD",
        source=req.source,
        language=req.language,
        contentAr=raw_msg,
        contentEn=raw_msg,
        createdAt=now_user,
    )

    sections_ar: list[str] = []
    sections_en: list[str] = []

    # 1. فحص أوامر الواجهة والسمات (UI / Theme Action)
    ui_action, ui_ar, ui_en = _detect_ui_action(norm_msg)
    if ui_action is not None:
        sections_ar.append(f"🎨 **تحديث الواجهة الهولوغرامية:** {ui_ar}")
        sections_en.append(f"🎨 **Holographic UI Update:** {ui_en}")

    # 2. فحص نية مقترح صفقة مالية (يمر حتماً عبر propose_order بنفس سياسة TERMINAL دون تنفيذ تلقائي!)
    proposal_evaluation: TradeProposalEvaluation | None = None
    proposal_input = _extract_trade_proposal_intent(norm_msg, req.source)
    if proposal_input is not None:
        proposal_evaluation = propose_order(proposal_input)
        p = proposal_evaluation.proposal
        c = proposal_evaluation.estimatedCosts
        r = proposal_evaluation.riskAssessment
        if proposal_evaluation.status == "APPROVED_FOR_AUTH":
            sections_ar.append(
                f"🛡️ **تم تجهيز مقترح صفقة مهيكل (لم يُنفذ تلقائياً):** أمر `{p.side}` لكمية `{p.quantity:g} {p.symbol}` "
                f"({p.orderType}) بسعر مرجعي `${p.referencePrice:,.2f}` وقيمة اسمية `${c.notionalUsd:,.2f}` "
                f"(التكلفة التقديرية: `${c.totalEstimatedCostUsd:,.2f}` / `{c.costBps:.1f} bps`). "
                f"اجتاز المقترح جميع ضوابط المخاطر الخمسة (`{r.riskLevel}` — درجة `{r.riskScore}/100`) وهو جاهز في تذكرة التصاريح بانتظار تأكيدك الصريح."
            )
            sections_en.append(
                f"🛡️ **Structured Trade Proposal Staged (NOT Auto-Executed):** `{p.side}` `{p.quantity:g} {p.symbol}` "
                f"({p.orderType}) @ ref `${p.referencePrice:,.2f}`, notional `${c.notionalUsd:,.2f}` "
                f"(est. cost `${c.totalEstimatedCostUsd:,.2f}` / `{c.costBps:.1f} bps`). "
                f"Passed all 5 deterministic risk checks (`{r.riskLevel}` — score `{r.riskScore}/100`) and awaits your explicit confirmation in the authorization ticket."
            )
        else:
            viol_text = " | ".join(r.violations)
            sections_ar.append(
                f"⛔ **رفض رقابي من محرك المخاطر الحتمي:** تم إنشاء المقترح `{p.side} {p.quantity:g} {p.symbol}` "
                f"بقيمة `${c.notionalUsd:,.2f}` عبر قناة `{req.source}`، لكنه **مرفوض للتنفيذ** لعدم اجتياز الضوابط: {viol_text}."
            )
            sections_en.append(
                f"⛔ **Blocked by Deterministic Risk Engine:** Staged `{p.side} {p.quantity:g} {p.symbol}` "
                f"(`${c.notionalUsd:,.2f}` via `{req.source}`), **REJECTED_BY_RISK** due to policy violations: {viol_text}."
            )

    # 3. فحص طلبات تحليل المحفظة ومسار التريليون
    portfolio_keywords = [
        "محفظة", "محفظتي", "المحفظة", "أداء", "اداء", "رصيد", "تريليون", "مراكز", "ربح",
        "portfolio", "performance", "balance", "equity", "trilunair", "positions", "pnl",
    ]
    is_portfolio_query = any(k in lower_msg for k in portfolio_keywords) and (
        ui_action is None or ui_action.type != "NAVIGATE_VIEW" or "حلل" in lower_msg or "اشرح" in lower_msg or "أداء" in lower_msg or "analyze" in lower_msg or "explain" in lower_msg
    )
    if is_portfolio_query:
        snap = get_portfolio_snapshot()
        pos_summary_ar = "، ".join(
            f"{pos.symbol} ({pos.quantity:g} وحدة بقيمة ${pos.marketValueUsd:,.2f} وربح غير محقق ${pos.unrealizedPnlUsd:+,.2f})"
            for pos in snap.positions
        ) or "لا توجد مراكز مفتوحة حالياً (100% سيولة نقدية)"
        pos_summary_en = ", ".join(
            f"{pos.symbol} ({pos.quantity:g} units = ${pos.marketValueUsd:,.2f}, uPnL ${pos.unrealizedPnlUsd:+,.2f})"
            for pos in snap.positions
        ) or "No open positions (100% cash)"

        sections_ar.append(
            f"💼 **تحليل المحفظة ومسار التريليون ({snap.tradingMode}):** إجمالي حقوق الملكية `${snap.totalEquity:,.2f}` "
            f"(السيولة النقدية: `${snap.cashBalance:,.2f}` | قيمة المراكز: `${snap.positionsValue:,.2f}`). "
            f"العائد اليومي: `${snap.dailyPnl:+,.2f}` (`{snap.dailyPnlPct:+.2f}%`)، القيمة المعرضة للمخاطر VaR 95%: `${snap.var95Usd:,.2f}`، "
            f"والتراجع الحالي `{snap.currentDrawdownPct:.2f}%` من أصل سقف `{snap.maxAllowedDrawdownPct:.1f}%`. المراكز النشطة: {pos_summary_ar}."
        )
        sections_en.append(
            f"💼 **Portfolio & Trilunair Trajectory ({snap.tradingMode}):** Total Equity `${snap.totalEquity:,.2f}` "
            f"(Cash: `${snap.cashBalance:,.2f}` | Positions: `${snap.positionsValue:,.2f}`). "
            f"Daily P&L: `${snap.dailyPnl:+,.2f}` (`{snap.dailyPnlPct:+.2f}%`), 95% Daily VaR: `${snap.var95Usd:,.2f}`, "
            f"Current Drawdown `{snap.currentDrawdownPct:.2f}%` (cap `{snap.maxAllowedDrawdownPct:.1f}%`). Active holdings: {pos_summary_en}."
        )

    # 4. فحص المقارنة بين الأصول (Multi-Asset Comparison)
    mentioned_symbols = market_engine.extract_symbols_from_text(norm_msg)
    compare_keywords = ["قارن", "مقارنة", "مقابل", "أيهما", "ايهما", "compare", "comparison", "versus", " vs "]
    is_comparison = any(k in lower_msg for k in compare_keywords) or len(mentioned_symbols) >= 2

    if is_comparison:
        comp_syms = list(mentioned_symbols)
        if len(comp_syms) == 0:
            comp_syms = ["BTC-USD", "XAU-USD"]
        elif len(comp_syms) == 1:
            fallback_peer = "XAU-USD" if comp_syms[0] != "XAU-USD" else "BTC-USD"
            comp_syms.append(fallback_peer)

        comp_assets = [market_engine.get_asset(s) for s in comp_syms[:3]]
        valid_comp = [a for a in comp_assets if a is not None]
        if len(valid_comp) >= 2:
            scored = sorted(
                valid_comp,
                key=lambda a: (a.change24hPct / max(0.5, a.volatilityPct)) - (a.spreadBps * 0.05),
                reverse=True,
            )
            leader = scored[0]
            rows_ar = " | ".join(
                f"{a.symbol}: السعر ${a.price:,.2f}، تغير {a.change24hPct:+.2f}%، تقلب {a.volatilityPct:.2f}%، سبريد {a.spreadBps:.1f} bps"
                for a in valid_comp
            )
            rows_en = " | ".join(
                f"{a.symbol}: ${a.price:,.2f}, 24h {a.change24hPct:+.2f}%, vol {a.volatilityPct:.2f}%, spread {a.spreadBps:.1f} bps"
                for a in valid_comp
            )
            sections_ar.append(
                f"⚖️ **مقارنة الفرص الكمية:** [{rows_ar}]. يتصدر **{leader.symbol}** من حيث كفاءة العائد المعدل بالتقلب وتكلفة التنفيذ."
            )
            sections_en.append(
                f"⚖️ **Cross-Asset Quantitative Comparison:** [{rows_en}]. **{leader.symbol}** leads on volatility-adjusted momentum and spread efficiency."
            )

    # 5. عقد اجتماع مجلس الوكلاء عند تحليل أصل أو مقارنة أو تجهيز مقترح صفقة (أو إذا لم يكن الأمر مجرد تبديل سمة بحت)
    meeting_result: AgentMeetingResult | None = None
    should_convene = req.triggerMeeting and (
        len(mentioned_symbols) > 0
        or proposal_evaluation is not None
        or is_comparison
        or (ui_action is None and not is_portfolio_query)
    )

    if should_convene:
        primary_sym = (
            proposal_input.symbol
            if proposal_input is not None
            else (mentioned_symbols[0] if mentioned_symbols else "BTC-USD")
        )
        meeting_result = convene_meeting(
            symbol=primary_sym,
            horizon="1h",
            language=req.language,
            proposed_qty=proposal_input.quantity if proposal_input else None,
            proposed_side=proposal_input.side if proposal_input else None,
        )
        rec = meeting_result.finalRecommendation
        sections_ar.append(
            f"🏛️ **خلاصة قاعة اجتماع الوكلاء ({meeting_result.symbol}):** {rec.headlineAr} "
            f"(توافق المجلس `{meeting_result.consensus.agreementScorePct}%` | عدم اليقين `{meeting_result.evidenceAndUncertainty.uncertaintyScorePct}%`). "
            f"{rec.actionableSummaryAr}"
        )
        sections_en.append(
            f"🏛️ **Agent Council Roundtable ({meeting_result.symbol}):** {rec.headlineEn} "
            f"(Consensus `{meeting_result.consensus.agreementScorePct}%` | Uncertainty `{meeting_result.evidenceAndUncertainty.uncertaintyScorePct}%`). "
            f"{rec.actionableSummaryEn}"
        )

        # إذا طلب المستخدم التركيز على رمز معين دون أمر سمة سابق، يمكن تمرير SELECT_SYMBOL للواجهة
        if ui_action is None and len(mentioned_symbols) == 1 and proposal_evaluation is None:
            ui_action = UiCommandAction(
                type="SELECT_SYMBOL", payload={"symbol": primary_sym}
            )

    # إثراء سحابي اختياري عند ضبط مفاتيح البيئة دون المساس بالنتائج الحتمية
    cloud_note = _try_optional_cloud_enrichment(
        "\n".join(sections_en), req.language
    )
    if cloud_note:
        if req.language == "ar":
            sections_ar.append(f"✨ **ملاحظة النموذج السحابي المساند:** {cloud_note}")
        else:
            sections_en.append(f"✨ **Cloud Co-Pilot Note:** {cloud_note}")

    content_ar = "\n\n".join(sections_ar)
    content_en = "\n\n".join(sections_en)

    # تحديد هوية الوكيل المجيب بناءً على اختيار المستخدم (فريق كامل أو وكيل متخصص بعينه)
    matched_agent = next(
        (a for a in AGENTS_REGISTRY if a.agentId == req.selectedAgent),
        AGENTS_REGISTRY[-1],  # chief-strategist عند اختيار team
    )

    assistant_record = ChatMessageRecord(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        role="assistant",
        senderNameAr=matched_agent.nameAr,
        senderNameEn=matched_agent.nameEn,
        agentId=matched_agent.agentId,
        source=req.source,
        language=req.language,
        contentAr=content_ar,
        contentEn=content_en,
        createdAt=utc_now_iso(),
        uiAction=ui_action,
        tradeProposalEvaluation=proposal_evaluation,
        meetingId=meeting_result.meetingId if meeting_result else None,
    )

    with db_session() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, message_json, created_at) VALUES (?, ?, ?)",
            (
                user_record.id,
                json.dumps(user_record.model_dump(), ensure_ascii=False),
                user_record.createdAt,
            ),
        )
        conn.execute(
            "INSERT INTO chat_messages (id, message_json, created_at) VALUES (?, ?, ?)",
            (
                assistant_record.id,
                json.dumps(assistant_record.model_dump(), ensure_ascii=False),
                assistant_record.createdAt,
            ),
        )

    return AiCommandResponse(
        userMessage=user_record,
        assistantMessage=assistant_record,
        uiAction=ui_action,
        tradeProposalEvaluation=proposal_evaluation,
        meeting=meeting_result,
    )
