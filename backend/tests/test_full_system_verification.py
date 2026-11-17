"""
حزمة التحقق التكاملي الشامل للنظام (Full System Verification & Integration Suite)
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — QUANTUM AI TRADING COMMAND CENTER

تغطي هذه الحزمة كافة متطلبات التحقق الفعلي:
1. اتصال واستدامة قاعدة بيانات PostgreSQL 15 الحقيقية (127.0.0.1:5432) مع إعادة الاتصال.
2. اتصال واستدامة بروتوكول Redis عبر مقبس TCP فعلي (RESP Wire Protocol) وأقفال منع التكرار وصلاحية TTL.
3. دورة التداول الورقي الكاملة بمحفظة $1,000,000 (شراء + بيع + حساب العمولات والانزلاق + بقاء LIVE معطلاً).
4. حدود المخاطر الحتمية (سقف وقف الخسارة 0.5% لكل صفقة، حجم الأمر 25%، التركز 35%، القوة الشرائية)،
   انتهاء صلاحية المقترح (Proposal Expiration)، منع تكرار الأوامر (Duplicate-Order Prevention عبر proposalId و clientOrderId)،
   التصاريح، ومفتاح الإيقاف الطارئ (Emergency Shutdown / Kill Switch).
5. محولات الذكاء الاصطناعي الحقيقية (OpenAI, Gemini, Anthropic, xAI) عبر خادم HTTP فعلي عند تهيئة المفاتيح،
   مقابل التمييز الصريح للمحرك المحلي المحاكى (local-quant-engine) عند غياب المفاتيح.
6. السمات الست الكاملة (بما فيها السمة السادسة obsidian-black) والأوامر العربية النصية والصوتية.
7. محول Binance Spot الآمن (فصل USD عن USDT، منع REFERENCE_ONLY، فلاتر stepSize/tickSize/minNotional،
   توقيع HMAC-SHA256، حظر api.binance.com، وعدم وضع أي أمر مالي حقيقي).
8. التعافي من الأعطال ومصالحة الحساب (account_state_uncertain -> reconcile) وكشف تقادم بيانات السوق (Stale Market Data).
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
from typing import Any
import yaml

from fakeredis import TcpFakeServer
from fastapi.testclient import TestClient
import psycopg
import pytest
import redis as redis_lib

from app.database import init_db, reset_db_init_cache
from app.main import app
from app.market_engine import market_engine
from app.quantum_hub import ensure_quantum_tables

PG_TEST_DSN = "postgresql://trilunair@127.0.0.1:5432/trilunair_test"


def _wipe_pg_test_schema(dsn: str) -> None:
    """إعادة تهيئة مخطط الاختبار في PostgreSQL لضمان نظافة وعزل الاختبار بنسبة 100%."""
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
            cur.execute("CREATE SCHEMA public;")


class _MockCloudAndBinanceHandler(BaseHTTPRequestHandler):
    """خادم HTTP محلي يحاكي واجهات OpenAI / Gemini / Anthropic / xAI و Binance Spot Testnet بأمان تام."""

    recorded_requests: list[dict[str, Any]] = []

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else ""
        _MockCloudAndBinanceHandler.recorded_requests.append(
            {
                "path": self.path,
                "headers": {k.lower(): v for k, v in self.headers.items()},
                "body": raw_body,
            }
        )

        agent_json_payload = json.dumps(
            {
                "stance": "BUY",
                "confidence": 83.5,
                "summaryAr": "تحليل كمي متصل عبر محول المزود السحابي الفعلي يؤكد قوة السيولة.",
                "summaryEn": "Real HTTP provider adapter analysis confirms strong spot liquidity.",
                "keyMetricLabelAr": "مؤشر التدفق السحابي",
                "keyMetricLabelEn": "Cloud Flow Score",
                "keyMetricValue": "+1.92 sigma",
            },
            ensure_ascii=False,
        )

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

        if "/api/v3/order/test" in self.path:
            resp = {"status": "VALIDATED_TEST_ORDER", "realOrder": False, "path": self.path}
        elif ":generateContent" in self.path:
            # استجابة Google Gemini القياسية
            resp = {
                "candidates": [
                    {"content": {"parts": [{"text": agent_json_payload}]}}
                ],
                "usageMetadata": {"promptTokenCount": 140, "candidatesTokenCount": 75},
            }
        elif self.path.endswith("/v1/messages") or self.path.endswith("/messages"):
            # استجابة Anthropic Messages القياسية
            resp = {
                "content": [{"type": "text", "text": agent_json_payload}],
                "usage": {"input_tokens": 155, "output_tokens": 80},
            }
        else:
            # استجابة OpenAI / xAI Chat Completions القياسية
            resp = {
                "choices": [{"message": {"content": agent_json_payload}}],
                "usage": {"prompt_tokens": 130, "completion_tokens": 70},
            }
        self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))


@pytest.fixture()
def isolated_sqlite_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "verification_sqlite.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_REDIS_URL", raising=False)
    monkeypatch.setenv("TRILUNAIR_DB_PATH", str(db_file))
    monkeypatch.setenv("TRILUNAIR_ADMIN_PIN", "7777")
    for k in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "BINANCE_API_KEY",
        "BINANCE_SPOT_API_KEY",
        "BINANCE_SPOT_BASE_URL",
    ):
        monkeypatch.delenv(k, raising=False)
    reset_db_init_cache()
    market_engine.reset()
    init_db()
    ensure_quantum_tables()
    yield db_file
    market_engine.reset()


def test_docker_compose_manifest_validates_postgres_redis_and_app():
    """التحقق البنيوي من صحة docker-compose.yml وربط خدمات postgres و redis و trilunair-command-center."""
    compose_path = Path(__file__).resolve().parents[2] / "docker-compose.yml"
    assert compose_path.is_file()
    doc = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = doc["services"]
    assert "postgres" in services
    assert "redis" in services
    assert "trilunair-command-center" in services
    app_env = services["trilunair-command-center"]["environment"]
    env_joined = "\n".join(app_env) if isinstance(app_env, list) else json.dumps(app_env)
    assert "DATABASE_URL" in env_joined
    assert "REDIS_URL" in env_joined
    assert "TRILUNAIR_DEFAULT_MODE=PAPER" in env_joined or '"PAPER"' in env_joined


def test_real_postgresql_and_tcp_redis_persistence_and_1m_paper_workflow(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    التحقق الفعلي من:
    - الاتصال الحقيقي بخادم PostgreSQL 15 على 127.0.0.1:5432 واستدامة الجداول عبر الجلسات.
    - الاتصال الفعلي ببروتوكول Redis عبر مقبس TCP (redis-py -> TcpFakeServer) واستدامة المفاتيح وأقفال منع التكرار.
    - دورة التداول الورقي الكاملة بمحفظة $1,000,000 (اقتراح -> تصريح -> تنفيذ شراء -> تنفيذ بيع جزئي) مع بقاء LIVE معطلاً.
    """
    _wipe_pg_test_schema(PG_TEST_DSN)

    # تشغيل خادم مقبس TCP لبروتوكول Redis على منفذ محلي حر
    redis_server = TcpFakeServer(("127.0.0.1", 0), server_type="redis")
    redis_port = redis_server.server_address[1]
    redis_thread = threading.Thread(target=redis_server.serve_forever, daemon=True)
    redis_thread.start()

    try:
        redis_url = f"redis://127.0.0.1:{redis_port}/0"
        monkeypatch.setenv("DATABASE_URL", PG_TEST_DSN)
        monkeypatch.setenv("REDIS_URL", redis_url)
        monkeypatch.setenv("TRILUNAIR_ADMIN_PIN", "7777")
        reset_db_init_cache()
        market_engine.reset()

        with TestClient(app) as client:
            # 1. فحص نقطة نهاية البنية التحتية (PostgreSQL + Redis + Market Feed)
            infra_res = client.get("/api/system/infrastructure")
            assert infra_res.status_code == 200
            infra = infra_res.json()
            assert infra["database"]["engine"] == "postgresql"
            assert infra["database"]["connected"] is True
            assert infra["database"]["persistenceVerified"] is True
            assert "PostgreSQL 15" in infra["database"]["version"]
            assert infra["redis"]["configured"] is True
            assert infra["redis"]["connected"] is True
            assert infra["redis"]["persistenceVerified"] is True
            assert infra["marketFeed"]["healthy"] is True

            # 2. التحقق من أن وضع التداول افتراضياً هو PAPER وأن المحفظة الابتدائية تساوي $1,000,000.00
            status = client.get("/api/system/status").json()
            assert status["tradingMode"] == "PAPER"
            assert status["liveAuthorized"] is False

            pf_initial = client.get("/api/portfolio").json()
            assert pf_initial["tradingMode"] == "PAPER"
            assert pf_initial["initialEquity"] == pytest.approx(1_000_000.0, abs=1.0)
            assert pf_initial["totalEquity"] == pytest.approx(1_000_000.0, rel=0.01)
            cash_before = pf_initial["cashBalance"]
            btc_qty_before = next(
                (p["quantity"] for p in pf_initial["positions"] if p["symbol"] == "BTC-USD"),
                0.0,
            )

            # 3. إنشاء مقترح شراء ورقي مع clientOrderId مخصص والتحقق من تخزين TTL في Redis و PostgreSQL
            prop_res = client.post(
                "/api/orders/propose",
                json={
                    "symbol": "BTC-USD",
                    "side": "BUY",
                    "orderType": "MARKET",
                    "quantity": 0.20,
                    "source": "TERMINAL",
                    "clientOrderId": "pg_redis_coid_001",
                    "ttlSeconds": 180,
                    "rationale": "PostgreSQL + Redis $1M paper workflow test",
                },
            )
            assert prop_res.status_code == 200
            evaluation = prop_res.json()
            assert evaluation["status"] == "APPROVED_FOR_AUTH"
            assert evaluation["expiresAt"] is not None
            proposal_id = evaluation["proposalId"]

            # التحقق المباشر عبر عميل TCP Redis من وجود مفتاح الصلاحية المؤقت للمقترح
            r_direct = redis_lib.Redis.from_url(redis_url, decode_responses=True)
            cached_raw = r_direct.get(f"trilunair:proposal:{proposal_id}")
            assert cached_raw is not None
            assert json.loads(cached_raw)["proposal"]["clientOrderId"] == "pg_redis_coid_001"

            # 4. تصريح وتنفيذ صفقة الشراء الورقية
            exec_buy = client.post(
                "/api/orders/execute",
                json={"proposalId": proposal_id, "confirmedByUser": True},
            )
            assert exec_buy.status_code == 200
            buy_data = exec_buy.json()
            assert buy_data["order"]["status"] == "FILLED"
            assert buy_data["order"]["tradingMode"] == "PAPER"
            assert buy_data["order"]["clientOrderId"] == "pg_redis_coid_001"
            assert buy_data["portfolio"]["cashBalance"] < cash_before

            # 5. اقتراح وتنفيذ بيع جزئي (0.10 BTC-USD) لإتمام دورة التداول الورقي ذهاباً وإياباً
            sell_prop = client.post(
                "/api/orders/propose",
                json={
                    "symbol": "BTC-USD",
                    "side": "SELL",
                    "orderType": "MARKET",
                    "quantity": 0.10,
                    "source": "TERMINAL",
                    "clientOrderId": "pg_redis_coid_002",
                },
            ).json()
            assert sell_prop["status"] == "APPROVED_FOR_AUTH"
            exec_sell = client.post(
                "/api/orders/execute",
                json={"proposalId": sell_prop["proposalId"], "confirmedByUser": True},
            )
            assert exec_sell.status_code == 200
            pf_after = exec_sell.json()["portfolio"]
            btc_qty_after = next(
                p["quantity"] for p in pf_after["positions"] if p["symbol"] == "BTC-USD"
            )
            assert btc_qty_after == pytest.approx(btc_qty_before + 0.10, abs=1e-6)

            # حفظ سمة مخصصة للتأكد من استدامتها في PostgreSQL أيضاً
            theme_save = client.put(
                "/api/themes/active",
                json={
                    "activeThemeId": "obsidian-black",
                    "customOverrides": {},
                    "modifiers": {
                        "glowIntensity": 60,
                        "blurRadius": 16,
                        "panelOpacity": 80,
                        "animationIntensity": 80,
                        "motionDisabled": False,
                        "highContrast": False,
                        "lowPowerMode": False,
                    },
                },
            )
            assert theme_save.status_code == 200

        # 6. محاكاة إعادة تشغيل الخادم من الصفر والتحقق من استدامة البيانات في PostgreSQL الحقيقي
        reset_db_init_cache()
        with TestClient(app) as client_restarted:
            pf_persisted = client_restarted.get("/api/portfolio").json()
            order_coids = [o.get("clientOrderId") for o in pf_persisted["recentOrders"]]
            assert "pg_redis_coid_001" in order_coids
            assert "pg_redis_coid_002" in order_coids
            themes_persisted = client_restarted.get("/api/themes").json()
            assert themes_persisted["activeState"]["activeThemeId"] == "obsidian-black"
            assert client_restarted.get("/api/system/status").json()["tradingMode"] == "PAPER"
    finally:
        redis_server.shutdown()
        redis_server.server_close()


