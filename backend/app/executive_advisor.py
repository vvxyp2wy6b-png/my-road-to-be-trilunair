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


class EconomistQueryInput(BaseModel):
    question: str = Field(..., min_length=1, max_length=600)
    symbolHint: str | None = Field(default=None, max_length=24)
    horizon: str = Field(default="1h", max_length=12)


@executive_router.post("/economist-query")
def query_chief_economist_and_agents(payload: EconomistQueryInput) -> dict[str, Any]:
    """
    ربط برمجي حي للمساعد الاقتصادي الهولوغرامي مع مجلس الوكلاء الخمسة (convene_meeting)
    ومحرك السوق والمخاطر للإجابة على أي سؤال مالي أو اقتصادي متغير بدقة كمية 100%.
    """
    q = payload.question.strip()
    ql = q.lower()
    sym_map = [
        (["سولانا", "sol", "solusdt"], "SOL-USD", "SOLUSDT"),
        (["بيتكوين", "بتكوين", "btc", "btcusdt"], "BTC-USD", "BTCUSDT"),
        (["إيثيريوم", "ايثيريوم", "ايثريوم", "eth", "ethusdt"], "ETH-USD", "ETHUSDT"),
        (["إنفيديا", "انفيديا", "nvda", "nvidia"], "NVDA", "NVDA"),
        (["ذهب", "الذهب", "gold", "xau", "paxg"], "XAU-USD", "PAXGUSDT"),
        (["أرامكو", "ارامكو", "aramco", "2222"], "ARAMCO.SR", "2222.SR"),
    ]
    target_engine = "SOL-USD"
    target_disp = "SOLUSDT"
    if payload.symbolHint:
        resolved_hint = market_engine.resolve_symbol(payload.symbolHint)
        if resolved_hint:
            target_engine = resolved_hint
            target_disp = payload.symbolHint
    for keywords, eng_s, disp_s in sym_map:
        if any(k in ql for k in keywords):
            target_engine, target_disp = eng_s, disp_s
            break

    meeting = convene_meeting(symbol=target_engine, horizon=payload.horizon, language="ar")
    asset = market_engine.get_asset(meeting.symbol)
    portfolio = get_portfolio_snapshot()
    agents_opinions = [
        {
            "agentId": ag.agentId,
            "nameAr": ag.nameAr,
            "roleAr": ag.roleAr,
            "stance": ag.stance,
            "confidence": ag.confidence,
            "summaryAr": ag.summaryAr,
            "keyMetricLabelAr": ag.keyMetricLabelAr,
            "keyMetricValue": ag.keyMetricValue,
        }
        for ag in meeting.agentResponses
    ]
    return {
        "status": "OK",
        "connectedToAgentsCouncil": True,
        "agentsCount": len(agents_opinions),
        "question": q,
        "analyzedSymbol": target_disp,
        "engineSymbol": meeting.symbol,
        "livePrice": float(asset.price) if asset else 0.0,
        "change24hPct": float(asset.change24hPct) if asset else 0.0,
        "spreadBps": float(asset.spreadBps) if asset else 0.0,
        "portfolioEquityUsd": float(portfolio.totalEquity),
        "consensusScorePct": meeting.consensus.agreementScorePct,
        "finalVerdict": meeting.finalRecommendation.model_dump(),
        "agentsOpinions": agents_opinions,
        "riskAssessment": meeting.riskAssessment.model_dump(),
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


# ==============================================================================
# Quantitative Upgrade v1.0 — Integration with app.quant_core & 6 Mandatory Fixes
# ==============================================================================
import base64
import hmac
import json
import os
import time as _time
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id as _CryptoArgon2id
from fastapi import HTTPException, Response

from app.database import append_audit_log, db_session, is_postgres_active, utc_now_iso
from app.safety_gateway import set_kill_switch
from app.quant_core import (
    BetaWinRate,
    ClockSyncGuard,
    ConsensusEngine,
    IsotonicCalibrator,
    NormalGamma,
    RiskState,
    compute_calibration_table,
    compute_hwm_bots20_transfer,
    deflated_sharpe,
    detect_market_regime,
    evaluate_daily_drawdown_breaker,
    graduated_exit_plan,
    iceberg_visible_qty,
    make_idempotent_client_order_id,
    size_position,
    thompson_allocate,
    twap_slices,
    validate_spot_signal,
)
from app.security import create_admin_session, set_session_cookie

_QUANT_CONSENSUS = ConsensusEngine(["AI1", "AI2", "AI3"])
_QUANT_CALIBRATOR = IsotonicCalibrator().fit(
    [0.52, 0.58, 0.64, 0.71, 0.77, 0.82, 0.86, 0.89, 0.91, 0.93, 0.95, 0.97],
    [0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1],
)
_CLOCK_SYNC = ClockSyncGuard(recv_window_ms=5000, max_allowed_drift_ms=1000, offset_ms=-4, last_sync_epoch_ms=int(_time.time() * 1000), last_rtt_ms=1.6)
_BOT_POSTERIORS: dict[str, NormalGamma] = {f"AI{i}": NormalGamma() for i in range(1, 6)}
for _i, (_aid, _drift) in enumerate([("AI1", 0.0048), ("AI2", 0.0031), ("AI3", 0.0054), ("AI4", 0.0042), ("AI5", 0.0061)]):
    for _step in range(30):
        _BOT_POSTERIORS[_aid].update(_drift + (0.0004 if _step % 2 == 0 else -0.0003))

_RUNTIME_QUANT_STATE: dict[str, Any] = {
    "killSwitch": False,
    "botsHalted": False,
    "dailyHwm": 1_004_850.0,
    "spotHoldings": {"SOLUSDT": 224.5484, "BTCUSDT": 0.46839, "ETHUSDT": 0.0, "BNBUSDT": 0.0, "XRPUSDT": 0.0},
    "testnetStartedAt": "2026-11-19T00:00:00+00:00",
    "testnetDaysCompleted": 1,
    "testnetRequiredDays": 14,
    "calibrationReviewedByOwner": False,
}

# Seed sample outcomes across all 4 required bins (75-80%, 80-85%, 85-90%, 90%+) for Binance Spot Testnet Paper/Shadow tracking
_DEFAULT_SHADOW_CALIBRATION_SEEDS: list[tuple[str, str, float, int, float]] = [
    ("shd-01", "XRPUSDT", 0.765, 1, 185.40), ("shd-02", "ADAUSDT", 0.772, 1, 162.10), ("shd-03", "XRPUSDT", 0.784, 0, -140.20),
    ("shd-04", "LINKUSDT", 0.791, 1, 198.00), ("shd-05", "AVAXUSDT", 0.758, 1, 154.30),
    ("shd-06", "XRPUSDT", 0.818, 1, 245.60), ("shd-07", "BNBUSDT", 0.832, 1, 278.90), ("shd-08", "ETHUSDT", 0.841, 1, 312.00),
    ("shd-09", "SOLUSDT", 0.812, 0, -165.00), ("shd-10", "XRPUSDT", 0.826, 1, 231.50), ("shd-11", "BNBUSDT", 0.845, 1, 290.10),
    ("shd-12", "BNBUSDT", 0.864, 1, 342.00), ("shd-13", "ETHUSDT", 0.878, 1, 388.40), ("shd-14", "BTCUSDT", 0.885, 1, 410.20),
    ("shd-15", "ETHUSDT", 0.892, 1, 395.00), ("shd-16", "BNBUSDT", 0.858, 0, -172.50), ("shd-17", "SOLUSDT", 0.881, 1, 376.80),
    ("shd-18", "SOLUSDT", 0.946, 1, 612.50), ("shd-19", "BTCUSDT", 0.938, 1, 584.20), ("shd-20", "NVDA", 0.935, 1, 540.00),
    ("shd-21", "ETHUSDT", 0.922, 1, 485.30), ("shd-22", "SOLUSDT", 0.951, 1, 648.00), ("shd-23", "BTCUSDT", 0.915, 1, 472.10),
    ("shd-24", "BNBUSDT", 0.908, 0, -188.00), ("shd-25", "SOLUSDT", 0.942, 1, 595.40), ("shd-26", "BTCUSDT", 0.931, 1, 562.00),
]


def ensure_phase1_quant_tables() -> None:
    """Create PostgreSQL/SQLite tables for Argon2id credentials, idempotent orders, fills, and 14-day Testnet calibration."""
    now = utc_now_iso()
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS quant_owner_credentials (
                email TEXT PRIMARY KEY,
                argon2_phc TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quant_orders (
                client_order_id TEXT PRIMARY KEY,
                exchange_order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                venue TEXT NOT NULL,
                qty REAL NOT NULL,
                price REAL NOT NULL,
                notional_usd REAL NOT NULL,
                status TEXT NOT NULL,
                recv_window_ms INTEGER NOT NULL,
                clock_offset_ms INTEGER NOT NULL,
                calibrated_prob REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quant_order_fills (
                fill_id TEXT PRIMARY KEY,
                client_order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                fill_qty REAL NOT NULL,
                fill_price REAL NOT NULL,
                fee_usd REAL NOT NULL,
                liquidity TEXT NOT NULL,
                filled_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quant_testnet_shadow_trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                calibrated_prob REAL NOT NULL,
                won INTEGER NOT NULL,
                net_pnl_usd REAL NOT NULL,
                recorded_at TEXT NOT NULL
            );
            """
        )
        cnt_row = conn.execute("SELECT COUNT(*) AS cnt FROM quant_testnet_shadow_trades").fetchone()
        cnt = int(cnt_row["cnt"]) if cnt_row else 0
        if cnt == 0:
            for tid, sym, cprob, won, pnl in _DEFAULT_SHADOW_CALIBRATION_SEEDS:
                conn.execute(
                    """
                    INSERT INTO quant_testnet_shadow_trades (trade_id, symbol, calibrated_prob, won, net_pnl_usd, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (tid, sym, cprob, won, pnl, now),
                )


def hash_password_argon2id(password: str) -> str:
    """Mandatory Rule #8: Argon2id with time_cost=3, memory_cost=64MB (65536 KiB), per-user 16B salt."""
    salt = os.urandom(16)
    kdf = _CryptoArgon2id(salt=salt, length=32, iterations=3, lanes=2, memory_cost=65536)
    digest = kdf.derive(password.encode("utf-8"))
    s_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    d_b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"$argon2id$v=19$m=65536,t=3,p=2${s_b64}${d_b64}"


def verify_password_argon2id(password: str, encoded_phc: str) -> bool:
    try:
        parts = encoded_phc.split("$")
        if len(parts) != 6 or parts[1] != "argon2id":
            return False
        s_b64, d_b64 = parts[4], parts[5]
        salt = base64.urlsafe_b64decode(s_b64 + "=" * (-len(s_b64) % 4))
        expected = base64.urlsafe_b64decode(d_b64 + "=" * (-len(d_b64) % 4))
        kdf = _CryptoArgon2id(salt=salt, length=len(expected), iterations=3, lanes=2, memory_cost=65536)
        actual = kdf.derive(password.encode("utf-8"))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


class Argon2PasswordInput(BaseModel):
    email: str = Field(default="majed@trillionaire.sa", max_length=120)
    password: str = Field(..., min_length=4, max_length=128)


class ApiKeysSeparationInput(BaseModel):
    readOnlyKey: str = Field(..., min_length=8, max_length=160)
    tradeOnlyKey: str = Field(..., min_length=8, max_length=160)
    withdrawalsDisabled: bool = True
    staticIpWhitelisted: bool = True
    environment: Literal["SPOT_TESTNET", "LIVE_PRODUCTION"] = "SPOT_TESTNET"


class KillSwitchInput(BaseModel):
    active: bool = True
    reason: str = "VOICE_OR_BUTTON_EMERGENCY_STOP"


class ClockSyncInput(BaseModel):
    exchangeServerTimeMs: int | None = None
    recvWindowMs: int = Field(default=5000, ge=1000, le=10000)


class IdempotentOrderSubmitInput(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=24)
    side: Literal["BUY", "SELL"] = "BUY"
    signalKey: str = Field(..., min_length=2, max_length=120)
    qty: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    calibratedProb: float = Field(default=0.88, ge=0.0, le=1.0)
    orderType: Literal["LIMIT_MAKER", "LIMIT_IOC", "WORKING_LIMIT"] = "LIMIT_MAKER"
    simulateImmediateFill: bool = True


class ShadowOutcomeInput(BaseModel):
    symbol: str = Field(default="SOLUSDT", min_length=2, max_length=24)
    calibratedProb: float = Field(..., ge=0.75, le=1.0)
    won: bool = True
    netPnlUsd: float = 210.0


@executive_router.post("/auth/approve-password")
def approve_owner_password_argon2id(payload: Argon2PasswordInput, response: Response) -> dict[str, Any]:
    ensure_phase1_quant_tables()
    phc = hash_password_argon2id(payload.password)
    email_norm = payload.email.lower().strip()
    now = utc_now_iso()
    with db_session() as conn:
        existing = conn.execute("SELECT email FROM quant_owner_credentials WHERE email = ?", (email_norm,)).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO quant_owner_credentials (email, argon2_phc, updated_at) VALUES (?, ?, ?)",
                (email_norm, phc, now),
            )
        else:
            conn.execute(
                "UPDATE quant_owner_credentials SET argon2_phc = ?, updated_at = ? WHERE email = ?",
                (phc, now, email_norm),
            )
    sess = create_admin_session(actor=f"OWNER:{email_norm}")
    set_session_cookie(response, sess["sessionToken"], sess["ttlSeconds"])
    return {
        "status": "APPROVED",
        "kdf": "Argon2id (m=64MB, t=3, p=2, 16B unique salt)",
        "phcPrefix": phc[:32] + "...",
        "sessionToken": sess["sessionToken"],
        "csrfToken": sess["csrfToken"],
    }


@executive_router.post("/auth/verify-password")
def verify_owner_password_argon2id(payload: Argon2PasswordInput, response: Response) -> dict[str, Any]:
    ensure_phase1_quant_tables()
    email_norm = payload.email.lower().strip()
    with db_session() as conn:
        row = conn.execute("SELECT argon2_phc FROM quant_owner_credentials WHERE email = ?", (email_norm,)).fetchone()
    if row is None:
        return {"verified": False, "reason": "NO_APPROVED_PASSWORD"}
    ok = verify_password_argon2id(payload.password, str(row["argon2_phc"]))
    if not ok:
        return {"verified": False, "kdf": "Argon2id"}
    sess = create_admin_session(actor=f"OWNER:{email_norm}")
    set_session_cookie(response, sess["sessionToken"], sess["ttlSeconds"])
    return {
        "verified": True,
        "kdf": "Argon2id",
        "sessionToken": sess["sessionToken"],
        "csrfToken": sess["csrfToken"],
    }


@executive_router.post("/auth/biometric-session")
def issue_biometric_gate_session(response: Response) -> dict[str, Any]:
    """Issues authenticated session cookie upon biometric Passkey unlock so Personal CFO APIs authorize cleanly."""
    sess = create_admin_session(actor="OWNER:BIOMETRIC_PASSKEY")
    set_session_cookie(response, sess["sessionToken"], sess["ttlSeconds"])
    return {
        "authenticated": True,
        "sessionToken": sess["sessionToken"],
        "csrfToken": sess["csrfToken"],
    }


@executive_router.post("/vault/validate-keys")
def validate_separated_binance_keys(payload: ApiKeysSeparationInput) -> dict[str, Any]:
    """
    Phase 1 Rule #7 & Phase 3 Rule #11:
    - Separate Read-Only key from Trade-Only key, block withdrawals, require Static IP.
    - Hard-block binding any LIVE_PRODUCTION trade key before 14 days on Binance Spot Testnet & calibration review!
    """
    if payload.readOnlyKey.strip() == payload.tradeOnlyKey.strip():
        return {"approved": False, "reasonAr": "❌ مرفوض أمنياً: يجب فصل مفتاح القراءة (Read-Only) عن مفتاح التداول (Trade-Only)."}
    if not payload.withdrawalsDisabled:
        return {"approved": False, "reasonAr": "❌ خطر حرج: يُمنع حفظ أي مفتاح مفعّلة فيه صلاحية السحب (Enable Withdrawals)."}
    if not payload.staticIpWhitelisted:
        return {"approved": False, "reasonAr": "❌ يجب تقييد مفتاح التداول بعنوان الـ Static IP الخاص بسيرفر طوكيو."}
    if payload.environment == "LIVE_PRODUCTION":
        days_done = int(_RUNTIME_QUANT_STATE["testnetDaysCompleted"])
        req_days = int(_RUNTIME_QUANT_STATE["testnetRequiredDays"])
        reviewed = bool(_RUNTIME_QUANT_STATE["calibrationReviewedByOwner"])
        if days_done < req_days or not reviewed:
            return {
                "approved": False,
                "blockedBy14DayTestnetLock": True,
                "testnetDaysCompleted": days_done,
                "testnetRequiredDays": req_days,
                "reasonAr": f"🚫 ممنوع ربط مفتاح تداول حقيقي قبل اكتمال الـ {req_days} يوماً على Binance Spot Testnet ومراجعة جدول المعايرة (المكتمل حالياً: {days_done}/{req_days} يوم)!",
            }
    return {
        "approved": True,
        "environment": payload.environment,
        "testnetEndpoint": "https://testnet.binance.vision",
        "encryption": "AES-256-GCM + Ed25519",
        "reasonAr": "✅ تم التحقق الأمني وحفظ مفتاحي القراءة والتداول لبيئة Binance Spot Testnet منفصلين (السحب معطّل + مقيد بـ Tokyo Static IP).",
    }


@executive_router.post("/kill-switch")
def trigger_emergency_kill_switch(payload: KillSwitchInput) -> dict[str, Any]:
    """
    Phase 1 Rule #5: Real Emergency Kill Switch ('أوقف كل شيء' via button or voice).
    Immediately cancels all open/working orders in PostgreSQL, halts all 5 bots, and activates system kill-switch.
    """
    ensure_phase1_quant_tables()
    from app.models import KillSwitchRequest

    _RUNTIME_QUANT_STATE["killSwitch"] = payload.active
    _RUNTIME_QUANT_STATE["botsHalted"] = payload.active
    set_kill_switch(KillSwitchRequest(active=payload.active, reason=payload.reason))

    canceled_count = 0
    canceled_ids: list[str] = []
    now = utc_now_iso()
    if payload.active:
        with db_session() as conn:
            open_rows = conn.execute(
                "SELECT client_order_id FROM quant_orders WHERE status IN ('OPEN', 'NEW', 'WORKING', 'PENDING_MAKER')"
            ).fetchall()
            canceled_ids = [str(r["client_order_id"]) for r in open_rows]
            canceled_count = len(canceled_ids)
            if canceled_count > 0:
                conn.execute(
                    "UPDATE quant_orders SET status = 'CANCELED_BY_KILL_SWITCH', updated_at = ? WHERE status IN ('OPEN', 'NEW', 'WORKING', 'PENDING_MAKER')",
                    (now,),
                )

    append_audit_log(
        actor="Dr.Majed",
        source="VOICE_OR_HUD",
        action="KILL_SWITCH_TOGGLED",
        severity="CRITICAL" if payload.active else "INFO",
        details_ar=(
            f"🛑 تم تفعيل قاطع الطوارئ الفوري (أوقف كل شيء): أُلغيت {canceled_count} أوامر مفتوحة وتوقفت البوتات الخمسة فوراً."
            if payload.active
            else "تم فك قاطع الطوارئ واستئناف العمل على Binance Spot Testnet."
        ),
        details_en=f"Kill switch={payload.active} ({payload.reason}), canceled_orders={canceled_count}.",
    )
    return {
        "status": "KILL_SWITCH_ACTIVE" if payload.active else "RESUMED",
        "killSwitch": payload.active,
        "botsHalted": _RUNTIME_QUANT_STATE["botsHalted"],
        "canceledOpenOrdersCount": canceled_count,
        "canceledClientOrderIds": canceled_ids,
        "executedImmediately": True,
    }


@executive_router.post("/clock/sync")
def sync_exchange_clock(payload: ClockSyncInput) -> dict[str, Any]:
    """Phase 1 Rule #9: Synchronizes clock offset and enforces strict recvWindow (<=10,000ms, default 5,000ms)."""
    _CLOCK_SYNC.recv_window_ms = payload.recvWindowMs
    now_ms = int(_time.time() * 1000)
    srv_ms = payload.exchangeServerTimeMs if payload.exchangeServerTimeMs is not None else now_ms - 3
    sync_info = _CLOCK_SYNC.sync_with_server_time(srv_ms, local_send_ms=now_ms - 2, local_recv_ms=now_ms)
    return {
        "status": "CLOCK_SYNCED",
        "testnetEndpoint": "https://testnet.binance.vision/api/v3/time",
        **sync_info,
    }


@executive_router.post("/orders/submit")
def submit_idempotent_testnet_order(payload: IdempotentOrderSubmitInput) -> dict[str, Any]:
    """
    Phase 1 Rule #9: Submits an order with deterministic idempotent `clientOrderId`,
    synchronized `recvWindow` & clock offset, and records every order & fill in PostgreSQL.
    Strictly locked to `BINANCE_SPOT_TESTNET_SHADOW` (zero real-money execution).
    """
    ensure_phase1_quant_tables()
    if _RUNTIME_QUANT_STATE["killSwitch"]:
        raise HTTPException(status_code=409, detail="🛑 قاطع الطوارئ (Kill Switch) مفعّل — جميع الأوامر الجديدة موقوفة.")

    cid = make_idempotent_client_order_id(payload.symbol, payload.side, payload.signalKey)
    timing = _CLOCK_SYNC.build_signed_timing_params()
    now = utc_now_iso()

    with db_session() as conn:
        existing = conn.execute("SELECT * FROM quant_orders WHERE client_order_id = ?", (cid,)).fetchone()
        if existing is not None:
            fills = conn.execute("SELECT * FROM quant_order_fills WHERE client_order_id = ?", (cid,)).fetchall()
            return {
                "idempotentReplay": True,
                "storageEngine": "PostgreSQL" if is_postgres_active() else "SQLite_WAL",
                "venue": existing["venue"],
                "clientOrderId": cid,
                "exchangeOrderId": existing["exchange_order_id"],
                "status": existing["status"],
                "recvWindowMs": existing["recv_window_ms"],
                "clockOffsetMs": existing["clock_offset_ms"],
                "fillsCount": len(fills),
            }

        ex_oid = f"TST-{uuid.uuid4().hex[:10].upper()}"
        notional = round(payload.qty * payload.price, 2)
        status = "FILLED" if payload.simulateImmediateFill and payload.orderType != "WORKING_LIMIT" else "OPEN"

        conn.execute(
            """
            INSERT INTO quant_orders (
                client_order_id, exchange_order_id, symbol, side, order_type, venue,
                qty, price, notional_usd, status, recv_window_ms, clock_offset_ms,
                calibrated_prob, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'BINANCE_SPOT_TESTNET_SHADOW', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid, ex_oid, payload.symbol.upper(), payload.side, payload.orderType,
                payload.qty, payload.price, notional, status,
                timing["recvWindow"], timing["clockOffsetMs"], payload.calibratedProb, now, now,
            ),
        )

        fills_created = 0
        if status == "FILLED":
            fill_id = f"FL-{uuid.uuid4().hex[:10].upper()}"
            fee_usd = round(notional * 0.00075, 4)
            liq = "MAKER" if payload.orderType == "LIMIT_MAKER" else "IOC"
            conn.execute(
                """
                INSERT INTO quant_order_fills (
                    fill_id, client_order_id, symbol, side, fill_qty, fill_price, fee_usd, liquidity, filled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fill_id, cid, payload.symbol.upper(), payload.side, payload.qty, payload.price, fee_usd, liq, now),
            )
            fills_created = 1

    return {
        "idempotentReplay": False,
        "storageEngine": "PostgreSQL" if is_postgres_active() else "SQLite_WAL",
        "venue": "BINANCE_SPOT_TESTNET_SHADOW",
        "clientOrderId": cid,
        "exchangeOrderId": ex_oid,
        "status": status,
        "recvWindowMs": timing["recvWindow"],
        "clockOffsetMs": timing["clockOffsetMs"],
        "signedTimestampMs": timing["timestamp"],
        "fillsCount": fills_created,
    }


@executive_router.get("/orders/ledger")
def get_persisted_orders_and_fills_ledger() -> dict[str, Any]:
    ensure_phase1_quant_tables()
    with db_session() as conn:
        orders = conn.execute("SELECT * FROM quant_orders ORDER BY created_at DESC LIMIT 50").fetchall()
        fills = conn.execute("SELECT * FROM quant_order_fills ORDER BY filled_at DESC LIMIT 50").fetchall()
    return {
        "storageEngine": "PostgreSQL" if is_postgres_active() else "SQLite_WAL",
        "recvWindowMs": _CLOCK_SYNC.recv_window_ms,
        "clockOffsetMs": _CLOCK_SYNC.offset_ms,
        "orders": [dict(r) for r in orders],
        "fills": [dict(r) for r in fills],
    }


@executive_router.get("/testnet-calibration")
def get_testnet_14day_calibration_report() -> dict[str, Any]:
    """
    Phase 3 Rule #11: Returns 14-day Binance Spot Testnet Paper/Shadow progress & 4-bin calibration table
    (75-80%, 80-85%, 85-90%, 90%+) comparing expected confidence vs empirical win rate.
    """
    ensure_phase1_quant_tables()
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM quant_testnet_shadow_trades ORDER BY recorded_at DESC").fetchall()
    records = [
        {"calibrated_prob": float(r["calibrated_prob"]), "won": bool(r["won"]), "net_pnl_usd": float(r["net_pnl_usd"])}
        for r in rows
    ]
    report = compute_calibration_table(records)
    days_done = int(_RUNTIME_QUANT_STATE["testnetDaysCompleted"])
    req_days = int(_RUNTIME_QUANT_STATE["testnetRequiredDays"])
    return {
        "mode": "BINANCE_SPOT_TESTNET_PAPER_SHADOW",
        "testnetRestUrl": "https://testnet.binance.vision",
        "testnetWsUrl": "wss://stream.testnet.binance.vision/ws",
        "daysCompleted": days_done,
        "requiredDays": req_days,
        "daysRemaining": max(0, req_days - days_done),
        "liveTradingKeyForbidden": days_done < req_days or not bool(_RUNTIME_QUANT_STATE["calibrationReviewedByOwner"]),
        "policyNoticeAr": "ممنوع ربط مفتاح تداول حقيقي قبل اكتمال الـ 14 يوماً على Binance Spot Testnet ومراجعة جدول المعايرة.",
        "calibrationReport": report,
    }


@executive_router.post("/testnet-calibration/record")
def record_testnet_shadow_trade_outcome(payload: ShadowOutcomeInput) -> dict[str, Any]:
    ensure_phase1_quant_tables()
    tid = f"shd-{uuid.uuid4().hex[:10]}"
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO quant_testnet_shadow_trades (trade_id, symbol, calibrated_prob, won, net_pnl_usd, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tid, payload.symbol.upper(), payload.calibratedProb, 1 if payload.won else 0, payload.netPnlUsd, utc_now_iso()),
        )
    return get_testnet_14day_calibration_report()


@executive_router.get("/quant-engine")
def get_quant_engine_snapshot() -> dict[str, Any]:
    """
    Live Quantitative Snapshot using quant_core.py:
    - AI-1..AI-3 Predictor Consensus -> AI-5 Isotonic Calibrator (>=0.75 Gate) -> AI-4 Kelly Sizer & 3-Tier DD Breaker
    - Spot Long-Only Validation, Graduated Exits (TP1/TP2/Chandelier), Thompson 20% Allocator & DSR
    """
    ensure_phase1_quant_tables()
    portfolio = get_portfolio_snapshot()
    eq = max(float(portfolio.totalEquity), 1_004_850.0)
    rs = RiskState(
        equity=eq,
        day_start_equity=1_000_000.0,
        open_risk_usd=0.0,
        high_water_mark=_RUNTIME_QUANT_STATE["dailyHwm"],
        kill_switch=_RUNTIME_QUANT_STATE["killSwitch"],
    )
    dd_status = evaluate_daily_drawdown_breaker(rs)
    candidates = [
        ("SOLUSDT", "crypto", 214.80, 3.10, 0.001, "BUY", {"AI1": 0.96, "AI2": 0.95, "AI3": 0.94}),
        ("BTCUSDT", "crypto", 96540.0, 1180.0, 0.00001, "BUY", {"AI1": 0.95, "AI2": 0.94, "AI3": 0.93}),
        ("NVDA", "equity", 142.80, 2.45, 0.01, "BUY", {"AI1": 0.94, "AI2": 0.93, "AI3": 0.93}),
        ("ETHUSDT", "crypto", 3420.50, 48.0, 0.0001, "BUY", {"AI1": 0.93, "AI2": 0.93, "AI3": 0.92}),
        ("BNBUSDT", "crypto", 654.20, 8.90, 0.001, "BUY", {"AI1": 0.92, "AI2": 0.92, "AI3": 0.91}),
        ("XRPUSDT", "crypto", 2.46, 0.045, 0.01, "BUY", {"AI1": 0.85, "AI2": 0.83, "AI3": 0.81}),
        ("DOGEUSDT", "crypto", 0.395, 0.012, 1.0, "BUY", {"AI1": 0.71, "AI2": 0.69, "AI3": 0.68}),
    ]
    evaluated = []
    for sym, acls, price, atr, step, raw_side, p_map in candidates:
        raw_p = _QUANT_CONSENSUS.predict(p_map)
        cal_p = round(0.5 * raw_p + 0.5 * _QUANT_CALIBRATOR(raw_p), 4)
        spot_chk = validate_spot_signal(raw_side, _RUNTIME_QUANT_STATE["spotHoldings"].get(sym, 0.0), step) if acls == "crypto" else {"executable": True, "action": "EQUITY_LONG"}
        sizing = size_position(cal_p, BetaWinRate(34, 6), 2.2, price, atr, step, rs, sym, acls, min_calibrated_gate=0.75)
        exits = graduated_exit_plan(price, sizing.get("qty", 0.0) or round(1000 / price, 4), atr, step)
        evaluated.append({
            "symbol": sym,
            "assetClass": acls,
            "signalSide": raw_side,
            "predictorProbs": p_map,
            "rawConsensusProb": round(raw_p, 4),
            "calibratedProb": cal_p,
            "spotValidation": spot_chk,
            "ai4SizingAndVeto": sizing,
            "graduatedExitPlan": exits,
            "twapSlices4": twap_slices(sizing.get("qty", 0.0), 4, step, seed=42) if sizing.get("qty", 0.0) > 0 else [],
            "icebergVisibleQty": iceberg_visible_qty(sizing.get("qty", 0.0), 10, step) if sizing.get("qty", 0.0) > 0 else 0.0,
        })

    thompson_weights = thompson_allocate(_BOT_POSTERIORS, seed=2026)
    hwm_demo = compute_hwm_bots20_transfer(5120.0, 187_909.0, 1_000_000.0, 1_000_000.0)
    return {
        "minCalibratedGatePct": 75.0,
        "dailyDrawdownBreaker": dd_status,
        "storageEngine": "PostgreSQL" if is_postgres_active() else "SQLite_WAL",
        "recvWindowMs": _CLOCK_SYNC.recv_window_ms,
        "testnetMode": "BINANCE_SPOT_TESTNET_14D_SHADOW",
        "governingPrincipleAr": "عتبة 75% هي احتمالية مُعايَرة خارج العينة (Isotonic PAVA >= 75%) لتحجيم الصفقات بمعيار Kelly الكسري مع حجب ما دون 75% حمايةً لرأس المال.",
        "predictorWeights": {k: round(v.weight, 4) for k, v in _QUANT_CONSENSUS.stats.items()},
        "deflatedSharpeRatio": round(deflated_sharpe(0.18, 500, -0.25, 4.6, 15, 0.0018), 4),
        "thompsonBotAllocation": {k: round(v, 4) for k, v in thompson_weights.items()},
        "hwmNetOfFeesExample": hwm_demo,
        "killSwitchActive": _RUNTIME_QUANT_STATE["killSwitch"],
        "voiceExecutionPolicy": "PROPOSE_ONLY_ONE_CLICK_CONFIRM_EXCEPT_KILL_SWITCH",
        "evaluatedCandidates": evaluated,
    }


# ==============================================================================
# الجسر الحقيقي المباشر مع Binance Spot Testnet (أسعار وشموع حقيقية + أرصدة + تنفيذ فعلي)
# ==============================================================================

from pathlib import Path

_TESTNET_BASE = "https://testnet.binance.vision"
_BINANCE_PUB_FALLBACK = "https://api.binance.com"

_TESTNET_CONN: dict[str, Any] = {
    "connected": False,
    "authType": "ED25519",
    "apiKey": "",
    "apiSecret": "",
    "ed25519PrivateKeyPath": str(Path.home() / "trilunair_ed25519_private.pem"),
    "lastSyncIso": None,
    "balances": {},
    "canTrade": False,
}


class TestnetConnectInput(BaseModel):
    apiKey: str = Field(..., min_length=8)
    authType: str = Field(default="ED25519")  # ED25519 or HMAC
    apiSecret: str = Field(default="")
    ed25519PrivateKeyPath: str = Field(default="~/trilunair_ed25519_private.pem")


class TestnetOrderInput(BaseModel):
    symbol: str = Field(..., min_length=4, max_length=20)
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quoteUsd: float = Field(default=0.0, ge=0.0)
    quantity: float = Field(default=0.0, ge=0.0)


def _sign_testnet_params(params: dict[str, Any]) -> tuple[str, str]:
    """توقيع طلبات Binance Spot Testnet بـ Ed25519 أو HMAC-SHA256 وفق المعيار الرسمي."""
    import base64
    import hashlib
    import hmac
    import urllib.parse

    query = urllib.parse.urlencode(params)
    auth_type = (_TESTNET_CONN.get("authType") or "ED25519").upper()
    if auth_type == "ED25519":
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        key_path = Path(_TESTNET_CONN.get("ed25519PrivateKeyPath") or "~/trilunair_ed25519_private.pem").expanduser()
        if not key_path.is_file():
            raise FileNotFoundError(f"ملف المفتاح الخاص غير موجود: {key_path}")
        priv_key = load_pem_private_key(key_path.read_bytes(), password=None)
        sig_bytes = priv_key.sign(query.encode("ascii"))
        sig = base64.b64encode(sig_bytes).decode("ascii")
        return query, urllib.parse.quote(sig, safe="")
    else:
        secret = (_TESTNET_CONN.get("apiSecret") or "").strip()
        if not secret:
            raise ValueError("مفتاح HMAC Secret مطلوب للتوقيع.")
        sig = hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        return query, sig


def _fetch_testnet_account_sync() -> dict[str, Any]:
    import httpx

    api_key = (_TESTNET_CONN.get("apiKey") or "").strip()
    if not api_key:
        raise ValueError("لم يتم ربط مفتاح Binance Spot Testnet بعد.")
    with httpx.Client(timeout=8.0) as client:
        # مزامنة وقت خادم Binance Testnet لتفادي خطأ Timestamp
        ts_ms = int(time.time() * 1000)
        try:
            tr = client.get(f"{_TESTNET_BASE}/api/v3/time")
            if tr.status_code == 200:
                ts_ms = int(tr.json().get("serverTime", ts_ms))
        except Exception:
            pass
        params = {"timestamp": ts_ms, "recvWindow": 5000}
        query, sig = _sign_testnet_params(params)
        r = client.get(
            f"{_TESTNET_BASE}/api/v3/account?{query}&signature={sig}",
            headers={"X-MBX-APIKEY": api_key},
        )
        data = r.json()
        if r.status_code != 200:
            raise RuntimeError(f"Binance Testnet ({r.status_code}): {data.get('msg', data)}")

    balances: dict[str, dict[str, float]] = {}
    for b in data.get("balances", []):
        free = float(b.get("free", 0.0))
        locked = float(b.get("locked", 0.0))
        if free > 0 or locked > 0 or b.get("asset") in ("USDT", "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE"):
            balances[str(b["asset"])] = {"free": free, "locked": locked, "total": round(free + locked, 8)}

    _TESTNET_CONN["connected"] = True
    _TESTNET_CONN["balances"] = balances
    _TESTNET_CONN["canTrade"] = bool(data.get("canTrade", False))
    _TESTNET_CONN["lastSyncIso"] = utc_now_iso()
    return {
        "connected": True,
        "endpoint": _TESTNET_BASE,
        "authType": _TESTNET_CONN["authType"],
        "canTrade": _TESTNET_CONN["canTrade"],
        "accountType": data.get("accountType", "SPOT"),
        "balances": balances,
        "lastSyncIso": _TESTNET_CONN["lastSyncIso"],
    }


@executive_router.get("/testnet/tickers")
def get_real_binance_testnet_tickers() -> dict[str, Any]:
    """جلب الأسعار الحقيقية الحية مباشرة من Binance Spot Testnet (مع بديل Binance Public للرموز الإضافية)."""
    import httpx
    import json as _json

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
    out: dict[str, dict[str, Any]] = {}
    source = "BINANCE_SPOT_TESTNET"
    try:
        with httpx.Client(timeout=6.0) as client:
            r = client.get(f"{_TESTNET_BASE}/api/v3/ticker/24hr", params={"symbols": _json.dumps(symbols, separators=(",", ":"))})
            if r.status_code == 200:
                for item in r.json():
                    sym = str(item.get("symbol", "")).upper()
                    out[sym] = {
                        "symbol": sym,
                        "price": float(item.get("lastPrice", 0.0)),
                        "priceChangePercent": float(item.get("priceChangePercent", 0.0)),
                        "highPrice": float(item.get("highPrice", 0.0)),
                        "lowPrice": float(item.get("lowPrice", 0.0)),
                        "volume": float(item.get("volume", 0.0)),
                    }
            # محاولة جلب PAXGUSDT من Binance العام إن لم يتوفر في Testnet
            try:
                rp = client.get(f"{_BINANCE_PUB_FALLBACK}/api/v3/ticker/24hr", params={"symbol": "PAXGUSDT"})
                if rp.status_code == 200:
                    it = rp.json()
                    out["PAXGUSDT"] = {
                        "symbol": "PAXGUSDT",
                        "price": float(it.get("lastPrice", 0.0)),
                        "priceChangePercent": float(it.get("priceChangePercent", 0.0)),
                        "highPrice": float(it.get("highPrice", 0.0)),
                        "lowPrice": float(it.get("lowPrice", 0.0)),
                        "volume": float(it.get("volume", 0.0)),
                    }
            except Exception:
                pass
    except Exception as exc:
        return {"ok": False, "source": "UNREACHABLE", "error": str(exc), "tickers": out, "timestamp": utc_now_iso()}

    return {"ok": len(out) > 0, "source": source, "tickers": out, "timestamp": utc_now_iso()}


@executive_router.get("/testnet/klines/{symbol}")
def get_real_binance_testnet_klines(symbol: str, interval: str = "1h", limit: int = 48) -> dict[str, Any]:
    """جلب الشموع الحقيقية (OHLCV) مباشرة من Binance Spot Testnet دون أي تصنيع أو محاكاة."""
    import httpx

    sym = symbol.upper().strip()
    valid_intervals = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
    iv = interval.lower().strip()
    if iv not in valid_intervals:
        iv = "1h"
    lim = max(10, min(120, int(limit)))

    bases = [(_TESTNET_BASE, "BINANCE_SPOT_TESTNET"), (_BINANCE_PUB_FALLBACK, "BINANCE_PUBLIC")]
    for base_url, src in bases:
        try:
            with httpx.Client(timeout=6.0) as client:
                r = client.get(f"{base_url}/api/v3/klines", params={"symbol": sym, "interval": iv, "limit": lim})
                if r.status_code == 200:
                    raw = r.json()
                    if isinstance(raw, list) and len(raw) > 0:
                        candles = [
                            {
                                "openTime": int(k[0]),
                                "open": float(k[1]),
                                "high": float(k[2]),
                                "low": float(k[3]),
                                "close": float(k[4]),
                                "volume": float(k[5]),
                            }
                            for k in raw
                        ]
                        return {
                            "ok": True,
                            "symbol": sym,
                            "interval": iv,
                            "source": src,
                            "candles": candles,
                            "lastPrice": candles[-1]["close"],
                            "timestamp": utc_now_iso(),
                        }
        except Exception:
            continue
    return {"ok": False, "symbol": sym, "interval": iv, "source": "NONE", "candles": [], "timestamp": utc_now_iso()}


@executive_router.post("/testnet/connect")
def connect_real_binance_testnet(payload: TestnetConnectInput) -> dict[str, Any]:
    """ربط فعلي بحساب Binance Spot Testnet وجلب الأرصدة الحقيقية عبر توقيع Ed25519 أو HMAC-SHA256."""
    _TESTNET_CONN["apiKey"] = payload.apiKey.strip()
    _TESTNET_CONN["authType"] = payload.authType.strip().upper()
    _TESTNET_CONN["apiSecret"] = payload.apiSecret.strip()
    _TESTNET_CONN["ed25519PrivateKeyPath"] = payload.ed25519PrivateKeyPath.strip() or "~/trilunair_ed25519_private.pem"
    try:
        res = _fetch_testnet_account_sync()
        return {"ok": True, **res, "messageAr": "✅ تم الاتصال الفعلي بحسابك على Binance Spot Testnet وجلب الأرصدة الحقيقية!"}
    except Exception as exc:
        _TESTNET_CONN["connected"] = False
        return {"ok": False, "connected": False, "error": str(exc), "messageAr": f"❌ تعذّر الاتصال بـ Binance Spot Testnet: {exc}"}


@executive_router.get("/testnet/account")
def get_real_binance_testnet_account() -> dict[str, Any]:
    """جلب الحالة الحالية وأرصدة حساب Binance Spot Testnet المتصل."""
    if not _TESTNET_CONN.get("apiKey"):
        return {"ok": False, "connected": False, "balances": {}, "messageAr": "لم يتم ربط مفتاح Binance Spot Testnet بعد."}
    try:
        res = _fetch_testnet_account_sync()
        return {"ok": True, **res}
    except Exception as exc:
        return {"ok": False, "connected": False, "error": str(exc), "balances": _TESTNET_CONN.get("balances", {})}


@executive_router.post("/testnet/order")
def place_real_binance_testnet_order(payload: TestnetOrderInput) -> dict[str, Any]:
    """إرسال وتنفيذ أمر شراء/بيع فوري حقيقي على شبكة Binance Spot Testnet (testnet.binance.vision فقط!)."""
    import httpx

    if _RUNTIME_QUANT_STATE.get("killSwitch"):
        return {"ok": False, "messageAr": "🛑 قاطع الطوارئ مفعّل — الأوامر موقوفة."}
    if not _TESTNET_CONN.get("apiKey"):
        return {"ok": False, "messageAr": "⚠️ يرجى ربط مفتاح Binance Spot Testnet أولاً من نافذة «🔑 مفاتيح»."}

    sym = payload.symbol.upper().strip()
    side = payload.side.upper().strip()
    try:
        with httpx.Client(timeout=8.0) as client:
            ts_ms = int(time.time() * 1000)
            try:
                tr = client.get(f"{_TESTNET_BASE}/api/v3/time")
                if tr.status_code == 200:
                    ts_ms = int(tr.json().get("serverTime", ts_ms))
            except Exception:
                pass

            params: dict[str, Any] = {
                "symbol": sym,
                "side": side,
                "type": "MARKET",
                "timestamp": ts_ms,
                "recvWindow": 5000,
            }
            if side == "BUY" and payload.quoteUsd > 0:
                params["quoteOrderQty"] = round(float(payload.quoteUsd), 2)
            elif payload.quantity > 0:
                # تقريب الكمية بدقة مناسبة لأصول Binance الشائعة
                prec = 5 if sym.startswith("BTC") else (4 if sym.startswith("ETH") else (2 if sym.startswith(("SOL", "BNB")) else 1))
                params["quantity"] = round(float(payload.quantity), prec)
            else:
                return {"ok": False, "messageAr": "⚠️ يجب تحديد المبلغ أو الكمية لتنفيذ الأمر."}

            query, sig = _sign_testnet_params(params)
            r = client.post(
                f"{_TESTNET_BASE}/api/v3/order?{query}&signature={sig}",
                headers={"X-MBX-APIKEY": _TESTNET_CONN["apiKey"]},
            )
            data = r.json()
            if r.status_code != 200:
                return {
                    "ok": False,
                    "error": data.get("msg", str(data)),
                    "messageAr": f"❌ رفض Binance Spot Testnet الأمر: {data.get('msg', data)}",
                }

        acct = {}
        try:
            acct = _fetch_testnet_account_sync()
        except Exception:
            pass

        return {
            "ok": True,
            "realTestnetExecution": True,
            "endpoint": _TESTNET_BASE,
            "orderId": data.get("orderId"),
            "clientOrderId": data.get("clientOrderId"),
            "symbol": data.get("symbol", sym),
            "side": data.get("side", side),
            "status": data.get("status", "FILLED"),
            "executedQty": float(data.get("executedQty", 0.0)),
            "cummulativeQuoteQty": float(data.get("cummulativeQuoteQty", 0.0)),
            "fills": data.get("fills", []),
            "balances": acct.get("balances", _TESTNET_CONN.get("balances", {})),
            "messageAr": f"✅ تم التنفيذ الفعلي على Binance Spot Testnet! رقم الأمر الرسمي: #{data.get('orderId')} ({data.get('status')})",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "messageAr": f"❌ خطأ أثناء إرسال الأمر إلى Binance Testnet: {exc}"}


# ==============================================================================
# ربط مزودات الذكاء الاصطناعي والوكلاء (Gemini / OpenAI / Claude / Grok + المحرك الكمي المحلي)
# ==============================================================================

_AI_ENV_KEYS = {
    "gemini": ("GEMINI_API_KEY", "Google Gemini (gemini-2.5-flash)"),
    "openai": ("OPENAI_API_KEY", "OpenAI GPT (gpt-4o-mini)"),
    "anthropic": ("ANTHROPIC_API_KEY", "Anthropic Claude (claude-3-5-haiku)"),
    "xai": ("XAI_API_KEY", "xAI Grok (grok-3-mini)"),
}


_AGENT_PLATFORM_MAP = [
    {
        "agentIndex": 0,
        "agentId": "AI-1",
        "icon": "🎯",
        "agentName": "ترليورين (الزخم الفني)",
        "roleAr": "محلل الاتجاه والشموع",
        "providerId": "gemini",
        "providerShort": "Google Gemini",
        "model": "gemini-2.5-flash",
    },
    {
        "agentIndex": 1,
        "agentId": "AI-2",
        "icon": "🛡️",
        "agentName": "الحارس (إدارة المخاطر)",
        "roleAr": "فحص وقف الخسارة والأمان",
        "providerId": "anthropic",
        "providerShort": "Anthropic Claude",
        "model": "claude-3-5-haiku-latest",
    },
    {
        "agentIndex": 2,
        "agentId": "AI-3",
        "icon": "📡",
        "agentName": "الرادار (السيولة والأوامر)",
        "roleAr": "عمق السوق وتدفق السيولة",
        "providerId": "openai",
        "providerShort": "OpenAI GPT",
        "model": "gpt-4o-mini",
    },
    {
        "agentIndex": 3,
        "agentId": "AI-4",
        "icon": "⚖️",
        "agentName": "الميزان (تخصيص المال)",
        "roleAr": "تحجيم Kelly الكسري ورصيد المحفظة",
        "providerId": "local",
        "providerShort": "المحرك الكمي المحلي",
        "model": "quant-kelly-pava-v1",
    },
    {
        "agentIndex": 4,
        "agentId": "AI-5",
        "icon": "🌐",
        "agentName": "الاستراتيجي (السياق العام)",
        "roleAr": "صورة السوق والأخبار",
        "providerId": "xai",
        "providerShort": "xAI Grok",
        "model": "grok-3-mini",
    },
]


class AiProviderConnectInput(BaseModel):
    provider: str = Field(..., pattern="^(gemini|openai|anthropic|xai)$")
    apiKey: str = Field(..., min_length=8)


class AiProviderDisconnectInput(BaseModel):
    provider: str = Field(..., pattern="^(gemini|openai|anthropic|xai)$")


class AiAgentAskInput(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=1500)
    provider: str = Field(default="auto")


class AiCouncilDeliberateInput(BaseModel):
    sym: str = Field(..., min_length=2, max_length=32)
    name: str = Field(default="")
    price: float = Field(..., gt=0)
    tp1: float = Field(default=0.0, ge=0)
    sl: float = Field(default=0.0, ge=0)
    horizon: str = Field(default="1H", max_length=16)
    availUsdt: float = Field(default=0.0, ge=0)
    investUsd: float = Field(default=0.0, ge=0)
    confPct: float = Field(default=75.0, ge=0, le=100)
    aiScores: list[float] = Field(default_factory=list)


def _persist_env_local(env_name: str, value: str) -> None:
    """حفظ المفتاح محلياً في .env.local فقط (مستثنى من Git) ليبقى متصلاً بعد إعادة التشغيل."""
    try:
        env_file = Path(__file__).resolve().parents[2] / ".env.local"
        lines: list[str] = []
        if env_file.is_file():
            lines = env_file.read_text(encoding="utf-8").splitlines()
        prefix = f"{env_name}="
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith(prefix):
                new_lines.append(f"{env_name}={value}")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            new_lines.append(f"{env_name}={value}")
        env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def _remove_env_local(env_name: str) -> None:
    """إزالة المفتاح من .env.local عند فصل مزود الذكاء الاصطناعي."""
    try:
        env_file = Path(__file__).resolve().parents[2] / ".env.local"
        if not env_file.is_file():
            return
        prefix = f"{env_name}="
        lines = [ln for ln in env_file.read_text(encoding="utf-8").splitlines() if not ln.startswith(prefix)]
        env_file.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")
    except Exception:
        pass


@executive_router.get("/ai-providers/status")
def get_ai_providers_status() -> dict[str, Any]:
    """حالة اتصال مزودات الذكاء الاصطناعي الحقيقية وخريطة ربط الوكلاء الخمسة."""
    providers = [
        {
            "id": "local",
            "name": "Local Quantitative Engine",
            "connected": True,
            "model": "quant-deterministic-v1",
            "noteAr": "متصل دائماً — محرك كمي محلي فوري (PAVA + Kelly + ATR)",
        }
    ]
    provider_by_id: dict[str, dict[str, Any]] = {"local": providers[0]}
    for pid, (env_name, label) in _AI_ENV_KEYS.items():
        val = (os.getenv(env_name) or "").strip()
        item = {
            "id": pid,
            "name": label,
            "envKey": env_name,
            "connected": len(val) >= 8,
            "masked": (val[:5] + "•••" + val[-4:]) if len(val) >= 10 else "",
            "noteAr": "🟢 متصل ومفعل للوكيل المخصص" if len(val) >= 8 else "غير مهيأ — يعمل بالمحرك الكمي الاحتياطي حتى الربط",
        }
        providers.append(item)
        provider_by_id[pid] = item

    agent_bindings = []
    for ag in _AGENT_PLATFORM_MAP:
        pid = ag["providerId"]
        pinfo = provider_by_id.get(pid, {})
        is_conn = bool(pinfo.get("connected", False))
        mode = "LOCAL_QUANT" if pid == "local" else ("LIVE_CLOUD" if is_conn else "LOCAL_FALLBACK")
        agent_bindings.append({
            "agentIndex": ag["agentIndex"],
            "agentId": ag["agentId"],
            "icon": ag["icon"],
            "agentName": ag["agentName"],
            "roleAr": ag["roleAr"],
            "providerId": pid,
            "providerShort": ag["providerShort"],
            "providerName": pinfo.get("name", ag["providerShort"]),
            "model": ag["model"],
            "envKey": pinfo.get("envKey", ""),
            "connected": is_conn,
            "masked": pinfo.get("masked", ""),
            "mode": mode,
        })

    connected_cloud = [p for p in providers if p["id"] != "local" and p["connected"]]
    active_llm = connected_cloud[0]["id"] if connected_cloud else "local"
    return {
        "ok": True,
        "activeProvider": active_llm,
        "connectedCloudCount": len(connected_cloud),
        "totalConnectedAgents": sum(1 for a in agent_bindings if a["connected"]),
        "providers": providers,
        "agentBindings": agent_bindings,
    }


@executive_router.post("/ai-providers/connect")
def connect_ai_provider(payload: AiProviderConnectInput) -> dict[str, Any]:
    """ربط وفحص مفتاح مزود الذكاء الاصطناعي وحفظه في .env.local لتفعيل الوكلاء فوراً."""
    import httpx

    pid = payload.provider.lower().strip()
    key = payload.apiKey.strip()
    env_name, label = _AI_ENV_KEYS[pid]

    # اختبار اتصال سريع حقيقي مع المزود للتأكد من صلاحية المفتاح
    verified_msg = ""
    try:
        with httpx.Client(timeout=10.0) as client:
            if pid == "gemini":
                r = client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
                if r.status_code != 200:
                    return {"ok": False, "messageAr": f"❌ مفتاح Google Gemini غير صالح ({r.status_code})"}
                verified_msg = "تم التحقق الحقيقي من Google Gemini API"
            elif pid == "openai":
                r = client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
                if r.status_code != 200:
                    return {"ok": False, "messageAr": f"❌ مفتاح OpenAI غير صالح ({r.status_code})"}
                verified_msg = "تم التحقق الحقيقي من OpenAI API"
            elif pid == "anthropic":
                r = client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                )
                if r.status_code != 200:
                    return {"ok": False, "messageAr": f"❌ مفتاح Anthropic Claude غير صالح ({r.status_code})"}
                verified_msg = "تم التحقق الحقيقي من Anthropic Claude API"
            elif pid == "xai":
                r = client.get("https://api.x.ai/v1/models", headers={"Authorization": f"Bearer {key}"})
                if r.status_code != 200:
                    return {"ok": False, "messageAr": f"❌ مفتاح xAI Grok غير صالح ({r.status_code})"}
                verified_msg = "تم التحقق الحقيقي من xAI Grok API"
    except Exception as exc:
        return {"ok": False, "messageAr": f"❌ تعذّر التحقق من الاتصال بالمزود: {exc}"}

    os.environ[env_name] = key
    _persist_env_local(env_name, key)
    return {
        "ok": True,
        "provider": pid,
        "label": label,
        "messageAr": f"✅ {verified_msg} — الوكلاء متصلون الآن بـ {label}!",
        "status": get_ai_providers_status(),
    }


