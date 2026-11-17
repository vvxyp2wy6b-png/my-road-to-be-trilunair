"""
مجموعة الاختبارات الشاملة للخادم الخلفي وبوابة الأمان المالي ومجلس الوكلاء.
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

تغطي هذه الاختبارات:
1. الإقلاع الآمن في وضع التداول الورقي الافتراضي (PAPER) وبذر المحفظة الابتدائية ($1,000,000).
2. بوابة تصاريح التداول الحقيقي (LIVE) ومفتاح الإيقاف الطارئ (Kill Switch) وسجل التدقيق الأمني.
3. تطابق السياسات 100% بين الأوامر الصوتية (VOICE) والنصية (TEXT) واليدوية (TERMINAL).
4. محرك المخاطر الحتمي ورفض الأوامر المفرطة، البيع المكشوف، نقص السيولة، التراجع اليومي، والتجميد الطارئ.
5. معالجة الأوامر العربية والإنجليزية (التحليل، المقارنة، شرح المحفظة، تغيير السمات، ومقترحات الصفقات الصوتية دون تنفيذ تلقائي).
6. اكتمال مخرجات قاعة اجتماع الوكلاء الخمسة (التوافق، الاختلاف، الأدلة، عدم اليقين، التكاليف، المخاطر، التوصية).
7. استدامة محرك السمات الهولوغرامية الخمس والسمات المخصصة والتحقق من الاستيراد.
8. خدمات الصوت (STT / TTS بصيغة RIFF WAV صالحة) والبث الحي عبر WebSocket (/ws/market).
"""

from __future__ import annotations

import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.database import db_session, init_db
from app.llm_adapters import reset_llm_adapter_state
from app.main import app
from app.market_engine import market_engine
from app.safety_gateway import LIVE_CONFIRMATION_PHRASE
from app.security import rate_limiter

TEST_STRONG_SECRET = "TestSuiteAdmin#2026!Strong"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """تهيئة عميل اختبار معزول بقاعدة بيانات SQLite مؤقتة وإعادة ضبط محرك السوق ومحدد المعدل."""
    test_db = tmp_path / "test_trilunair.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("TRILUNAIR_DB_PATH", str(test_db))
    monkeypatch.setenv("TRILUNAIR_ADMIN_SECRET", TEST_STRONG_SECRET)
    monkeypatch.delenv("TRILUNAIR_ADMIN_SECRET_HASH", raising=False)
    monkeypatch.delenv("TRILUNAIR_ADMIN_PIN", raising=False)
    monkeypatch.setenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    rate_limiter.reset()
    reset_llm_adapter_state()
    market_engine.reset()
    init_db(force_recheck=True)

    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# 1. اختبارات التداول الورقي الافتراضي وبذر المحفظة وحالة النظام
# ==============================================================================


def test_default_paper_trading_mode_and_seeded_portfolio(client: TestClient) -> None:
    """التحقق من أن النظام يقلع دائماً في وضع PAPER المقفل مع رأسمال $1M ومركزين ابتدائيين."""
    status_res = client.get("/api/system/status")
    assert status_res.status_code == 200
    status = status_res.json()

    assert status["appName"] == "My Road to be Trilunair Dr.MaJoOoOoOoD"
    assert status["tradingMode"] == "PAPER"
    assert status["killSwitchActive"] is False
    assert status["liveAuthorized"] is False
    assert status["executionLockedToPaper"] is True
    assert all(status["safetyChecks"].values()) is True

    port_res = client.get("/api/portfolio")
    assert port_res.status_code == 200
    portfolio = port_res.json()

    assert portfolio["tradingMode"] == "PAPER"
    assert portfolio["initialEquity"] == 1_000_000.0
    assert portfolio["trilunairTargetUsd"] == 1_000_000_000_000.0
    assert portfolio["cashBalance"] == pytest.approx(932_725.0, rel=1e-4)
    assert portfolio["totalEquity"] > 1_000_000.0
    assert len(portfolio["positions"]) == 2
    held_symbols = {p["symbol"] for p in portfolio["positions"]}
    assert held_symbols == {"BTC-USD", "NVDA"}


