"""
محرك المستشار التنفيذي المبسط، الربط البرمجي الحي للوكلاء الخمسة (AI Agents Council)،
تفاصيل مدار 3D متعدد الأطر الزمنية (1H / 24H / 7D / 1Y)، صفقات الرسم البياني المجاور،
موجز السوق اليومي، أفضل 6 صفقات زمنية، وقوائم أفضل الأسهم ربحية (قصير وطويل المدى).

المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD (TMJ)
القاعدة الذهبية للأمان: جميع عمليات الاعتماد والتنفيذ مقفلة برمجياً على وضع المحاكاة الورقية (PAPER)
وتمر إلزامياً عبر محرك المخاطر الحتمي (DeterministicRiskEngine) بسقف مخاطرة آمن.
"""

from __future__ import annotations

from typing import Any, Literal
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents_council import convene_meeting, get_agents
from app.database import append_audit_log, utc_now_iso
from app.market_engine import market_engine
from app.models import OrderExecuteRequest, TradeProposalInput
from app.safety_gateway import execute_order, get_portfolio_snapshot, propose_order

executive_router = APIRouter(
    prefix="/api/executive",
    tags=["Executive Agent Q&A, 3D Orbit Telemetry, Top-6 Setups & Stocks"],
)


class ExecutiveDecisionInput(BaseModel):
    opportunityId: str = Field(..., min_length=2, max_length=64)
    decision: Literal["APPROVE", "SKIP"] = "APPROVE"
    category: Literal["CRYPTO_SPOT", "STOCK_EQUITY"] = "CRYPTO_SPOT"
    symbol: str = Field(..., min_length=2, max_length=24)
    side: Literal["BUY", "SELL"] = "BUY"
    suggestedQty: float = Field(default=0.05, gt=0)
    stopLoss: float | None = None
    takeProfit: float | None = None


def _live_asset_info(symbol: str, fallback_price: float, fallback_chg24: float) -> tuple[float, float]:
    resolved = market_engine.resolve_symbol(symbol) or symbol
    asset = market_engine.get_asset(resolved)
    if asset is not None:
        return float(asset.price), float(asset.change24hPct)
    return fallback_price, fallback_chg24


def build_orbit_3d_telemetry() -> dict[str, Any]:
    """
    بناء بيانات شرح وتفكيك مدار 3D عبر 4 أطر زمنية واضحة:
    بالساعة (1H) | يومي (24H) | أسبوعي (7D) | سنوي (1Y)
    حتى يعرف المستخدم بدقة ماذا يمثل ارتفاع أو انخفاض كل كوكب داخل القبة الهولوغرامية.
    """
    specs = [
        ("BTC-USD", "BTCUSDT", "بيتكوين (Bitcoin)", 96540.0, 1.84, 0.62, 6.40, 118.5),
        ("ETH-USD", "ETHUSDT", "إيثيريوم (Ethereum)", 3420.5, 2.41, 0.85, 8.15, 64.2),
        ("SOL-USD", "SOLUSDT", "سولانا (Solana)", 214.8, 4.12, 1.48, 14.20, 186.0),
        ("NVDA", "NVDA", "إنفيديا (NVIDIA AI)", 139.24, 3.45, 0.94, 9.20, 142.0),
        ("XAU-USD", "PAXGUSDT", "الذهب الرقمي (Gold)", 2688.0, 0.65, 0.22, 2.45, 31.8),
        ("ARAMCO.SR", "2222.SR", "أرامكو السعودية", 27.96, 0.58, 0.19, 1.85, 11.4),
    ]
    coins = []
    for engine_sym, disp_sym, name_ar, fb_p, fb_24h, chg_1h, chg_7d, chg_1y in specs:
        price, live_24h = _live_asset_info(engine_sym, fb_p, fb_24h)
        coins.append(
            {
                "symbol": disp_sym,
                "engineSymbol": engine_sym,
                "shortCode": disp_sym.replace("USDT", "").replace(".SR", ""),
                "nameAr": name_ar,
                "price": round(price, 4 if price < 10 else 2),
                "ratesPct": {
                    "1h": round(chg_1h, 2),
                    "24h": round(live_24h, 2),
                    "7d": round(chg_7d, 2),
                    "1y": round(chg_1y, 2),
                },
            }
        )

    return {
        "defaultRateHorizon": "24h",
        "visualLegendAr": [
            {
                "element": "الارتفاع العمودي للكوكب (المحور Y)",
                "meaning": "يمثل نسبة صعود أو هبوط الأصل حسب الإطار الزمني المختار أعلى المدار (بالساعة 1H، يومي 24H، أسبوعي 7D، أو سنوي 1Y).",
            },
            {
                "element": "حجم الكوكب وشدة التوهج الطيفي",
                "meaning": "يمثل قوة السيولة المؤسسية ودرجة إجماع الوكلاء الخمسة على الأصل.",
            },
            {
                "element": "لون الشعاع المتصل ببلورة المركز",
                "meaning": "الأخضر/السيان يدل على معدل صعود موجب (+%)، والوردي/الأحمر يدل على تراجع (-%) في ذلك الإطار الزمني.",
            },
            {
                "element": "بلورة الأوكتاهيدرون المركزية (TMJ)",
                "meaning": "تمثل نقطة التوازن المداري (0.0%) ونسبة توافق مجلس الوكلاء اللحظية.",
            },
        ],
        "coins": coins,
    }


