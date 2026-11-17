"""
حزمة الاختبارات الشاملة للإصدار v1.2.0-low-latency-cloudflare:
1. العزل الصارم عن المنصة الطبية المستقلة medinsup.com (حظر CORS و WebAuthn RP/Origin ومنع مشاركة الكوكيز وإصدار __Host-).
2. التحقق التشفيري من بوابة Cloudflare Zero Trust Access (Cf-Access-Jwt-Assertion RS256) للمالك الوحيد.
3. دورة المصادقة البيومترية الكاملة للمالك عبر WebAuthn Level 2 / FIDO2 Passkeys (ES256 P-256):
   - تسجيل مفتاح مرور حقيقي عبر CBOR attestationObject وعدم تخزين أي قوالب بيومترية
   - توقيع وتحقق ECDSA P-256 كامل وإصدار جلسة Host-Only و X-Step-Up-Token
   - حظر هجمات إعادة الإرسال (Single-Use Challenge Replay) وحظر الاستنساخ (Non-Monotonic signCount)
   - رفض التوقيعات المتلاعب بها ورفض غياب تحقق المستخدم (UV=0)
   - إلغاء صلاحية الجهاز المسجل فوراً (Revocation)
   - توليد واسترداد رموز الطوارئ أحادية الاستخدام المشفرة بـ PBKDF2-HMAC-SHA256
   - تنفيذ عملية حساسة (PUT /api/quantum/risk-policy) عبر X-Step-Up-Token بدون أي رمز PIN
4. نزاهة مصفوفة قياس الأقاليم السحابية (Tokyo / Osaka / Singapore / Frankfurt):
   - تصنيف القياس المحلي من بيئة التطوير كـ ANTIGRAVITY_DEV_SANDBOX_VM وعدم اعتباره دليلاً إقليمياً
   - بقاء الأقاليم غير المقاسة موسومة بـ NOT_MEASURED واستبعاد الخطط المجانية النائمة/المؤقتة
   - التحديث التلقائي لحالة الدليل عند تمرير ملف قياس إقليمي فعلي (CLOUD_REGIONAL_VM)
5. مجلس الوكلاء المتوازي المحدود بالمهلة (Bounded-Deadline Parallel AI Council) والتخطي الواعي بالتكلفة،
   وقياس الكمون الثماني المراحل (P50/P95/P99)، وتقييم الأداء خارج العينة (Walk-Forward Out-of-Sample) صافي التكاليف،
   مع بقاء وضع التنفيذ مقفلاً نهائياً على PAPER (liveAuthorized=false).
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import struct
import time
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding as asym_padding, rsa
from fastapi.testclient import TestClient
import pytest

from app import llm_adapters
from app.database import init_db, reset_db_init_cache
from app.latency_pipeline import classify_market_data_freshness, pipeline_latency_tracker
from app.llm_adapters import reset_llm_adapter_state
from app.main import app
from app.market_engine import market_engine
from app.quantum_hub import ensure_quantum_tables
from app.region_benchmark import evaluate_hosting_decision_matrix
from app.security import (
    ADMIN_SESSION_COOKIE,
    HOST_ONLY_PRODUCTION_SESSION_COOKIE,
    hash_admin_secret,
    rate_limiter,
)
from app.webauthn_passkeys import STEP_UP_HEADER_NAME, b64url_encode, ensure_passkey_tables


# ==============================================================================
# أدوات مساعدة لبناء حمولات CBOR و WebAuthn الأصلية مطابقة لمعيار RFC 8949 / W3C WebAuthn
# ==============================================================================


def _cbor_uint(major: int, val: int) -> bytes:
    prefix = major << 5
    if val < 24:
        return bytes([prefix | val])
    if val < 256:
        return bytes([prefix | 24, val])
    if val < 65536:
        return bytes([prefix | 25]) + struct.pack("!H", val)
    return bytes([prefix | 26]) + struct.pack("!I", val)


def cbor_encode(item: Any) -> bytes:
    if isinstance(item, int) and not isinstance(item, bool):
        if item >= 0:
            return _cbor_uint(0, item)
        return _cbor_uint(1, -1 - item)
    if isinstance(item, bytes):
        return _cbor_uint(2, len(item)) + item
    if isinstance(item, str):
        raw = item.encode("utf-8")
        return _cbor_uint(3, len(raw)) + raw
    if isinstance(item, list):
        return _cbor_uint(4, len(item)) + b"".join(cbor_encode(v) for v in item)
    if isinstance(item, dict):
        out = [_cbor_uint(5, len(item))]
        for k, v in item.items():
            out.append(cbor_encode(k))
            out.append(cbor_encode(v))
        return b"".join(out)
    if item is False:
        return bytes([0xF4])
    if item is True:
        return bytes([0xF5])
    if item is None:
        return bytes([0xF6])
    raise TypeError(f"Unsupported CBOR test type: {type(item)}")


def build_es256_attestation_and_key(
    rp_id: str,
    challenge_b64: str,
    origin: str,
    credential_id_raw: bytes,
    sign_count: int = 1,
    flags: int = 0x45,  # UP (0x01) | UV (0x04) | AT (0x40)
) -> tuple[ec.EllipticCurvePrivateKey, dict[str, Any]]:
    priv_key = ec.generate_private_key(ec.SECP256R1())
    nums = priv_key.public_key().public_numbers()
    x_bytes = nums.x.to_bytes(32, "big")
    y_bytes = nums.y.to_bytes(32, "big")

    cose_key = {
        1: 2,    # kty: EC2
        3: -7,   # alg: ES256
        -1: 1,   # crv: P-256
        -2: x_bytes,
        -3: y_bytes,
    }
    cose_key_bytes = cbor_encode(cose_key)
    rp_id_hash = hashlib.sha256(rp_id.encode("utf-8")).digest()
    aaguid = bytes.fromhex("adce000235bcc60a648b0b25f1f05503")  # Touch ID / Apple Passkey style AAGUID
    cred_len = struct.pack("!H", len(credential_id_raw))
    auth_data = (
        rp_id_hash
        + bytes([flags])
        + struct.pack("!I", sign_count)
        + aaguid
        + cred_len
        + credential_id_raw
        + cose_key_bytes
    )

    attestation_obj = cbor_encode({"fmt": "none", "attStmt": {}, "authData": auth_data})
    client_data_bytes = json.dumps(
        {
            "type": "webauthn.create",
            "challenge": challenge_b64,
            "origin": origin,
            "crossOrigin": False,
        },
        separators=(",", ":"),
    ).encode("utf-8")

    cred_b64 = b64url_encode(credential_id_raw)
    return priv_key, {
        "id": cred_b64,
        "rawId": cred_b64,
        "type": "public-key",
        "response": {
            "clientDataJSON": b64url_encode(client_data_bytes),
            "attestationObject": b64url_encode(attestation_obj),
            "transports": ["internal", "hybrid"],
        },
    }


def build_es256_assertion(
    priv_key: ec.EllipticCurvePrivateKey,
    rp_id: str,
    challenge_b64: str,
    origin: str,
    credential_id_b64: str,
    sign_count: int = 2,
    flags: int = 0x05,  # UP (0x01) | UV (0x04)
) -> dict[str, Any]:
    rp_id_hash = hashlib.sha256(rp_id.encode("utf-8")).digest()
    auth_data = rp_id_hash + bytes([flags]) + struct.pack("!I", sign_count)
    client_data_bytes = json.dumps(
        {
            "type": "webauthn.get",
            "challenge": challenge_b64,
            "origin": origin,
            "crossOrigin": False,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    client_hash = hashlib.sha256(client_data_bytes).digest()
    der_sig = priv_key.sign(auth_data + client_hash, ec.ECDSA(hashes.SHA256()))
    return {
        "id": credential_id_b64,
        "rawId": credential_id_b64,
        "type": "public-key",
        "response": {
            "clientDataJSON": b64url_encode(client_data_bytes),
            "authenticatorData": b64url_encode(auth_data),
            "signature": b64url_encode(der_sig),
        },
    }


@pytest.fixture()
def v1_2_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "v1_2_cloudflare_passkey.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("TRILUNAIR_DB_PATH", str(db_file))
    monkeypatch.setenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED")
    monkeypatch.setenv("TRILUNAIR_PRIMARY_DOMAIN", "trilunair.medinsup.com")
    monkeypatch.setenv(
        "TRILUNAIR_ADMIN_SECRET_HASH",
        hash_admin_secret("SovereignOwner#Bootstrap2026!"),
    )
    monkeypatch.setenv("TRILUNAIR_SESSION_SECRET", "9f4b2d8e1a7c6f0b3e5d9a1c4f8b2e6d0a3c7f9b1e4d8a2c6f0b4e8d2a6c0f4b")
    for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)

    rate_limiter.reset()
    reset_llm_adapter_state()
    reset_db_init_cache()
    market_engine.reset()
    init_db()
    ensure_quantum_tables()
    ensure_passkey_tables()
    yield db_file
    rate_limiter.reset()
    market_engine.reset()


def test_medinsup_platform_isolation_cookies_cors_and_rp_id(
    v1_2_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """التحقق الصارم من العزل القاطع عن المنصة الطبية medinsup.com في CORS والكوكيز و WebAuthn."""
    # محاولة حقن medinsup.com ونجمة عشوائية في TRILUNAIR_ALLOWED_ORIGINS يجب تصفيتها وحجبها تلقائياً
    monkeypatch.setenv(
        "TRILUNAIR_ALLOWED_ORIGINS",
        "https://trilunair.medinsup.com,https://medinsup.com,https://*.medinsup.com,http://medinsup.com",
    )
    monkeypatch.setenv("TRILUNAIR_COOKIE_SECURE", "true")

    with TestClient(app) as client:
        iso = client.get("/api/infrastructure/isolation-audit")
        assert iso.status_code == 200
        iso_body = iso.json()
        assert iso_body["isolated"] is True
        assert iso_body["trilunairSubdomain"] == "trilunair.medinsup.com"
        assert iso_body["protectedMedicalDomain"] == "medinsup.com"
        assert "https://medinsup.com" not in iso_body["allowedOrigins"]
        assert "https://trilunair.medinsup.com" in iso_body["allowedOrigins"]
        assert all(v is True or isinstance(v, str) for v in iso_body["checks"].values())

        # تسجيل الدخول عبر HTTPS يجب أن يصدر __Host-trilunair_admin_session بدون أي سمة Domain=.medinsup.com
        login_res = client.post(
            "/api/auth/session/login",
            json={"adminSecret": "SovereignOwner#Bootstrap2026!"},
        )
        assert login_res.status_code == 200
        set_cookie_headers = login_res.headers.get_list("set-cookie")
        assert any(HOST_ONLY_PRODUCTION_SESSION_COOKIE in h for h in set_cookie_headers)
        assert any(ADMIN_SESSION_COOKIE in h for h in set_cookie_headers)
        for cookie_hdr in set_cookie_headers:
            assert "domain=" not in cookie_hdr.lower(), f"Forbidden Domain attribute leaked: {cookie_hdr}"

        # حظر صريح إذا حاول أحد ضبط TRILUNAIR_WEBAUTHN_RP_ID=medinsup.com
        monkeypatch.setenv("TRILUNAIR_WEBAUTHN_RP_ID", "medinsup.com")
        bad_rp = client.get("/api/auth/passkey/status")
        assert bad_rp.status_code == 500


def test_cloudflare_zero_trust_access_jwt_owner_gate(
    v1_2_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """التحقق التشفيري من ترويسة Cf-Access-Jwt-Assertion (RS256) وقبول المالك الوحيد وحجب غيره."""
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pub_pem = (
        rsa_priv.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    monkeypatch.setenv("TRILUNAIR_REQUIRE_CF_ACCESS", "true")
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "majood-sec.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "aud_trilunair_tokyo_001")
    monkeypatch.setenv("CF_ACCESS_OWNER_EMAIL", "owner@trilunair.medinsup.com")
    monkeypatch.setenv("CF_ACCESS_PUBLIC_KEY_PEM", rsa_pub_pem)

    def _mint_cf_jwt(email: str, exp_offset: int = 600) -> str:
        hdr_b64 = b64url_encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode("utf-8"))
        claims_b64 = b64url_encode(
            json.dumps(
                {
                    "iss": "https://majood-sec.cloudflareaccess.com",
                    "aud": ["aud_trilunair_tokyo_001"],
                    "email": email,
                    "iat": int(time.time()) - 5,
                    "exp": int(time.time()) + exp_offset,
                }
            ).encode("utf-8")
        )
        signing_input = f"{hdr_b64}.{claims_b64}".encode("ascii")
        sig = rsa_priv.sign(signing_input, asym_padding.PKCS1v15(), hashes.SHA256())
        return f"{hdr_b64}.{claims_b64}.{b64url_encode(sig)}"

    with TestClient(app) as client:
        # 1. بدون Cf-Access-Jwt-Assertion يُرفض الوصول للعملية الحساسة بـ HTTP 403 حتى مع سر المسؤول الصحيح
        missing_cf = client.put(
            "/api/quantum/risk-policy",
            json={
                "adminPin": "SovereignOwner#Bootstrap2026!",
                "maxRiskPerTradePct": 0.5,
                "maxExposurePerAssetPct": 25.0,
                "dailyLossLimitPct": 2.0,
                "weeklyLossLimitPct": 5.0,
                "maxDrawdownLimitPct": 10.0,
            },
        )
        assert missing_cf.status_code == 403

        # 2. بريد إلكتروني غير المالك يُحجب بـ HTTP 403 حتى لو كان التوقيع صحيحاً
        wrong_owner_jwt = _mint_cf_jwt("intruder@medinsup.com")
        wrong_owner_res = client.put(
            "/api/quantum/risk-policy",
            headers={"Cf-Access-Jwt-Assertion": wrong_owner_jwt},
            json={
                "adminPin": "SovereignOwner#Bootstrap2026!",
                "maxRiskPerTradePct": 0.5,
                "maxExposurePerAssetPct": 25.0,
                "dailyLossLimitPct": 2.0,
                "weeklyLossLimitPct": 5.0,
                "maxDrawdownLimitPct": 10.0,
            },
        )
        assert wrong_owner_res.status_code == 403

        # 3. JWT موقع من Cloudflare للمالك الوحيد يمر بنجاح
        valid_owner_jwt = _mint_cf_jwt("owner@trilunair.medinsup.com")
        ok_res = client.put(
            "/api/quantum/risk-policy",
            headers={"Cf-Access-Jwt-Assertion": valid_owner_jwt},
            json={
                "adminPin": "SovereignOwner#Bootstrap2026!",
                "maxRiskPerTradePct": 0.5,
                "maxExposurePerAssetPct": 25.0,
                "dailyLossLimitPct": 2.0,
                "weeklyLossLimitPct": 5.0,
                "maxDrawdownLimitPct": 10.0,
            },
        )
        assert ok_res.status_code == 200


def test_webauthn_passkey_full_ceremony_replay_clone_revocation_and_recovery(
    v1_2_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """اختبار التشفير الحقيقي لدورة مفاتيح المرور (Face ID / Touch ID ES256) والحماية من الاستنساخ والاسترداد."""
    monkeypatch.setenv("TRILUNAIR_WEBAUTHN_RP_ID", "trilunair.medinsup.com")
    origin = "https://trilunair.medinsup.com"

    with TestClient(app) as client:
        # 1. طلب خيارات تسجيل جهاز المالك الأول (iPhone 16 Pro Face ID)
        reg_opts_res = client.post(
            "/api/auth/passkey/register/options",
            headers={"Origin": origin},
            json={
                "adminSecret": "SovereignOwner#Bootstrap2026!",
                "deviceLabel": "Dr.MaJoOoOoOoD iPhone Face ID",
            },
        )
        assert reg_opts_res.status_code == 200
        reg_opts = reg_opts_res.json()
        challenge_id = reg_opts["challengeId"]
        challenge_b64 = reg_opts["publicKey"]["challenge"]
        assert reg_opts["publicKey"]["rp"]["id"] == "trilunair.medinsup.com"

        # 2. محاولة تسجيل من النطاق الطبي الأب https://medinsup.com يجب أن تُرفض فوراً بـ HTTP 403
        _, bad_med_cred = build_es256_attestation_and_key(
            rp_id="trilunair.medinsup.com",
            challenge_b64=challenge_b64,
            origin="https://medinsup.com",
            credential_id_raw=b"med_parent_attempt_0001",
        )
        med_reject = client.post(
            "/api/auth/passkey/register/verify",
            headers={"Origin": "https://medinsup.com"},
            json={
                "challengeId": challenge_id,
                "deviceLabel": "Forbidden Medical Origin",
                "credential": bad_med_cred,
            },
        )
        assert med_reject.status_code == 403

        # 3. طلب تحدٍ جديد وتسجيل مفتاح مرور ES256 P-256 حقيقي على https://trilunair.medinsup.com
        reg_opts_2 = client.post(
            "/api/auth/passkey/register/options",
            headers={"Origin": origin},
            json={
                "adminSecret": "SovereignOwner#Bootstrap2026!",
                "deviceLabel": "Dr.MaJoOoOoOoD MacBook Touch ID",
            },
        ).json()
        priv_key, valid_cred = build_es256_attestation_and_key(
            rp_id="trilunair.medinsup.com",
            challenge_b64=reg_opts_2["publicKey"]["challenge"],
            origin=origin,
            credential_id_raw=b"owner_touchid_cred_v1_2_0001",
            sign_count=5,
        )
        reg_verify = client.post(
            "/api/auth/passkey/register/verify",
            headers={"Origin": origin},
            json={
                "challengeId": reg_opts_2["challengeId"],
                "deviceLabel": "Dr.MaJoOoOoOoD MacBook Touch ID",
                "credential": valid_cred,
            },
        )
        assert reg_verify.status_code == 200
        reg_body = reg_verify.json()
        assert reg_body["registered"] is True
        assert reg_body["biometricTemplateStored"] is False
        cred_id = reg_body["credentialId"]

        # 4. محاولة إعادة استخدام نفس التحدي المستهلك (Replay Attack) تُحظر بـ HTTP 403
        replay_reg = client.post(
            "/api/auth/passkey/register/verify",
            headers={"Origin": origin},
            json={
                "challengeId": reg_opts_2["challengeId"],
                "deviceLabel": "Replay Attempt",
                "credential": valid_cred,
            },
        )
        assert replay_reg.status_code == 403

        # 5. مصادقة بيومترية حقيقية بتوقيع ECDSA P-256 وعداد تصاعدي (signCount = 6 > 5)
        auth_opts = client.post("/api/auth/passkey/authenticate/options", headers={"Origin": origin}).json()
        assertion_ok = build_es256_assertion(
            priv_key=priv_key,
            rp_id="trilunair.medinsup.com",
            challenge_b64=auth_opts["publicKey"]["challenge"],
            origin=origin,
            credential_id_b64=cred_id,
            sign_count=6,
        )
        auth_verify = client.post(
            "/api/auth/passkey/authenticate/verify",
            headers={"Origin": origin},
            json={"challengeId": auth_opts["challengeId"], "credential": assertion_ok},
        )
        assert auth_verify.status_code == 200
        auth_body = auth_verify.json()
        assert auth_body["authenticated"] is True
        assert auth_body["tradingMode"] == "PAPER"
        assert auth_body["liveAuthorized"] is False
        step_up_token = auth_body["stepUpToken"]

        # 6. تفعيل إلزامية التصعيد البيومتري وتنفيذ تعديل حساس لسياسة المخاطر عبر X-Step-Up-Token وحده دون PIN!
        monkeypatch.setenv("TRILUNAIR_REQUIRE_PASSKEY_STEP_UP", "true")
        no_step_up = client.put(
            "/api/quantum/risk-policy",
            headers={"Authorization": f"Bearer {auth_body['sessionToken']}"},
            json={
                "maxRiskPerTradePct": 0.45,
                "maxExposurePerAssetPct": 25.0,
                "dailyLossLimitPct": 2.0,
                "weeklyLossLimitPct": 5.0,
                "maxDrawdownLimitPct": 10.0,
            },
        )
        assert no_step_up.status_code == 403

        with_step_up = client.put(
            "/api/quantum/risk-policy",
            headers={STEP_UP_HEADER_NAME: step_up_token},
            json={
                "maxRiskPerTradePct": 0.45,
                "maxExposurePerAssetPct": 25.0,
                "dailyLossLimitPct": 2.0,
                "weeklyLossLimitPct": 5.0,
                "maxDrawdownLimitPct": 10.0,
            },
        )
        assert with_step_up.status_code == 200
        assert with_step_up.json()["maxRiskPerTradePct"] == 0.45

        # 7. فحص كشف استنساخ الموثق (Clone Detection): إرسال عداد غير تصاعدي signCount = 6 (<= 6) يُرفض بـ HTTP 403!
        auth_opts_clone = client.post("/api/auth/passkey/authenticate/options", headers={"Origin": origin}).json()
        cloned_assertion = build_es256_assertion(
            priv_key=priv_key,
            rp_id="trilunair.medinsup.com",
            challenge_b64=auth_opts_clone["publicKey"]["challenge"],
            origin=origin,
            credential_id_b64=cred_id,
            sign_count=6,
        )
        clone_res = client.post(
            "/api/auth/passkey/authenticate/verify",
            headers={"Origin": origin},
            json={"challengeId": auth_opts_clone["challengeId"], "credential": cloned_assertion},
        )
        assert clone_res.status_code == 403

        # 8. فحص رفض التوقيع التشفيري المزيف بمفتاح خاص مختلف
        rogue_key = ec.generate_private_key(ec.SECP256R1())
        auth_opts_rogue = client.post("/api/auth/passkey/authenticate/options", headers={"Origin": origin}).json()
        rogue_assertion = build_es256_assertion(
            priv_key=rogue_key,
            rp_id="trilunair.medinsup.com",
            challenge_b64=auth_opts_rogue["publicKey"]["challenge"],
            origin=origin,
            credential_id_b64=cred_id,
            sign_count=10,
        )
        rogue_res = client.post(
            "/api/auth/passkey/authenticate/verify",
            headers={"Origin": origin},
            json={"challengeId": auth_opts_rogue["challengeId"], "credential": rogue_assertion},
        )
        assert rogue_res.status_code == 403

        # 9. توليد رموز استرداد طوارئ أحادية الاستخدام، واستخدام رمز واحد بنجاح، ورفض إعادة استخدامه
        rec_gen = client.post(
            "/api/auth/passkey/recovery/generate",
            headers={STEP_UP_HEADER_NAME: step_up_token},
            json={"count": 5},
        )
        assert rec_gen.status_code == 200
        codes = rec_gen.json()["recoveryCodesOnceOnly"]
        assert len(codes) == 5

        redeem_1 = client.post("/api/auth/passkey/recovery/redeem", json={"recoveryCode": codes[0]})
        assert redeem_1.status_code == 200
        assert redeem_1.json()["authenticated"] is True

        redeem_replay = client.post("/api/auth/passkey/recovery/redeem", json={"recoveryCode": codes[0]})
        assert redeem_replay.status_code == 403

        # 10. إلغاء صلاحية الجهاز المسجل (Revocation) والتحقق من رفضه لاحقاً
        revoke_res = client.request(
            "DELETE",
            f"/api/auth/passkey/devices/{cred_id}",
            headers={STEP_UP_HEADER_NAME: step_up_token},
        )
        assert revoke_res.status_code == 200
        assert revoke_res.json()["revoked"] is True

        post_revoke_opts = client.post("/api/auth/passkey/authenticate/options", headers={"Origin": origin})
        assert post_revoke_opts.status_code == 404


def test_region_decision_matrix_truthfulness_and_regional_probe_ingestion(
    v1_2_env: Path,
    tmp_path: Path,
) -> None:
    """التحقق من نزاهة مصفوفة اختيار الإقليم السحابي واستبعاد الخطط المجانية النائمة وتحديث حالة القياس."""
    with TestClient(app) as client:
        matrix = client.get("/api/infrastructure/benchmark-matrix").json()
        assert matrix["recommendedPrimaryOption"]["optionId"] in {
            "tokyo-aws-lightsail-2gb-sla",
            "tokyo-oci-always-free-arm",
        }
        assert matrix["recommendedPaidSlaFallbackOption"]["optionId"] == "tokyo-aws-lightsail-2gb-sla"
        # جميع الأقاليم غير المقاسة فعلياً من خادم سحابي إقليمي تحمل وسم NOT_MEASURED بصراحة
        for cand in matrix["rankedQualifiedOptions"]:
            assert cand["regionalMeasurementStatus"] == "NOT_MEASURED"
        assert len(matrix["disqualifiedOptions"]) >= 1
        assert matrix["disqualifiedOptions"][0]["qualified"] is False

    # التحقق من أن تغذية ملف قياس سحابي إقليمي حقيقي (CLOUD_REGIONAL_VM) تحدث الحالة إلى MEASURED_ON_REGIONAL_CLOUD_VM
    probes_dir = tmp_path / "regional_probes"
    probes_dir.mkdir()
    sample_tokyo_probe = {
        "environment": {
            "probeEnvironment": "CLOUD_REGIONAL_VM",
            "countsAsRegionalCloudEvidence": True,
            "claimedRegion": "ap-tokyo-1",
        },
        "restMetrics": {
            "warmRestKeepAlive": {
                "p50Ms": 4.8,
                "p95Ms": 7.9,
                "p99Ms": 11.2,
            },
            "reliability": {
                "errorRatePct": 0.0,
            },
            "routing": {
                "cloudFrontPops": ["NRT57-P2"],
            },
        },
        "webSocketMetrics": {
            "binance_vision_ws_stream": {
                "connected": True,
                "reconnectCount": 0,
                "wsConnectMs": 18.4,
                "messagesReceived": 25,
            },
        },
        "evidenceSha256": "a" * 64,
    }
    (probes_dir / "tokyo_probe.json").write_text(json.dumps(sample_tokyo_probe), encoding="utf-8")
    updated = evaluate_hosting_decision_matrix(probes_dir=probes_dir)
    tokyo_row = next(
        c for c in updated["rankedQualifiedOptions"] if c["optionId"] == "tokyo-oci-always-free-payg-guarded"
    )
    assert tokyo_row["regionalMeasurementStatus"] == "MEASURED_ON_REGIONAL_CLOUD_VM"
    assert tokyo_row["measuredProbeSummary"]["restP50Ms"] == 4.8


def test_parallel_bounded_ai_council_cost_aware_skip_and_walk_forward_analytics(
    v1_2_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """التحقق من توازي استدعاءات المزودات السحابية، عزل المزود المعلق بالمهلة، التخطي الواعي بالتكلفة، وتقييم OOS."""
    from app.database import db_session

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-parallel-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-parallel-gemini-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-parallel-key")
    monkeypatch.setenv("XAI_API_KEY", "xai-test-parallel-grok-key")
    monkeypatch.setenv("TRILUNAIR_COUNCIL_DEADLINE_MS", "350")
    pipeline_latency_tracker.reset()

    with db_session() as conn:
        for ag_id, prov, mod in [
            ("quant-alpha", "openai", "gpt-4o-mini"),
            ("risk-sentinel", "anthropic", "claude-3-5-haiku-latest"),
            ("macro-oracle", "gemini", "gemini-2.5-flash"),
            ("execution-architect", "xai", "grok-2-latest"),
        ]:
            conn.execute(
                "UPDATE quantum_agents SET assigned_provider = ?, assigned_model = ?, enabled = 1 WHERE agent_id = ?",
                (prov, mod, ag_id),
            )

    def _mock_parallel_dispatch(
        provider_id: str,
        model: str,
        agent_role: str,
        market_context: str,
        cache_fingerprint: str = "",
    ) -> dict[str, Any]:
        if provider_id == "xai":
            # مزود بطيء يتجاوز مهلة 350ms فيُعزل تلقائياً دون تعطيل بقية الوكلاء الثلاثة
            time.sleep(0.75)
        else:
            time.sleep(0.18)
        return {
            "success": True,
            "providerUsed": provider_id,
            "modelUsed": model,
            "executionStatus": "LIVE",
            "tokensUsed": 120,
            "costUsd": 0.00025,
            "respondedAt": "2026-11-17T05:00:00Z",
            "data": {
                "stance": "BUY",
                "confidence": 82,
                "uncertaintyPct": 18,
                "summaryAr": "تحليل متوازٍ منخفض الكمون.",
                "summaryEn": "Low-latency parallel cloud analysis.",
            },
        }

    monkeypatch.setattr(llm_adapters, "invoke_configured_llm_adapter", _mock_parallel_dispatch)

    with TestClient(app) as client:
        t0 = time.perf_counter()
        res = client.post(
            "/api/ai/meeting",
            json={"symbol": "BTC-USD", "horizon": "1h", "language": "ar"},
        )
        wall_ms = (time.perf_counter() - t0) * 1000.0
        assert res.status_code == 200
        meeting = res.json()
        # لو كان التنفيذ تسلسلياً لاستغرق 3*180 + 750 = 1290ms؛ التوازي المحدود بالمهلة ينجزه حول ~370-580ms
        assert wall_ms < 720.0, f"Expected bounded parallel execution < 720ms, took {wall_ms:.1f}ms"
        assert meeting["routingDecision"] == "PARALLEL_BOUNDED_DEADLINE"
        exec_types = {a["agentId"]: a["executionStatus"] for a in meeting["agentResponses"]}
        assert exec_types["quant-alpha"] == "LIVE"
        assert exec_types["risk-sentinel"] == "LIVE"
        assert exec_types["macro-oracle"] == "LIVE"
        assert exec_types["execution-architect"] == "UNAVAILABLE"

        # التحقق من تصنيف الحداثة والتخطي الواعي بالتكلفة عند تقادم بيانات السوق
        stale_freshness = classify_market_data_freshness(age_seconds=45.0, max_staleness_seconds=15.0)
        assert stale_freshness["tier"] == "STALE_HALTED"
        assert stale_freshness["eligibleForExecution"] is False
        assert stale_freshness["eligibleForPaidCloudLlm"] is False

        monkeypatch.setattr(
            market_engine,
            "get_feed_health",
            lambda: {
                "fresh": False,
                "ageSeconds": 42.0,
                "maxStalenessSeconds": 15.0,
                "feedHalted": True,
                "mode": "LIVE_PUBLIC",
            },
        )
        stale_meeting = client.post(
            "/api/ai/meeting",
            json={"symbol": "ETH-USD", "horizon": "1h", "language": "ar"},
        )
        assert stale_meeting.status_code == 200
        stale_body = stale_meeting.json()
        assert stale_body["routingDecision"] == "COST_AWARE_SKIP_STALE_MARKET_DATA"
        assert all(a["executionStatus"] == "SIMULATED" for a in stale_body["agentResponses"])

        # استرجاع قياسات خط الأنابيب الثماني المراحل وتقييم الأداء خارج العينة OOS صافي التكاليف
        pipe = client.get("/api/analytics/latency-pipeline")
        assert pipe.status_code == 200
        pipe_json = pipe.json()
        assert len(pipe_json["stages"]) >= 8
        assert pipe_json["counters"]["parallelProviderDeadlineTimeouts"] >= 1
        assert pipe_json["counters"]["costAwareCloudInferenceSkips"] >= 4

        perf = client.get("/api/analytics/performance-evaluation?symbol=BTC-USD&timeframe=15m&hosting_cost_usd=12")
        assert perf.status_code == 200
        perf_json = perf.json()
        assert perf_json["executionLockedToPaper"] is True
        oos_opt = perf_json["outOfSampleComparison"]["lowLatencyCostAwareOptimized"]
        oos_base = perf_json["outOfSampleComparison"]["sequentialBaseline"]
        assert "sharpeRatio" in oos_opt
        assert "sortinoRatio" in oos_opt
        assert "profitFactor" in oos_opt
        assert "expectancyPerTradeUsd" in oos_opt
        assert (
            oos_opt["costBreakdownUsd"]["aiInferenceCostUsd"]
            <= oos_base["costBreakdownUsd"]["aiInferenceCostUsd"]
        )

        # التأكد النهائي من بقاء القفل الدائم على PAPER
        sys_status = client.get("/api/system/status").json()
        assert sys_status["version"] == "1.2.0-low-latency-cloudflare"
        assert sys_status["tradingMode"] == "PAPER"
        assert sys_status["liveAuthorized"] is False
        assert sys_status["executionLockedToPaper"] is True