# ==============================================================================
# 2. اختبارات القفل السيادي على وضع PAPER ومفتاح الإيقاف الطارئ (Kill Switch)
# ==============================================================================


def test_live_trading_gate_enforces_permanent_paper_lock_and_audit_trail(
    client: TestClient,
) -> None:
    """التحقق من رفض تفعيل LIVE نهائياً في الإصدار v1.1.0-cloud-paper حتى عند إدخال سر المسؤول الصحيح."""
    # 1. رفض عند عدم الإقرار بالمخاطر
    r1 = client.post(
        "/api/auth/trading-mode",
        json={
            "targetMode": "LIVE",
            "adminPin": TEST_STRONG_SECRET,
            "confirmationPhrase": LIVE_CONFIRMATION_PHRASE,
            "acknowledgeRealCapitalRisk": False,
        },
    )
    assert r1.status_code == 403

    # 2. رفض عند إدخال عبارة تأكيد خاطئة
    r2 = client.post(
        "/api/auth/trading-mode",
        json={
            "targetMode": "LIVE",
            "adminPin": TEST_STRONG_SECRET,
            "confirmationPhrase": "ENABLE LIVE PLEASE",
            "acknowledgeRealCapitalRisk": True,
        },
    )
    assert r2.status_code == 403

    # 3. رفض عند إدخال سر مسؤول خاطئ أو ضعيف
    r3 = client.post(
        "/api/auth/trading-mode",
        json={
            "targetMode": "LIVE",
            "adminPin": "WrongSecret#1234",
            "confirmationPhrase": LIVE_CONFIRMATION_PHRASE,
            "acknowledgeRealCapitalRisk": True,
        },
    )
    assert r3.status_code == 403

    # التأكد من بقاء النظام في وضع PAPER بعد المحاولات الفاشلة
    assert client.get("/api/system/status").json()["tradingMode"] == "PAPER"

    # 4. تفعيل مفتاح الإيقاف الطارئ ثم محاولة طلب LIVE -> يُرفض بـ 403
    ks_on = client.post(
        "/api/auth/kill-switch",
        json={"active": True, "reason": "اختبار تجميد الطوارئ"},
    )
    assert ks_on.status_code == 200
    assert ks_on.json()["killSwitchActive"] is True

    r4 = client.post(
        "/api/auth/trading-mode",
        json={
            "targetMode": "LIVE",
            "adminPin": TEST_STRONG_SECRET,
            "confirmationPhrase": LIVE_CONFIRMATION_PHRASE,
            "acknowledgeRealCapitalRisk": True,
        },
    )
    assert r4.status_code == 403

    # إلغاء مفتاح الطوارئ -> يظل النظام في وضع PAPER
    ks_off = client.post(
        "/api/auth/kill-switch",
        json={"active": False, "reason": "انتهاء اختبار التجميد"},
    )
    assert ks_off.status_code == 200
    assert ks_off.json()["tradingMode"] == "PAPER"
    assert ks_off.json()["killSwitchActive"] is False

    # 5. حتى مع استيفاء جميع الشروط والسر الصحيح، يظل الإصدار v1.1.0-cloud-paper مقفلاً على PAPER بـ HTTP 403!
    r_locked = client.post(
        "/api/auth/trading-mode",
        json={
            "targetMode": "LIVE",
            "adminPin": TEST_STRONG_SECRET,
            "confirmationPhrase": LIVE_CONFIRMATION_PHRASE,
            "acknowledgeRealCapitalRisk": True,
        },
    )
    assert r_locked.status_code == 403
    assert "LIVE_EXECUTION_LOCKED" in r_locked.json()["detail"]

    locked_state = client.get("/api/system/status").json()
    assert locked_state["tradingMode"] == "PAPER"
    assert locked_state["liveAuthorized"] is False

    # 6. الصفقات الورقية المعتمدة تُنفذ في وضع PAPER فقط مع isSimulatedFill=True
    prop = client.post(
        "/api/orders/propose",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "orderType": "MARKET",
            "quantity": 1.0,
            "source": "TERMINAL",
        },
    ).json()
    assert prop["requiresLivePin"] is False

    exec_paper = client.post(
        "/api/orders/execute",
        json={
            "proposalId": prop["proposalId"],
            "confirmedByUser": True,
            "source": "TERMINAL",
        },
    )
    assert exec_paper.status_code == 200
    assert exec_paper.json()["order"]["tradingMode"] == "PAPER"
    assert exec_paper.json()["order"]["isSimulatedFill"] is True

    # 7. تفعيل مفتاح الطوارئ يبقي النظام في PAPER ويجمد التنفيذ
    ks_emergency = client.post(
        "/api/auth/kill-switch",
        json={"active": True, "reason": "إيقاف طارئ فوري"},
    )
    assert ks_emergency.status_code == 200
    assert ks_emergency.json()["tradingMode"] == "PAPER"
    assert ks_emergency.json()["liveAuthorized"] is False
    assert ks_emergency.json()["killSwitchActive"] is True

    # التحقق من تسجيل الأحداث الأمنية في سجل التدقيق
    logs = client.get("/api/auth/audit-logs").json()
    actions = [entry["action"] for entry in logs]
    assert "LIVE_AUTH_BLOCKED_INVALID_SECRET" in actions
    assert "LIVE_AUTH_BLOCKED_RELEASE_PAPER_LOCK" in actions
    assert "KILL_SWITCH_ACTIVATED" in actions