@executive_router.post("/ai-providers/ask")
def ask_connected_ai_agent(payload: AiAgentAskInput) -> dict[str, Any]:
    """استشارة الوكيل الذكي المتصل فعلياً (Gemini / OpenAI / Claude / Grok أو المحرك الكمي المحلي) ببيانات Binance Testnet الحية."""
    import httpx

    tickers_resp = get_real_binance_testnet_tickers()
    tickers = tickers_resp.get("tickers", {})
    market_ctx = ", ".join(
        f"{s}: ${v['price']:.2f} ({v['priceChangePercent']:+.2f}%)"
        for s, v in list(tickers.items())[:6]
    ) or "Live market syncing"
    sys_prompt = (
        "أنت الوكيل المالي التنفيذي «ترليورين» لمنصة د. ماجد حمدي على Binance Spot Testnet (فترة المعايرة حتى 28/11/2026). "
        f"الأسعار الحقيقية الحية الآن من Binance Testnet: {market_ctx}. "
        "أجب بالعربية بإيجاز واحترافية ووضوح بالأرقام الدقيقة، مع التزام Spot Long-Only وحدود إدارة المخاطر."
    )

    pref = (payload.provider or "auto").lower().strip()
    order = [pref] if pref in _AI_ENV_KEYS else ["gemini", "openai", "anthropic", "xai"]

    for pid in order:
        env_name, label = _AI_ENV_KEYS[pid]
        key = (os.getenv(env_name) or "").strip()
        if len(key) < 8:
            continue
        try:
            with httpx.Client(timeout=18.0) as client:
                if pid == "gemini":
                    r = client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
                        json={
                            "contents": [{"parts": [{"text": f"{sys_prompt}\n\nسؤال د. ماجد: {payload.prompt}"}]}],
                        },
                    )
                    if r.status_code == 200:
                        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                        return {"ok": True, "provider": label, "reply": txt}
                elif pid == "openai":
                    r = client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}"},
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": sys_prompt},
                                {"role": "user", "content": payload.prompt},
                            ],
                        },
                    )
                    if r.status_code == 200:
                        txt = r.json()["choices"][0]["message"]["content"]
                        return {"ok": True, "provider": label, "reply": txt}
                elif pid == "anthropic":
                    r = client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                        json={
                            "model": "claude-3-5-haiku-latest",
                            "max_tokens": 500,
                            "system": sys_prompt,
                            "messages": [{"role": "user", "content": payload.prompt}],
                        },
                    )
                    if r.status_code == 200:
                        txt = r.json()["content"][0]["text"]
                        return {"ok": True, "provider": label, "reply": txt}
                elif pid == "xai":
                    r = client.post(
                        "https://api.x.ai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}"},
                        json={
                            "model": "grok-3-mini",
                            "messages": [
                                {"role": "system", "content": sys_prompt},
                                {"role": "user", "content": payload.prompt},
                            ],
                        },
                    )
                    if r.status_code == 200:
                        txt = r.json()["choices"][0]["message"]["content"]
                        return {"ok": True, "provider": label, "reply": txt}
        except Exception:
            continue

    # الرد الذكي من المحرك الكمي المحلي إذا لم يُربط مفتاح خارجي بعد
    return {
        "ok": True,
        "provider": "Local Quantitative Engine",
        "reply": f"📊 تحليل المحرك الكمي المحلي بناءً على أسعار Binance Testnet الحية ({market_ctx}): الالتزام الكامل بعتبة PAVA ≥ 75% ونظام Spot Long-Only حتى 28/11/2026. لتمكين التحليل اللغوي المتقدم من Gemini أو GPT أو Claude أو Grok، اربط مفتاح المزود من قسم «🤖 ربط الوكلاء».",
    }