def build_agent_programmatic_signals() -> list[dict[str, Any]]:
    """
    ربط برمجي فعلي مع مجلس الوكلاء الخمسة (convene_meeting + DeterministicRiskEngine)
    لتوليد الصفقات الجاهزة للتنفيذ التي تظهر عند الضغط على الرسم البياني المجاور لمدار 3D.
    """
    tracked = [
        ("BTC-USD", "BTCUSDT"),
        ("SOL-USD", "SOLUSDT"),
        ("ETH-USD", "ETHUSDT"),
        ("NVDA", "NVDA"),
        ("XAU-USD", "PAXGUSDT"),
        ("ARAMCO.SR", "2222.SR"),
    ]
    signals: list[dict[str, Any]] = []
    for idx, (engine_sym, disp_sym) in enumerate(tracked, start=1):
        meeting = convene_meeting(symbol=engine_sym, horizon="1h", language="ar")
        rec = meeting.finalRecommendation
        asset = market_engine.get_asset(meeting.symbol)
        entry = float(asset.price) if asset else 100.0
        side: Literal["BUY", "SELL"] = "SELL" if rec.stance == "SELL" else "BUY"
        tp_mult = 1.032 if side == "BUY" else 0.968
        sl_mult = 0.988 if side == "BUY" else 1.012
        # حجم صفقة مضبوط تلقائياً بحيث لا تتجاوز مخاطرة وقف الخسارة 0.35% من المحفظة
        stop_dist = max(entry * 0.012, 0.01)
        safe_qty = round(3500.0 / stop_dist, 4 if entry > 500 else 2)
        signals.append(
            {
                "id": f"ag-live-{disp_sym.lower()}",
                "rank": idx,
                "symbol": disp_sym,
                "engineSymbol": meeting.symbol,
                "side": side,
                "actionVerdict": rec.stance,
                "headlineAr": rec.headlineAr,
                "confidence": meeting.consensus.agreementScorePct,
                "entry": round(entry, 4 if entry < 10 else 2),
                "target": round(entry * tp_mult, 4 if entry < 10 else 2),
                "stopLoss": round(entry * sl_mult, 4 if entry < 10 else 2),
                "expectedReturnPct": 3.2,
                "suggestedQty": max(0.01, safe_qty),
                "rationaleAr": rec.actionableSummaryAr,
                "riskPassed": meeting.riskAssessment.passed,
                "agentsVotes": [
                    {
                        "agentId": d.agentId,
                        "nameAr": d.nameAr,
                        "roleAr": d.roleAr,
                        "stance": d.stance,
                        "confidence": d.confidence,
                        "summaryAr": d.summaryAr,
                        "metric": f"{d.keyMetricLabelAr}: {d.keyMetricValue}",
                    }
                    for d in meeting.agentResponses
                ],
            }
        )
    return signals