# ==============================================================================
# 3. اختبارات السياسة الموحدة عبر VOICE و TEXT و TERMINAL
# ==============================================================================


def test_unified_policy_enforcement_across_voice_text_and_terminal(
    client: TestClient,
) -> None:
    """التحقق من خضوع أوامر VOICE و TEXT و TERMINAL لنفس حسابات التكلفة وفحوصات المخاطر حرفياً."""
    sources = ["VOICE", "TEXT", "TERMINAL"]
    evaluations = []

    # أ) اختبار مقترح صالح متطابق من المصادر الثلاثة
    for src in sources:
        res = client.post(
            "/api/orders/propose",
            json={
                "symbol": "SOL-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 20.0,
                "source": src,
            },
        )
        assert res.status_code == 200
        evaluations.append(res.json())

    base_eval = evaluations[0]
    for ev in evaluations[1:]:
        assert ev["status"] == base_eval["status"] == "APPROVED_FOR_AUTH"
        assert ev["estimatedCosts"] == base_eval["estimatedCosts"]
        assert ev["riskAssessment"]["riskScore"] == base_eval["riskAssessment"]["riskScore"]
        assert ev["riskAssessment"]["checks"] == base_eval["riskAssessment"]["checks"]

    # ب) اختبار أمر مفرط (>25% من المحفظة) من المصادر الثلاثة -> يُرفض بنفس المخالفات تماماً
    rejected_evals = []
    for src in sources:
        res = client.post(
            "/api/orders/propose",
            json={
                "symbol": "BTC-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 3.5,  # ~337,750$ > 25% من المليون
                "source": src,
            },
        )
        assert res.status_code == 200
        ev = res.json()
        assert ev["status"] == "REJECTED_BY_RISK"
        rejected_evals.append(ev)

        # التأكد من استحالة تنفيذ أي مقترح مرفوض بغض النظر عن المصدر
        exec_res = client.post(
            "/api/orders/execute",
            json={
                "proposalId": ev["proposalId"],
                "confirmedByUser": True,
                "source": src,
            },
        )
        assert exec_res.status_code == 403

    assert (
        rejected_evals[0]["riskAssessment"]["violations"]
        == rejected_evals[1]["riskAssessment"]["violations"]
        == rejected_evals[2]["riskAssessment"]["violations"]
    )

    # ج) تنفيذ المقترحات الصالحة بعد التأكيد وتسجيل المصدر الصحيح في سجل الأوامر والتدقيق
    for idx, src in enumerate(sources):
        exec_ok = client.post(
            "/api/orders/execute",
            json={
                "proposalId": evaluations[idx]["proposalId"],
                "confirmedByUser": True,
                "source": src,
            },
        )
        assert exec_ok.status_code == 200
        assert exec_ok.json()["order"]["source"] == src