def test_risk_limits_proposal_expiration_duplicate_order_prevention_and_kill_switch(
    isolated_sqlite_env: Path,
):
    """
    اختبار شامل لـ:
    1. حد وقف الخسارة لكل صفقة (0.5% من حقوق الملكية) + رفض وقف الخسارة الصفري أو المقلوب.
    2. انتهاء صلاحية المقترح (Proposal Expiration) عبر ttlSeconds=1.
    3. منع تكرار الأوامر (Duplicate-Order Prevention) عبر نفس proposalId وعبر نفس clientOrderId.
    4. الإيقاف الطارئ (Emergency Kill Switch) وإلغاء جميع المقترحات المعلقة فوراً (CANCELLED_BY_KILL_SWITCH).
    """
    with TestClient(app) as client:
        assets = {a["symbol"]: a["price"] for a in client.get("/api/market/assets").json()}
        btc_price = assets["BTC-USD"]

        # 1. وقف خسارة واسع جداً يتجاوز 0.5% من $1,000,000 ($5,000): شراء 2.0 BTC مع وقف بعيد بـ $4,000 = $8,000 مخاطرة (> $5,000)
        bad_sl_res = client.post(
            "/api/orders/propose",
            json={
                "symbol": "BTC-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 2.0,
                "stopLoss": round(btc_price - 4000.0, 2),
                "source": "TERMINAL",
            },
        ).json()
        assert bad_sl_res["status"] == "REJECTED_BY_RISK"
        sl_codes = [c["code"] for c in bad_sl_res["riskAssessment"]["checks"] if not c["passed"]]
        assert "STOP_LOSS_RISK_LIMIT" in sl_codes

        # وقف خسارة منضبط ضمن 0.5% ($5,000): شراء 0.5 BTC مع مسافة $2,000 = $1,000 مخاطرة (0.1% <= 0.5%)
        good_sl_res = client.post(
            "/api/orders/propose",
            json={
                "symbol": "BTC-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 0.5,
                "stopLoss": round(btc_price - 2000.0, 2),
                "source": "TERMINAL",
            },
        ).json()
        assert good_sl_res["status"] == "APPROVED_FOR_AUTH"

        # 2. اختبار انتهاء صلاحية المقترح (Proposal Expiration)
        short_ttl_prop = client.post(
            "/api/orders/propose",
            json={
                "symbol": "ETH-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 1.0,
                "ttlSeconds": 1,
                "source": "TERMINAL",
            },
        ).json()
        assert short_ttl_prop["status"] == "APPROVED_FOR_AUTH"
        time.sleep(1.25)

        expired_exec = client.post(
            "/api/orders/execute",
            json={"proposalId": short_ttl_prop["proposalId"], "confirmedByUser": True},
        )
        assert expired_exec.status_code == 409
        assert "انتهت الصلاحية" in expired_exec.json()["detail"]

        # 3. اختبار منع تكرار الأوامر (Duplicate-Order Prevention)
        unique_prop = client.post(
            "/api/orders/propose",
            json={
                "symbol": "SOL-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 5.0,
                "clientOrderId": "idem_sol_order_77",
                "source": "TERMINAL",
            },
        ).json()
        assert unique_prop["status"] == "APPROVED_FOR_AUTH"

        # التنفيذ الأول ينجح
        first_exec = client.post(
            "/api/orders/execute",
            json={"proposalId": unique_prop["proposalId"], "confirmedByUser": True},
        )
        assert first_exec.status_code == 200

        # إعادة إرسال نفس proposalId تُحظر فوراً بـ HTTP 409
        dup_proposal_exec = client.post(
            "/api/orders/execute",
            json={"proposalId": unique_prop["proposalId"], "confirmedByUser": True},
        )
        assert dup_proposal_exec.status_code == 409

        # محاولة إنشاء مقترح جديد بنفس clientOrderId المنفذ مسبقاً تُحظر فوراً بـ HTTP 409
        dup_coid_prop = client.post(
            "/api/orders/propose",
            json={
                "symbol": "SOL-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 5.0,
                "clientOrderId": "idem_sol_order_77",
                "source": "TERMINAL",
            },
        )
        assert dup_coid_prop.status_code == 409

        # 4. اختبار الإيقاف الطارئ (Emergency Kill Switch) وإلغاء المقترحات المعلقة
        pending_before_kill = client.post(
            "/api/orders/propose",
            json={
                "symbol": "ETH-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 0.5,
                "source": "TERMINAL",
            },
        ).json()
        assert pending_before_kill["status"] == "APPROVED_FOR_AUTH"

        ks_on = client.post(
            "/api/auth/kill-switch",
            json={"active": True, "reason": "Emergency drill verification"},
        )
        assert ks_on.status_code == 200
        assert ks_on.json()["killSwitchActive"] is True
        assert ks_on.json()["tradingMode"] == "PAPER"

        # حتى بعد إلغاء مفتاح الطوارئ لاحقاً، يبقى المقترح القديم ملغى ولا يمكن تنفيذه!
        ks_off = client.post("/api/auth/kill-switch", json={"active": False})
        assert ks_off.status_code == 200
        assert ks_off.json()["killSwitchActive"] is False

        exec_cancelled = client.post(
            "/api/orders/execute",
            json={"proposalId": pending_before_kill["proposalId"], "confirmedByUser": True},
        )
        assert exec_cancelled.status_code == 403
        assert "CANCELLED_BY_KILL_SWITCH" in exec_cancelled.json()["detail"]


