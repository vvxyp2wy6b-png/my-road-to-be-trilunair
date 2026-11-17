"""
حزمة الاختبارات الشاملة للإصدار v1.1.0-cloud-paper (Cloud Integration & Production Hardening Suite).
تختبر فعلياً نقاط التحقق الـ 20 المطلوبة:
1. خلو المستودع وملفات التهيئة من أي رموز اختبار افتراضية (7777 / trilunair_quantum_pw) أو مفاتيح مكشوفة.
2. مصادقة المسؤول بنظام Fail-Closed (HTTP 503)، رفض الأسرار الضعيفة، التجزئة بـ PBKDF2-HMAC-SHA256،
   الحماية من التخمين المتكرر (HTTP 429 Brute-Force Lockout)، الجلسات الموقعة، حماية CSRF، وإبطال الجلسات.
3. القفل السيادي الدائم على وضع PAPER (liveAuthorized=false) وحظر تفعيل LIVE أو AUTONOMOUS نهائياً (HTTP 403).
4. اتساق الحدود الخمسة الموحدة للمخاطر (0.5% صفقة، 25% تعرض للأصل الواحد، 2% خسارة يومية، 5% خسارة أسبوعية، 10% سحب أقصى).
5. الاتصال الحقيقي بواجهة Binance Spot العامة للأسعار والشموع وعمق دفتر الأوامر وفلاتر الرموز
   (https://data-api.binance.vision/api/v3/...) مع مزامنة تسلسل دفتر الأوامر وبث WebSocket ومعالجة HTTP 429،
   وبقاء التنفيذ ورقياً 100% دون أي مسار لأمر حقيقي.
6. مرونة محولات الذكاء الاصطناعي المتعددة (إعادة المحاولة عند HTTP 503، التهدئة عند HTTP 429، التخزين المؤقت CACHED،
   عزل الأعطال UNAVAILABLE دون إسقاط المجلس، وحقول المداولة المثرية).
7. دعم صيغ الصوت المتوافقة مع متصفح Safari (audio/mp4) عبر /api/voice/stt، ولوحة العمليات السحابية الشفافة /api/system/operations.
"""

from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any
import yaml

from fastapi.testclient import TestClient
import pytest
import websockets

from app.binance_market_data import BinanceSpotPublicDataClient, OrderBookSynchronizer, binance_public_client
from app.database import db_session, init_db, reset_db_init_cache
from app.llm_adapters import reset_llm_adapter_state
from app.main import app
from app.market_engine import market_engine
from app.quantum_hub import ensure_quantum_tables
from app.safety_gateway import LIVE_CONFIRMATION_PHRASE
from app.security import ADMIN_SESSION_COOKIE, CSRF_HEADER_NAME, hash_admin_secret, rate_limiter, redact_sensitive_value


@pytest.fixture()
def hardened_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "v1_1_hardened.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_REDIS_URL", raising=False)
    monkeypatch.setenv("TRILUNAIR_DB_PATH", str(db_file))
    monkeypatch.setenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED")
    monkeypatch.delenv("TRILUNAIR_ADMIN_SECRET", raising=False)
    monkeypatch.delenv("TRILUNAIR_ADMIN_SECRET_HASH", raising=False)
    monkeypatch.delenv("TRILUNAIR_ADMIN_PIN", raising=False)
    for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    rate_limiter.reset()
    reset_llm_adapter_state()
    reset_db_init_cache()
    market_engine.reset()
    init_db()
    ensure_quantum_tables()
    yield db_file
    rate_limiter.reset()
    market_engine.reset()


def test_repository_configs_and_ui_purged_of_default_pins_and_secrets() -> None:
    """التحقق الصارم من خلو ملفات التهيئة والواجهة من الرمز التجريبي 7777 وكلمة المرور القديمة."""
    repo_root = Path(__file__).resolve().parents[2]

    env_example = (repo_root / ".env.example").read_text(encoding="utf-8")
    assert "7777" not in env_example
    assert "trilunair_quantum_pw" not in env_example
    assert "<REPLACE_WITH_" in env_example

    compose_main = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "7777" not in compose_main
    assert "trilunair_quantum_pw" not in compose_main
    parsed_main = yaml.safe_load(compose_main)
    assert "postgres" in parsed_main["services"]
    assert "redis" in parsed_main["services"]
    assert "trilunair-command-center" in parsed_main["services"]

    compose_cloud = (repo_root / "docker-compose.cloud.yml").read_text(encoding="utf-8")
    parsed_cloud = yaml.safe_load(compose_cloud)
    assert "caddy-reverse-proxy" in parsed_cloud["services"]
    assert (repo_root / "deploy" / "Caddyfile").is_file()

    gov_tsx = (repo_root / "frontend" / "src" / "components" / "Governance" / "GovernanceView.tsx").read_text(
        encoding="utf-8"
    )
    hub_tsx = (repo_root / "frontend" / "src" / "components" / "IntelligenceHub" / "IntelligenceHubView.tsx").read_text(
        encoding="utf-8"
    )
    assert "7777" not in gov_tsx
    assert "7777" not in hub_tsx