# ==============================================================================
# 4. اختبارات الضوابط الخمسة لمحرك المخاطر الحتمي (Deterministic Risk Engine)
# ==============================================================================


def test_deterministic_risk_engine_all_rejection_scenarios(client: TestClient) -> None:
    """التحقق من رفض الأوامر المفرطة، نقص السيولة، البيع المكشوف، تراجع المحفظة، والتجميد الطارئ."""
    # 1. رفض البيع المكشوف (بيع أصل غير مملوك أو بكمية أكبر من المملوك)
    naked_sell = client.post(
        "/api/orders/propose",
        json={
            "symbol": "XAU-USD",
            "side": "SELL",
            "orderType": "MARKET",
            "quantity": 5.0,
            "source": "VOICE",
        },
    ).json()
    assert naked_sell["status"] == "REJECTED_BY_RISK"
    conc_check = next(
        c for c in naked_sell["riskAssessment"]["checks"] if c["code"] == "MAX_CONCENTRATION"
    )
    assert conc_check["passed"] is False

    # 2. رفض تجاوز الحد الأقصى لحجم الأمر الواحد (>25% من حقوق الملكية)
    oversized = client.post(
        "/api/orders/propose",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "orderType": "MARKET",
            "quantity": 90.0,  # ~307,800$ > 25%
            "source": "TEXT",
        },
    ).json()
    assert oversized["status"] == "REJECTED_BY_RISK"
    notional_check = next(
        c for c in oversized["riskAssessment"]["checks"] if c["code"] == "MAX_ORDER_NOTIONAL"
    )
    assert notional_check["passed"] is False

    # 3. رفض عدم كفاية السيولة النقدية (SUFFICIENT_BUYING_POWER)
    with db_session() as conn:
        conn.execute("UPDATE system_state SET cash_balance = 1500.0 WHERE id = 1")

    low_cash_prop = client.post(
        "/api/orders/propose",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "orderType": "MARKET",
            "quantity": 1.0,  # 3,420$ > 1,500$ نقد متاح
            "source": "TERMINAL",
        },
    ).json()
    assert low_cash_prop["status"] == "REJECTED_BY_RISK"
    cash_check = next(
        c for c in low_cash_prop["riskAssessment"]["checks"] if c["code"] == "SUFFICIENT_BUYING_POWER"
    )
    assert cash_check["passed"] is False

    # 4. رفض تجاوز حد التراجع اليومي (DAILY_DRAWDOWN_LIMIT >= 5%)
    # استعادة النقد مع رفع peak_equity لمحاكاة تراجع يتجاوز 5%
    with db_session() as conn:
        conn.execute(
            "UPDATE system_state SET cash_balance = 850000.0, peak_equity = 1000000.0 WHERE id = 1"
        )
    dd_prop = client.post(
        "/api/orders/propose",
        json={
            "symbol": "NVDA",
            "side": "BUY",
            "orderType": "MARKET",
            "quantity": 10.0,
            "source": "TERMINAL",
        },
    ).json()
    assert dd_prop["status"] == "REJECTED_BY_RISK"
    dd_check = next(
        c for c in dd_prop["riskAssessment"]["checks"] if c["code"] == "DAILY_DRAWDOWN_LIMIT"
    )
    assert dd_check["passed"] is False

    # استعادة الحالة القياسية لاختبار تجميد مفتاح الطوارئ
    with db_session() as conn:
        conn.execute(
            "UPDATE system_state SET cash_balance = 932725.0, peak_equity = 1001795.0 WHERE id = 1"
        )

    # 5. إنشاء مقترح صالح، ثم تفعيل Kill Switch -> يُلغى المقترح المعلق ويُرفض أي مقترح جديد
    valid_prop = client.post(
        "/api/orders/propose",
        json={
            "symbol": "ARAMCO.SR",
            "side": "BUY",
            "orderType": "MARKET",
            "quantity": 100.0,
            "source": "TERMINAL",
        },
    ).json()
    assert valid_prop["status"] == "APPROVED_FOR_AUTH"

    client.post("/api/auth/kill-switch", json={"active": True, "reason": "تجميد اختباري"})

    frozen_prop = client.post(
        "/api/orders/propose",
        json={
            "symbol": "ARAMCO.SR",
            "side": "BUY",
            "orderType": "MARKET",
            "quantity": 100.0,
            "source": "VOICE",
        },
    ).json()
    assert frozen_prop["status"] == "REJECTED_BY_RISK"
    ks_check = next(
        c for c in frozen_prop["riskAssessment"]["checks"] if c["code"] == "KILL_SWITCH"
    )
    assert ks_check["passed"] is False

    # محاولة تنفيذ المقترح القديم أثناء التجميد تُرفض بـ 403
    exec_frozen = client.post(
        "/api/orders/execute",
        json={
            "proposalId": valid_prop["proposalId"],
            "confirmedByUser": True,
            "source": "TERMINAL",
        },
    )
    assert exec_frozen.status_code == 403