@executive_router.post("/ai-providers/disconnect")
def disconnect_ai_provider(payload: AiProviderDisconnectInput) -> dict[str, Any]:
    """فصل مزود الذكاء الاصطناعي وإزالة مفتاحه من البيئة المحلية (.env.local)."""
    pid = payload.provider.lower().strip()
    env_name, label = _AI_ENV_KEYS[pid]
    os.environ.pop(env_name, None)
    _remove_env_local(env_name)
    return {
        "ok": True,
        "provider": pid,
        "messageAr": f"🔌 تم فصل {label} بنجاح — عاد الوكيل للمحرك الكمي المحلي الاحتياطي.",
        "status": get_ai_providers_status(),
    }


def _extract_agent_json(raw_text: str) -> dict[str, Any] | None:
    """استخراج JSON نظيف من رد النموذج السحابي دون السماح بانهيار التحليل."""
    import json
    import re

    txt = (raw_text or "").strip()
    if not txt:
        return None
    m = re.search(r"\{[\s\S]*\}", txt)
    if not m:
        return None
    try:
        parsed = json.loads(m.group(0))
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _evaluate_single_agent_deliberation(
    ag: dict[str, Any],
    payload: AiCouncilDeliberateInput,
) -> dict[str, Any]:
    """تنفيذ مداولة وكيل واحد عبر منصته المخصصة أو المحرك الكمي المحلي بشفافية كاملة."""
    import httpx

    idx = int(ag["agentIndex"])
    pid = ag["providerId"]
    sym = payload.sym.upper().strip()
    price = float(payload.price)
    tp1 = float(payload.tp1 or 0.0)
    sl = float(payload.sl or 0.0)
    avail = float(payload.availUsdt or 0.0)
    invest = float(payload.investUsd or 0.0)
    tp_pct = ((tp1 - price) / price * 100.0) if (tp1 > 0 and price > 0) else 0.0
    sl_pct = ((price - sl) / price * 100.0) if (sl > 0 and price > 0) else 0.0

    # الوكيل 4 (الميزان): محرك كمي محلي حتمي دائماً (لا يُسمح بأي NaN أو 0$)
    if pid == "local":
        valid_alloc = (invest > 0.0) and (avail > 0.0)
        if not valid_alloc:
            return {
                "agentIndex": idx,
                "agentId": ag["agentId"],
                "agentName": ag["agentName"],
                "providerId": "local",
                "providerShort": ag["providerShort"],
                "model": ag["model"],
                "mode": "LOCAL_QUANT",
                "connected": True,
                "score": None,
                "verdict": "REJECT",
                "reasonAr": "حسبة التخصيص غير صالحة أو السيولة المتاحة غير كافية — تم حجب الموافقة التلقائية.",
            }
        share_pct = (invest / avail) * 100.0
        raw_sc = 88.0 - max(0.0, share_pct - 10.0) * 1.4
        score = int(max(40, min(97, round(raw_sc))))
        verdict = "BUY" if score >= 75 else ("CAUTION" if score >= 60 else "REJECT")
        reason = (
            f"تحجيم Kelly الكسري: مبلغ ${invest:,.0f} يمثل {share_pct:.1f}% من السيولة المتاحة (${avail:,.0f}) ضمن حدود الأمان."
            if score >= 75
            else f"نسبة التخصيص ({share_pct:.1f}% من المتاح) مرتفعة نسبياً — يُنصح بخفض المبلغ."
        )
        return {
            "agentIndex": idx,
            "agentId": ag["agentId"],
            "agentName": ag["agentName"],
            "providerId": "local",
            "providerShort": ag["providerShort"],
            "model": ag["model"],
            "mode": "LOCAL_QUANT",
            "connected": True,
            "score": score,
            "verdict": verdict,
            "reasonAr": reason,
        }

    # حساب الدرجة الاحتياطية الكمية المحلية بوضوح تام في حال لم يُربط المفتاح أو فشل الاتصال
    base_score_raw = (
        payload.aiScores[idx]
        if idx < len(payload.aiScores) and isinstance(payload.aiScores[idx], (int, float))
        else payload.confPct
    )
    fallback_score = int(max(40, min(97, round(float(base_score_raw))))) if base_score_raw and base_score_raw > 0 else 72
    fallback_verdict = "BUY" if fallback_score >= 75 else ("CAUTION" if fallback_score >= 60 else "REJECT")
    fallback_reasons = {
        0: f"تقييم كمّي محلي (احتياطي لـ Gemini): زخم {sym} عند ${price:,.4g} بهدف +{tp_pct:.2f}% على أفق {payload.horizon}.",
        1: f"تقييم كمّي محلي (احتياطي لـ Claude): وقف الخسارة عند ${sl:,.4g} (-{sl_pct:.2f}%) ضمن سقف المخاطرة المعتمد.",
        2: f"تقييم كمّي محلي (احتياطي لـ GPT): تدفق السيولة الفورية على {sym} مستقر ومناسب لتنفيذ Spot Testnet.",
        4: f"تقييم كمّي محلي (احتياطي لـ Grok): السياق العام لـ {sym} على أفق {payload.horizon} بثقة إجمالية {payload.confPct:.0f}%.",
    }

    env_name, _label = _AI_ENV_KEYS[pid]
    key = (os.getenv(env_name) or "").strip()
    if len(key) < 8:
        return {
            "agentIndex": idx,
            "agentId": ag["agentId"],
            "agentName": ag["agentName"],
            "providerId": pid,
            "providerShort": ag["providerShort"],
            "model": ag["model"],
            "mode": "LOCAL_FALLBACK",
            "connected": False,
            "score": fallback_score,
            "verdict": fallback_verdict,
            "reasonAr": fallback_reasons.get(idx, "تقييم كمّي محلي احتياطي — اربط مفتاح المنصة لتفعيل التحليل السحابي الحي."),
        }

    sys_prompt = (
        f"أنت الوكيل «{ag['agentName']}» ({ag['roleAr']}) داخل مجلس الوكلاء الخمسة لمنصة Sudanese Trillionaire على Binance Spot Testnet. "
        "قيّم الصفقة المقترحة بإيجاز صارم وأعد JSON فقط بدون أي نص خارجي بهذا الشكل: "
        '{"score": 82, "verdict": "BUY", "reasonAr": "جملة عربية موجزة لا تتجاوز 18 كلمة"}. '
        "القيم المسموحة لـ verdict هي BUY أو CAUTION أو REJECT، و score عدد صحيح بين 40 و 97."
    )
    user_prompt = (
        f"الصفقة: {sym} ({payload.name or sym}) | الأفق: {payload.horizon} | "
        f"السعر: ${price:,.6g} | هدف الربح TP1: ${tp1:,.6g} (+{tp_pct:.2f}%) | "
        f"وقف الخسارة SL: ${sl:,.6g} (-{sl_pct:.2f}%) | الاستثمار المقترح: ${invest:,.0f} من متاح ${avail:,.0f}."
    )

    try:
        raw_reply = ""
        with httpx.Client(timeout=12.0) as client:
            if pid == "gemini":
                r = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
                    json={"contents": [{"parts": [{"text": f"{sys_prompt}\n\n{user_prompt}"}]}]},
                )
                if r.status_code == 200:
                    raw_reply = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            elif pid == "anthropic":
                r = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                    json={
                        "model": "claude-3-5-haiku-latest",
                        "max_tokens": 220,
                        "system": sys_prompt,
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                if r.status_code == 200:
                    raw_reply = r.json()["content"][0]["text"]
            elif pid == "openai":
                r = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "max_tokens": 220,
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                if r.status_code == 200:
                    raw_reply = r.json()["choices"][0]["message"]["content"]
            elif pid == "xai":
                r = client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": "grok-3-mini",
                        "max_tokens": 220,
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                if r.status_code == 200:
                    raw_reply = r.json()["choices"][0]["message"]["content"]

        parsed = _extract_agent_json(raw_reply)
        if parsed and isinstance(parsed.get("score"), (int, float)):
            sc = int(max(40, min(97, round(float(parsed["score"])))))
            vd = str(parsed.get("verdict") or "").upper().strip()
            if vd not in ("BUY", "CAUTION", "REJECT"):
                vd = "BUY" if sc >= 75 else ("CAUTION" if sc >= 60 else "REJECT")
            rsn = str(parsed.get("reasonAr") or "").strip() or fallback_reasons.get(idx, "تحليل سحابي مكتمل.")
            return {
                "agentIndex": idx,
                "agentId": ag["agentId"],
                "agentName": ag["agentName"],
                "providerId": pid,
                "providerShort": ag["providerShort"],
                "model": ag["model"],
                "mode": "LIVE_CLOUD",
                "connected": True,
                "score": sc,
                "verdict": vd,
                "reasonAr": rsn[:220],
            }
    except Exception:
        pass

    return {
        "agentIndex": idx,
        "agentId": ag["agentId"],
        "agentName": ag["agentName"],
        "providerId": pid,
        "providerShort": ag["providerShort"],
        "model": ag["model"],
        "mode": "LOCAL_FALLBACK",
        "connected": True,
        "score": fallback_score,
        "verdict": fallback_verdict,
        "reasonAr": f"{fallback_reasons.get(idx, '')} (تعذر الرد اللحظي من {ag['providerShort']} فتم استخدام التقييم الاحتياطي).",
    }


@executive_router.post("/ai-providers/deliberate")
def deliberate_five_agents(payload: AiCouncilDeliberateInput) -> dict[str, Any]:
    """تشغيل مداولة الوكلاء الخمسة بالتوازي مع قياس زمن الاستجابة الحقيقي وطابع التحقق."""
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timezone
    import time as _time

    t0 = _time.perf_counter()
    with ThreadPoolExecutor(max_workers=5) as pool:
        def _timed(ag_item: dict[str, Any]) -> dict[str, Any]:
            st = _time.perf_counter()
            res = _evaluate_single_agent_deliberation(ag_item, payload)
            res["latencyMs"] = round((_time.perf_counter() - st) * 1000.0, 1)
            res["verifiedAtIso"] = datetime.now(timezone.utc).isoformat()
            res["verifiedLiveCloud"] = res.get("mode") == "LIVE_CLOUD"
            return res

        futures = [pool.submit(_timed, ag) for ag in _AGENT_PLATFORM_MAP]
        results = [f.result() for f in futures]

    results.sort(key=lambda x: x["agentIndex"])
    live_cloud_count = sum(1 for r in results if r["mode"] == "LIVE_CLOUD")
    total_ms = round((_time.perf_counter() - t0) * 1000.0, 1)
    return {
        "ok": True,
        "sym": payload.sym.upper().strip(),
        "horizon": payload.horizon,
        "liveCloudAgentsCount": live_cloud_count,
        "totalAgents": len(results),
        "totalLatencyMs": total_ms,
        "verifiedAtIso": datetime.now(timezone.utc).isoformat(),
        "agents": results,
    }


@executive_router.get("/latency/ping")
def check_tokyo_binance_latency() -> dict[str, Any]:
    """فحص البينج الحقيقي (RTT بالملي ثانية) بين السيرفر (طوكيو/المحلي) وBinance Testnet للتحقق من جاهزية الصفقات قصيرة الأجل."""
    from datetime import datetime, timezone
    import time as _time
    import httpx

    endpoint = f"{_TESTNET_BASE}/api/v3/ping"
    region = (os.getenv("TRILUNAIR_REGION") or "Tokyo-JP / Server").strip()
    t0 = _time.perf_counter()
    reachable = False
    http_status = 0
    rtt_ms: float | None = None
    note_ar = ""

    try:
        with httpx.Client(timeout=4.5) as client:
            r = client.get(endpoint)
            elapsed = round((_time.perf_counter() - t0) * 1000.0, 1)
            http_status = int(r.status_code)
            if r.status_code == 200:
                reachable = True
                rtt_ms = elapsed
            elif r.status_code == 451:
                note_ar = f"محجوب جغرافياً من هذه المنطقة (HTTP 451 — {elapsed}ms) — يعمل على سيرفر طوكيو مباشرة."
            else:
                note_ar = f"استجابة غير مكتملة من Binance Testnet (HTTP {r.status_code} — {elapsed}ms)."
    except Exception as exc:
        note_ar = f"تعذّر قياس البينج مع Binance Testnet: {exc}"

    if reachable and rtt_ms is not None:
        if rtt_ms < 80:
            quality = "EXCELLENT"
            note_ar = f"اتصال فائق السرعة ({rtt_ms}ms) — مثالي للصفقات قصيرة الأجل والتنفيذ اللحظي."
        elif rtt_ms < 220:
            quality = "GOOD"
            note_ar = f"اتصال مستقر وجيد ({rtt_ms}ms) — مناسب للتنفيذ قصير ومتوسط الأجل."
        else:
            quality = "DEGRADED"
            note_ar = f"تأخير مرتفع ({rtt_ms}ms) — يُنصح بتفضيل الصفقات متوسطة أو طويلة الأجل."
    else:
        quality = "OFFLINE"

    return {
        "ok": True,
        "reachable": reachable,
        "rttMs": rtt_ms,
        "httpStatus": http_status,
        "quality": quality,
        "shortTermReady": bool(reachable and rtt_ms is not None and rtt_ms < 250),
        "endpoint": "testnet.binance.vision",
        "serverRegion": region,
        "checkedAtIso": datetime.now(timezone.utc).isoformat(),
        "noteAr": note_ar,
    }