def test_fail_closed_auth_pbkdf2_brute_force_csrf_sessions_and_redaction(
    hardened_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    اختبار الأمان الصلب:
    - الإغلاق الآمن (HTTP 503) عند غياب سر المسؤول أو عند ضبط قيمة ضعيفة مثل 7777.
    - التجزئة والتحقق عبر PBKDF2-HMAC-SHA256.
    - الحظر المؤقت (HTTP 429) عند تكرار المحاولات الخاطئة.
    - الجلسات الموقعة (HttpOnly Cookie + X-CSRF-Token) ورفض التعديل بدون CSRF وإبطال الجلسة عند الخروج.
    - ترويسات الأمان الصارمة وتنقية الأسرار من السجلات.
    """
    monkeypatch.setenv("TRILUNAIR_ENV", "production")
    monkeypatch.setenv("TRILUNAIR_ALLOWED_ORIGINS", "https://testserver")
    monkeypatch.setenv("TRILUNAIR_AUTH_MAX_ATTEMPTS", "3")

    with TestClient(app, base_url="https://testserver") as client:
        # 1. بدون تهيئة أي سر مسؤول -> يجب أن يفشل الدخول بإغلاق آمن HTTP 503
        r_unconf = client.post("/api/auth/session/login", json={"adminSecret": "SomeStrongCandidate#1"})
        assert r_unconf.status_code == 503

        # 2. تهيئة الرمز الضعيف المحظور 7777 -> يجب أن يُرفض أيضاً بـ HTTP 503 (WEAK_SECRET)
        monkeypatch.setenv("TRILUNAIR_ADMIN_PIN", "7777")
        r_weak = client.post("/api/auth/session/login", json={"adminSecret": "7777"})
        assert r_weak.status_code == 503
        monkeypatch.delenv("TRILUNAIR_ADMIN_PIN", raising=False)

        # 3. تهيئة تجزئة PBKDF2-HMAC-SHA256 قوية واختبار الحماية من التخمين (Brute Force -> 429)
        strong_secret = "DrMajoodQuantum#2026!Cloud"
        monkeypatch.setenv("TRILUNAIR_ADMIN_SECRET_HASH", hash_admin_secret(strong_secret))

        assert client.post("/api/auth/session/login", json={"adminSecret": "WrongAttempt#1"}).status_code == 403
        assert client.post("/api/auth/session/login", json={"adminSecret": "WrongAttempt#2"}).status_code == 403
        r_lockout = client.post("/api/auth/session/login", json={"adminSecret": "WrongAttempt#3"})
        assert r_lockout.status_code == 429
        assert "Retry-After" in r_lockout.headers

        # حتى السر الصحيح يُحظر مؤقتاً أثناء فترة التجميد قبل إعادة ضبط النافذة
        assert client.post("/api/auth/session/login", json={"adminSecret": strong_secret}).status_code == 429
        rate_limiter.reset()

        # 4. تسجيل الدخول الصحيح ينشئ ملف ارتباط HttpOnly ورمز CSRF
        login_res = client.post("/api/auth/session/login", json={"adminSecret": strong_secret})
        assert login_res.status_code == 200
        assert login_res.headers["X-Frame-Options"] == "DENY"
        assert login_res.headers["X-Content-Type-Options"] == "nosniff"
        assert login_res.headers["X-Trilunair-Execution-Mode"] == "PAPER-LOCKED"
        assert ADMIN_SESSION_COOKIE in login_res.cookies
        login_body = login_res.json()
        csrf_token = login_body["csrfToken"]
        session_token = login_body["sessionToken"]

        # 5. طلب حساس في الإنتاج يعتمد على الكوكي بدون ترويسة X-CSRF-Token يُرفض بـ HTTP 403
        no_csrf_feed = client.post("/api/market/feed-control", json={"action": "resume"})
        assert no_csrf_feed.status_code == 403

        # ومع ترويسة X-CSRF-Token الصحيحة يُقبل بـ HTTP 200
        ok_csrf_feed = client.post(
            "/api/market/feed-control",
            json={"action": "resume"},
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        assert ok_csrf_feed.status_code == 200

        # 6. تسجيل الخروج يبطل الجلسة فوراً حتى لو أُعيد استخدام رمز Bearer
        logout_res = client.post(
            "/api/auth/session/logout",
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert logout_res.status_code == 200
        assert logout_res.json()["revoked"] is True

        revoked_check = client.post(
            "/api/market/feed-control",
            json={"action": "resume"},
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert revoked_check.status_code == 401

    # 7. تنقية الأسرار من السجلات المركزية
    redacted = redact_sensitive_value(
        {
            "apiKey": "sk-testredact12345",
            "note": "Auth header Bearer eyJhbGciOiJIUzI1NiJ9.payload",
            "symbol": "BTCUSDT",
        }
    )
    assert redacted["apiKey"] == "[REDACTED]"
    assert "[REDACTED_SECRET]" in redacted["note"]
    assert redacted["symbol"] == "BTCUSDT"


def test_permanent_paper_lock_and_unified_five_risk_limits(
    hardened_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    التحقق من:
    - استحالة تفعيل LIVE أو AUTONOMOUS.
    - مطابقة الحدود الخمسة الموحدة للمخاطر (0.5% / 25% / 2% / 5% / 10%) في قاعدة البيانات والـ API والمحرك.
    """
    strong_secret = "RiskConsistency#2026!Secret"
    monkeypatch.setenv("TRILUNAIR_ADMIN_SECRET", strong_secret)

    with TestClient(app) as client:
        status = client.get("/api/system/status").json()
        rp = status["riskPolicy"]
        assert rp["maxRiskPerTradePct"] == 0.5
        assert rp["maxExposurePerAssetPct"] == 25.0
        assert rp["dailyLossLimitPct"] == 2.0
        assert rp["weeklyLossLimitPct"] == 5.0
        assert rp["maxDrawdownLimitPct"] == 10.0
        assert rp["prohibitLeverage"] is True

        # رفض تفعيل سياسة AUTONOMOUS في بوابة الحوكمة الكمية بـ HTTP 403
        auto_res = client.post(
            "/api/quantum/governance/policy",
            json={"policy": "AUTONOMOUS", "adminPin": strong_secret},
        )
        assert auto_res.status_code == 403

        # المحفظة المبدئية تحتوي على 0.5 BTC (~$48,250 = ~4.8%).
        # شراء 2.15 BTC إضافية (~$207,475 = ~20.7% حجم أمر منفرد <= 25%) يرفع إجمالي تركز BTC إلى ~25.5% (> 25%)!
        # في الإصدار القديم (35%) كان يمر؛ في الإصدار v1.1 (25%) يجب أن يُرفض بكود MAX_CONCENTRATION!
        conc_25_res = client.post(
            "/api/orders/propose",
            json={
                "symbol": "BTC-USD",
                "side": "BUY",
                "orderType": "MARKET",
                "quantity": 2.15,
                "source": "TERMINAL",
            },
        ).json()
        assert conc_25_res["status"] == "REJECTED_BY_RISK"
        failed_codes = [c["code"] for c in conc_25_res["riskAssessment"]["checks"] if not c["passed"]]
        assert "MAX_CONCENTRATION" in failed_codes

        # اختبار قاطع الخسارة اليومية (2.0%): إذا كان daily_start_equity = 1,030,000 وحقوق الملكية ~1,001,795 (خسارة ~2.74% >= 2%)
        with db_session() as conn:
            conn.execute("UPDATE system_state SET daily_start_equity = 1030000.0 WHERE id = 1")
        daily_breaker = client.post(
            "/api/orders/propose",
            json={"symbol": "SOL-USD", "side": "BUY", "orderType": "MARKET", "quantity": 5.0, "source": "TERMINAL"},
        ).json()
        assert daily_breaker["status"] == "REJECTED_BY_RISK"
        assert "DAILY_DRAWDOWN_LIMIT" in [
            c["code"] for c in daily_breaker["riskAssessment"]["checks"] if not c["passed"]
        ]

        # اختبار قاطع الخسارة الأسبوعية (5.0%) مع بقاء اليومية سليمة:
        with db_session() as conn:
            conn.execute(
                "UPDATE system_state SET daily_start_equity = 1002000.0, weekly_start_equity = 1060000.0 WHERE id = 1"
            )
        weekly_breaker = client.post(
            "/api/orders/propose",
            json={"symbol": "SOL-USD", "side": "BUY", "orderType": "MARKET", "quantity": 5.0, "source": "TERMINAL"},
        ).json()
        assert weekly_breaker["status"] == "REJECTED_BY_RISK"
        assert "WEEKLY_LOSS_LIMIT" in [
            c["code"] for c in weekly_breaker["riskAssessment"]["checks"] if not c["passed"]
        ]

        # اختبار قاطع السحب الأقصى (10.0%) مع بقاء اليومية والأسبوعية سليمتين:
        with db_session() as conn:
            conn.execute(
                "UPDATE system_state SET daily_start_equity = 1002000.0, weekly_start_equity = 1005000.0, peak_equity = 1120000.0 WHERE id = 1"
            )
        max_dd_breaker = client.post(
            "/api/orders/propose",
            json={"symbol": "SOL-USD", "side": "BUY", "orderType": "MARKET", "quantity": 5.0, "source": "TERMINAL"},
        ).json()
        assert max_dd_breaker["status"] == "REJECTED_BY_RISK"
        assert "MAX_DRAWDOWN_LIMIT" in [
            c["code"] for c in max_dd_breaker["riskAssessment"]["checks"] if not c["passed"]
        ]


def test_real_binance_spot_public_rest_and_websocket_sync_paper_only(
    hardened_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    التحقق المزدوج لبيانات سوق Binance Spot العامة (القسم 8):
    1. اتصال HTTPS حي وحقيقي بخادم Binance العام الرسمي (https://data-api.binance.vision)
       لجلب الأسعار الحية (ticker/24hr) والشموع (klines) وعمق دفتر الأوامر (depth) وفلاتر الرموز (exchangeInfo)،
       والتأكد من تغذية محرك السوق الورقي بها مع بقاء التنفيذ PAPER 100%.
    2. اختبار مزامنة تسلسل دفتر الأوامر (lastUpdateId / U / u) وبث WebSocket الحي عبر خادم WebSocket محلي.
    """
    monkeypatch.setenv("TRILUNAIR_MARKET_DATA_MODE", "LIVE_PUBLIC")
    monkeypatch.setenv("BINANCE_SPOT_PUBLIC_REST_URL", "https://data-api.binance.vision")

    live_tickers = binance_public_client.fetch_live_tickers(force=True)
    assert set(live_tickers.keys()) == {"BTC-USD", "ETH-USD", "SOL-USD"}
    assert live_tickers["BTC-USD"]["binanceSymbol"] == "BTCUSDT"
    assert live_tickers["BTC-USD"]["price"] > 1000.0
    assert live_tickers["ETH-USD"]["price"] > 50.0
    assert live_tickers["SOL-USD"]["price"] > 1.0

    filters = binance_public_client.fetch_exchange_filters()
    assert "BTCUSDT" in filters
    assert filters["BTCUSDT"]["tickSize"] > 0
    assert filters["BTCUSDT"]["stepSize"] > 0

    with TestClient(app) as client:
        assets = {a["symbol"]: a for a in client.get("/api/market/assets").json()}
        assert assets["BTC-USD"]["dataSource"] in {"BINANCE_PUBLIC_REST", "BINANCE_PUBLIC_WS"}
        assert assets["XAU-USD"]["dataSource"] == "SIMULATED"

        candles_btc = client.get("/api/market/candles/BTC-USD?timeframe=15m&limit=25").json()
        assert candles_btc["dataSource"] == "BINANCE_PUBLIC_REST"
        assert len(candles_btc["candles"]) >= 20
        assert len(candles_btc["bids"]) >= 5
        assert len(candles_btc["asks"]) >= 5
        assert candles_btc["lastUpdateId"] is not None

        # التأكد القاطع من أن التداول لا يزال PAPER ومقفلاً حتى أثناء تدفق أسعار Binance الحية
        ops = client.get("/api/system/operations").json()
        assert ops["executionSafety"]["tradingMode"] == "PAPER"
        assert ops["executionSafety"]["liveAuthorized"] is False
        assert ops["executionSafety"]["realOrdersPermitted"] is False
        assert ops["subsystems"]["binancePublicMarketData"]["restStatus"] == "CONNECTED"

    # اختبار خوارزمية مزامنة دفتر الأوامر (OrderBookSynchronizer) واكتشاف الفجوات التسلسلية
    ob = OrderBookSynchronizer("BTCUSDT")
    ob.apply_snapshot(last_update_id=1000, bids=[["96000.00", "1.5"]], asks=[["96001.00", "1.2"]])
    assert ob.synced is True
    # حدث متسلسل صالح: U <= 1001 <= u
    assert ob.apply_diff_event(first_update_id=1000, final_update_id=1002, bids=[["96000.50", "0.8"]], asks=[]) is True
    assert ob.last_update_id == 1002
    # فجوة تسلسلية (U=1010 > 1002 + 1) -> يجب أن يرفض التحديث ويطلب إعادة أخذ لقطة Snapshot
    assert ob.apply_diff_event(first_update_id=1010, final_update_id=1012, bids=[], asks=[]) is False
    assert ob.needs_resync is True

    # اختبار عميل WebSocket ضد خادم WebSocket محلي فعلي يرسل أحداث 24hrTicker
    async def _verify_local_ws_stream() -> None:
        ws_client = BinanceSpotPublicDataClient()

        async def _ws_handler(websocket):
            await websocket.send(
                json.dumps(
                    {
                        "stream": "btcusdt@ticker",
                        "data": {
                            "e": "24hrTicker",
                            "s": "BTCUSDT",
                            "c": "98765.43",
                            "P": "2.50",
                            "h": "99500.00",
                            "l": "96000.00",
                            "q": "1500000000.0",
                            "b": "98765.00",
                            "a": "98766.00",
                        },
                    }
                )
            )
            await websocket.wait_closed()

        async with websockets.serve(_ws_handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            async with websockets.connect(f"ws://127.0.0.1:{port}") as conn:
                raw_msg = await asyncio.wait_for(conn.recv(), timeout=3.0)
                ws_client.handle_ws_stream_payload(json.loads(raw_msg))

        snap = ws_client.get_cached_ticker("BTCUSDT")
        assert snap is not None
        assert snap["price"] == pytest.approx(98765.43)
        assert snap["source"] == "BINANCE_PUBLIC_WS"

    asyncio.run(_verify_local_ws_stream())


class _ResilientLlmAndVoiceMockHandler(BaseHTTPRequestHandler):
    """خادم اختبار محلي لاختبار إعادة المحاولة عند 503، التهدئة عند 429، التخزين المؤقت، وتفريغ صوت Safari mp4."""

    openai_attempts = 0
    xai_429_hits = 0
    stt_mime_seen: list[str] = []

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw_bytes = self.rfile.read(length) if length > 0 else b""

        if "/audio/transcriptions" in self.path:
            text_preview = raw_bytes.decode("latin-1", errors="ignore")
            if "audio/mp4" in text_preview:
                _ResilientLlmAndVoiceMockHandler.stt_mime_seen.append("audio/mp4")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"text": "حلل البيتكوين عبر سافاري"}).encode("utf-8"))
            return

        if "/xai/v1/chat/completions" in self.path:
            _ResilientLlmAndVoiceMockHandler.xai_429_hits += 1
            self.send_response(429)
            self.send_header("Retry-After", "45")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"rate_limit_exceeded"}')
            return

        if "/openai/v1/chat/completions" in self.path:
            _ResilientLlmAndVoiceMockHandler.openai_attempts += 1
            if _ResilientLlmAndVoiceMockHandler.openai_attempts == 1:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"transient_upstream_unavailable"}')
                return

        payload = json.dumps(
            {
                "stance": "BUY",
                "confidence": 86.0,
                "summaryAr": "استجابة سحابية ناجحة بعد التعافي من الخطأ العابر.",
                "summaryEn": "Cloud response succeeded after transient retry.",
                "keyMetricLabelAr": "مرونة السحابة",
                "keyMetricLabelEn": "Cloud Resilience",
                "keyMetricValue": "RETRY_OK",
            },
            ensure_ascii=False,
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "choices": [{"message": {"content": payload}}],
                    "usage": {"prompt_tokens": 110, "completion_tokens": 60},
                },
                ensure_ascii=False,
            ).encode("utf-8")
        )


def test_multi_provider_retry_cache_rate_limit_isolation_and_safari_mp4_voice(
    hardened_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    التحقق من:
    1. نجاح إعادة المحاولة التلقائية عند HTTP 503 ثم استخدام ذاكرة التخزين المؤقت (CACHED) في الطلب المتكرر.
    2. عزل فشل HTTP 429 لمزود xAI (يتحول الوكيل إلى UNAVAILABLE احتياطياً دون فشل اجتماع المجلس).
    3. دعم رفع ملف صوتي بصيغة Safari (audio/mp4) إلى /api/voice/stt.
    """
    _ResilientLlmAndVoiceMockHandler.openai_attempts = 0
    _ResilientLlmAndVoiceMockHandler.xai_429_hits = 0
    _ResilientLlmAndVoiceMockHandler.stt_mime_seen.clear()

    srv = ThreadingHTTPServer(("127.0.0.1", 0), _ResilientLlmAndVoiceMockHandler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()

    try:
        base = f"http://127.0.0.1:{port}"
        monkeypatch.setenv("OPENAI_API_KEY", "sk-resilience-test-key")
        monkeypatch.setenv("OPENAI_BASE_URL", f"{base}/openai/v1")
        monkeypatch.setenv("OPENAI_STT_URL", f"{base}/openai/v1/audio/transcriptions")
        monkeypatch.setenv("XAI_API_KEY", "xai-ratelimit-test-key")
        monkeypatch.setenv("XAI_BASE_URL", f"{base}/xai/v1")
        monkeypatch.setenv("TRILUNAIR_LLM_MAX_RETRIES", "2")
        monkeypatch.setenv("TRILUNAIR_LLM_CACHE_TTL_SEC", "60")

        with TestClient(app) as client:
            client.put(
                "/api/quantum/agents/quant-alpha",
                json={"assignedProvider": "openai", "assignedModel": "gpt-4o-mini"},
            )
            client.put(
                "/api/quantum/agents/execution-architect",
                json={"assignedProvider": "xai", "assignedModel": "grok-3-mini"},
            )

            # الاجتماع الأول: OpenAI يفشل أول مرة بـ 503 ثم ينجح في المحاولة الثانية (LIVE)؛ xAI يُرجع 429 فيُعزل كـ UNAVAILABLE دون إسقاط الاجتماع!
            m1 = client.post("/api/ai/meeting", json={"symbol": "BTC-USD", "horizon": "24h", "language": "ar"})
            assert m1.status_code == 200
            agents_m1 = {a["agentId"]: a for a in m1.json()["agentResponses"]}
            assert _ResilientLlmAndVoiceMockHandler.openai_attempts == 2
            assert agents_m1["quant-alpha"]["executionStatus"] == "LIVE"
            assert agents_m1["quant-alpha"]["uncertaintyPct"] == pytest.approx(14.0)
            assert agents_m1["quant-alpha"]["respondedAt"] is not None
            assert agents_m1["execution-architect"]["executionStatus"] == "UNAVAILABLE"
            assert agents_m1["risk-sentinel"]["executionStatus"] == "SIMULATED"

            # الاجتماع الثاني الفوري بنفس المعطيات: يجب أن يُخدم quant-alpha من الذاكرة المؤقتة بحالة CACHED دون استدعاء HTTP إضافي!
            m2 = client.post("/api/ai/meeting", json={"symbol": "BTC-USD", "horizon": "24h", "language": "ar"}).json()
            agents_m2 = {a["agentId"]: a for a in m2["agentResponses"]}
            assert agents_m2["quant-alpha"]["executionStatus"] == "CACHED"
            assert _ResilientLlmAndVoiceMockHandler.openai_attempts == 2

            # اختبار رفع ملف صوتي بصيغة Safari (speech.mp4 / audio/mp4) عبر /api/voice/stt
            stt_res = client.post(
                "/api/voice/stt",
                data={"language": "ar"},
                files={"file": ("speech.mp4", b"\x00\x00\x00\x18ftypmp42safari", "audio/mp4")},
            )
            assert stt_res.status_code == 200
            stt_json = stt_res.json()
            assert stt_json["status"] == "OK"
            assert stt_json["mimeType"] == "audio/mp4"
            assert "سافاري" in stt_json["transcript"]
            assert "audio/mp4" in _ResilientLlmAndVoiceMockHandler.stt_mime_seen
    finally:
        srv.shutdown()
        srv.server_close()