# ==============================================================================
# 5. اختبارات الأوامر الصوتية والنصية بالعربية والإنجليزية وقاعة اجتماع الوكلاء
# ==============================================================================


def test_arabic_and_english_ai_commands_and_no_auto_execution(client: TestClient) -> None:
    """التحقق من فهم الأوامر العربية والإنجليزية وتجهيز الصفقات الصوتية دون تنفيذ تلقائي."""
    initial_portfolio = client.get("/api/portfolio").json()
    initial_orders_count = len(initial_portfolio["recentOrders"])
    initial_cash = initial_portfolio["cashBalance"]

    # 1. أمر صوتي عربي مركب (تحليل + مقارنة + تجهيز مقترح صفقة شراء)
    voice_cmd_res = client.post(
        "/api/ai/command",
        json={
            "message": "حلل BTC وقارنها مع الذهب وجهز مقترح شراء 0.2 BTC",
            "language": "ar",
            "source": "VOICE",
            "selectedAgent": "team",
            "triggerMeeting": True,
        },
    )
    assert voice_cmd_res.status_code == 200
    cmd_data = voice_cmd_res.json()

    # التحقق من إنشاء مقترح الصفقة المهيكل عبر محرك المخاطر دون أي تنفيذ تلقائي!
    proposal_eval = cmd_data["tradeProposalEvaluation"]
    assert proposal_eval is not None
    assert proposal_eval["status"] == "APPROVED_FOR_AUTH"
    assert proposal_eval["proposal"]["symbol"] == "BTC-USD"
    assert proposal_eval["proposal"]["side"] == "BUY"
    assert proposal_eval["proposal"]["quantity"] == pytest.approx(0.2)
    assert proposal_eval["proposal"]["source"] == "VOICE"

    # التأكد القاطع من عدم خصم أي نقد وعدم تنفيذ الصفقة تلقائياً
    after_voice_portfolio = client.get("/api/portfolio").json()
    assert after_voice_portfolio["cashBalance"] == initial_cash
    assert len(after_voice_portfolio["recentOrders"]) == initial_orders_count

    # 2. أمر تبديل السمة باللغة العربية -> يصدر uiAction ويحدث قاعدة البيانات
    theme_cmd_res = client.post(
        "/api/ai/command",
        json={
            "message": "حول السمة إلى السيان الكمي",
            "language": "ar",
            "source": "VOICE",
            "selectedAgent": "team",
            "triggerMeeting": False,
        },
    )
    assert theme_cmd_res.status_code == 200
    theme_cmd = theme_cmd_res.json()
    assert theme_cmd["uiAction"] is not None
    assert theme_cmd["uiAction"]["type"] == "SWITCH_THEME"
    assert theme_cmd["uiAction"]["payload"]["themeId"] == "quantum-cyan"
    assert client.get("/api/themes").json()["activeState"]["activeThemeId"] == "quantum-cyan"

    # 3. أمر شرح أداء المحفظة بالإنجليزية
    port_cmd_res = client.post(
        "/api/ai/command",
        json={
            "message": "Explain my portfolio performance and Trilunair progress",
            "language": "en",
            "source": "TEXT",
            "selectedAgent": "risk-sentinel",
            "triggerMeeting": False,
        },
    )
    assert port_cmd_res.status_code == 200
    port_cmd = port_cmd_res.json()
    assert "Total Equity" in port_cmd["assistantMessage"]["contentEn"]
    assert port_cmd["assistantMessage"]["agentId"] == "risk-sentinel"