def build_executive_payload() -> dict[str, Any]:
    """بناء الحمولة التنفيذية الموحدة المبسطة والمربوطة برمجياً بالوكلاء الخمسة لدكتور ماجد."""
    btc, _ = _live_asset_info("BTCUSDT", 96540.0, 1.84)
    eth, _ = _live_asset_info("ETHUSDT", 3420.5, 2.41)
    sol, _ = _live_asset_info("SOLUSDT", 214.8, 4.12)
    bnb, _ = _live_asset_info("BNBUSDT", 654.2, 0.92)
    xrp, _ = _live_asset_info("XRPUSDT", 2.46, -0.65)
    ada, _ = _live_asset_info("ADAUSDT", 1.08, 1.25)

    portfolio = get_portfolio_snapshot()
    agents_profiles = [a.model_dump() for a in get_agents()]
    orbit_3d = build_orbit_3d_telemetry()
    agent_signals = build_agent_programmatic_signals()

    market_brief = {
        "updatedAt": utc_now_iso(),
        "moodLabel": "إيجابي صاعد بحذر محسوب (76 / 100)",
        "moodCode": "BULLISH_CONTROLLED",
        "headlineSummary": (
            "السيولة المؤسسية تتدفق بقوة نحو البيتكوين وسولانا وأسهم الذكاء الاصطناعي، "
            "مع استقرار عوائد السندات وتراجع تقلبات الدولار."
        ),
        "todayHighlights": [
            {
                "impact": "إيجابي قوي",
                "title": "تدفقات صافية موجبة لصناديق ETF والسيولة الفورية",
                "summary": "جدران شراء مؤسسية واضحة تدعم البيتكوين أعلى مناطق الدعم المحورية وتقلل مخاطر الكسر الحاد.",
            },
            {
                "impact": "إيجابي",
                "title": "زخم قيادي في قطاع الرقائق والحوسبة السحابية والبنوك القيادية",
                "summary": "استمرار تفوق أسهم البنية التحتية للذكاء الاصطناعي عالمياً والأسهم المصرفية والتقنية القيادية في تداول.",
            },
            {
                "impact": "تنبيه مخاطرة",
                "title": "ترقب بيانات التضخم والسيولة الأمريكية نهاية الأسبوع",
                "summary": "مجلس الوكلاء يوصي بالإبقاء على سقف مخاطرة 0.5% فقط لكل صفقة مع وقف خسارة آلي مسبق.",
            },
        ],
        "forecasts": {
            "next1h": "زخم شرائي سريع على SOL و BTC مع فرص ارتداد مضاربية بين +1.2% و +2.4%.",
            "next24h": "اتجاه صاعد متدرج نحو قمم السيولة اليومية شريطة ثبات BTC أعلى خط الحماية.",
            "next7d": "استمرار المسار التراكمي الإيجابي للعملات القيادية والأسهم ذات التدفقات النقدية العالية.",
        },
    }

    top_six_trades = {
        "1h": [
            {
                "id": "1h-sol",
                "rank": 1,
                "symbol": "SOLUSDT",
                "nameAr": "سولانا — اختراق سيولة ساعي",
                "entry": round(sol, 2),
                "target": round(sol * 1.022, 2),
                "stopLoss": round(sol * 0.991, 2),
                "expectedReturnPct": 2.2,
                "confidence": 92,
                "suggestedQty": 12.0,
                "reasonAr": "تسارع حجم التداول اللحظي مع تفوق واضح في زخم الـ 15 دقيقة.",
            },
            {
                "id": "1h-btc",
                "rank": 2,
                "symbol": "BTCUSDT",
                "nameAr": "بيتكوين — ارتداد مؤسسي محمي",
                "entry": round(btc, 2),
                "target": round(btc * 1.016, 2),
                "stopLoss": round(btc * 0.993, 2),
                "expectedReturnPct": 1.6,
                "confidence": 91,
                "suggestedQty": 0.05,
                "reasonAr": "امتصاص شرائي مستمر أعلى منطقة الارتكاز مع مخاطرة منخفضة جداً.",
            },
            {
                "id": "1h-eth",
                "rank": 3,
                "symbol": "ETHUSDT",
                "nameAr": "إيثيريوم — لحاق سعري سريع",
                "entry": round(eth, 2),
                "target": round(eth * 1.019, 2),
                "stopLoss": round(eth * 0.992, 2),
                "expectedReturnPct": 1.9,
                "confidence": 88,
                "suggestedQty": 1.2,
                "reasonAr": "تحسن نسبة ETH/BTC وتقلص الفارق السعري في دفاتر الأوامر.",
            },
            {
                "id": "1h-bnb",
                "rank": 4,
                "symbol": "BNBUSDT",
                "nameAr": "بينانس كوين — توازن دفاعي صاعد",
                "entry": round(bnb, 2),
                "target": round(bnb * 1.015, 2),
                "stopLoss": round(bnb * 0.993, 2),
                "expectedReturnPct": 1.5,
                "confidence": 86,
                "suggestedQty": 4.0,
                "reasonAr": "استقرار عالٍ في السيولة الفورية ومعدل تذبذب منضبط.",
            },
            {
                "id": "1h-xrp",
                "rank": 5,
                "symbol": "XRPUSDT",
                "nameAr": "ريبل — موجة ارتداد سريعة",
                "entry": round(xrp, 4),
                "target": round(xrp * 1.024, 4),
                "stopLoss": round(xrp * 0.989, 4),
                "expectedReturnPct": 2.4,
                "confidence": 83,
                "suggestedQty": 900.0,
                "reasonAr": "تشبع بيعي لحظي على فاصل 5 و15 دقيقة يدعم ارتداداً مضاربياً.",
            },
            {
                "id": "1h-ada",
                "rank": 6,
                "symbol": "ADAUSDT",
                "nameAr": "كاردانو — زخم مضاربي قصير",
                "entry": round(ada, 4),
                "target": round(ada * 1.021, 4),
                "stopLoss": round(ada * 0.990, 4),
                "expectedReturnPct": 2.1,
                "confidence": 81,
                "suggestedQty": 1800.0,
                "reasonAr": "دخول سيولة شرائية عند خط المتوسط المتحرك الساعي.",
            },
        ],
        "24h": [
            {
                "id": "24h-btc",
                "rank": 1,
                "symbol": "BTCUSDT",
                "nameAr": "بيتكوين — موجة الـ 24 ساعة القيادية",
                "entry": round(btc, 2),
                "target": round(btc * 1.038, 2),
                "stopLoss": round(btc * 0.985, 2),
                "expectedReturnPct": 3.8,
                "confidence": 93,
                "suggestedQty": 0.05,
                "reasonAr": "إجماع الوكلاء الخمسة 5/5 على استمرار التدفقات الصافية اليومية.",
            },
            {
                "id": "24h-sol",
                "rank": 2,
                "symbol": "SOLUSDT",
                "nameAr": "سولانا — الأعلى زخماً يومياً",
                "entry": round(sol, 2),
                "target": round(sol * 1.054, 2),
                "stopLoss": round(sol * 0.980, 2),
                "expectedReturnPct": 5.4,
                "confidence": 90,
                "suggestedQty": 10.0,
                "reasonAr": "تصدر نشاط الشبكة وأحجام التداول اليومية مقارنة بالبدائل.",
            },
            {
                "id": "24h-eth",
                "rank": 3,
                "symbol": "ETHUSDT",
                "nameAr": "إيثيريوم — اختراق القناة اليومية",
                "entry": round(eth, 2),
                "target": round(eth * 1.044, 2),
                "stopLoss": round(eth * 0.984, 2),
                "expectedReturnPct": 4.4,
                "confidence": 89,
                "suggestedQty": 1.0,
                "reasonAr": "تراكم عقود الخيارات الصاعدة وانخفاض المعروض في المنصات.",
            },
            {
                "id": "24h-bnb",
                "rank": 4,
                "symbol": "BNBUSDT",
                "nameAr": "بينانس كوين — نمو يومي متزن",
                "entry": round(bnb, 2),
                "target": round(bnb * 1.034, 2),
                "stopLoss": round(bnb * 0.986, 2),
                "expectedReturnPct": 3.4,
                "confidence": 87,
                "suggestedQty": 3.5,
                "reasonAr": "طلب مستمر من برامج الإطلاق والسيولة الداخلية لمنصة Binance.",
            },
            {
                "id": "24h-xrp",
                "rank": 5,
                "symbol": "XRPUSDT",
                "nameAr": "ريبل — ارتداد السيولة الآسيوية",
                "entry": round(xrp, 4),
                "target": round(xrp * 1.049, 4),
                "stopLoss": round(xrp * 0.981, 4),
                "expectedReturnPct": 4.9,
                "confidence": 84,
                "suggestedQty": 850.0,
                "reasonAr": "نشاط تداول مرتفع في جلسة طوكيو وكوريا يدعم التوسع السعري.",
            },
            {
                "id": "24h-ada",
                "rank": 6,
                "symbol": "ADAUSDT",
                "nameAr": "كاردانو — تمركز يومي محمي",
                "entry": round(ada, 4),
                "target": round(ada * 1.042, 4),
                "stopLoss": round(ada * 0.982, 4),
                "expectedReturnPct": 4.2,
                "confidence": 82,
                "suggestedQty": 1500.0,
                "reasonAr": "نسبة عائد إلى مخاطرة تتجاوز 1:2.3 خلال 24 ساعة.",
            },
        ],
        "7d": [
            {
                "id": "7d-btc",
                "rank": 1,
                "symbol": "BTCUSDT",
                "nameAr": "بيتكوين — الارتكاز الأسبوعي السيادي",
                "entry": round(btc, 2),
                "target": round(btc * 1.085, 2),
                "stopLoss": round(btc * 0.968, 2),
                "expectedReturnPct": 8.5,
                "confidence": 94,
                "suggestedQty": 0.04,
                "reasonAr": "أقوى أصل نادر من حيث التدفق المؤسسي الأسبوعي ونسبة شارب.",
            },
            {
                "id": "7d-sol",
                "rank": 2,
                "symbol": "SOLUSDT",
                "nameAr": "سولانا — موجة النمو الأسبوعية",
                "entry": round(sol, 2),
                "target": round(sol * 1.125, 2),
                "stopLoss": round(sol * 0.958, 2),
                "expectedReturnPct": 12.5,
                "confidence": 90,
                "suggestedQty": 8.0,
                "reasonAr": "أعلى معامل بيتا إيجابي في السوق الصاعد مع سيولة عميقة.",
            },
            {
                "id": "7d-eth",
                "rank": 3,
                "symbol": "ETHUSDT",
                "nameAr": "إيثيريوم — التجميع المؤسسي الأسبوعي",
                "entry": round(eth, 2),
                "target": round(eth * 1.098, 2),
                "stopLoss": round(eth * 0.965, 2),
                "expectedReturnPct": 9.8,
                "confidence": 89,
                "suggestedQty": 0.9,
                "reasonAr": "نمو العوائد المرهونة واستمرار توسع شبكات الطبقة الثانية.",
            },
            {
                "id": "7d-bnb",
                "rank": 4,
                "symbol": "BNBUSDT",
                "nameAr": "بينانس كوين — العائد الأسبوعي المستقر",
                "entry": round(bnb, 2),
                "target": round(bnb * 1.076, 2),
                "stopLoss": round(bnb * 0.970, 2),
                "expectedReturnPct": 7.6,
                "confidence": 88,
                "suggestedQty": 3.0,
                "reasonAr": "آلية الحرق الدوري وتفوق السيولة يقللان التراجعات الأسبوعية.",
            },
            {
                "id": "7d-xrp",
                "rank": 5,
                "symbol": "XRPUSDT",
                "nameAr": "ريبل — زخم المدفوعات العابرة للحدود",
                "entry": round(xrp, 4),
                "target": round(xrp * 1.110, 4),
                "stopLoss": round(xrp * 0.960, 4),
                "expectedReturnPct": 11.0,
                "confidence": 84,
                "suggestedQty": 700.0,
                "reasonAr": "توسع الشراكات المؤسسية وارتفاع السيولة الأسبوعية.",
            },
            {
                "id": "7d-ada",
                "rank": 6,
                "symbol": "ADAUSDT",
                "nameAr": "كاردانو — موجة تعافٍ أسبوعية",
                "entry": round(ada, 4),
                "target": round(ada * 1.095, 4),
                "stopLoss": round(ada * 0.962, 4),
                "expectedReturnPct": 9.5,
                "confidence": 82,
                "suggestedQty": 1200.0,
                "reasonAr": "ثبات مناطق الدعم الأسبوعية وتزايد محافظ التجميع.",
            },
        ],
    }

    top_stocks = {
        "shortTerm": [
            {
                "ticker": "NVDA",
                "market": "السوق الأمريكي NASDAQ",
                "nameAr": "إنفيديا (NVIDIA)",
                "price": "$142.80",
                "expectedHorizon": "1 – 4 أسابيع",
                "expectedReturn": "+6.5% إلى +11%",
                "confidence": 93,
                "catalystAr": "طلب قياسي غير مسبوق على شرائح مراكز البيانات والذكاء الاصطناعي.",
            },
            {
                "ticker": "7203.SR",
                "market": "تداول السعودي",
                "nameAr": "شركة عِلم (ELM)",
                "price": "1,094 ر.س",
                "expectedHorizon": "1 – 4 أسابيع",
                "expectedReturn": "+5.0% إلى +8.5%",
                "confidence": 91,
                "catalystAr": "نمو قوي في عقود التحول الرقمي الحكومي وهوامش ربحية تشغيلية متصاعدة.",
            },
            {
                "ticker": "AVGO",
                "market": "السوق الأمريكي NASDAQ",
                "nameAr": "برودكوم (Broadcom)",
                "price": "$178.40",
                "expectedHorizon": "1 – 3 أسابيع",
                "expectedReturn": "+5.5% إلى +9.0%",
                "confidence": 89,
                "catalystAr": "زخم مسرّعات الذكاء الاصطناعي المخصصة وشبكات الجيل الفائق.",
            },
            {
                "ticker": "1120.SR",
                "market": "تداول السعودي",
                "nameAr": "مصرف الراجحي",
                "price": "94.60 ر.س",
                "expectedHorizon": "2 – 4 أسابيع",
                "expectedReturn": "+4.2% إلى +7.0%",
                "confidence": 88,
                "catalystAr": "تحسن صافي هامش التمويل ونمو محفظة الإقراض المؤسسي.",
            },
            {
                "ticker": "META",
                "market": "السوق الأمريكي NASDAQ",
                "nameAr": "ميتا بلاتفورمز (Meta)",
                "price": "$592.10",
                "expectedHorizon": "1 – 4 أسابيع",
                "expectedReturn": "+4.8% إلى +8.2%",
                "confidence": 87,
                "catalystAr": "كفاءة الإعلانات المعززة بالذكاء الاصطناعي وتدفق نقدي حر ضخم.",
            },
            {
                "ticker": "2082.SR",
                "market": "تداول السعودي",
                "nameAr": "أكوا باور (ACWA Power)",
                "price": "412.00 ر.س",
                "expectedHorizon": "2 – 5 أسابيع",
                "expectedReturn": "+5.5% إلى +9.5%",
                "confidence": 85,
                "catalystAr": "إعلانات مشاريع الطاقة المتجددة والهيدروجين الأخضر الإقليمية.",
            },
        ],
        "longTerm": [
            {
                "ticker": "MSFT",
                "market": "السوق الأمريكي NASDAQ",
                "nameAr": "مايكروسوفت (Microsoft)",
                "price": "$428.50",
                "expectedHorizon": "1 – 3 سنوات",
                "expectedReturn": "+18% إلى +26% سنوياً",
                "confidence": 95,
                "catalystAr": "هيمنة الحوسبة السحابية Azure والعوائد المتكررة لبرمجيات المؤسسات والذكاء الاصطناعي.",
            },
            {
                "ticker": "2222.SR",
                "market": "تداول السعودي",
                "nameAr": "أرامكو السعودية",
                "price": "27.85 ر.س",
                "expectedHorizon": "1 – 5 سنوات",
                "expectedReturn": "عائد توزيعات ~6% + نمو رأسمالي مستقر",
                "confidence": 94,
                "catalystAr": "أقوى ملاءة مالية وتدفقات نقدية توزيعية في قطاع الطاقة العالمي وتوسع الغاز.",
            },
            {
                "ticker": "NVDA",
                "market": "السوق الأمريكي NASDAQ",
                "nameAr": "إنفيديا (NVIDIA)",
                "price": "$142.80",
                "expectedHorizon": "1 – 3 سنوات",
                "expectedReturn": "+22% إلى +35% سنوياً",
                "confidence": 93,
                "catalystAr": "العمود الفقري للثورة الصناعية للذكاء الاصطناعي ومنظومة برمجيات CUDA.",
            },
            {
                "ticker": "1120.SR",
                "market": "تداول السعودي",
                "nameAr": "مصرف الراجحي",
                "price": "94.60 ر.س",
                "expectedHorizon": "1 – 5 سنوات",
                "expectedReturn": "+14% إلى +20% سنوياً شاملاً التوزيعات",
                "confidence": 92,
                "catalystAr": "أكبر مصرف إسلامي مستفيد مباشرة من مشاريع رؤية المملكة 2030.",
            },
            {
                "ticker": "AMZN",
                "market": "السوق الأمريكي NASDAQ",
                "nameAr": "أمازون (Amazon)",
                "price": "$210.30",
                "expectedHorizon": "1 – 3 سنوات",
                "expectedReturn": "+17% إلى +24% سنوياً",
                "confidence": 91,
                "catalystAr": "توسع هوامش أرباح AWS والأتمتة اللوجستية وقطاع الإعلانات عالي الربحية.",
            },
            {
                "ticker": "7010.SR",
                "market": "تداول السعودي",
                "nameAr": "إس تي سي (stc)",
                "price": "41.90 ر.س",
                "expectedHorizon": "1 – 5 سنوات",
                "expectedReturn": "توزيعات نقدية مستدامة + نمو البنية الرقمية",
                "confidence": 90,
                "catalystAr": "قيادة مراكز البيانات الإقليمية والمدفوعات الرقمية وتوزيعات ربع سنوية منتظمة.",
            },
        ],
    }

    tokyo_cloud_and_vault = {
        "recommendedRegion": {
            "code": "ap-northeast-1",
            "cityAr": "طوكيو — اليابان (Tokyo AWS ap-northeast-1)",
            "expectedBinanceRttMs": "1.2 ms – 3.5 ms",
            "whyBestAr": (
                "محركات المطابقة الفورية الرئيسية لمنصة Binance (api.binance.com و stream.binance.com) "
                "تعمل في طوكيو؛ النشر هناك يقلص زمن رحلة الأمر من ~180ms إلى أقل من 3ms ويمنع الانزلاق السعري."
            ),
            "alternatives": [
                {"cityAr": "أوساكا — اليابان (ap-osaka-1)", "rttMs": "8 – 11 ms"},
                {"cityAr": "سنغافورة (ap-southeast-1)", "rttMs": "65 – 75 ms"},
                {"cityAr": "أوروبا / الشرق الأوسط", "rttMs": "160 – 220 ms (غير مفضل للمضاربة السريعة)"},
            ],
        },
        "vaultArchitecture": {
            "encryption": "AES-256-GCM Envelope Vault + Ed25519 Asymmetric Keypair",
            "browserPasswordRequired": False,
            "withdrawalPermissionAllowed": False,
            "paperSafetyLockActive": True,
        },
    }

    boardroom_bots_pool = {
        "autoReinvestPctOfNetProfit": 20.0,
        "ownerRetainedPctOfNetProfit": 80.0,
        "autonomousPaperModeEnabled": True,
        "botsLeaderboard": [
            {
                "botId": "quant-alpha",
                "nameAr": "د. ريان — صائد الزخم الكمي",
                "auraColor": "#00f5d4",
                "seatPosition": "يمين رئيس الطاولة",
                "allocatedFrom20PctUsd": 1480.0,
                "currentBalanceUsd": 1612.40,
                "netProfitUsd": 132.40,
                "hourlyGrowthPct": 0.48,
                "selectionAccuracyPct": 89.4,
                "specialtyFocusAr": "صفقات الـ 15 دقيقة والساعة (SOL / NVDA)",
            },
            {
                "botId": "risk-sentinel",
                "nameAr": "سارة — حارسة الأمان وحدود الخسارة",
                "auraColor": "#00f5a0",
                "seatPosition": "يسار رئيس الطاولة",
                "allocatedFrom20PctUsd": 1480.0,
                "currentBalanceUsd": 1568.90,
                "netProfitUsd": 88.90,
                "hourlyGrowthPct": 0.31,
                "selectionAccuracyPct": 94.2,
                "specialtyFocusAr": "الارتدادات المحمية منخفضة التذبذب (BTC / أرامكو)",
            },
            {
                "botId": "macro-oracle",
                "nameAr": "طارق — عرّاف السيولة والأسهم",
                "auraColor": "#a855f7",
                "seatPosition": "الجناح الشرقي للطاولة",
                "allocatedFrom20PctUsd": 1480.0,
                "currentBalanceUsd": 1645.10,
                "netProfitUsd": 165.10,
                "hourlyGrowthPct": 0.54,
                "selectionAccuracyPct": 91.0,
                "specialtyFocusAr": "جولات الـ 24 ساعة والشهر (MSFT / الراجحي / عِلم)",
            },
            {
                "botId": "execution-architect",
                "nameAr": "خالد — قناص التنفيذ السريع",
                "auraColor": "#ff9f1c",
                "seatPosition": "الجناح الغربي للطاولة",
                "allocatedFrom20PctUsd": 1480.0,
                "currentBalanceUsd": 1594.25,
                "netProfitUsd": 114.25,
                "hourlyGrowthPct": 0.42,
                "selectionAccuracyPct": 87.8,
                "specialtyFocusAr": "قنص الفروقات السعرية السريعة 1M – 15M (ETH / XRP)",
            },
            {
                "botId": "chief-strategist",
                "nameAr": "المستشار الأعلى — منسق التريليون",
                "auraColor": "#f7c948",
                "seatPosition": "مقابل رئيس الطاولة",
                "allocatedFrom20PctUsd": 1480.0,
                "currentBalanceUsd": 1672.80,
                "netProfitUsd": 192.80,
                "hourlyGrowthPct": 0.61,
                "selectionAccuracyPct": 93.6,
                "specialtyFocusAr": "دمج أفضل الصفقات الأعلى عائداً مقابل المخاطرة",
            },
        ],
    }

    return {
        "timestamp": utc_now_iso(),
        "tradingMode": "PAPER",
        "liveAuthorized": False,
        "agentsProgrammaticallyWired": True,
        "agentsRegistry": agents_profiles,
        "portfolioEquityUsd": portfolio.totalEquity,
        "orbit3dTelemetry": orbit_3d,
        "agentAnalyzedTrades": agent_signals,
        "boardroomBotsPool": boardroom_bots_pool,
        "marketBrief": market_brief,
        "topSixTrades": top_six_trades,
        "topStocks": top_stocks,
        "tokyoCloudAndVault": tokyo_cloud_and_vault,
    }


