"""
حزمة الاختبارات الشاملة للإصدار v1.3.0-binance-personal-guard:
تتحقق بصرامة من:
1. المصداقية الكاملة عند عدم تكوين مفاتيح المالك: إرجاع PENDING_OWNER_SETUP دون ادعاء الاتصال مطلقاً.
2. توليد زوج مفاتيح Ed25519 بالجانب الخلفي، التشفير بـ AES-256-GCM، ومزامنة القراءة فقط مقابل خادم محلي يحاكي Binance الرسمي
   ويتحقق تشفيرياً من توقيع Ed25519 وترويسة X-MBX-APIKEY.
3. فحص الصلاحيات المغلق بأمان (Fail-Closed): رفض فوري للمفاتيح التي تفعل السحب أو الهامش أو العقود الآجلة أو التحويلات أو التداول في فتحة القراءة.
4. اختبارات تسرب البيانات السرية والمدخلات المحظورة (رفض كلمات المرور وعبارات الاسترداد وOTP، عدم ظهور الأسرار في الردود أو قاعدة البيانات الصريحة أو السجلات أو مطالبات الذكاء الاصطناعي، التدوير والإبطال الفوري).
5. معالجة أخطاء الشبكة وتقييد المعدل (HTTP 429 Cooldown) من Binance.
6. إلزامية التصعيد البيومتري للمالك عبر WebAuthn Passkey (Face ID / Touch ID -> X-Step-Up-Token) لحفظ أو تدوير أو إبطال المفاتيح أو تعديل حدود التداول.
7. محاسبة المحفظة الفورية (متوسط التكلفة المرجح، الأرباح المحققة وغير المحققة بعد الرسوم، فصل رأس المال المودع عن أرباح السوق، والمطابقة دون ازدواج حسابي في ميزانية 2,125 ريال بالمدير المالي الشخصي مع بقاء محفظة المليون دولار الورقية مستقلة تماماً).
8. الاختبارات السلبية القاطعة (Negative Execution Gate Tests): إثبات استحالة تنفيذ أوامر العقود الآجلة أو الهامش أو الرافعة أو السحب أو الأوامر الفورية الحقيقية طالما النظام مقفل على PAPER (tradingMode='PAPER', liveAuthorized=False, executionLockedToPaper=True).
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi.testclient import TestClient
import pytest

from app.database import init_db
from app.main import app
from app.security import hash_admin_secret, rate_limiter, redact_sensitive_value, security_telemetry
from tests.test_v1_2_cloudflare_passkey_latency import (
    build_es256_assertion,
    build_es256_attestation_and_key,
)


class MockBinanceOfficialSpotServer:
    """
    خادم HTTP محلي معزول للاختبارات الآلية يحاكي نقاط نهاية Binance Spot & Capital الرسمية،
    ويتحقق فعلياً من توقيع Ed25519 الرقمي وترويسة X-MBX-APIKEY لكل طلب موقع!
    """

    def __init__(self) -> None:
        self.expected_api_key: str = ""
        self.expected_public_key_pem: str = ""
        self.api_restrictions: dict[str, Any] = {
            "ipRestrict": True,
            "createTime": 1731700000000,
            "enableReading": True,
            "enableSpotAndMarginTrading": False,
            "enableWithdrawals": False,
            "enableInternalTransfer": False,
            "enableMargin": False,
            "enableFutures": False,
            "permitsUniversalTransfer": False,
            "enableVanillaOptions": False,
        }
        self.sapi_restrictions_http_status: int = 200
        self.force_rate_limit_429: bool = False
        self.order_submissions_received: int = 0
        self.signature_verifications_passed: int = 0

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        self.balances = [
            {"asset": "USDT", "free": "166.67", "locked": "0.00"},
            {"asset": "BTC", "free": "0.00400000", "locked": "0.00000000"},
            {"asset": "ZERO", "free": "0.00000000", "locked": "0.00000000"},
        ]
        self.prices = [
            {"symbol": "BTCUSDT", "price": "105000.00"},
            {"symbol": "ETHUSDT", "price": "3400.00"},
            {"symbol": "SOLUSDT", "price": "210.00"},
        ]
        # إيداع 566.67 USDT (= 2,125.01 ريال)، شراء 0.005 BTC بسعر 100,000 (= 500 USDT) عمولة 0.50 USDT،
        # ثم بيع 0.001 BTC بسعر 110,000 (= 110 USDT) عمولة 0.10 USDT -> المتبقي 0.004 BTC و ~176.07 USDT (أو 166.67)
        # لنضبط الأرقام المحاسبية بدقة تامة 100% للمطابقة التامة (RECONCILED_EXACT):
        # الإيداع: 566.67 USDT
        # الشراء: 0.005 BTC @ 98,000 = 490.00 USDT، العمولة = 0.50 USDT -> النقد المتبقي = 76.17 USDT
        # البيع: 0.001 BTC @ 110,000 = 110.00 USDT، العمولة = 0.50 USDT -> النقد النهائي = 185.67 USDT، والـ BTC النهائي = 0.004 BTC!
        self.balances[0]["free"] = "185.67"
        self.deposits = [
            {
                "id": "dep_owner_2125_001",
                "amount": "566.67",
                "coin": "USDT",
                "network": "TRX",
                "status": 1,
                "txId": "0xmockdeposit2125sar001",
                "insertTime": now_ms - 3600_000,
            }
        ]
        self.withdrawals: list[dict[str, Any]] = []
        self.orders_by_symbol: dict[str, list[dict[str, Any]]] = {
            "BTCUSDT": [
                {
                    "symbol": "BTCUSDT",
                    "orderId": 900101,
                    "clientOrderId": "own_buy_1",
                    "price": "98000.00",
                    "origQty": "0.00500000",
                    "executedQty": "0.00500000",
                    "cummulativeQuoteQty": "490.00",
                    "status": "FILLED",
                    "type": "LIMIT",
                    "side": "BUY",
                    "time": now_ms - 2400_000,
                },
                {
                    "symbol": "BTCUSDT",
                    "orderId": 900102,
                    "clientOrderId": "own_sell_1",
                    "price": "110000.00",
                    "origQty": "0.00100000",
                    "executedQty": "0.00100000",
                    "cummulativeQuoteQty": "110.00",
                    "status": "FILLED",
                    "type": "LIMIT",
                    "side": "SELL",
                    "time": now_ms - 1200_000,
                },
            ]
        }
        self.trades_by_symbol: dict[str, list[dict[str, Any]]] = {
            "BTCUSDT": [
                {
                    "symbol": "BTCUSDT",
                    "id": 5001,
                    "orderId": 900101,
                    "price": "98000.00",
                    "qty": "0.00500000",
                    "quoteQty": "490.00",
                    "commission": "0.50",
                    "commissionAsset": "USDT",
                    "time": now_ms - 2400_000,
                    "isBuyer": True,
                    "isMaker": True,
                },
                {
                    "symbol": "BTCUSDT",
                    "id": 5002,
                    "orderId": 900102,
                    "price": "110000.00",
                    "qty": "0.00100000",
                    "quoteQty": "110.00",
                    "commission": "0.50",
                    "commissionAsset": "USDT",
                    "time": now_ms - 1200_000,
                    "isBuyer": False,
                    "isMaker": False,
                },
            ]
        }

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def _send_json(self, code: int, body: Any, extra_headers: dict[str, str] | None = None) -> None:
                raw = json.dumps(body).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("X-MBX-USED-WEIGHT-1M", "28")
                for hk, hv in (extra_headers or {}).items():
                    self.send_header(hk, hv)
                self.end_headers()
                self.wfile.write(raw)

            def _verify_ed25519_signed(self) -> bool:
                api_hdr = self.headers.get("X-MBX-APIKEY", "")
                if not outer.expected_api_key or api_hdr != outer.expected_api_key:
                    self._send_json(401, {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."})
                    return False
                parsed = urlparse(self.path)
                raw_qs = parsed.query
                if "&signature=" not in raw_qs:
                    self._send_json(400, {"code": -1102, "msg": "Mandatory parameter 'signature' was not sent."})
                    return False
                unsigned_qs, sig_part = raw_qs.rsplit("&signature=", 1)
                sig_b64 = parse_qs(f"signature={sig_part}")["signature"][0]
                pub_key = serialization.load_pem_public_key(outer.expected_public_key_pem.encode("utf-8"))
                assert isinstance(pub_key, ed25519.Ed25519PublicKey)
                try:
                    pub_key.verify(base64.b64decode(sig_b64), unsigned_qs.encode("ascii"))
                except Exception:
                    self._send_json(401, {"code": -1022, "msg": "Signature for this request is not valid."})
                    return False
                outer.signature_verifications_passed += 1
                return True

            def do_POST(self) -> None:  # noqa: N802
                outer.order_submissions_received += 1
                self._send_json(403, {"msg": "Real order should never reach Binance in PAPER lock!"})

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if outer.force_rate_limit_429 and parsed.path not in {"/api/v3/time", "/api/v3/ticker/price"}:
                    self._send_json(
                        429,
                        {"code": -1003, "msg": "Too many requests; current limit is 1200 requests per minute."},
                        extra_headers={"Retry-After": "12", "X-MBX-USED-WEIGHT-1M": "1200"},
                    )
                    return

                if parsed.path == "/api/v3/time":
                    self._send_json(200, {"serverTime": int(time.time() * 1000)})
                    return

                if parsed.path == "/api/v3/ticker/price":
                    self._send_json(200, outer.prices)
                    return

                if not self._verify_ed25519_signed():
                    return

                if parsed.path == "/api/v3/account":
                    self._send_json(
                        200,
                        {
                            "makerCommission": 10,
                            "takerCommission": 10,
                            "canTrade": bool(outer.api_restrictions.get("enableSpotAndMarginTrading", False)),
                            "canWithdraw": bool(outer.api_restrictions.get("enableWithdrawals", False)),
                            "canDeposit": True,
                            "accountType": "SPOT",
                            "permissions": ["SPOT"],
                            "balances": outer.balances,
                        },
                    )
                    return

                if parsed.path == "/sapi/v1/account/apiRestrictions":
                    if outer.sapi_restrictions_http_status != 200:
                        self._send_json(outer.sapi_restrictions_http_status, {"msg": "Endpoint unavailable"})
                        return
                    self._send_json(200, outer.api_restrictions)
                    return

                if parsed.path == "/api/v3/allOrders":
                    sym = parse_qs(parsed.query).get("symbol", ["BTCUSDT"])[0]
                    self._send_json(200, outer.orders_by_symbol.get(sym, []))
                    return

                if parsed.path == "/api/v3/myTrades":
                    sym = parse_qs(parsed.query).get("symbol", ["BTCUSDT"])[0]
                    self._send_json(200, outer.trades_by_symbol.get(sym, []))
                    return

                if parsed.path == "/sapi/v1/capital/deposit/hisrec":
                    self._send_json(200, outer.deposits)
                    return

                if parsed.path == "/sapi/v1/capital/withdraw/history":
                    self._send_json(200, outer.withdrawals)
                    return

                self._send_json(404, {"msg": "Not found"})

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self._httpd.server_port}"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


@pytest.fixture()
def v1_3_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "trilunair_v1_3_test.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("TRILUNAIR_DB_PATH", str(db_file))
    monkeypatch.setenv("TRILUNAIR_ENV", "development")
    monkeypatch.setenv("TRILUNAIR_PRIMARY_DOMAIN", "trilunair.medinsup.com")
    monkeypatch.setenv("TRILUNAIR_VAULT_MASTER_KEY", "TrilunairIsolatedVaultKey#2026! Aes256Gcm")
    monkeypatch.setenv("TRILUNAIR_SESSION_SECRET", "TrilunairSessionKey#2026!Isolated")
    monkeypatch.setenv(
        "TRILUNAIR_ADMIN_SECRET_HASH",
        hash_admin_secret("SovereignOwner#Bootstrap2026!"),
    )
    monkeypatch.setenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED")
    rate_limiter.reset()
    init_db()
    return db_file


@pytest.fixture()
def mock_binance():
    srv = MockBinanceOfficialSpotServer()
    srv.start()
    try:
        yield srv
    finally:
        srv.stop()


def test_default_pending_owner_setup_and_medinsup_secret_isolation(
    v1_3_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """التحقق من أن الحالة الافتراضية هي PENDING_OWNER_SETUP دائماً عند غياب مفاتيح المالك، وعزل متغيرات MEDINSUP_*."""
    _ = v1_3_env
    with TestClient(app) as client:
        ov = client.get("/api/binance/personal/overview").json()
        assert ov["connectionStatus"] == "PENDING_OWNER_SETUP"
        assert ov["tradingMode"] == "PAPER"
        assert ov["liveAuthorized"] is False
        assert ov["executionLockedToPaper"] is True
        assert ov["segregatedFromPaperTrading"] is True
        assert ov["balances"] == []

        cfo = client.get("/api/wealth/overview").json()
        bridge = cfo["binancePersonalCfoBridge"]
        assert bridge["connectionStatus"] == "PENDING_OWNER_SETUP"
        assert bridge["plannedMonthlyCryptoAllocationSar"] == 2125.0
        assert bridge["governanceInvariants"]["assumesGuaranteedReturns"] is False
        assert bridge["governanceInvariants"]["treatsProjectedEmploymentBenefitsAsCash"] is False
        assert bridge["actualVsPaperStrategyComparison"]["actualNetReturnAfterFeesPct"] is None

        # فحص كشف تصادم الأسرار مع MEDINSUP_*
        iso_ok = client.get("/api/infrastructure/isolation-audit").json()
        assert iso_ok["isolated"] is True
        assert iso_ok["checks"]["separateBinanceAndVaultSecretsVerified"] is True

        monkeypatch.setenv("MEDINSUP_PROD_DB_SECRET", "TrilunairIsolatedVaultKey#2026! Aes256Gcm")
        iso_collision = client.get("/api/infrastructure/isolation-audit").json()
        assert iso_collision["isolated"] is False
        assert iso_collision["checks"]["separateBinanceAndVaultSecretsVerified"] is False


def test_ed25519_vault_readonly_sync_accounting_and_cfo_anti_double_count(
    v1_3_env: Path,
    mock_binance: MockBinanceOfficialSpotServer,
) -> None:
    """
    اختبار دورة الربط الكاملة للقراءة فقط:
    - توليد زوج مفاتيح Ed25519 داخل خزنة الخادم (المفتاح الخاص مشفر بـ AES-256-GCM ولا يخرج للعميل).
    - التحقق التشفيري من توقيع Ed25519 ومزامنة الأرصدة والأوامر والصفقات والإيداعات.
    - التحقق من دقة محاسبة متوسط التكلفة والربح المحقق وغير المحقق بعد الرسوم، ومطابقة الـ 2,125 ريال دون ازدواج حسابي.
    - التأكد من عدم تأثر رصيد المحاكاة الورقية ($1,000,000 PAPER).
    """
    raw_api_key = "BN_PERSONAL_RO_KEY_998877665544332211_XYZ"
    mock_binance.expected_api_key = raw_api_key

    with TestClient(app) as client:
        paper_before = client.get("/api/portfolio").json()
        assert paper_before["totalEquity"] > 990_000.0
        paper_cash_before = paper_before["cashBalance"]

        # 1. توليد زوج مفاتيح Ed25519 بالجانب الخلفي
        gen_res = client.post(
            "/api/binance/personal/ed25519/generate",
            json={"purpose": "READ_ONLY_MONITORING", "adminSecret": "SovereignOwner#Bootstrap2026!"},
        )
        assert gen_res.status_code == 200
        gen_body = gen_res.json()
        assert gen_body["privateKeyExported"] is False
        assert "BEGIN PUBLIC KEY" in gen_body["publicKeyPem"]
        assert "PRIVATE KEY" not in json.dumps(gen_body)
        mock_binance.expected_public_key_pem = gen_body["publicKeyPem"]

        # 2. حفظ مفتاح API مقترناً بـ generatedKeypairId
        save_res = client.post(
            "/api/binance/personal/credentials",
            json={
                "purpose": "READ_ONLY_MONITORING",
                "keyLabel": "Majood Personal Read-Only",
                "authAlgorithm": "ED25519",
                "environment": "LOCAL_MOCK",
                "customBaseUrl": mock_binance.base_url,
                "apiKey": raw_api_key,
                "generatedKeypairId": gen_body["keypairId"],
                "trustedIps": ["203.0.113.77"],
                "trackedSymbols": ["BTCUSDT"],
                "verifyImmediately": True,
                "adminSecret": "SovereignOwner#Bootstrap2026!",
            },
        )
        assert save_res.status_code == 200, save_res.text
        saved = save_res.json()
        assert saved["saved"] is True
        assert saved["apiKeyMasked"] == "BN_P••••••••_XYZ"
        assert raw_api_key not in json.dumps(saved)
        assert saved["verification"]["connectionStatus"] == "VERIFIED_READ_ONLY"
        assert mock_binance.signature_verifications_passed >= 2

        # 3. التأكد من عدم تخزين مفتاح API أو المفتاح الخاص كنص صريح داخل ملف SQLite على القرص
        conn = sqlite3.connect(str(v1_3_env))
        db_dump = "\n".join(conn.iterdump())
        conn.close()
        assert raw_api_key not in db_dump
        assert "BEGIN PRIVATE KEY" not in db_dump
        assert "v1:aes256gcm:" in db_dump

        # 4. تشغيل مزامنة القراءة فقط والتحقق من المحاسبة والمطابقة
        sync_res = client.post(
            "/api/binance/personal/sync",
            json={"purpose": "READ_ONLY_MONITORING", "adminSecret": "SovereignOwner#Bootstrap2026!"},
        )
        assert sync_res.status_code == 200, sync_res.text
        ov = sync_res.json()
        assert ov["connectionStatus"] == "VERIFIED_READ_ONLY"
        assert raw_api_key not in json.dumps(ov)

        ps = ov["portfolioSummary"]
        # التحقق الرياضي الدقيق:
        # الشراء: 0.005 BTC بتكلفة 490 USDT + 0.50 عمولة = 490.50 USDT -> متوسط التكلفة = 98,100.00 دولار/BTC
        # البيع: 0.001 BTC بسعر 110,000 = 110 USDT - 0.50 عمولة = 109.50 صافي، وتكلفة الجزء المباع = 98.10 -> ربح محقق = +11.40 دولار!
        # المتبقي: 0.004 BTC بسعر حالي 105,000 = 420.00 دولار، وتكلفته المتبقية = 0.004 * 98,100 = 392.40 -> ربح غير محقق = +27.60 دولار!
        # النقد المتاح: 185.67 USDT -> إجمالي المحفظة = 420.00 + 185.67 = 605.67 دولار!
        assert ps["availableQuoteCashUsd"] == pytest.approx(185.67, abs=0.02)
        assert ps["investedCryptoCapitalUsd"] == pytest.approx(420.00, abs=0.02)
        assert ps["totalEquityUsd"] == pytest.approx(605.67, abs=0.02)
        assert ps["netContributedCapitalUsd"] == pytest.approx(566.67, abs=0.02)
        assert ps["realizedPnlUsd"] == pytest.approx(11.40, abs=0.02)
        assert ps["unrealizedPnlUsd"] == pytest.approx(27.60, abs=0.02)
        assert ps["cumulativeFeesUsd"] == pytest.approx(1.00, abs=0.01)
        assert ps["reconciliationStatus"] == "RECONCILED_EXACT"

        # 5. اختبار عدم الازدواج الحسابي في المدير المالي الشخصي (Personal CFO SAR 2,125):
        # نستورد كشف حساب بنكي بتحويل 2,125 ريال إلى Binance، ونسجل قيد دفتر أستاذ بـ 2,125 ريال،
        # بجانب إيداع Binance المتزامن (566.67 USDT = 2,125.01 ريال) ومشتريات BTC (490 USDT = 1,837.50 ريال)
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        client.post(
            "/api/wealth/statements/import",
            json={
                "transactions": [
                    {
                        "txDate": today_iso,
                        "description": "Bank Transfer to Personal Binance Spot",
                        "amountSar": 2125.0,
                        "category": "INVESTMENT_ALLOCATION",
                        "accountSource": "ALRAJHI_CURRENT",
                        "entryKind": "ACTUAL_EXPENSE",
                    }
                ]
            },
        )
        client.post(
            "/api/wealth/investment/ledger",
            json={
                "contributionDate": today_iso,
                "amountSar": 2125.0,
                "diversifiedWeightPct": 0.0,
                "saudiEquitiesWeightPct": 0.0,
                "cryptoSpotPaperWeightPct": 100.0,
            },
        )

        cfo = client.get("/api/wealth/overview").json()
        rec = cfo["binancePersonalCfoBridge"]["cycleReconciliation"]
        assert rec["reconciledWithoutDoubleCount"] is True
        # بدلاً من جمع (2125 + 2125 + 2125.01 + 1837.50 = 8,212.51 ريال)، يوحدها المحرك في 2,125.01 ريال فقط!
        assert rec["deduplicatedActualDeploymentSar"] == pytest.approx(2125.01, abs=0.05)

        # 6. التأكد من أن محفظة المليون دولار الورقية لم تتغير ولم تختلط بأرصدة Binance الفعلية
        paper_after = client.get("/api/portfolio").json()
        assert paper_after["cashBalance"] == pytest.approx(paper_cash_before, abs=0.01)
        assert paper_after["totalEquity"] > 990_000.0
        assert mock_binance.order_submissions_received == 0


def test_fail_closed_permission_scope_and_rate_limit_cooldown(
    v1_3_env: Path,
    mock_binance: MockBinanceOfficialSpotServer,
) -> None:
    """رفض المفاتيح ذات صلاحية السحب أو العقود الآجلة أو التداول في فتحة القراءة فقط، واختبار التهدئة عند HTTP 429."""
    _ = v1_3_env
    raw_key = "BN_UNSAFE_TEST_KEY_112233445566"
    mock_binance.expected_api_key = raw_key

    with TestClient(app) as client:
        gen = client.post(
            "/api/binance/personal/ed25519/generate",
            json={"purpose": "READ_ONLY_MONITORING", "adminSecret": "SovereignOwner#Bootstrap2026!"},
        ).json()
        mock_binance.expected_public_key_pem = gen["publicKeyPem"]

        client.post(
            "/api/binance/personal/credentials",
            json={
                "purpose": "READ_ONLY_MONITORING",
                "authAlgorithm": "ED25519",
                "environment": "LOCAL_MOCK",
                "customBaseUrl": mock_binance.base_url,
                "apiKey": raw_key,
                "generatedKeypairId": gen["keypairId"],
                "verifyImmediately": False,
                "adminSecret": "SovereignOwner#Bootstrap2026!",
            },
        )

        # 1. تفعيل السحب والهامش على Binance يجب أن يُحظر فوراً بـ HTTP 403
        mock_binance.api_restrictions["enableWithdrawals"] = True
        mock_binance.api_restrictions["enableFutures"] = True
        bad_perm = client.post(
            "/api/binance/personal/verify-permissions",
            json={"purpose": "READ_ONLY_MONITORING", "adminSecret": "SovereignOwner#Bootstrap2026!"},
        )
        assert bad_perm.status_code == 403
        assert "WITHDRAWALS_PERMISSION_FORBIDDEN" in bad_perm.json()["detail"]
        assert "FUTURES_LEVERAGE_PERMISSION_FORBIDDEN" in bad_perm.json()["detail"]
        assert client.get("/api/binance/personal/overview").json()["connectionStatus"] == "BLOCKED_UNSAFE_PERMISSIONS"

        # 2. تفعيل التداول الفوري داخل فتحة القراءة فقط (READ_ONLY_MONITORING) يُرفض أيضاً لفرض الفصل بين المفاتيح
        mock_binance.api_restrictions["enableWithdrawals"] = False
        mock_binance.api_restrictions["enableFutures"] = False
        mock_binance.api_restrictions["enableSpotAndMarginTrading"] = True
        ro_trading_reject = client.post(
            "/api/binance/personal/verify-permissions",
            json={"purpose": "READ_ONLY_MONITORING", "adminSecret": "SovereignOwner#Bootstrap2026!"},
        )
        assert ro_trading_reject.status_code == 403
        assert "READ_ONLY_SLOT_REJECTS_TRADING_PERMISSION" in ro_trading_reject.json()["detail"]

        # 3. تعذر الوصول لـ /sapi/v1/account/apiRestrictions يُغلق بأمان (Fail-Closed HTTP 502)
        mock_binance.api_restrictions["enableSpotAndMarginTrading"] = False
        mock_binance.sapi_restrictions_http_status = 500
        fail_closed = client.post(
            "/api/binance/personal/verify-permissions",
            json={"purpose": "READ_ONLY_MONITORING", "adminSecret": "SovereignOwner#Bootstrap2026!"},
        )
        assert fail_closed.status_code == 502
        mock_binance.sapi_restrictions_http_status = 200

        # 4. اختبار استجابة التهدئة عند HTTP 429 (Rate Limit Cooldown)
        mock_binance.force_rate_limit_429 = True
        rl_first = client.post(
            "/api/binance/personal/verify-permissions",
            json={"purpose": "READ_ONLY_MONITORING", "adminSecret": "SovereignOwner#Bootstrap2026!"},
        )
        assert rl_first.status_code == 429
        mock_binance.force_rate_limit_429 = False
        # الطلب التالي فوراً يُرفض محلياً بفترة التهدئة دون إغراق خادم Binance
        rl_cached = client.post(
            "/api/binance/personal/verify-permissions",
            json={"purpose": "READ_ONLY_MONITORING", "adminSecret": "SovereignOwner#Bootstrap2026!"},
        )
        assert rl_cached.status_code == 429
        assert "BINANCE_RATE_LIMIT_COOLDOWN" in rl_cached.json()["detail"]


def test_prohibited_inputs_secret_redaction_rotation_and_revocation(
    v1_3_env: Path,
) -> None:
    """رفض كلمات المرور وعبارات الاسترداد وOTP، وتنقية الأسرار من السجلات ومطالبات الذكاء الاصطناعي، والتدوير والإبطال."""
    _ = v1_3_env
    with TestClient(app) as client:
        # 1. رفض إرسال كلمة مرور Binance أو OTP
        for bad_field in ("password", "binancePassword", "seedPhrase", "otp", "sessionCookie"):
            r = client.post(
                "/api/binance/personal/credentials",
                json={
                    "purpose": "READ_ONLY_MONITORING",
                    "authAlgorithm": "HMAC_SHA256",
                    "apiKey": "VALID_LOOKING_KEY_123456",
                    "apiSecret": "VALID_LOOKING_SECRET_123456",
                    bad_field: "never-accept-this",
                    "adminSecret": "SovereignOwner#Bootstrap2026!",
                },
            )
            assert r.status_code == 400
            assert "PROHIBITED_SENSITIVE_INPUT" in r.json()["detail"]

        # 2. رفض عبارة الاسترداد المكونة من 12 كلمة داخل حقل apiSecret
        mnemonic_res = client.post(
            "/api/binance/personal/credentials",
            json={
                "purpose": "READ_ONLY_MONITORING",
                "authAlgorithm": "HMAC_SHA256",
                "apiKey": "VALID_LOOKING_KEY_123456",
                "apiSecret": "abandon ability able about above absent absorb abstract absurd abuse access accident",
                "adminSecret": "SovereignOwner#Bootstrap2026!",
            },
        )
        assert mnemonic_res.status_code == 400
        assert "PROHIBITED_SEED_PHRASE_DETECTED" in mnemonic_res.json()["detail"]

        # 3. حفظ ثم تدوير ثم إبطال فوري مع عدم ظهور أي سر في السجلات
        secret_v1 = "HMAC_SUPER_SECRET_V1_DO_NOT_LEAK_999"
        secret_v2 = "HMAC_SUPER_SECRET_V2_ROTATED_888"
        s1 = client.post(
            "/api/binance/personal/credentials",
            json={
                "purpose": "READ_ONLY_MONITORING",
                "authAlgorithm": "HMAC_SHA256",
                "apiKey": "FIRST_KEY_1234567890",
                "apiSecret": secret_v1,
                "adminSecret": "SovereignOwner#Bootstrap2026!",
            },
        )
        assert s1.status_code == 200

        rot = client.post(
            "/api/binance/personal/credentials/READ_ONLY_MONITORING/rotate",
            json={
                "authAlgorithm": "HMAC_SHA256",
                "apiKey": "SECOND_KEY_0987654321",
                "apiSecret": secret_v2,
                "adminSecret": "SovereignOwner#Bootstrap2026!",
            },
        )
        assert rot.status_code == 200
        assert rot.json()["rotated"] is True
        ov_rot = client.get("/api/binance/personal/overview").json()
        assert ov_rot["credentialSlots"]["READ_ONLY_MONITORING"]["rotatedCount"] == 1
        assert ov_rot["credentialSlots"]["READ_ONLY_MONITORING"]["apiKeyMasked"] == "SECO••••••••4321"

        rev = client.delete(
            "/api/binance/personal/credentials/READ_ONLY_MONITORING?adminSecret=SovereignOwner%23Bootstrap2026%21"
        )
        assert rev.status_code == 200
        assert client.get("/api/binance/personal/overview").json()["connectionStatus"] == "PENDING_OWNER_SETUP"

        # 4. التحقق من تنقية الأسرار والمفاتيح الخاصة من السجلات وسياقات الذكاء الاصطناعي
        audit_text = json.dumps(client.get("/api/auth/audit-logs").json())
        telemetry_text = json.dumps(security_telemetry.snapshot())
        for forbidden_leak in (secret_v1, secret_v2, "FIRST_KEY_1234567890", "SECOND_KEY_0987654321"):
            assert forbidden_leak not in audit_text
            assert forbidden_leak not in telemetry_text

        fake_pem = "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIFakeKeyMaterial1234567890\n-----END PRIVATE KEY-----"
        scrubbed_prompt = redact_sensitive_value(
            f"Analyze portfolio X-MBX-APIKEY: SECRETKEY123456789 and signature=abcdef0123456789abcdef012345 {fake_pem}"
        )
        assert "SECRETKEY123456789" not in scrubbed_prompt
        assert "IFakeKeyMaterial" not in scrubbed_prompt
        assert "[REDACTED_PRIVATE_KEY_PEM]" in scrubbed_prompt


def test_biometric_passkey_step_up_and_negative_live_spot_execution_locks(
    v1_3_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    اختبار إلزامية التصعيد البيومتري (Face ID / Touch ID WebAuthn Passkey) والاختبارات السلبية القاطعة:
    - بعد تسجيل مفتاح مرور للمالك، يُرفض حفظ المفاتيح أو تعديل سقوف LIVE_SPOT بدون X-Step-Up-Token (HTTP 403).
    - تُحظر كافة عمليات العقود الآجلة والهامش والرافعة والاقتراض والسحب والتحويلات والتصعيد الذاتي (HTTP 403).
    - يُحظر إرسال أو إلغاء أي أمر تداول فوري حقيقي حتى بعد تقديم X-Step-Up-Token واجتياز البوابات ١–٧،
      ويظل النظام مقفلاً على PAPER (tradingMode='PAPER', liveAuthorized=False, executionLockedToPaper=True).
    """
    _ = v1_3_env
    origin = "https://trilunair.medinsup.com"
    monkeypatch.setenv("TRILUNAIR_WEBAUTHN_RP_ID", "trilunair.medinsup.com")

    with TestClient(app) as client:
        # 1. تسجيل مفتاح مرور ES256 حقيقي (Face ID / Touch ID) للمالك
        reg_opts = client.post(
            "/api/auth/passkey/register/options",
            headers={"Origin": origin},
            json={
                "adminSecret": "SovereignOwner#Bootstrap2026!",
                "deviceLabel": "Owner iPhone 16 Pro Face ID",
            },
        ).json()
        priv_key, cred_payload = build_es256_attestation_and_key(
            rp_id="trilunair.medinsup.com",
            challenge_b64=reg_opts["publicKey"]["challenge"],
            origin=origin,
            credential_id_raw=b"majood_faceid_v1_3_cred_01",
            sign_count=10,
        )
        reg_ver = client.post(
            "/api/auth/passkey/register/verify",
            headers={"Origin": origin},
            json={
                "challengeId": reg_opts["challengeId"],
                "deviceLabel": "Owner iPhone 16 Pro Face ID",
                "credential": cred_payload,
            },
        )
        assert reg_ver.status_code == 200
        cred_id = reg_ver.json()["credentialId"]

        # 2. محاولة حفظ مفتاح Binance باستخدام رمز المسؤول فقط وبدون X-Step-Up-Token البيومتري تُرفض بـ HTTP 403!
        no_biometric = client.post(
            "/api/binance/personal/credentials",
            json={
                "purpose": "READ_ONLY_MONITORING",
                "authAlgorithm": "HMAC_SHA256",
                "apiKey": "BIO_PROTECTED_KEY_123456",
                "apiSecret": "BIO_PROTECTED_SECRET_123456",
                "adminSecret": "SovereignOwner#Bootstrap2026!",
            },
        )
        assert no_biometric.status_code == 403
        assert "BIOMETRIC_PASSKEY_STEP_UP_REQUIRED" in no_biometric.json()["detail"]

        # 3. إجراء مصادقة بيومترية حقيقية للحصول على X-Step-Up-Token قصير العمر
        auth_opts = client.post("/api/auth/passkey/authenticate/options", headers={"Origin": origin}).json()
        assertion = build_es256_assertion(
            priv_key=priv_key,
            rp_id="trilunair.medinsup.com",
            challenge_b64=auth_opts["publicKey"]["challenge"],
            origin=origin,
            credential_id_b64=cred_id,
            sign_count=11,
        )
        auth_ver = client.post(
            "/api/auth/passkey/authenticate/verify",
            headers={"Origin": origin},
            json={"challengeId": auth_opts["challengeId"], "credential": assertion},
        )
        assert auth_ver.status_code == 200
        step_up_token = auth_ver.json()["stepUpToken"]

        # 4. مع X-Step-Up-Token ينجح حفظ مفتاح القراءة وسقوف حدود المالك لـ LIVE_SPOT
        with_biometric = client.post(
            "/api/binance/personal/credentials",
            headers={"X-Step-Up-Token": step_up_token},
            json={
                "purpose": "READ_ONLY_MONITORING",
                "authAlgorithm": "HMAC_SHA256",
                "apiKey": "BIO_PROTECTED_KEY_123456",
                "apiSecret": "BIO_PROTECTED_SECRET_123456",
            },
        )
        assert with_biometric.status_code == 200
        assert with_biometric.json()["authorizedVia"] == "WEBAUTHN_BIOMETRIC_PASSKEY"

        limits_res = client.put(
            "/api/binance/spot-execution/limits",
            headers={"X-Step-Up-Token": step_up_token},
            json={
                "jurisdictionEligibilityConfirmed": True,
                "jurisdictionCountryCode": "SA",
                "maxSingleOrderSar": 750.0,
                "maxDailySpotSar": 1500.0,
                "maxMonthlySpotSar": 2125.0,
                "maxSingleAssetExposurePct": 45.0,
                "requireBiometricPerOrder": True,
                "allowedSpotSymbols": ["BTCUSDT", "ETHUSDT"],
            },
        )
        assert limits_res.status_code == 200
        readiness = limits_res.json()
        assert readiness["tradingMode"] == "PAPER"
        assert readiness["liveAuthorized"] is False
        assert readiness["executionLockedToPaper"] is True
        assert readiness["realOrdersPermitted"] is False
        gate8 = [g for g in readiness["gates"] if g["gateNumber"] == 8][0]
        assert gate8["passed"] is False

        # 5. التحقق الجاف (Dry-Run) يعمل بأمان دون إرسال أي أمر حقيقي، ويرفض تجاوز سقف الأمر الفردي (750 ريال)
        dry_ok = client.post(
            "/api/binance/spot-execution/dry-run",
            headers={"X-Step-Up-Token": step_up_token},
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "orderType": "LIMIT",
                "quantity": 0.001,
                "price": 100000.0,  # 100 USD = 375 SAR <= 750 SAR
            },
        )
        assert dry_ok.status_code == 200
        assert dry_ok.json()["passedValidation"] is True
        assert dry_ok.json()["realOrderSubmitted"] is False

        dry_over_cap = client.post(
            "/api/binance/spot-execution/dry-run",
            headers={"X-Step-Up-Token": step_up_token},
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "orderType": "LIMIT",
                "quantity": 0.01,
                "price": 100000.0,  # 1,000 USD = 3,750 SAR > 750 SAR
            },
        )
        assert dry_over_cap.status_code == 200
        assert dry_over_cap.json()["passedValidation"] is False
        assert any("EXCEEDS_MAX_SINGLE_ORDER_SAR" in r for r in dry_over_cap.json()["rejections"])

        # 6. الاختبارات السلبية المعمارية: حظر العقود الآجلة والهامش والرافعة والاقتراض والسحب والتحويلات والتصعيد الذاتي
        prohibited_cases = [
            {"symbol": "BTCUSDT", "marketType": "FUTURES", "side": "BUY", "quantity": 0.001},
            {"symbol": "BTCUSDT", "marketType": "MARGIN", "isIsolated": True, "side": "BUY", "quantity": 0.001},
            {"symbol": "BTCUSDT", "leverage": 5.0, "side": "BUY", "quantity": 0.001},
            {"symbol": "BTCUSDT", "sideEffectType": "MARGIN_BUY", "autoBorrow": True, "side": "BUY", "quantity": 0.001},
            {"operation": "WITHDRAWAL", "withdrawAddress": "0xexternal", "symbol": "USDT", "quantity": 50},
            {"operation": "UNIVERSAL_TRANSFER", "transferTarget": "UMFUTURE", "symbol": "USDT", "quantity": 50},
            {"operation": "ESCALATE_PERMISSIONS", "autonomousEscalation": True, "symbol": "BTCUSDT", "quantity": 0.001},
        ]
        for bad_payload in prohibited_cases:
            blocked = client.post(
                "/api/binance/spot-execution/submit",
                headers={"X-Step-Up-Token": step_up_token},
                json=bad_payload,
            )
            assert blocked.status_code == 403
            assert "PROHIBITED_NON_SPOT_OPERATION" in blocked.json()["detail"]

        # 7. الاختبار السلبي النهائي الحاسم: حتى الأمر الفوري الصحيح مع X-Step-Up-Token يُحظر تنفيذه الحقيقي بـ HTTP 403!
        spot_submit_blocked = client.post(
            "/api/binance/spot-execution/submit",
            headers={"X-Step-Up-Token": step_up_token},
            json={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "orderType": "LIMIT",
                "quantity": 0.001,
                "price": 100000.0,
            },
        )
        assert spot_submit_blocked.status_code == 403
        assert "LIVE_SPOT_EXECUTION_LOCKED_TO_PAPER" in spot_submit_blocked.json()["detail"]

        cancel_blocked = client.delete(
            "/api/binance/spot-execution/order?symbol=BTCUSDT&orderId=900101",
            headers={"X-Step-Up-Token": step_up_token},
        )
        assert cancel_blocked.status_code == 403
        assert "LIVE_SPOT_EXECUTION_LOCKED_TO_PAPER" in cancel_blocked.json()["detail"]

        final_sys = client.get("/api/system/status").json()
        assert final_sys["tradingMode"] == "PAPER"
        assert final_sys["liveAuthorized"] is False
        assert final_sys["executionLockedToPaper"] is True