def test_agent_meeting_room_completeness(client: TestClient) -> None:
    """التحقق من اكتمال بنية اجتماع الوكلاء الخمسة ونقاط الاتفاق والاختلاف والأدلة والمخاطر."""
    res = client.post(
        "/api/ai/meeting",
        json={"symbol": "NVDA", "horizon": "1h", "language": "ar"},
    )
    assert res.status_code == 200
    meeting = res.json()

    assert meeting["symbol"] == "NVDA"
    assert len(meeting["agentResponses"]) == 5
    agent_ids = [a["agentId"] for a in meeting["agentResponses"]]
    assert agent_ids == [
        "quant-alpha",
        "risk-sentinel",
        "macro-oracle",
        "execution-architect",
        "chief-strategist",
    ]

    # فحص التوافق والاختلاف البناء
    consensus = meeting["consensus"]
    assert 0 <= consensus["agreementScorePct"] <= 100
    assert len(consensus["agreementsAr"]) >= 1
    assert len(consensus["agreementsEn"]) >= 1
    assert len(consensus["disagreementsAr"]) >= 1
    assert len(consensus["disagreementsEn"]) >= 1

    # فحص الأدلة وعدم اليقين
    ev_unc = meeting["evidenceAndUncertainty"]
    assert 0 <= ev_unc["uncertaintyScorePct"] <= 100
    assert len(ev_unc["evidenceAr"]) >= 2
    assert len(ev_unc["uncertaintiesAr"]) >= 1

    # فحص التكاليف وتقييم المخاطر والتوصية النهائية
    assert meeting["estimatedCosts"]["notionalUsd"] > 0
    assert len(meeting["riskAssessment"]["checks"]) >= 7
    rec = meeting["finalRecommendation"]
    assert rec["stance"] in ("BUY", "SELL", "HOLD", "CAUTION")
    assert rec["suggestedQuantity"] > 0
    assert len(rec["headlineAr"]) > 5
    assert len(rec["actionableSummaryEn"]) > 10


# ==============================================================================
# 6. اختبارات محرك السمات الهولوغرامية المستديم (Dynamic Theme Engine)
# ==============================================================================