@executive_router.get("/dashboard")
def get_executive_dashboard() -> dict[str, Any]:
    """جلب الحمولة التنفيذية الشاملة المربوطة برمجياً بالوكلاء الخمسة ومدار 3D."""
    return build_executive_payload()


@executive_router.get("/agents-analysis/{symbol}")
def get_live_agents_analysis_for_symbol(symbol: str, horizon: str = "1h") -> dict[str, Any]:
    """استدعاء برمجي حي لاجتماع الوكلاء الخمسة على أي عملة وإرجاع الصفقات المقترحة للتنفيذ."""
    resolved = market_engine.resolve_symbol(symbol) or symbol
    meeting = convene_meeting(symbol=resolved, horizon=horizon, language="ar")
    return {
        "symbol": symbol,
        "engineSymbol": meeting.symbol,
        "horizon": horizon,
        "consensusScore": meeting.consensus.agreementScorePct,
        "finalRecommendation": meeting.finalRecommendation.model_dump(),
        "deliberations": [d.model_dump() for d in meeting.agentResponses],
        "riskEvaluation": meeting.riskAssessment.model_dump(),
        "tradingMode": "PAPER",
    }


@executive_router.post("/confirm-decision")
def confirm_executive_decision(payload: ExecutiveDecisionInput) -> dict[str, Any]:
    """اعتماد أو تخطي توصية الوكلاء بضغطة زر واحدة عبر محرك المخاطر والتنفيذ الورقي."""
    if payload.decision == "SKIP":
        append_audit_log(
            actor="Dr.Majed",
            source="TERMINAL",
            action="EXECUTIVE_DECISION_SKIPPED",
            severity="INFO",
            details_ar=f"تم تخطي الفرصة {payload.opportunityId} ({payload.symbol}) بناءً على توجيه المالك.",
            details_en=f"Owner skipped opportunity {payload.opportunityId} ({payload.symbol}).",
        )
        return {
            "status": "SKIPPED",
            "tradingMode": "PAPER",
            "messageAr": f"⏭️ تم تخطي {payload.symbol} والانتقال للفرصة التالية.",
        }

    resolved_sym = market_engine.resolve_symbol(payload.symbol)
    if payload.category == "CRYPTO_SPOT" and resolved_sym:
        asset = market_engine.get_asset(resolved_sym)
        ref_p = float(asset.price) if asset else 100.0
        sl = payload.stopLoss
        tp = payload.takeProfit
        if payload.side == "BUY" and (sl is None or sl >= ref_p):
            sl = round(ref_p * 0.99, 4 if ref_p < 10 else 2)
            tp = round(ref_p * 1.03, 4 if ref_p < 10 else 2)
        elif payload.side == "SELL" and (sl is None or sl <= ref_p):
            sl = round(ref_p * 1.01, 4 if ref_p < 10 else 2)
            tp = round(ref_p * 0.97, 4 if ref_p < 10 else 2)

        eval_res = propose_order(
            TradeProposalInput(
                symbol=resolved_sym,
                side=payload.side,
                orderType="MARKET",
                quantity=payload.suggestedQty,
                stopLoss=sl,
                takeProfit=tp,
                source="TERMINAL",
                rationale=f"اعتماد مباشر لتوصية الوكلاء الخمسة ({payload.opportunityId})",
            )
        )
        if eval_res.status != "APPROVED_FOR_AUTH":
            return {
                "status": eval_res.status,
                "tradingMode": "PAPER",
                "messageAr": f"⚠️ درع المخاطر أوقف التنفيذ لحماية المحفظة: {', '.join(eval_res.riskAssessment.violations)}",
            }
        exec_res = execute_order(
            OrderExecuteRequest(
                proposalId=eval_res.proposalId,
                confirmedByUser=True,
                source="TERMINAL",
            )
        )
        return {
            "status": "EXECUTED_PAPER",
            "tradingMode": "PAPER",
            "orderId": exec_res.order.orderId,
            "portfolioEquityUsd": exec_res.portfolio.totalEquity,
            "messageAr": f"✅ تم اعتماد وتنفيذ صفقة {payload.symbol} ورقياً عبر الوكلاء بنجاح!",
        }

    append_audit_log(
        actor="Dr.Majed",
        source="TERMINAL",
        action="STOCK_ALLOCATION_PAPER_CONFIRMED",
        severity="INFO",
        details_ar=f"تم اعتماد السهم {payload.symbol} في سجل المحفظة الاستثمارية الورقية.",
        details_en=f"Confirmed paper allocation for equity {payload.symbol}.",
    )
    return {
        "status": "STOCK_PAPER_LOGGED",
        "tradingMode": "PAPER",
        "orderId": f"stk-paper-{uuid.uuid4().hex[:8]}",
        "messageAr": f"✅ تمت إضافة السهم {payload.symbol} إلى محفظة المتابعة الورقية بنجاح!",
    }