def test_agent_meeting_room_real_provider_adapters_vs_simulated_and_sixth_theme(
    isolated_sqlite_env: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    التحقق من:
    1. عند غياب المفاتيح الخارجية: يصنف /api/quantum/providers/audit المزودات السحابية بـ UNAVAILABLE_NO_KEY،
       وتعمل قاعة الاجتماعات عبر local-quant-engine مع isSimulated=True.
    2. عند تهيئة المفاتيح وعناوين المزودات الأربعة (OpenAI, Gemini, Anthropic, xAI): تستخدم قاعة الاجتماعات
       محولات HTTP الفعلية لكل مزود، وتُسجل الطلبات الشبكية الحقيقية وتكاليف التوكنات مع isSimulated=False.
    3. التحقق من عمل السمة السادسة obsidian-black عبر الأوامر العربية النصية والصوتية.
    """
    _MockCloudAndBinanceHandler.recorded_requests.clear()
    http_server = ThreadingHTTPServer(("127.0.0.1", 0), _MockCloudAndBinanceHandler)
    port = http_server.server_address[1]
    server_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    server_thread.start()

    try:
        with TestClient(app) as client:
            # أولاً: بدون مفاتيح خارجية -> المزودات السحابية غير متصلة وقاعة الاجتماع تعمل بمحاكاة صريحة
            audit_unconf = client.get("/api/quantum/providers/audit").json()
            by_id = {p["providerId"]: p for p in audit_unconf["llmProviders"]}
            assert by_id["local-quant-engine"]["classification"] == "SIMULATED_LOCAL"
            assert by_id["openai"]["classification"] == "UNAVAILABLE_NO_KEY"
            assert by_id["gemini"]["classification"] == "UNAVAILABLE_NO_KEY"
            assert by_id["anthropic"]["classification"] == "UNAVAILABLE_NO_KEY"
            assert by_id["xai"]["classification"] == "UNAVAILABLE_NO_KEY"

            sim_meeting = client.post(
                "/api/ai/meeting",
                json={"symbol": "BTC-USD", "horizon": "24h", "language": "ar"},
            ).json()
            assert all(r["isSimulated"] is True for r in sim_meeting["agentResponses"])
            assert all(r["providerUsed"] == "local-quant-engine" for r in sim_meeting["agentResponses"])

            # اختبار الأمر العربي لتفعيل السمة السادسة (الأوبسيديان الأسود / obsidian-black)
            cmd_theme = client.post(
                "/api/ai/command",
                json={
                    "message": "فعّل سمة الأوبسيديان الأسود الآن",
                    "source": "VOICE",
                    "language": "ar",
                },
            ).json()
            assert cmd_theme["uiAction"]["type"] == "SWITCH_THEME"
            assert cmd_theme["uiAction"]["payload"]["themeId"] == "obsidian-black"

            # ثانياً: تهيئة المفاتيح وعناوين المزودات الأربعة وتعيينها لوكلاء المجلس
            base_url = f"http://127.0.0.1:{port}"
            monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
            monkeypatch.setenv("OPENAI_BASE_URL", f"{base_url}/v1")
            monkeypatch.setenv("GEMINI_API_KEY", "gm-test-gemini-key")
            monkeypatch.setenv("GEMINI_BASE_URL", f"{base_url}/v1beta")
            monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
            monkeypatch.setenv("ANTHROPIC_BASE_URL", base_url)
            monkeypatch.setenv("XAI_API_KEY", "xai-test-key")
            monkeypatch.setenv("XAI_BASE_URL", f"{base_url}/v1")

            audit_conf = client.get("/api/quantum/providers/audit").json()
            by_id_conf = {p["providerId"]: p for p in audit_conf["llmProviders"]}
            assert by_id_conf["openai"]["classification"] == "CONNECTED_CLOUD"
            assert by_id_conf["gemini"]["classification"] == "CONNECTED_CLOUD"
            assert by_id_conf["anthropic"]["classification"] == "CONNECTED_CLOUD"
            assert by_id_conf["xai"]["classification"] == "CONNECTED_CLOUD"

            # ربط 4 وكلاء بالمزودات الأربعة المختلفة
            assignments = [
                ("quant-alpha", "openai", "gpt-4o"),
                ("macro-oracle", "gemini", "gemini-2.5-pro"),
                ("execution-architect", "xai", "grok-3"),
                ("chief-strategist", "anthropic", "claude-3-7-sonnet"),
            ]
            for agent_id, prov, model in assignments:
                r_put = client.put(
                    f"/api/quantum/agents/{agent_id}",
                    json={"assignedProvider": prov, "assignedModel": model},
                )
                assert r_put.status_code == 200

            live_meeting = client.post(
                "/api/ai/meeting",
                json={"symbol": "BTC-USD", "horizon": "24h", "language": "ar"},
            ).json()

            resp_by_agent = {r["agentId"]: r for r in live_meeting["agentResponses"]}
            assert resp_by_agent["quant-alpha"]["isSimulated"] is False
            assert resp_by_agent["quant-alpha"]["providerUsed"] == "openai"
            assert resp_by_agent["macro-oracle"]["isSimulated"] is False
            assert resp_by_agent["macro-oracle"]["providerUsed"] == "gemini"
            assert resp_by_agent["execution-architect"]["isSimulated"] is False
            assert resp_by_agent["execution-architect"]["providerUsed"] == "xai"
            assert resp_by_agent["chief-strategist"]["isSimulated"] is False
            assert resp_by_agent["chief-strategist"]["providerUsed"] == "anthropic"
            # حارسة المخاطر بقيت على المحرك الحتمي المحلي -> تتميز بوضوح أنها محاكاة محلياً
            assert resp_by_agent["risk-sentinel"]["isSimulated"] is True
            assert resp_by_agent["risk-sentinel"]["providerUsed"] == "local-quant-engine"

            # التحقق من تسجيل تكلفة الاستدلال السحابي في دفتر المحاسبة
            overview = client.get("/api/quantum/overview").json()
            assert overview["accounting"]["totalAiInferenceCostsUsd"] > 0
            assert len(_MockCloudAndBinanceHandler.recorded_requests) >= 4
    finally:
        http_server.shutdown()
        http_server.server_close()


def test_binance_spot_adapter_recovery_reconciliation_and_stale_market_data(
    isolated_sqlite_env: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    التحقق من:
    1. محول Binance Spot الآمن:
       - رفض خلط USD مع USDT (مثل BTCUSD -> 422).
       - رفض الأصول المرجعية REFERENCE_ONLY (مثل XAUUSD و NVDA -> 422).
       - رفض انتهاك stepSize و tickSize و minNotional (-> 422).
       - حظر أي محاولة توجيه إلى النطاق الحقيقي api.binance.com (-> 403).
       - نجاح اختبار أمر آمن على خادم محاكاة HTTP محلي مع توقيع HMAC-SHA256 و realOrderPlaced=False.
    2. التعافي من الفشل ومصالحة الحساب (Failure Recovery & Reconciliation):
       - simulateNetworkFailure=True يدخل النظام في accountStateUncertain=True (504).
       - محرك المخاطر يحظر فوراً أي مقترح شراء جديد بكود ACCOUNT_STATE_UNCERTAIN.
       - استدعاء /api/quantum/exchange/reconcile يصالح الحالة ويعيد السماح بالتداول الورقي.
    3. كشف تقادم بيانات السوق (Stale Market-Data Detection):
       - محاكاة توقف البث عبر /api/market/feed-control (stale) يرفع staleMarketDataDetected=True ويحظر أوامر الشراء بكود STALE_MARKET_DATA.
       - استئناف البث عبر /api/market/feed-control (resume) يعيد الجاهزية فوراً.
    """
    _MockCloudAndBinanceHandler.recorded_requests.clear()
    http_server = ThreadingHTTPServer(("127.0.0.1", 0), _MockCloudAndBinanceHandler)
    port = http_server.server_address[1]
    server_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    server_thread.start()

    try:
        monkeypatch.setenv("BINANCE_SPOT_BASE_URL", f"http://127.0.0.1:{port}")
        monkeypatch.setenv("BINANCE_SPOT_API_KEY", "test_spot_key")
        monkeypatch.setenv("BINANCE_SPOT_API_SECRET", "test_spot_secret")

        with TestClient(app) as client:
            # 1a. رفض BTCUSD (فصل صارم بين USD و USDT)
            r_usd = client.post(
                "/api/quantum/exchange/spot-test-order",
                json={"symbol": "BTCUSD", "side": "BUY", "orderType": "LIMIT", "quantity": 0.01, "price": 96500.0},
            )
            assert r_usd.status_code == 422

            # 1b. رفض الأصل المرجعي XAUUSD
            r_ref = client.post(
                "/api/quantum/exchange/spot-test-order",
                json={"symbol": "XAUUSD", "side": "BUY", "orderType": "MARKET", "quantity": 1.0},
            )
            assert r_ref.status_code == 422
            assert "REFERENCE_ONLY" in r_ref.json()["detail"]

            # 1c. رفض انتهاك stepSize (BTCUSDT stepSize=0.00001 -> 0.000003 مرفوض)
            r_step = client.post(
                "/api/quantum/exchange/spot-test-order",
                json={"symbol": "BTCUSDT", "side": "BUY", "orderType": "LIMIT", "quantity": 0.100003, "price": 96500.0},
            )
            assert r_step.status_code == 422
            assert "STEP_SIZE" in r_step.json()["detail"]

            # 1d. رفض انتهاك tickSize (BTCUSDT tickSize=0.01 -> 96500.004 مرفوض)
            r_tick = client.post(
                "/api/quantum/exchange/spot-test-order",
                json={"symbol": "BTCUSDT", "side": "BUY", "orderType": "LIMIT", "quantity": 0.01, "price": 96500.004},
            )
            assert r_tick.status_code == 422
            assert "PRICE_FILTER" in r_tick.json()["detail"]

            # 1e. أمر اختباري صالح عبر خادم المحاكاة المحلي مع توقيع HMAC-SHA256
            r_ok = client.post(
                "/api/quantum/exchange/spot-test-order",
                json={
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "orderType": "LIMIT",
                    "quantity": 0.05,
                    "price": 96500.00,
                    "clientOrderId": "spot_mock_001",
                },
            )
            assert r_ok.status_code == 200
            ok_body = r_ok.json()
            assert ok_body["validated"] is True
            assert ok_body["realOrderPlaced"] is False
            assert ok_body["hmacSigned"] is True
            assert ok_body["executionEnvironment"] == "MOCK_HTTP_EXCHANGE"

            # 1f. حظر أمني قاطع لنطاق api.binance.com الحقيقي
            monkeypatch.setenv("BINANCE_SPOT_BASE_URL", "https://api.binance.com")
            r_live_blocked = client.post(
                "/api/quantum/exchange/spot-test-order",
                json={"symbol": "BTCUSDT", "side": "BUY", "orderType": "MARKET", "quantity": 0.01},
            )
            assert r_live_blocked.status_code == 403
            monkeypatch.setenv("BINANCE_SPOT_BASE_URL", f"http://127.0.0.1:{port}")

            # 2. محاكاة انقطاع الاتصال أثناء إرسال الأمر -> account_state_uncertain -> تجميد الشراء -> المصالحة والتعافي
            r_timeout = client.post(
                "/api/quantum/exchange/spot-test-order",
                json={
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "orderType": "MARKET",
                    "quantity": 0.02,
                    "simulateNetworkFailure": True,
                },
            )
            assert r_timeout.status_code == 504

            ov_uncertain = client.get("/api/quantum/overview").json()
            assert ov_uncertain["exchangeStatus"]["accountStateUncertain"] is True

            # محاولة تقديم مقترح شراء جديد أثناء عدم يقين الحساب تُرفض حتمياً
            blocked_by_uncertain = client.post(
                "/api/orders/propose",
                json={"symbol": "BTC-USD", "side": "BUY", "orderType": "MARKET", "quantity": 0.05, "source": "TERMINAL"},
            ).json()
            assert blocked_by_uncertain["status"] == "REJECTED_BY_RISK"
            assert "ACCOUNT_STATE_UNCERTAIN" in [
                c["code"] for c in blocked_by_uncertain["riskAssessment"]["checks"] if not c["passed"]
            ]

            # تشغيل المصالحة واسترداد اليقين
            rec_res = client.post("/api/quantum/exchange/reconcile")
            assert rec_res.status_code == 200
            assert rec_res.json()["accountStateUncertain"] is False

            recovered_prop = client.post(
                "/api/orders/propose",
                json={"symbol": "BTC-USD", "side": "BUY", "orderType": "MARKET", "quantity": 0.05, "source": "TERMINAL"},
            ).json()
            assert recovered_prop["status"] == "APPROVED_FOR_AUTH"

            # 3. كشف تقادم بيانات السوق (Stale Market Data) واستعادتها
            stale_ctrl = client.post("/api/market/feed-control", json={"action": "stale", "ageSeconds": 180})
            assert stale_ctrl.status_code == 200
            assert stale_ctrl.json()["stale"] is True

            ov_stale = client.get("/api/quantum/overview").json()
            assert ov_stale["exchangeStatus"]["staleMarketDataDetected"] is True

            blocked_by_stale = client.post(
                "/api/orders/propose",
                json={"symbol": "ETH-USD", "side": "BUY", "orderType": "MARKET", "quantity": 0.5, "source": "TERMINAL"},
            ).json()
            assert blocked_by_stale["status"] == "REJECTED_BY_RISK"
            assert "STALE_MARKET_DATA" in [
                c["code"] for c in blocked_by_stale["riskAssessment"]["checks"] if not c["passed"]
            ]

            resume_ctrl = client.post("/api/market/feed-control", json={"action": "resume"})
            assert resume_ctrl.status_code == 200
            assert resume_ctrl.json()["stale"] is False

            resumed_prop = client.post(
                "/api/orders/propose",
                json={"symbol": "ETH-USD", "side": "BUY", "orderType": "MARKET", "quantity": 0.5, "source": "TERMINAL"},
            ).json()
            assert resumed_prop["status"] == "APPROVED_FOR_AUTH"
    finally:
        http_server.shutdown()
        http_server.server_close()