def test_dynamic_theme_engine_persistence_and_import_validation(
    client: TestClient,
) -> None:
    """التحقق من السمات الست الأساسية، حفظ وحذف السمة المخصصة، والتحقق من الاستيراد."""
    initial = client.get("/api/themes").json()
    assert len(initial["presets"]) == 6
    preset_ids = [p["id"] for p in initial["presets"]]
    assert preset_ids == [
        "royal-gold",
        "quantum-cyan",
        "nebula-purple",
        "emerald-matrix",
        "arctic-platinum",
        "obsidian-black",
    ]

    # حفظ سمة مخصصة جديدة
    base_tokens = initial["presets"][0]["tokens"]
    custom_payload = {
        "id": "custom-sovereign-ruby",
        "nameAr": "ياقوت السيادة",
        "nameEn": "Sovereign Ruby",
        "descriptionAr": "سمة ياقوتية مخصصة للاختبار.",
        "descriptionEn": "Custom ruby theme for testing.",
        "tokens": {**base_tokens, "accentPrimary": "#ff2e63"},
    }
    save_res = client.post("/api/themes/custom", json=custom_payload)
    assert save_res.status_code == 200
    assert save_res.json()["isCustom"] is True

    # تفعيل السمة المخصصة مع تعديل معاملات التباين والطاقة
    active_res = client.put(
        "/api/themes/active",
        json={
            "activeThemeId": "custom-sovereign-ruby",
            "customOverrides": {"accentSecondary": "#08d9d6"},
            "modifiers": {
                "glowIntensity": 45,
                "blurRadius": 12,
                "panelOpacity": 85,
                "animationIntensity": 60,
                "motionDisabled": True,
                "highContrast": True,
                "lowPowerMode": True,
            },
        },
    )
    assert active_res.status_code == 200

    persisted = client.get("/api/themes").json()
    assert len(persisted["customThemes"]) == 1
    assert persisted["activeState"]["activeThemeId"] == "custom-sovereign-ruby"
    assert persisted["activeState"]["modifiers"]["highContrast"] is True
    assert persisted["activeState"]["modifiers"]["lowPowerMode"] is True

    # اختبار استيراد ملف JSON صالح (صيغة الحزمة المصدرة)
    valid_import = client.post(
        "/api/themes/import",
        json={
            "theme": {
                "nameAr": "أفق الكوبالت",
                "nameEn": "Cobalt Horizon",
                "tokens": {
                    "bgBase": "#050814",
                    "bgSurface": "#101935",
                    "accentPrimary": "#3b82f6",
                    "textPrimary": "#f8fafc",
                },
            }
        },
    )
    assert valid_import.status_code == 200
    assert valid_import.json()["isCustom"] is True

    # رفض استيراد ملف JSON تنقصه الألوان الأساسية أو يحتوي قيمة غير صالحة
    invalid_import = client.post(
        "/api/themes/import",
        json={"theme": {"nameEn": "Broken", "tokens": {"bgBase": "not-a-valid-color"}}},
    )
    assert invalid_import.status_code == 400

    # حذف السمة المخصصة النشطة يعيد المؤشر تلقائياً إلى royal-gold
    del_res = client.delete("/api/themes/custom/custom-sovereign-ruby")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True
    after_del = client.get("/api/themes").json()
    assert after_del["activeState"]["activeThemeId"] == "royal-gold"


# ==============================================================================
# 7. اختبارات الأسواق، الشموع، الصوت (STT/TTS)، والبث الحي عبر WebSocket
# ==============================================================================


def test_market_candles_and_voice_endpoints(client: TestClient) -> None:
    """التحقق من بيانات الأصول الستة والشموع اليابانية ونقاط نهاية الصوت STT/TTS."""
    assets = client.get("/api/market/assets").json()
    assert len(assets) == 6

    for tf in ("5m", "15m", "1h", "4h"):
        candles_res = client.get(f"/api/market/candles/BTC-USD?timeframe={tf}&limit=45")
        assert candles_res.status_code == 200
        cdata = candles_res.json()
        assert cdata["symbol"] == "BTC-USD"
        assert cdata["timeframe"] == tf
        assert len(cdata["candles"]) == 45
        assert cdata["supportLevel"] < cdata["resistanceLevel"]
        assert len(cdata["bids"]) == 8
        assert len(cdata["asks"]) == 8

    # اختبار STT الاحتياطي
    stt_res = client.post(
        "/api/voice/stt",
        json={"language": "ar", "transcript": "حلل البيتكوين"},
    )
    assert stt_res.status_code == 200
    assert stt_res.json()["browserSpeechPrimary"] is True

    # اختبار TTS وإثبات سلامة ترويسة ملف RIFF WAVE
    tts_res = client.post(
        "/api/voice/tts",
        json={"text": "مرحباً بك في مركز القيادة", "language": "ar"},
    )
    assert tts_res.status_code == 200
    tts_json = tts_res.json()
    raw_wav = base64.b64decode(tts_json["audioBase64"])
    assert raw_wav[:4] == b"RIFF"
    assert raw_wav[8:12] == b"WAVE"


def test_websocket_market_live_tick_broadcast(client: TestClient) -> None:
    """التحقق من اتصال WebSocket على /ws/market واستقبال رسائل MARKET_TICK الحية."""
    with client.websocket_connect("/ws/market") as ws:
        tick = ws.receive_json()
        assert tick["type"] == "MARKET_TICK"
        assert len(tick["assets"]) == 6
        assert tick["totalEquity"] > 0
        assert "dailyPnl" in tick
        assert "dailyPnlPct" in tick

        ws.send_text("ping")
        second_tick = ws.receive_json()
        assert second_tick["type"] == "MARKET_TICK"
        assert len(second_tick["assets"]) == 6
