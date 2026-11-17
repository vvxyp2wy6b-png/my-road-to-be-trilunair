"""
تكامل حساب Binance الشخصي الرسمي للمالك، الخزنة المشفرة للمفاتيح، ومحرك المحاسبة والمطابقة الفورية (READ-ONLY).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.3.0-binance-personal-guard

الركائز الأمنية والمعمارية الإلزامية في هذه الوحدة:
1. دعم آليات التوثيق الرسمية الموثقة من Binance حصراً:
   - Ed25519 غير المتماثل (الموصى به رقم #1): توليد زوج المفاتيح داخل الخادم الخلفي وتشفير المفتاح الخاص فوراً بـ AES-256-GCM
     بحيث لا يغادر الخادم إطلاقاً، وإظهار المفتاح العام (PUBLIC KEY PEM) فقط ليربطه المالك في Binance API Management.
   - RSA-SHA256 غير المتماثل.
   - HMAC-SHA256 المتماثل.
2. الفصل المعماري القاطع بين:
   - فتحة بيانات اعتماد المراقبة القرائية (READ_ONLY_MONITORING) — ترفض أي مفتاح يحمل صلاحية تداول أو سحب أو هامش أو عقود آجلة.
   - فتحة الإعداد المستقبلي للتداول الفوري (FUTURE_SPOT_EXECUTION) — تبقى معطلة التنفيذ ومقفلة على وضع PAPER.
   - بيانات محفظة المحاكاة الورقية ($1,000,000 PAPER) — جداول مستقلة تماماً دون أي خلط في الأرصدة أو العوائد.
3. الحظر القاطع لطلب أو قبول كلمة مرور Binance أو عبارة الاسترداد (Seed Phrase) أو رموز OTP أو الكوكيز أو القوالب الحيوية.
4. اشتراط التصعيد البيومتري للمالك عبر WebAuthn Passkey (Face ID / Touch ID -> X-Step-Up-Token) عند وجود مفتاح مرور مسجل
   أو تفعيل سياسة الإلزام البيومتري لجميع عمليات إنشاء أو حفظ أو تدوير أو إبطال بيانات اعتماد Binance.
5. المصداقية الصارمة: عند عدم تكوين مفاتيح المالك، تُبلّغ الحالة دائماً بـ PENDING_OWNER_SETUP ولا يُدّعى الاتصال مطلقاً.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import time
from typing import Any, Literal
from urllib.parse import urlencode
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.database import append_audit_log, db_session, utc_now_iso
from app.market_engine import market_engine
from app.security import (
    create_outbound_http_client,
    decrypt_vault_secret,
    encrypt_vault_secret,
    get_client_identifier,
    mask_api_key,
    redact_sensitive_value,
    require_authenticated_session_or_secret,
    security_telemetry,
)
from app.webauthn_passkeys import list_registered_passkeys, verify_step_up_token

SAR_PER_USD_PEG = 3.75
PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR = 2125.0
PLANNED_MONTHLY_CRYPTO_ALLOCATION_USD = round(PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR / SAR_PER_USD_PEG, 2)

DEFAULT_MAINNET_BASE_URL = "https://api.binance.com"
DEFAULT_SPOT_TESTNET_BASE_URL = "https://testnet.binance.vision"

CredentialPurpose = Literal["READ_ONLY_MONITORING", "FUTURE_SPOT_EXECUTION"]
AuthAlgorithm = Literal["ED25519", "RSA_SHA256", "HMAC_SHA256"]
BinanceEnvironment = Literal["MAINNET", "SPOT_TESTNET", "LOCAL_MOCK"]

STABLECOIN_USD_ASSETS: frozenset[str] = frozenset({"USDT", "USDC", "FDUSD", "BUSD", "TUSD", "USD"})

DEFAULT_TRACKED_SPOT_SYMBOLS: tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
)

FORBIDDEN_SENSITIVE_PAYLOAD_FIELDS: frozenset[str] = frozenset(
    {
        "password",
        "binancepassword",
        "loginpassword",
        "seedphrase",
        "recoveryphrase",
        "mnemonic",
        "otp",
        "totp",
        "twofactorcode",
        "2facode",
        "smscode",
        "emailcode",
        "sessioncookie",
        "cookie",
        "biometricdata",
        "biometrictemplate",
        "faceidimage",
        "touchidtemplate",
    }
)

binance_personal_router = APIRouter(
    prefix="/api/binance/personal",
    tags=["Personal Binance Spot Monitoring (Read-Only & Vault)"],
)


# ==============================================================================
# 1. Database Schema Initialization (PostgreSQL 15/16 + SQLite Compatible)
# ==============================================================================


def ensure_binance_personal_tables() -> None:
    """تهيئة جداول حساب Binance الشخصي المعزولة بالكامل عن محفظة PAPER الورقية."""
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS binance_generated_keypairs (
                keypair_id TEXT PRIMARY KEY,
                purpose TEXT NOT NULL,
                algorithm TEXT NOT NULL DEFAULT 'ED25519',
                public_key_pem TEXT NOT NULL,
                private_key_ciphertext TEXT NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS binance_owner_credentials (
                purpose TEXT PRIMARY KEY,
                credential_id TEXT NOT NULL,
                key_label TEXT NOT NULL,
                auth_algorithm TEXT NOT NULL,
                environment TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key_masked TEXT NOT NULL,
                api_key_sha256 TEXT NOT NULL,
                api_key_ciphertext TEXT NOT NULL,
                secret_ciphertext TEXT NOT NULL,
                public_key_pem TEXT NOT NULL DEFAULT '',
                trusted_ips_json TEXT NOT NULL DEFAULT '[]',
                tracked_symbols_json TEXT NOT NULL DEFAULT '["BTCUSDT","ETHUSDT","SOLUSDT"]',
                permission_snapshot_json TEXT NOT NULL DEFAULT '{}',
                verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
                verification_reason TEXT NOT NULL DEFAULT '',
                rotated_count INTEGER NOT NULL DEFAULT 0,
                used_weight_1m INTEGER NOT NULL DEFAULT 0,
                rate_limit_cooldown_until REAL NOT NULL DEFAULT 0,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                last_latency_ms REAL NOT NULL DEFAULT 0,
                clock_skew_ms INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_verified_at TEXT NOT NULL DEFAULT '',
                last_synced_at TEXT NOT NULL DEFAULT '',
                revoked_at TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS binance_personal_balances (
                asset TEXT PRIMARY KEY,
                free_qty REAL NOT NULL DEFAULT 0.0,
                locked_qty REAL NOT NULL DEFAULT 0.0,
                total_qty REAL NOT NULL DEFAULT 0.0,
                price_usd REAL NOT NULL DEFAULT 0.0,
                value_usd REAL NOT NULL DEFAULT 0.0,
                value_sar REAL NOT NULL DEFAULT 0.0,
                avg_cost_basis_usd REAL NOT NULL DEFAULT 0.0,
                total_cost_basis_usd REAL NOT NULL DEFAULT 0.0,
                unrealized_pnl_usd REAL NOT NULL DEFAULT 0.0,
                unrealized_pnl_pct REAL NOT NULL DEFAULT 0.0,
                realized_pnl_usd REAL NOT NULL DEFAULT 0.0,
                cumulative_fees_usd REAL NOT NULL DEFAULT 0.0,
                reconciled_status TEXT NOT NULL DEFAULT 'RECONCILED_EXACT',
                reconciled_delta_qty REAL NOT NULL DEFAULT 0.0,
                is_quote_cash INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS binance_personal_orders (
                order_uid TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                binance_order_id TEXT NOT NULL,
                client_order_id TEXT NOT NULL DEFAULT '',
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                status TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0.0,
                orig_qty REAL NOT NULL DEFAULT 0.0,
                executed_qty REAL NOT NULL DEFAULT 0.0,
                cummulative_quote_qty REAL NOT NULL DEFAULT 0.0,
                order_time_iso TEXT NOT NULL,
                order_time_ms INTEGER NOT NULL,
                synced_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS binance_personal_trades (
                trade_uid TEXT PRIMARY KEY,
                trade_fingerprint TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                binance_trade_id TEXT NOT NULL,
                binance_order_id TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                qty REAL NOT NULL,
                quote_qty REAL NOT NULL,
                commission REAL NOT NULL DEFAULT 0.0,
                commission_asset TEXT NOT NULL DEFAULT 'USDT',
                commission_usd REAL NOT NULL DEFAULT 0.0,
                is_maker INTEGER NOT NULL DEFAULT 0,
                trade_time_iso TEXT NOT NULL,
                trade_time_ms INTEGER NOT NULL,
                synced_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS binance_personal_cashflows (
                cashflow_id TEXT PRIMARY KEY,
                tx_fingerprint TEXT NOT NULL UNIQUE,
                direction TEXT NOT NULL,
                coin TEXT NOT NULL,
                amount REAL NOT NULL,
                amount_usd REAL NOT NULL,
                amount_sar REAL NOT NULL,
                transaction_fee REAL NOT NULL DEFAULT 0.0,
                status_label TEXT NOT NULL,
                network TEXT NOT NULL DEFAULT '',
                tx_id_hash TEXT NOT NULL DEFAULT '',
                occurred_at_iso TEXT NOT NULL,
                occurred_at_ms INTEGER NOT NULL,
                synced_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS binance_personal_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                total_equity_usd REAL NOT NULL,
                total_equity_sar REAL NOT NULL,
                quote_cash_usd REAL NOT NULL,
                invested_crypto_usd REAL NOT NULL,
                net_contributed_usd REAL NOT NULL,
                realized_pnl_usd REAL NOT NULL,
                unrealized_pnl_usd REAL NOT NULL,
                cumulative_fees_usd REAL NOT NULL,
                drawdown_pct REAL NOT NULL DEFAULT 0.0,
                recorded_at TEXT NOT NULL
            );
            """
        )


# ==============================================================================
# 2. Cryptographic Key Generation, Request Signing & Biometric Step-Up Guard
# ==============================================================================


def reject_prohibited_credential_fields(raw_payload: dict[str, Any]) -> None:
    """رفض صارم لأي محاولة لإرسال كلمة مرور Binance أو عبارة استرداد أو رمز OTP أو بيانات حيوية خام."""
    if not isinstance(raw_payload, dict):
        return
    for key in raw_payload.keys():
        normalized = str(key).strip().lower().replace("_", "").replace("-", "")
        if normalized in FORBIDDEN_SENSITIVE_PAYLOAD_FIELDS:
            security_telemetry.emit_event(
                "PROHIBITED_BINANCE_CREDENTIAL_INPUT_REJECTED",
                severity="CRITICAL",
                details={"rejectedField": str(key)},
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    f"PROHIBITED_SENSITIVE_INPUT: TRILUNAIR never requests or accepts '{key}' "
                    "(Binance passwords, seed/recovery phrases, OTPs, session cookies, or raw biometric data are strictly forbidden)."
                ),
            )
    # فحص القيم النصية لكشف عبارات الاسترداد المكونة من 12 أو 24 كلمة بالخطأ في حقل السر
    for field_name in ("apiSecret", "privateKeyPem", "apiKey", "keyLabel"):
        val = str(raw_payload.get(field_name) or "").strip()
        words = [w for w in val.split() if w.isalpha()]
        if field_name != "keyLabel" and len(words) in {12, 15, 18, 21, 24} and "BEGIN" not in val:
            security_telemetry.emit_event(
                "MNEMONIC_SEED_PHRASE_REJECTED",
                severity="CRITICAL",
                details={"field": field_name, "wordCount": len(words)},
            )
            raise HTTPException(
                status_code=400,
                detail="PROHIBITED_SEED_PHRASE_DETECTED: Never enter a wallet seed/recovery phrase; only restricted Binance API credentials are permitted.",
            )


def require_owner_biometric_for_binance(
    request: Request,
    provided_admin_secret: str | None,
    action_label: str,
    require_biometric_when_enrolled: bool = True,
) -> dict[str, Any]:
    """
    فرض مصادقة المالك مع التصعيد البيومتري عبر WebAuthn Passkey (Face ID / Touch ID -> X-Step-Up-Token):
    - إذا كان للمالك مفتاح مرور بيومتري نشط مسجل (أو فُعّل TRILUNAIR_REQUIRE_PASSKEY_STEP_UP=true)،
      يجب تقديم ترويسة X-Step-Up-Token صالحة صادرة عن مصادقة WebAuthn حقيقية؛ ولا يكفي رمز المسؤول وحده.
    - إذا لم يُسجل مفتاح مرور بعد في بيئة الإعداد الأولي، يُلزم بجلسة مسؤول موثقة أو سر مسؤول صالح.
    """
    active_passkeys = list_registered_passkeys(include_revoked=False)
    force_passkey = os.getenv("TRILUNAIR_REQUIRE_PASSKEY_STEP_UP", "false").strip().lower() == "true"
    step_up_hdr = (request.headers.get("X-Step-Up-Token") or "").strip()

    if step_up_hdr:
        claims = verify_step_up_token(step_up_hdr)
        if claims is None:
            security_telemetry.emit_event(
                "BINANCE_BIOMETRIC_STEP_UP_INVALID",
                severity="WARNING",
                details={"action": action_label, "client": get_client_identifier(request)},
            )
            raise HTTPException(
                status_code=401,
                detail="INVALID_BIOMETRIC_STEP_UP_TOKEN: رمز التصعيد البيومتري (X-Step-Up-Token) غير صالح أو منتهي الصلاحية.",
            )
        return {
            "authMethod": "WEBAUTHN_BIOMETRIC_PASSKEY",
            "biometricStepUpVerified": True,
            "claims": claims,
        }

    if require_biometric_when_enrolled and (len(active_passkeys) > 0 or force_passkey):
        security_telemetry.emit_event(
            "BINANCE_BIOMETRIC_STEP_UP_REQUIRED",
            severity="WARNING",
            details={
                "action": action_label,
                "activePasskeyCount": len(active_passkeys),
                "client": get_client_identifier(request),
            },
        )
        raise HTTPException(
            status_code=403,
            detail=(
                "BIOMETRIC_PASSKEY_STEP_UP_REQUIRED: تتطلب إدارة بيانات اعتماد Binance الحساسة تأكيد الهوية البيومترية "
                "للمالك عبر Face ID / Touch ID (WebAuthn Passkey X-Step-Up-Token)."
            ),
        )

    base_auth = require_authenticated_session_or_secret(
        request,
        provided_admin_secret,
        action_label=action_label,
        require_step_up=False,
    )
    return {
        **base_auth,
        "biometricStepUpVerified": False,
    }


def generate_server_ed25519_keypair(purpose: CredentialPurpose = "READ_ONLY_MONITORING") -> dict[str, Any]:
    """
    توليد زوج مفاتيح Ed25519 غير متماثل رسمي متوافق مع Binance Spot API داخل الخادم الخلفي:
    - يُشفّر المفتاح الخاص (PKCS#8 PEM) فوراً عبر AES-256-GCM في قاعدة البيانات ولا يخرج من الخادم إطلاقاً.
    - يُعاد المفتاح العام (SubjectPublicKeyInfo PEM) فقط لينسخه المالك إلى شاشة Binance API Management.
    """
    ensure_binance_personal_tables()
    priv_key = ed25519.Ed25519PrivateKey.generate()
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    pub_pem = (
        priv_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )

    keypair_id = f"edk_{uuid.uuid4().hex[:16]}"
    aad = f"binance-ed25519-keypair:{purpose}:{keypair_id}"
    encrypted_priv = encrypt_vault_secret(priv_pem, aad_context=aad)
    now = utc_now_iso()

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO binance_generated_keypairs (
                keypair_id, purpose, algorithm, public_key_pem, private_key_ciphertext, consumed, created_at
            ) VALUES (?, ?, 'ED25519', ?, ?, 0, ?)
            """,
            (keypair_id, purpose, pub_pem, encrypted_priv, now),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="BINANCE_VAULT",
            action="BINANCE_ED25519_KEYPAIR_GENERATED",
            severity="INFO",
            details_ar=f"تم توليد زوج مفاتيح Ed25519 بالجانب الخلفي للغرض ({purpose})؛ المفتاح الخاص مشفر بـ AES-256-GCM ولم يغادر الخادم.",
            details_en=f"Generated server-side Ed25519 keypair ({keypair_id}) for {purpose}; private key encrypted in vault and never transmitted.",
            conn=conn,
        )

    return {
        "keypairId": keypair_id,
        "purpose": purpose,
        "algorithm": "ED25519",
        "publicKeyPem": pub_pem,
        "privateKeyExported": False,
        "createdAt": now,
        "binanceRegistrationInstructionsEn": (
            "1. Open Binance -> Account -> API Management -> Create API -> Self-generated Key. "
            "2. Paste ONLY this Public Key PEM and name the key 'TRILUNAIR Read-Only'. "
            "3. Keep ONLY 'Enable Reading' checked (leave Spot Trading, Withdrawals, Margin, and Futures UNCHECKED). "
            "4. Restrict access to your TRILUNAIR server IP, then paste the resulting API Key back into this wizard."
        ),
        "binanceRegistrationInstructionsAr": (
            "١. افتح Binance -> إدارة API -> إنشاء مفتاح ذاتي التوليد (Self-generated). "
            "٢. الصق المفتاح العام (Public Key) هذا فقط وسمّه TRILUNAIR Read-Only. "
            "٣. أبقِ صلاحية القراءة فقط (Enable Reading) مفعلة واترك التداول والسحب والهامش والعقود الآجلة غير مفعلة. "
            "٤. قيّد الوصول بعنوان IP الخادم الثابت ثم أدخل API Key الناتج في المعالج."
        ),
    }


def sign_binance_query(query_string: str, algorithm: AuthAlgorithm, secret_material: str) -> str:
    """
    توقيع سلسلة استعلام Binance الرسمية وفق المواصفات القياسية لـ Binance Spot REST API:
    - ED25519: توقيع سلسلة ASCII وإرجاع ترميز Base64 قياسي.
    - RSA_SHA256: توقيع PKCS#1 v1.5 مع SHA-256 وإرجاع ترميز Base64 قياسي.
    - HMAC_SHA256: توقيع HMAC-SHA256 وإرجاع ترميز الست عشري (Hex).
    """
    payload_bytes = query_string.encode("ascii")
    cleaned_secret = secret_material.strip()

    if algorithm == "ED25519":
        priv_key = serialization.load_pem_private_key(cleaned_secret.encode("utf-8"), password=None)
        if not isinstance(priv_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Provided PEM key is not a valid Ed25519 private key.")
        sig_bytes = priv_key.sign(payload_bytes)
        return base64.b64encode(sig_bytes).decode("ascii")

    if algorithm == "RSA_SHA256":
        priv_key = serialization.load_pem_private_key(cleaned_secret.encode("utf-8"), password=None)
        if not isinstance(priv_key, rsa.RSAPrivateKey):
            raise ValueError("Provided PEM key is not a valid RSA private key.")
        sig_bytes = priv_key.sign(payload_bytes, padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(sig_bytes).decode("ascii")

    if algorithm == "HMAC_SHA256":
        return hmac.new(cleaned_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    raise ValueError(f"Unsupported Binance signature algorithm: {algorithm}")


def _resolve_base_url(environment: BinanceEnvironment, custom_base_url: str | None) -> str:
    """تحديد عنوان API الأساسي بأمان مع رفض أي اتصال بالنطاق الطبي medinsup.com."""
    if custom_base_url and custom_base_url.strip():
        candidate = custom_base_url.strip().rstrip("/")
        lowered = candidate.lower()
        if "medinsup.com" in lowered:
            raise HTTPException(
                status_code=400,
                detail="PLATFORM_ISOLATION_VIOLATION: Binance base URL must never reference medinsup.com.",
            )
        if environment == "LOCAL_MOCK":
            if not (lowered.startswith("http://127.0.0.1") or lowered.startswith("http://localhost") or lowered.startswith("http://testserver")):
                raise HTTPException(
                    status_code=400,
                    detail="LOCAL_MOCK environment is restricted to loopback 127.0.0.1 / localhost addresses.",
                )
            return candidate
        if not lowered.startswith("https://"):
            raise HTTPException(status_code=400, detail="Binance base URL must use HTTPS.")
        return candidate

    if environment == "SPOT_TESTNET":
        return DEFAULT_SPOT_TESTNET_BASE_URL
    return DEFAULT_MAINNET_BASE_URL


# ==============================================================================
# 3. Signed Binance REST Client, Rate-Limit Guard & Fail-Closed Permission Audit
# ==============================================================================


def _load_decrypted_credential_material(purpose: CredentialPurpose = "READ_ONLY_MONITORING") -> dict[str, Any] | None:
    """تحميل وفك تشفير بيانات اعتماد المالك داخل الذاكرة الخلفية فقط (لا تُصدر خارج هذه الوحدة أبداً)."""
    ensure_binance_personal_tables()
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM binance_owner_credentials WHERE purpose = ? AND revoked_at = ''",
            (purpose,),
        ).fetchone()
    if row is None:
        return None

    cred_id = str(row["credential_id"])
    aad_api = f"binance-api-key:{purpose}:{cred_id}"
    aad_sec = f"binance-secret:{purpose}:{cred_id}"
    api_key_plain = decrypt_vault_secret(str(row["api_key_ciphertext"]), aad_context=aad_api)
    secret_plain = decrypt_vault_secret(str(row["secret_ciphertext"]), aad_context=aad_sec)
    return {
        "row": dict(row),
        "apiKey": api_key_plain,
        "secretMaterial": secret_plain,
    }


def _execute_signed_binance_get(
    *,
    base_url: str,
    path: str,
    params: dict[str, Any],
    api_key: str,
    secret_material: str,
    algorithm: AuthAlgorithm,
    purpose: CredentialPurpose,
    timeout_sec: float = 8.0,
) -> tuple[int, Any, dict[str, Any]]:
    """
    تنفيذ طلب GET موقع رسمي إلى Binance مع:
    - فحص فترة التهدئة (HTTP 429 / 418 Cooldown) قبل الإرسال.
    - حساب زمن الاستجابة الفعلي وتحديث عداد الوزن (X-MBX-USED-WEIGHT-1M).
    - تنقية أي ترويسات أو تواقيع عند تسجيل الأخطاء.
    """
    with db_session() as conn:
        state_row = conn.execute(
            "SELECT rate_limit_cooldown_until, clock_skew_ms FROM binance_owner_credentials WHERE purpose = ?",
            (purpose,),
        ).fetchone()

    now_wall = time.time()
    clock_skew_ms = 0
    if state_row is not None:
        cooldown_until = float(state_row["rate_limit_cooldown_until"] or 0.0)
        clock_skew_ms = int(state_row["clock_skew_ms"] or 0)
        if cooldown_until > now_wall:
            wait_sec = max(1, int(cooldown_until - now_wall) + 1)
            raise HTTPException(
                status_code=429,
                detail=f"BINANCE_RATE_LIMIT_COOLDOWN: Backing off for {wait_sec}s to respect Binance API weight limits.",
                headers={"Retry-After": str(wait_sec)},
            )

    signed_params = {k: v for k, v in params.items() if v is not None}
    signed_params.setdefault("recvWindow", 5000)
    signed_params["timestamp"] = int(time.time() * 1000) + clock_skew_ms
    query_str = urlencode(signed_params)
    signature = sign_binance_query(query_str, algorithm, secret_material)
    full_url = f"{base_url.rstrip('/')}{path}?{query_str}&signature={ urlencode({'s': signature})[2:] }"

    t0 = time.perf_counter()
    try:
        with create_outbound_http_client(base_url, timeout_sec=timeout_sec) as client:
            resp = client.get(full_url, headers={"X-MBX-APIKEY": api_key, "Accept": "application/json"})
    except Exception as exc:
        safe_err = redact_sensitive_value(str(exc))
        with db_session() as conn:
            conn.execute(
                "UPDATE binance_owner_credentials SET consecutive_failures = consecutive_failures + 1, updated_at = ? WHERE purpose = ?",
                (utc_now_iso(), purpose),
            )
        security_telemetry.emit_event(
            "BINANCE_PERSONAL_NETWORK_FAILURE",
            severity="WARNING",
            details={"purpose": purpose, "path": path, "error": safe_err},
        )
        raise HTTPException(
            status_code=502,
            detail=f"BINANCE_UPSTREAM_UNREACHABLE: Failed to reach official Binance endpoint {path}.",
        ) from exc

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    raw_weight_hdr = str(resp.headers.get("X-MBX-USED-WEIGHT-1M") or resp.headers.get("x-mbx-used-weight-1m") or "0")
    weight_token = raw_weight_hdr.split(",")[-1].strip()
    used_weight = int(weight_token) if weight_token.isdigit() else 0

    if resp.status_code in {429, 418}:
        raw_retry_hdr = str(resp.headers.get("Retry-After") or "30").split(",")[-1].strip()
        retry_after = max(5, int(raw_retry_hdr) if raw_retry_hdr.isdigit() else 30)
        cooldown_until = time.time() + retry_after
        with db_session() as conn:
            conn.execute(
                """
                UPDATE binance_owner_credentials
                SET used_weight_1m = ?, rate_limit_cooldown_until = ?, consecutive_failures = consecutive_failures + 1,
                    last_latency_ms = ?, updated_at = ?
                WHERE purpose = ?
                """,
                (used_weight, cooldown_until, latency_ms, utc_now_iso(), purpose),
            )
        security_telemetry.emit_event(
            "BINANCE_PERSONAL_RATE_LIMITED",
            severity="WARNING",
            details={"purpose": purpose, "path": path, "httpStatus": resp.status_code, "retryAfterSec": retry_after},
        )
        raise HTTPException(
            status_code=429,
            detail=f"BINANCE_UPSTREAM_RATE_LIMITED (HTTP {resp.status_code}): Cooldown enforced for {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    with db_session() as conn:
        if resp.status_code < 400:
            conn.execute(
                """
                UPDATE binance_owner_credentials
                SET used_weight_1m = ?, consecutive_failures = 0, last_latency_ms = ?, updated_at = ?
                WHERE purpose = ?
                """,
                (used_weight, latency_ms, utc_now_iso(), purpose),
            )
        else:
            conn.execute(
                """
                UPDATE binance_owner_credentials
                SET used_weight_1m = ?, consecutive_failures = consecutive_failures + 1, last_latency_ms = ?, updated_at = ?
                WHERE purpose = ?
                """,
                (used_weight, latency_ms, utc_now_iso(), purpose),
            )

    try:
        body = resp.json()
    except Exception:
        body = {"rawStatus": resp.status_code}

    meta = {"latencyMs": latency_ms, "usedWeight1m": used_weight}
    return resp.status_code, body, meta


def evaluate_permission_safety(
    *,
    purpose: CredentialPurpose,
    environment: str,
    api_restrictions: dict[str, Any] | None,
    account_info: dict[str, Any],
) -> dict[str, Any]:
    """
    التدقيق الصارم المغلق بأمان (Fail-Closed) لصلاحيات مفتاح API الشخصي:
    - يرفض فوراً أي مفتاح يفعل السحب (enableWithdrawals) أو الهامش (enableMargin) أو العقود الآجلة (enableFutures)
      أو التحويلات الداخلية/الشاملة (enableInternalTransfer / permitsUniversalTransfer) أو الخيارات.
    - في فتحة المراقبة القرائية (READ_ONLY_MONITORING): يرفض أيضاً أي مفتاح يحمل صلاحية التداول الفوري (enableSpotAndMarginTrading=True).
    """
    violations: list[str] = []
    acct_perms = [str(p).upper() for p in (account_info.get("permissions") or [])]

    for forbidden_acct_perm in ("MARGIN", "LEVERAGED", "TRD_GRP_FUTURES", "FUTURES", "OPTIONS"):
        if forbidden_acct_perm in acct_perms:
            violations.append(f"FORBIDDEN_ACCOUNT_SCOPE:{forbidden_acct_perm}")

    if api_restrictions is not None:
        enable_reading = bool(api_restrictions.get("enableReading", True))
        enable_spot = bool(api_restrictions.get("enableSpotAndMarginTrading", False))
        enable_withdrawals = bool(api_restrictions.get("enableWithdrawals", False))
        enable_margin = bool(api_restrictions.get("enableMargin", False))
        enable_futures = bool(api_restrictions.get("enableFutures", False))
        enable_internal_tx = bool(api_restrictions.get("enableInternalTransfer", False))
        enable_universal_tx = bool(api_restrictions.get("permitsUniversalTransfer", False))
        enable_options = bool(api_restrictions.get("enableVanillaOptions", False))
        enable_pm = bool(api_restrictions.get("enablePortfolioMarginTrading", False))
        ip_restrict = bool(api_restrictions.get("ipRestrict", False))

        if not enable_reading:
            violations.append("READING_PERMISSION_DISABLED")
        if enable_withdrawals:
            violations.append("WITHDRAWALS_PERMISSION_FORBIDDEN")
        if enable_margin:
            violations.append("MARGIN_BORROWING_PERMISSION_FORBIDDEN")
        if enable_futures:
            violations.append("FUTURES_LEVERAGE_PERMISSION_FORBIDDEN")
        if enable_internal_tx or enable_universal_tx:
            violations.append("EXTERNAL_OR_UNIVERSAL_TRANSFER_FORBIDDEN")
        if enable_options or enable_pm:
            violations.append("DERIVATIVES_PORTFOLIO_MARGIN_FORBIDDEN")
        if purpose == "READ_ONLY_MONITORING" and enable_spot:
            violations.append("READ_ONLY_SLOT_REJECTS_TRADING_PERMISSION")
    else:
        # يُسمح بغياب /sapi/v1/account/apiRestrictions في SPOT_TESTNET فقط لأن Testnet لا يستضيف مسارات /sapi/*
        if environment != "SPOT_TESTNET":
            violations.append("API_RESTRICTIONS_UNVERIFIABLE_FAIL_CLOSED")
        ip_restrict = False
        enable_reading = True
        enable_spot = bool(account_info.get("canTrade", False))
        enable_withdrawals = bool(account_info.get("canWithdraw", False))
        enable_margin = False
        enable_futures = False
        enable_internal_tx = False
        enable_universal_tx = False
        if enable_withdrawals:
            violations.append("WITHDRAWALS_PERMISSION_FORBIDDEN")

    safe = len(violations) == 0
    if not safe:
        status_code = "BLOCKED_UNSAFE_PERMISSIONS"
    elif purpose == "READ_ONLY_MONITORING":
        status_code = "VERIFIED_READ_ONLY"
    else:
        status_code = "VERIFIED_SPOT_RESTRICTED"

    return {
        "safe": safe,
        "verificationStatus": status_code,
        "violations": violations,
        "ipRestrictEnabledOnBinance": ip_restrict,
        "scopes": {
            "enableReading": enable_reading,
            "enableSpotTrading": enable_spot,
            "enableWithdrawals": enable_withdrawals,
            "enableMargin": enable_margin,
            "enableFutures": enable_futures,
            "enableInternalOrUniversalTransfer": enable_internal_tx or enable_universal_tx,
        },
        "accountPermissions": acct_perms,
    }


def verify_and_update_credential_permissions(purpose: CredentialPurpose = "READ_ONLY_MONITORING") -> dict[str, Any]:
    """الاتصال الرسمي بـ Binance للتحقق من صلاحيات المفتاح وتحديث حالة الأمان في قاعدة البيانات."""
    loaded = _load_decrypted_credential_material(purpose)
    if loaded is None:
        return {
            "configured": False,
            "connectionStatus": "PENDING_OWNER_SETUP",
            "purpose": purpose,
            "detailEn": "No personal Binance API credential configured for this slot yet.",
        }

    row = loaded["row"]
    base_url = str(row["base_url"])
    alg: AuthAlgorithm = row["auth_algorithm"]  # type: ignore[assignment]
    env_name = str(row["environment"])
    api_key = loaded["apiKey"]
    secret_mat = loaded["secretMaterial"]

    # 1. مزامنة فرق التوقيت مع /api/v3/time إن أمكن
    clock_skew_ms = 0
    try:
        with create_outbound_http_client(base_url, timeout_sec=5.0) as client:
            t_resp = client.get(f"{base_url.rstrip('/')}/api/v3/time")
            if t_resp.status_code == 200:
                srv_ms = int(t_resp.json().get("serverTime", 0))
                if srv_ms > 0:
                    clock_skew_ms = srv_ms - int(time.time() * 1000)
                    with db_session() as conn:
                        conn.execute(
                            "UPDATE binance_owner_credentials SET clock_skew_ms = ? WHERE purpose = ?",
                            (clock_skew_ms, purpose),
                        )
    except Exception:
        pass

    # 2. جلب /api/v3/account
    acc_status, acc_body, acc_meta = _execute_signed_binance_get(
        base_url=base_url,
        path="/api/v3/account",
        params={"omitZeroBalances": "false"},
        api_key=api_key,
        secret_material=secret_mat,
        algorithm=alg,
        purpose=purpose,
    )
    now = utc_now_iso()
    if acc_status != 200 or not isinstance(acc_body, dict):
        reason = redact_sensitive_value(str(acc_body.get("msg") if isinstance(acc_body, dict) else f"HTTP {acc_status}"))
        with db_session() as conn:
            conn.execute(
                """
                UPDATE binance_owner_credentials
                SET verification_status = 'AUTH_ERROR', verification_reason = ?, last_verified_at = ?, updated_at = ?
                WHERE purpose = ?
                """,
                (str(reason)[:240], now, now, purpose),
            )
        raise HTTPException(
            status_code=401 if acc_status in {401, 403} else 502,
            detail=f"BINANCE_ACCOUNT_AUTH_FAILED (HTTP {acc_status}): {reason}",
        )

    # 3. جلب /sapi/v1/account/apiRestrictions (إلزامي على MAINNET؛ اختياري فقط إذا أعاد 404 على SPOT_TESTNET)
    restr_status, restr_body, _ = _execute_signed_binance_get(
        base_url=base_url,
        path="/sapi/v1/account/apiRestrictions",
        params={},
        api_key=api_key,
        secret_material=secret_mat,
        algorithm=alg,
        purpose=purpose,
    )
    restrictions_dict: dict[str, Any] | None = None
    if restr_status == 200 and isinstance(restr_body, dict):
        restrictions_dict = restr_body
    elif env_name == "SPOT_TESTNET" and restr_status == 404:
        restrictions_dict = None
    else:
        with db_session() as conn:
            conn.execute(
                """
                UPDATE binance_owner_credentials
                SET verification_status = 'UNVERIFIED_FAIL_CLOSED',
                    verification_reason = 'Failed to verify /sapi/v1/account/apiRestrictions',
                    last_verified_at = ?, updated_at = ?
                WHERE purpose = ?
                """,
                (now, now, purpose),
            )
        raise HTTPException(
            status_code=502,
            detail="FAIL_CLOSED_PERMISSION_CHECK: Could not verify /sapi/v1/account/apiRestrictions from Binance.",
        )

    audit = evaluate_permission_safety(
        purpose=purpose,
        environment=env_name,
        api_restrictions=restrictions_dict,
        account_info=acc_body,
    )

    with db_session() as conn:
        conn.execute(
            """
            UPDATE binance_owner_credentials
            SET permission_snapshot_json = ?, verification_status = ?, verification_reason = ?,
                last_verified_at = ?, updated_at = ?
            WHERE purpose = ?
            """,
            (
                json.dumps(audit),
                audit["verificationStatus"],
                ", ".join(audit["violations"]) if audit["violations"] else "SAFE_LEAST_PRIVILEGE_VERIFIED",
                now,
                now,
                purpose,
            ),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="BINANCE_SECURITY_GUARD",
            action="BINANCE_API_PERMISSIONS_VERIFIED" if audit["safe"] else "BINANCE_UNSAFE_API_PERMISSIONS_BLOCKED",
            severity="INFO" if audit["safe"] else "CRITICAL",
            details_ar=(
                f"تم التحقق من صلاحيات مفتاح Binance ({purpose}): الحالة={audit['verificationStatus']}."
                if audit["safe"]
                else f"حظر أمني فوري لمفتاح Binance ({purpose}) بسبب صلاحيات خطرة: {', '.join(audit['violations'])}."
            ),
            details_en=(
                f"Verified Binance API key permissions ({purpose}): status={audit['verificationStatus']}."
                if audit["safe"]
                else f"Blocked unsafe Binance API key ({purpose}): {', '.join(audit['violations'])}."
            ),
            conn=conn,
        )

    if not audit["safe"]:
        security_telemetry.emit_event(
            "BINANCE_UNSAFE_API_KEY_BLOCKED",
            severity="CRITICAL",
            details={"purpose": purpose, "violations": audit["violations"]},
        )
        raise HTTPException(
            status_code=403,
            detail=f"UNSAFE_BINANCE_API_PERMISSIONS_BLOCKED: {', '.join(audit['violations'])}",
        )

    return {
        "configured": True,
        "purpose": purpose,
        "connectionStatus": audit["verificationStatus"],
        "permissionAudit": audit,
        "latencyMs": acc_meta["latencyMs"],
        "usedWeight1m": acc_meta["usedWeight1m"],
        "clockSkewMs": clock_skew_ms,
        "verifiedAt": now,
    }


# ==============================================================================
# 4. Portfolio Valuation, Cost Basis, P&L Accounting & Ledger Reconciliation
# ==============================================================================


def _resolve_asset_usd_price(asset: str, external_prices: dict[str, float] | None = None) -> float:
    """تحديد سعر الأصل بالدولار/USDT لتقييم المحفظة الفعلية بدقة دون المساس بمحفظة PAPER."""
    sym = asset.strip().upper()
    if sym in STABLECOIN_USD_ASSETS:
        return 1.0
    if sym == "SAR":
        return round(1.0 / SAR_PER_USD_PEG, 6)
    if external_prices:
        if sym in external_prices and external_prices[sym] > 0:
            return float(external_prices[sym])
        pair = f"{sym}USDT"
        if pair in external_prices and external_prices[pair] > 0:
            return float(external_prices[pair])

    # الرجوع الآمن لأسعار محرك السوق العامة (BTC, ETH, SOL, إلخ)
    for m_asset in market_engine.get_assets():
        base = m_asset.symbol.split("/")[0].split("-")[0].replace("USDT", "").strip().upper()
        if base == sym and m_asset.price > 0:
            return float(m_asset.price)
    return 0.0


def compute_spot_accounting_and_reconciliation(
    *,
    raw_balances: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    cashflows: list[dict[str, Any]],
    spot_prices_usd: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    حساب أساس التكلفة والأرباح والخسائر المحققة وغير المحققة والرسوم والمطابقة المحاسبية:
    المنهج المحاسبي الموثق: WEIGHTED_AVERAGE_COST_BASIS_SPOT_LEDGER
    - كل عملية شراء فورية تزيد الكمية وتضيف (quoteQty + buyFeeUsd) إلى إجمالي أساس التكلفة.
    - كل عملية بيع فورية تحقق ربحاً/خسارة صافية = (quoteQty - sellFeeUsd) - (soldQty * avgCostBasisUsd)،
      وتخفض إجمالي التكلفة بنفس النسبة مع خصم عمولة التداول بدقة.
    - الإيداعات والسحوبات تُعامل كتدفقات رأسمالية خارجية (Contributed Capital) منفصلة تماماً عن أرباح/خسائر السوق!
    - المطابقة (Reconciliation): تقارن الرصيد الفعلي المبلّغ من /api/v3/account مع الرصيد الدفتري المستنتج
      من (صافي الإيداعات - السحوبات + صافي المشتريات - المبيعات - الرسوم بالأصل).
    """
    # ترتيب الصفقات زمنياً من الأقدم للأحدث لحساب متوسط التكلفة المرجح بدقة
    sorted_trades = sorted(trades, key=lambda t: (int(t.get("time", 0)), str(t.get("id", ""))))

    ledger_qty_by_asset: dict[str, float] = {}
    cost_pool_usd_by_asset: dict[str, float] = {}
    realized_pnl_by_asset: dict[str, float] = {}
    fees_usd_by_asset: dict[str, float] = {}

    # 1. تسجيل التدفقات الرأسمالية (الإيداعات والسحوبات المؤكدة) في رصيد المطابقة
    total_deposits_usd = 0.0
    total_withdrawals_usd = 0.0
    for cf in cashflows:
        coin = str(cf.get("coin", "")).upper()
        amt = float(cf.get("amount", 0.0))
        px = _resolve_asset_usd_price(coin, spot_prices_usd)
        usd_val = amt * px
        direction = str(cf.get("direction", "")).upper()
        if direction == "DEPOSIT":
            ledger_qty_by_asset[coin] = ledger_qty_by_asset.get(coin, 0.0) + amt
            if coin not in STABLECOIN_USD_ASSETS and px > 0:
                cost_pool_usd_by_asset[coin] = cost_pool_usd_by_asset.get(coin, 0.0) + usd_val
            total_deposits_usd += usd_val
        elif direction == "WITHDRAWAL":
            fee = float(cf.get("transactionFee", 0.0))
            ledger_qty_by_asset[coin] = ledger_qty_by_asset.get(coin, 0.0) - amt - fee
            total_withdrawals_usd += usd_val

    # 2. معالجة سجل الصفقات الفورية (Spot Trades)
    for tr in sorted_trades:
        symbol = str(tr.get("symbol", "")).upper()
        base_asset = symbol[:-4] if symbol.endswith("USDT") else symbol[:-3]
        quote_asset = "USDT" if symbol.endswith("USDT") else symbol[-3:]
        is_buyer = bool(tr.get("isBuyer", str(tr.get("side", "")).upper() == "BUY"))
        qty = float(tr.get("qty", 0.0))
        quote_qty = float(tr.get("quoteQty", qty * float(tr.get("price", 0.0))))
        comm = float(tr.get("commission", 0.0))
        comm_asset = str(tr.get("commissionAsset", quote_asset)).upper()
        comm_px = _resolve_asset_usd_price(comm_asset, spot_prices_usd)
        comm_usd = comm * comm_px

        fees_usd_by_asset[base_asset] = fees_usd_by_asset.get(base_asset, 0.0) + comm_usd

        if is_buyer:
            eff_qty_added = qty - (comm if comm_asset == base_asset else 0.0)
            prev_qty = max(0.0, ledger_qty_by_asset.get(base_asset, 0.0))
            prev_cost = max(0.0, cost_pool_usd_by_asset.get(base_asset, 0.0))
            # إذا كانت العمولة مقتطعة من الأصل المشترى نفسه، فإن تكلفة quote_qty تمثل صافي الكمية المستلمة؛
            # وإذا كانت العمولة بعملة أخرى (مثل USDT أو BNB) نضيف قيمتها بالدولار لأساس التكلفة.
            added_cost_usd = quote_qty if comm_asset == base_asset else (quote_qty + comm_usd)
            ledger_qty_by_asset[base_asset] = prev_qty + eff_qty_added
            cost_pool_usd_by_asset[base_asset] = prev_cost + added_cost_usd
            ledger_qty_by_asset[quote_asset] = ledger_qty_by_asset.get(quote_asset, 0.0) - quote_qty - (
                comm if comm_asset == quote_asset else 0.0
            )
        else:
            prev_qty = max(0.0, ledger_qty_by_asset.get(base_asset, 0.0))
            prev_cost = max(0.0, cost_pool_usd_by_asset.get(base_asset, 0.0))
            avg_cost = (prev_cost / prev_qty) if prev_qty > 1e-12 else float(tr.get("price", 0.0))
            cost_removed = qty * avg_cost
            net_proceeds_usd = quote_qty - comm_usd
            realized = net_proceeds_usd - cost_removed
            realized_pnl_by_asset[base_asset] = realized_pnl_by_asset.get(base_asset, 0.0) + realized
            remaining_qty = max(0.0, prev_qty - qty - (comm if comm_asset == base_asset else 0.0))
            ledger_qty_by_asset[base_asset] = remaining_qty
            cost_pool_usd_by_asset[base_asset] = max(0.0, prev_cost - cost_removed) if remaining_qty > 1e-12 else 0.0
            ledger_qty_by_asset[quote_asset] = ledger_qty_by_asset.get(quote_asset, 0.0) + quote_qty - (
                comm if comm_asset == quote_asset else 0.0
            )

    # 3. بناء جدول الأرصدة الفعلي والمطابقة مع أرصدة حساب Binance
    balance_rows: list[dict[str, Any]] = []
    total_equity_usd = 0.0
    quote_cash_usd = 0.0
    invested_crypto_usd = 0.0
    total_unrealized_pnl_usd = 0.0
    total_realized_pnl_usd = round(sum(realized_pnl_by_asset.values()), 2)
    total_fees_usd = round(sum(fees_usd_by_asset.values()), 4)
    unreconciled_assets_count = 0

    for item in raw_balances:
        asset = str(item.get("asset", "")).strip().upper()
        free_q = float(item.get("free", 0.0))
        locked_q = float(item.get("locked", 0.0))
        total_q = round(free_q + locked_q, 10)
        has_history = asset in ledger_qty_by_asset or asset in realized_pnl_by_asset
        if total_q <= 1e-10 and not has_history:
            continue

        price_usd = _resolve_asset_usd_price(asset, spot_prices_usd)
        value_usd = round(total_q * price_usd, 2)
        value_sar = round(value_usd * SAR_PER_USD_PEG, 2)
        is_cash = asset in STABLECOIN_USD_ASSETS or asset == "SAR"

        if is_cash:
            avg_cost_usd = price_usd
            tot_cost_usd = value_usd
            unreal_usd = 0.0
            unreal_pct = 0.0
            quote_cash_usd += value_usd
        else:
            tracked_q = max(0.0, ledger_qty_by_asset.get(asset, 0.0))
            tracked_cost = max(0.0, cost_pool_usd_by_asset.get(asset, 0.0))
            if tracked_q > 1e-10 and total_q > 1e-10:
                avg_cost_usd = round(tracked_cost / tracked_q, 6)
                tot_cost_usd = round(avg_cost_usd * total_q, 2)
                unreal_usd = round(value_usd - tot_cost_usd, 2)
                unreal_pct = round((unreal_usd / tot_cost_usd) * 100.0, 2) if tot_cost_usd > 0.01 else 0.0
            else:
                # أرصدة كانت موجودة قبل نافذة المزامنة ولم يُستورد تاريخ شرائها بعد
                avg_cost_usd = round(price_usd, 6)
                tot_cost_usd = value_usd
                unreal_usd = 0.0
                unreal_pct = 0.0
            invested_crypto_usd += value_usd
            total_unrealized_pnl_usd += unreal_usd

        total_equity_usd += value_usd
        expected_q = ledger_qty_by_asset.get(asset, 0.0)
        delta_q = round(total_q - expected_q, 8)
        tolerance = 0.01 if is_cash else 1e-5
        if abs(delta_q) <= tolerance:
            rec_status = "RECONCILED_EXACT"
        elif expected_q == 0.0 and total_q > 0:
            rec_status = "UNTRACKED_PRE_SYNC_HOLDINGS_DETECTED"
            unreconciled_assets_count += 1
        else:
            rec_status = "LEDGER_DELTA_DETECTED"
            unreconciled_assets_count += 1

        balance_rows.append(
            {
                "asset": asset,
                "freeQty": free_q,
                "lockedQty": locked_q,
                "totalQty": total_q,
                "priceUsd": round(price_usd, 6),
                "valueUsd": value_usd,
                "valueSar": value_sar,
                "avgCostBasisUsd": avg_cost_usd,
                "totalCostBasisUsd": tot_cost_usd,
                "unrealizedPnlUsd": unreal_usd,
                "unrealizedPnlPct": unreal_pct,
                "realizedPnlUsd": round(realized_pnl_by_asset.get(asset, 0.0), 2),
                "cumulativeFeesUsd": round(fees_usd_by_asset.get(asset, 0.0), 4),
                "reconciliationStatus": rec_status,
                "reconciledDeltaQty": delta_q,
                "isQuoteCash": is_cash,
            }
        )

    balance_rows.sort(key=lambda b: b["valueUsd"], reverse=True)
    total_equity_usd = round(total_equity_usd, 2)
    for b in balance_rows:
        b["allocationWeightPct"] = round((b["valueUsd"] / total_equity_usd) * 100.0, 2) if total_equity_usd > 0 else 0.0

    net_contributed_usd = round(total_deposits_usd - total_withdrawals_usd, 2)
    net_market_pnl_after_fees_usd = round(total_realized_pnl_usd + total_unrealized_pnl_usd, 2)

    return {
        "accountingMethod": "WEIGHTED_AVERAGE_COST_BASIS_SPOT_LEDGER",
        "accountingMethodDescriptionEn": (
            "Weighted-average Spot cost basis per asset; deposits and withdrawals are segregated as external capital "
            "flows so contributed principal is never conflated with market P&L. Realized and unrealized P&L are reported net of Spot trading fees."
        ),
        "totalEquityUsd": total_equity_usd,
        "totalEquitySar": round(total_equity_usd * SAR_PER_USD_PEG, 2),
        "quoteCashUsd": round(quote_cash_usd, 2),
        "quoteCashSar": round(quote_cash_usd * SAR_PER_USD_PEG, 2),
        "investedCryptoUsd": round(invested_crypto_usd, 2),
        "investedCryptoSar": round(invested_crypto_usd * SAR_PER_USD_PEG, 2),
        "cryptoMarketExposurePct": round((invested_crypto_usd / total_equity_usd) * 100.0, 2) if total_equity_usd > 0 else 0.0,
        "totalDepositsUsd": round(total_deposits_usd, 2),
        "totalWithdrawalsUsd": round(total_withdrawals_usd, 2),
        "netContributedCapitalUsd": net_contributed_usd,
        "netContributedCapitalSar": round(net_contributed_usd * SAR_PER_USD_PEG, 2),
        "realizedPnlUsd": total_realized_pnl_usd,
        "realizedPnlSar": round(total_realized_pnl_usd * SAR_PER_USD_PEG, 2),
        "unrealizedPnlUsd": round(total_unrealized_pnl_usd, 2),
        "unrealizedPnlSar": round(total_unrealized_pnl_usd * SAR_PER_USD_PEG, 2),
        "netMarketPnlAfterFeesUsd": net_market_pnl_after_fees_usd,
        "netMarketPnlAfterFeesSar": round(net_market_pnl_after_fees_usd * SAR_PER_USD_PEG, 2),
        "cumulativeFeesUsd": total_fees_usd,
        "cumulativeFeesSar": round(total_fees_usd * SAR_PER_USD_PEG, 2),
        "reconciliationSummary": {
            "status": "RECONCILED_EXACT" if unreconciled_assets_count == 0 else "PARTIAL_PRE_SYNC_HISTORY_NOTE",
            "unreconciledAssetsCount": unreconciled_assets_count,
            "totalAssetsEvaluated": len(balance_rows),
        },
        "balances": balance_rows,
    }


# ==============================================================================
# 5. Live Account Read-Only Synchronization Engine
# ==============================================================================


def sync_personal_binance_account(purpose: CredentialPurpose = "READ_ONLY_MONITORING") -> dict[str, Any]:
    """
    مزامنة شاملة للقراءة فقط من حساب Binance الشخصي للمالك:
    1. التحقق الصارم أولاً من صلاحيات المفتاح (Fail-Closed) ومنع أي مفتاح يحمل صلاحيات سحب أو هامش أو عقود آجلة.
    2. جلب الأرصدة الفورية (/api/v3/account) والأسعار الفورية (/api/v3/ticker/price).
    3. جلب سجل الأوامر (/api/v3/allOrders) وسجل الصفقات (/api/v3/myTrades) للأزواج المتتبعة.
    4. جلب سجل الإيداعات (/sapi/v1/capital/deposit/hisrec) والسحوبات (/sapi/v1/capital/withdraw/history) حيثما يتاح.
    5. حساب أساس التكلفة، الأرباح والخسائر بعد الرسوم، التراجع (Drawdown)، والمطابقة المحاسبية وحفظها في جداول معزولة.
    """
    perm_check = verify_and_update_credential_permissions(purpose=purpose)
    if not perm_check.get("configured"):
        raise HTTPException(
            status_code=409,
            detail="PENDING_OWNER_SETUP: Configure a Read-Only personal Binance API key before syncing.",
        )

    loaded = _load_decrypted_credential_material(purpose)
    assert loaded is not None
    row = loaded["row"]
    base_url = str(row["base_url"])
    alg: AuthAlgorithm = row["auth_algorithm"]  # type: ignore[assignment]
    api_key = loaded["apiKey"]
    secret_mat = loaded["secretMaterial"]
    tracked_symbols: list[str] = json.loads(str(row["tracked_symbols_json"] or '["BTCUSDT","ETHUSDT","SOLUSDT"]'))

    # 1. جلب الأرصدة من /api/v3/account
    acc_status, acc_body, _ = _execute_signed_binance_get(
        base_url=base_url,
        path="/api/v3/account",
        params={"omitZeroBalances": "true"},
        api_key=api_key,
        secret_material=secret_mat,
        algorithm=alg,
        purpose=purpose,
    )
    if acc_status != 200 or not isinstance(acc_body, dict):
        raise HTTPException(status_code=502, detail=f"Failed to fetch /api/v3/account (HTTP {acc_status}).")

    raw_balances = acc_body.get("balances") or []

    # 2. جلب أسعار السوق الفورية للتقييم الدقيق
    spot_prices: dict[str, float] = {}
    try:
        with create_outbound_http_client(base_url, timeout_sec=6.0) as client:
            pr_resp = client.get(f"{base_url.rstrip('/')}/api/v3/ticker/price")
            if pr_resp.status_code == 200 and isinstance(pr_resp.json(), list):
                for entry in pr_resp.json():
                    sym = str(entry.get("symbol", "")).upper()
                    if sym.endswith("USDT"):
                        spot_prices[sym] = float(entry.get("price", 0.0))
                        spot_prices[sym[:-4]] = float(entry.get("price", 0.0))
    except Exception:
        pass

    # 3. جلب سجل الأوامر وسجل الصفقات للأزواج المتتبعة
    synced_orders: list[dict[str, Any]] = []
    synced_trades: list[dict[str, Any]] = []
    for sym in tracked_symbols[:8]:
        clean_sym = sym.strip().upper()
        o_status, o_body, _ = _execute_signed_binance_get(
            base_url=base_url,
            path="/api/v3/allOrders",
            params={"symbol": clean_sym, "limit": 50},
            api_key=api_key,
            secret_material=secret_mat,
            algorithm=alg,
            purpose=purpose,
        )
        if o_status == 200 and isinstance(o_body, list):
            synced_orders.extend(o_body)

        t_status, t_body, _ = _execute_signed_binance_get(
            base_url=base_url,
            path="/api/v3/myTrades",
            params={"symbol": clean_sym, "limit": 100},
            api_key=api_key,
            secret_material=secret_mat,
            algorithm=alg,
            purpose=purpose,
        )
        if t_status == 200 and isinstance(t_body, list):
            for tr in t_body:
                tr["symbol"] = clean_sym
                synced_trades.append(tr)

    # 4. جلب سجل الإيداعات والسحوبات حيثما تسمح نقطة النهاية
    synced_cashflows: list[dict[str, Any]] = []
    dep_status, dep_body, _ = _execute_signed_binance_get(
        base_url=base_url,
        path="/sapi/v1/capital/deposit/hisrec",
        params={"limit": 100},
        api_key=api_key,
        secret_material=secret_mat,
        algorithm=alg,
        purpose=purpose,
    )
    if dep_status == 200 and isinstance(dep_body, list):
        for d in dep_body:
            if int(d.get("status", 1)) == 1:  # 1 == Credited / Success on Binance
                synced_cashflows.append(
                    {
                        "direction": "DEPOSIT",
                        "coin": str(d.get("coin", "USDT")).upper(),
                        "amount": float(d.get("amount", 0.0)),
                        "transactionFee": 0.0,
                        "statusLabel": "CREDITED",
                        "network": str(d.get("network", "")),
                        "txId": str(d.get("txId", d.get("id", ""))),
                        "timeMs": int(d.get("insertTime", int(time.time() * 1000))),
                    }
                )

    wd_status, wd_body, _ = _execute_signed_binance_get(
        base_url=base_url,
        path="/sapi/v1/capital/withdraw/history",
        params={"limit": 100},
        api_key=api_key,
        secret_material=secret_mat,
        algorithm=alg,
        purpose=purpose,
    )
    if wd_status == 200 and isinstance(wd_body, list):
        for w in wd_body:
            if int(w.get("status", 6)) == 6:  # 6 == Completed on Binance
                ts_raw = w.get("completeTime") or w.get("applyTime") or ""
                t_ms = int(time.time() * 1000)
                if isinstance(ts_raw, (int, float)):
                    t_ms = int(ts_raw)
                synced_cashflows.append(
                    {
                        "direction": "WITHDRAWAL",
                        "coin": str(w.get("coin", "USDT")).upper(),
                        "amount": float(w.get("amount", 0.0)),
                        "transactionFee": float(w.get("transactionFee", 0.0)),
                        "statusLabel": "COMPLETED",
                        "network": str(w.get("network", "")),
                        "txId": str(w.get("txId", w.get("id", ""))),
                        "timeMs": t_ms,
                    }
                )

    accounting = compute_spot_accounting_and_reconciliation(
        raw_balances=raw_balances,
        trades=synced_trades,
        cashflows=synced_cashflows,
        spot_prices_usd=spot_prices,
    )

    now = utc_now_iso()
    with db_session() as conn:
        # تحديث جدول الأرصدة الفورية الفعلي المعزول
        conn.execute("DELETE FROM binance_personal_balances")
        for b in accounting["balances"]:
            conn.execute(
                """
                INSERT INTO binance_personal_balances (
                    asset, free_qty, locked_qty, total_qty, price_usd, value_usd, value_sar,
                    avg_cost_basis_usd, total_cost_basis_usd, unrealized_pnl_usd, unrealized_pnl_pct,
                    realized_pnl_usd, cumulative_fees_usd, reconciled_status, reconciled_delta_qty,
                    is_quote_cash, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    b["asset"],
                    b["freeQty"],
                    b["lockedQty"],
                    b["totalQty"],
                    b["priceUsd"],
                    b["valueUsd"],
                    b["valueSar"],
                    b["avgCostBasisUsd"],
                    b["totalCostBasisUsd"],
                    b["unrealizedPnlUsd"],
                    b["unrealizedPnlPct"],
                    b["realizedPnlUsd"],
                    b["cumulativeFeesUsd"],
                    b["reconciliationStatus"],
                    b["reconciledDeltaQty"],
                    int(b["isQuoteCash"]),
                    now,
                ),
            )

        # حفظ الأوامر دون تكرار
        for o in synced_orders:
            sym = str(o.get("symbol", "")).upper()
            oid = str(o.get("orderId", ""))
            order_uid = f"{sym}:{oid}"
            o_ms = int(o.get("time") or o.get("updateTime") or int(time.time() * 1000))
            o_iso = datetime.fromtimestamp(o_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            existing_o = conn.execute(
                "SELECT order_uid FROM binance_personal_orders WHERE order_uid = ?",
                (order_uid,),
            ).fetchone()
            if existing_o is None:
                conn.execute(
                    """
                    INSERT INTO binance_personal_orders (
                        order_uid, symbol, binance_order_id, client_order_id, side, order_type, status,
                        price, orig_qty, executed_qty, cummulative_quote_qty, order_time_iso, order_time_ms, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_uid,
                        sym,
                        oid,
                        str(o.get("clientOrderId", "")),
                        str(o.get("side", "BUY")).upper(),
                        str(o.get("type", "LIMIT")).upper(),
                        str(o.get("status", "FILLED")).upper(),
                        float(o.get("price", 0.0)),
                        float(o.get("origQty", 0.0)),
                        float(o.get("executedQty", 0.0)),
                        float(o.get("cummulativeQuoteQty", 0.0)),
                        o_iso,
                        o_ms,
                        now,
                    ),
                )
            else:
                conn.execute(
                    "UPDATE binance_personal_orders SET status = ?, executed_qty = ?, cummulative_quote_qty = ?, synced_at = ? WHERE order_uid = ?",
                    (
                        str(o.get("status", "FILLED")).upper(),
                        float(o.get("executedQty", 0.0)),
                        float(o.get("cummulativeQuoteQty", 0.0)),
                        now,
                        order_uid,
                    ),
                )

        # حفظ الصفقات الفورية مع بصمة SHA-256 لمنع الازدواج الحسابي
        for tr in synced_trades:
            sym = str(tr.get("symbol", "")).upper()
            tid = str(tr.get("id", ""))
            oid = str(tr.get("orderId", ""))
            side = "BUY" if bool(tr.get("isBuyer", str(tr.get("side", "")).upper() == "BUY")) else "SELL"
            fp = hashlib.sha256(f"binance-spot-trade|{sym}|{tid}|{oid}".encode("utf-8")).hexdigest()
            if conn.execute("SELECT trade_uid FROM binance_personal_trades WHERE trade_fingerprint = ?", (fp,)).fetchone() is None:
                t_ms = int(tr.get("time", int(time.time() * 1000)))
                t_iso = datetime.fromtimestamp(t_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                comm = float(tr.get("commission", 0.0))
                comm_asset = str(tr.get("commissionAsset", "USDT")).upper()
                comm_usd = round(comm * _resolve_asset_usd_price(comm_asset, spot_prices), 6)
                conn.execute(
                    """
                    INSERT INTO binance_personal_trades (
                        trade_uid, trade_fingerprint, symbol, binance_trade_id, binance_order_id,
                        side, price, qty, quote_qty, commission, commission_asset, commission_usd,
                        is_maker, trade_time_iso, trade_time_ms, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"{sym}:{tid}",
                        fp,
                        sym,
                        tid,
                        oid,
                        side,
                        float(tr.get("price", 0.0)),
                        float(tr.get("qty", 0.0)),
                        float(tr.get("quoteQty", 0.0)),
                        comm,
                        comm_asset,
                        comm_usd,
                        int(bool(tr.get("isMaker", False))),
                        t_iso,
                        t_ms,
                        now,
                    ),
                )

        # حفظ الإيداعات والسحوبات مع بصمة SHA-256 لمنع الازدواج الحسابي مع كشوف البنك
        for cf in synced_cashflows:
            fp = hashlib.sha256(
                f"binance-cashflow|{cf['direction']}|{cf['coin']}|{cf['amount']:.8f}|{cf['txId']}|{cf['timeMs']}".encode("utf-8")
            ).hexdigest()
            if conn.execute("SELECT cashflow_id FROM binance_personal_cashflows WHERE tx_fingerprint = ?", (fp,)).fetchone() is None:
                px = _resolve_asset_usd_price(cf["coin"], spot_prices)
                amt_usd = round(cf["amount"] * px, 2)
                amt_sar = round(amt_usd * SAR_PER_USD_PEG, 2)
                c_iso = datetime.fromtimestamp(cf["timeMs"] / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                conn.execute(
                    """
                    INSERT INTO binance_personal_cashflows (
                        cashflow_id, tx_fingerprint, direction, coin, amount, amount_usd, amount_sar,
                        transaction_fee, status_label, network, tx_id_hash, occurred_at_iso, occurred_at_ms, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"bcf_{uuid.uuid4().hex[:12]}",
                        fp,
                        cf["direction"],
                        cf["coin"],
                        cf["amount"],
                        amt_usd,
                        amt_sar,
                        cf["transactionFee"],
                        cf["statusLabel"],
                        cf["network"],
                        hashlib.sha256(str(cf["txId"]).encode("utf-8")).hexdigest()[:24] if cf["txId"] else "",
                        c_iso,
                        cf["timeMs"],
                        now,
                    ),
                )

        # حساب التراجع (Drawdown) مقابل أعلى حقوق ملكية تاريخية مسجلة للحساب الفعلي
        peak_row = conn.execute("SELECT MAX(total_equity_usd) AS peak_eq FROM binance_personal_snapshots").fetchone()
        prev_peak = float(peak_row["peak_eq"] or 0.0) if peak_row else 0.0
        effective_peak = max(prev_peak, accounting["totalEquityUsd"])
        drawdown_pct = (
            round(((effective_peak - accounting["totalEquityUsd"]) / effective_peak) * 100.0, 2)
            if effective_peak > 0.01
            else 0.0
        )

        conn.execute(
            """
            INSERT INTO binance_personal_snapshots (
                snapshot_id, total_equity_usd, total_equity_sar, quote_cash_usd, invested_crypto_usd,
                net_contributed_usd, realized_pnl_usd, unrealized_pnl_usd, cumulative_fees_usd, drawdown_pct, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"bsnap_{uuid.uuid4().hex[:12]}",
                accounting["totalEquityUsd"],
                accounting["totalEquitySar"],
                accounting["quoteCashUsd"],
                accounting["investedCryptoUsd"],
                accounting["netContributedCapitalUsd"],
                accounting["realizedPnlUsd"],
                accounting["unrealizedPnlUsd"],
                accounting["cumulativeFeesUsd"],
                drawdown_pct,
                now,
            ),
        )
        conn.execute(
            "UPDATE binance_owner_credentials SET last_synced_at = ?, updated_at = ? WHERE purpose = ?",
            (now, now, purpose),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="BINANCE_READ_ONLY_SYNC",
            action="PERSONAL_BINANCE_SPOT_SYNCED",
            severity="INFO",
            details_ar=(
                f"تمت مزامنة الحساب الشخصي في Binance للقراءة فقط: إجمالي المحفظة {accounting['totalEquitySar']:,.2f} ريال "
                f"({accounting['totalEquityUsd']:,.2f} دولار) — دون إرسال أي أمر تداول."
            ),
            details_en=(
                f"Synced Read-Only personal Binance Spot portfolio: equity=${accounting['totalEquityUsd']:,.2f} "
                f"(SAR {accounting['totalEquitySar']:,.2f}); zero orders submitted."
            ),
            conn=conn,
        )

    return get_personal_binance_overview()


# ==============================================================================
# 6. Read-Only Overview Builder (Safe for UI — Zero Secret Exposure)
# ==============================================================================


def get_personal_binance_overview() -> dict[str, Any]:
    """
    بناء اللوحة الشاملة لمراقبة حساب Binance الشخصي للمالك:
    - لا تتضمن مطلقاً أي مفتاح API كامل أو مفتاح خاص أو سر مشفر.
    - عندما لا تكون مفاتيح المالك مكوّنة، تُعيد connectionStatus = 'PENDING_OWNER_SETUP' بصدق كامل.
    """
    ensure_binance_personal_tables()
    active_passkeys = list_registered_passkeys(include_revoked=False)

    with db_session() as conn:
        cred_rows = conn.execute(
            "SELECT * FROM binance_owner_credentials WHERE revoked_at = '' ORDER BY purpose ASC"
        ).fetchall()
        bal_rows = conn.execute(
            "SELECT * FROM binance_personal_balances ORDER BY value_usd DESC"
        ).fetchall()
        order_rows = conn.execute(
            "SELECT * FROM binance_personal_orders ORDER BY order_time_ms DESC LIMIT 40"
        ).fetchall()
        trade_rows = conn.execute(
            "SELECT * FROM binance_personal_trades ORDER BY trade_time_ms DESC LIMIT 50"
        ).fetchall()
        cf_rows = conn.execute(
            "SELECT * FROM binance_personal_cashflows ORDER BY occurred_at_ms DESC LIMIT 40"
        ).fetchall()
        latest_snap = conn.execute(
            "SELECT * FROM binance_personal_snapshots ORDER BY recorded_at DESC LIMIT 1"
        ).fetchone()

    slots_summary: dict[str, Any] = {
        "READ_ONLY_MONITORING": {"configured": False, "status": "PENDING_OWNER_SETUP"},
        "FUTURE_SPOT_EXECUTION": {"configured": False, "status": "NOT_CONFIGURED_LOCKED_TO_PAPER"},
    }
    primary_row: dict[str, Any] | None = None

    for r in cred_rows:
        rd = dict(r)
        p = str(rd["purpose"])
        perm_snap = json.loads(str(rd["permission_snapshot_json"] or "{}"))
        trusted_ips = json.loads(str(rd["trusted_ips_json"] or "[]"))
        tracked_syms = json.loads(str(rd["tracked_symbols_json"] or '["BTCUSDT","ETHUSDT","SOLUSDT"]'))
        slots_summary[p] = {
            "configured": True,
            "credentialId": rd["credential_id"],
            "keyLabel": rd["key_label"],
            "authAlgorithm": rd["auth_algorithm"],
            "environment": rd["environment"],
            "baseUrl": rd["base_url"],
            "apiKeyMasked": rd["api_key_masked"],
            "trustedIps": trusted_ips,
            "trackedSymbols": tracked_syms,
            "status": rd["verification_status"],
            "verificationReason": rd["verification_reason"],
            "permissionAudit": perm_snap,
            "rotatedCount": int(rd["rotated_count"]),
            "health": {
                "usedWeight1m": int(rd["used_weight_1m"]),
                "lastLatencyMs": float(rd["last_latency_ms"]),
                "clockSkewMs": int(rd["clock_skew_ms"]),
                "consecutiveFailures": int(rd["consecutive_failures"]),
                "rateLimitCooldownActive": float(rd["rate_limit_cooldown_until"] or 0.0) > time.time(),
            },
            "createdAt": rd["created_at"],
            "lastVerifiedAt": rd["last_verified_at"] or None,
            "lastSyncedAt": rd["last_synced_at"] or None,
        }
        if p == "READ_ONLY_MONITORING":
            primary_row = slots_summary[p]

    connection_status = (
        str(primary_row["status"]) if primary_row is not None else "PENDING_OWNER_SETUP"
    )

    total_eq_usd = float(latest_snap["total_equity_usd"]) if latest_snap else 0.0
    total_eq_sar = float(latest_snap["total_equity_sar"]) if latest_snap else 0.0
    quote_cash_usd = float(latest_snap["quote_cash_usd"]) if latest_snap else 0.0
    invested_crypto_usd = float(latest_snap["invested_crypto_usd"]) if latest_snap else 0.0
    net_contrib_usd = float(latest_snap["net_contributed_usd"]) if latest_snap else 0.0
    realized_usd = float(latest_snap["realized_pnl_usd"]) if latest_snap else 0.0
    unrealized_usd = float(latest_snap["unrealized_pnl_usd"]) if latest_snap else 0.0
    fees_usd = float(latest_snap["cumulative_fees_usd"]) if latest_snap else 0.0
    drawdown_pct = float(latest_snap["drawdown_pct"]) if latest_snap else 0.0

    formatted_balances = []
    unreconciled_count = 0
    for b in bal_rows:
        bd = dict(b)
        val_usd = float(bd["value_usd"])
        if str(bd["reconciled_status"]) != "RECONCILED_EXACT":
            unreconciled_count += 1
        formatted_balances.append(
            {
                "asset": bd["asset"],
                "freeQty": float(bd["free_qty"]),
                "lockedQty": float(bd["locked_qty"]),
                "totalQty": float(bd["total_qty"]),
                "priceUsd": float(bd["price_usd"]),
                "valueUsd": val_usd,
                "valueSar": float(bd["value_sar"]),
                "allocationWeightPct": round((val_usd / total_eq_usd) * 100.0, 2) if total_eq_usd > 0 else 0.0,
                "avgCostBasisUsd": float(bd["avg_cost_basis_usd"]),
                "totalCostBasisUsd": float(bd["total_cost_basis_usd"]),
                "unrealizedPnlUsd": float(bd["unrealized_pnl_usd"]),
                "unrealizedPnlPct": float(bd["unrealized_pnl_pct"]),
                "realizedPnlUsd": float(bd["realized_pnl_usd"]),
                "cumulativeFeesUsd": float(bd["cumulative_fees_usd"]),
                "reconciliationStatus": bd["reconciled_status"],
                "reconciledDeltaQty": float(bd["reconciled_delta_qty"]),
                "isQuoteCash": bool(bd["is_quote_cash"]),
                "updatedAt": bd["updated_at"],
            }
        )

    # حساب المشتريات والإيداعات في الشهر الميلادي الحالي مقابل مخصص 2,125 ريال
    now_utc = datetime.now(timezone.utc)
    month_prefix = now_utc.strftime("%Y-%m")
    current_month_deposits_sar = round(
        sum(
            float(c["amount_sar"])
            for c in cf_rows
            if str(c["direction"]) == "DEPOSIT" and str(c["occurred_at_iso"]).startswith(month_prefix)
        ),
        2,
    )
    current_month_spot_buys_sar = round(
        sum(
            float(t["quote_qty"]) * SAR_PER_USD_PEG
            for t in trade_rows
            if str(t["side"]) == "BUY" and str(t["trade_time_iso"]).startswith(month_prefix)
        ),
        2,
    )

    risk_alerts: list[dict[str, Any]] = []
    if connection_status == "PENDING_OWNER_SETUP":
        risk_alerts.append(
            {
                "code": "PENDING_OWNER_SETUP",
                "severity": "INFO",
                "messageEn": "Personal Binance account is PENDING OWNER SETUP. Generate an Ed25519 Public Key below and connect a Read-Only API key.",
                "messageAr": "حساب Binance الشخصي بانتظار إعداد المالك (PENDING OWNER SETUP). ولّد مفتاح Ed25519 العام أدناه واربط مفتاح قراءة فقط.",
            }
        )
    elif connection_status == "BLOCKED_UNSAFE_PERMISSIONS":
        risk_alerts.append(
            {
                "code": "UNSAFE_API_PERMISSIONS_BLOCKED",
                "severity": "CRITICAL",
                "messageEn": "Configured Binance key has forbidden permissions (withdrawals/margin/futures/trading on read-only slot) and is blocked.",
                "messageAr": "تم حظر المفتاح المكون لاحتوائه على صلاحيات محظورة (سحب أو هامش أو عقود آجلة أو تداول في فتحة القراءة فقط).",
            }
        )
    if drawdown_pct >= 10.0:
        risk_alerts.append(
            {
                "code": "PORTFOLIO_DRAWDOWN_ELEVATED",
                "severity": "WARNING",
                "messageEn": f"Live Spot portfolio drawdown is {drawdown_pct:.2f}% from recorded peak equity.",
                "messageAr": f"تراجع المحفظة الفورية الفعلية بلغ {drawdown_pct:.2f}% من أعلى قمة مسجلة.",
            }
        )
    if current_month_spot_buys_sar > PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR + 0.01:
        risk_alerts.append(
            {
                "code": "MONTHLY_CRYPTO_BUDGET_EXCEEDED",
                "severity": "WARNING",
                "messageEn": (
                    f"Current month Spot purchases (SAR {current_month_spot_buys_sar:,.2f}) exceed planned monthly budget "
                    f"(SAR {PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR:,.2f})."
                ),
                "messageAr": (
                    f"تجاوزت المشتريات الفورية لهذا الشهر ({current_month_spot_buys_sar:,.2f} ريال) الميزانية الشهرية المخططة ({PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR:,.2f} ريال)."
                ),
            }
        )

    return {
        "generatedAt": utc_now_iso(),
        "dashboardLabel": "LIVE ACCOUNT MONITORING",
        "segregatedFromPaperTrading": True,
        "tradingMode": "PAPER",
        "liveAuthorized": False,
        "executionLockedToPaper": True,
        "connectionStatus": connection_status,
        "supportedAuthMechanisms": [
            {
                "algorithm": "ED25519",
                "recommended": True,
                "label": "Ed25519 Asymmetric API Key (Server-Generated Keypair — Private Key Never Leaves Vault)",
                "officialDocs": "Binance Spot API v3 — Asymmetric Ed25519 Signature",
            },
            {
                "algorithm": "RSA_SHA256",
                "recommended": False,
                "label": "RSA-SHA256 Asymmetric API Key",
                "officialDocs": "Binance Spot API v3 — RSA PKCS#1 v1.5 Signature",
            },
            {
                "algorithm": "HMAC_SHA256",
                "recommended": False,
                "label": "HMAC-SHA256 Restricted API Key (Encrypted at Rest with AES-256-GCM)",
                "officialDocs": "Binance Spot API v3 — HMAC-SHA256 Signature",
            },
        ],
        "biometricArchitecture": {
            "binanceAppFaceIdExplanationEn": (
                "Binance iOS/Android Face ID authenticates you locally inside the official Binance mobile app only; "
                "third-party platforms never access your raw biometric Face ID/Touch ID sensor data."
            ),
            "trilunairPasskeyExplanationEn": (
                "TRILUNAIR uses OS-backed FIDO2 / WebAuthn Passkeys (Face ID on iPhone, Touch ID on Mac) bound to "
                "trilunair.medinsup.com to authorize credential changes and future trading approvals with zero biometric storage."
            ),
            "enrolledPasskeyCount": len(active_passkeys),
            "biometricStepUpRequiredForCredentialChanges": len(active_passkeys) > 0
            or os.getenv("TRILUNAIR_REQUIRE_PASSKEY_STEP_UP", "false").lower() == "true",
            "biometricTemplatesStoredOnServer": False,
        },
        "credentialSlots": slots_summary,
        "portfolioSummary": {
            "accountingMethod": "WEIGHTED_AVERAGE_COST_BASIS_SPOT_LEDGER",
            "totalEquityUsd": round(total_eq_usd, 2),
            "totalEquitySar": round(total_eq_sar, 2),
            "availableQuoteCashUsd": round(quote_cash_usd, 2),
            "availableQuoteCashSar": round(quote_cash_usd * SAR_PER_USD_PEG, 2),
            "investedCryptoCapitalUsd": round(invested_crypto_usd, 2),
            "investedCryptoCapitalSar": round(invested_crypto_usd * SAR_PER_USD_PEG, 2),
            "cryptoExposurePct": round((invested_crypto_usd / total_eq_usd) * 100.0, 2) if total_eq_usd > 0 else 0.0,
            "netContributedCapitalUsd": round(net_contrib_usd, 2),
            "netContributedCapitalSar": round(net_contrib_usd * SAR_PER_USD_PEG, 2),
            "realizedPnlUsd": round(realized_usd, 2),
            "realizedPnlSar": round(realized_usd * SAR_PER_USD_PEG, 2),
            "unrealizedPnlUsd": round(unrealized_usd, 2),
            "unrealizedPnlSar": round(unrealized_usd * SAR_PER_USD_PEG, 2),
            "netPnlAfterFeesUsd": round(realized_usd + unrealized_usd, 2),
            "netPnlAfterFeesSar": round((realized_usd + unrealized_usd) * SAR_PER_USD_PEG, 2),
            "cumulativeFeesUsd": round(fees_usd, 4),
            "cumulativeFeesSar": round(fees_usd * SAR_PER_USD_PEG, 2),
            "portfolioDrawdownPct": round(drawdown_pct, 2),
            "reconciliationStatus": "RECONCILED_EXACT" if unreconciled_count == 0 else "PARTIAL_PRE_SYNC_HISTORY_NOTE",
            "unreconciledAssetsCount": unreconciled_count,
        },
        "monthlyInvestmentBudgetTracking": {
            "plannedMonthlyAllocationSar": PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR,
            "plannedMonthlyAllocationUsd": PLANNED_MONTHLY_CRYPTO_ALLOCATION_USD,
            "currentMonth": month_prefix,
            "currentMonthVerifiedDepositsSar": current_month_deposits_sar,
            "currentMonthSpotPurchasesSar": current_month_spot_buys_sar,
            "remainingMonthlyBudgetSar": round(
                max(0.0, PLANNED_MONTHLY_CRYPTO_ALLOCATION_SAR - max(current_month_deposits_sar, current_month_spot_buys_sar)),
                2,
            ),
        },
        "balances": formatted_balances,
        "recentOrders": [
            {
                "orderUid": r["order_uid"],
                "symbol": r["symbol"],
                "orderId": r["binance_order_id"],
                "side": r["side"],
                "type": r["order_type"],
                "status": r["status"],
                "price": float(r["price"]),
                "origQty": float(r["orig_qty"]),
                "executedQty": float(r["executed_qty"]),
                "cummulativeQuoteQty": float(r["cummulative_quote_qty"]),
                "orderTimeIso": r["order_time_iso"],
            }
            for r in order_rows
        ],
        "recentTrades": [
            {
                "tradeUid": r["trade_uid"],
                "symbol": r["symbol"],
                "tradeId": r["binance_trade_id"],
                "orderId": r["binance_order_id"],
                "side": r["side"],
                "price": float(r["price"]),
                "qty": float(r["qty"]),
                "quoteQty": float(r["quote_qty"]),
                "commission": float(r["commission"]),
                "commissionAsset": r["commission_asset"],
                "commissionUsd": float(r["commission_usd"]),
                "tradeTimeIso": r["trade_time_iso"],
            }
            for r in trade_rows
        ],
        "recentCashflows": [
            {
                "cashflowId": r["cashflow_id"],
                "direction": r["direction"],
                "coin": r["coin"],
                "amount": float(r["amount"]),
                "amountUsd": float(r["amount_usd"]),
                "amountSar": float(r["amount_sar"]),
                "transactionFee": float(r["transaction_fee"]),
                "statusLabel": r["status_label"],
                "network": r["network"],
                "occurredAtIso": r["occurred_at_iso"],
            }
            for r in cf_rows
        ],
        "riskAlerts": risk_alerts,
    }


# ==============================================================================
# 7. Request Models & FastAPI Endpoints (/api/binance/personal/*)
# ==============================================================================


class GenerateEd25519Request(BaseModel):
    model_config = ConfigDict(extra="allow")
    purpose: CredentialPurpose = "READ_ONLY_MONITORING"
    adminSecret: str | None = None


class SaveBinanceCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    purpose: CredentialPurpose = "READ_ONLY_MONITORING"
    keyLabel: str = Field(default="Owner Personal Read-Only Key", min_length=2, max_length=100)
    authAlgorithm: AuthAlgorithm = "ED25519"
    environment: BinanceEnvironment = "MAINNET"
    customBaseUrl: str | None = None
    apiKey: str = Field(min_length=10, max_length=256)
    generatedKeypairId: str | None = None
    privateKeyPem: str | None = None
    apiSecret: str | None = None
    trustedIps: list[str] = Field(default_factory=list)
    trackedSymbols: list[str] = Field(default_factory=lambda: list(DEFAULT_TRACKED_SPOT_SYMBOLS[:4]))
    verifyImmediately: bool = False
    adminSecret: str | None = None


def _store_or_rotate_credential(
    req: SaveBinanceCredentialRequest,
    raw_body: dict[str, Any],
    is_rotation: bool = False,
) -> dict[str, Any]:
    """حفظ أو تدوير بيانات اعتماد Binance المشفرة بـ AES-256-GCM دون إرجاع أي سر للعميل."""
    reject_prohibited_credential_fields(raw_body)
    ensure_binance_personal_tables()

    base_url = _resolve_base_url(req.environment, req.customBaseUrl)
    api_key_clean = req.apiKey.strip()
    masked_key = mask_api_key(api_key_clean)
    api_key_hash = hashlib.sha256(api_key_clean.encode("utf-8")).hexdigest()

    public_key_pem = ""
    secret_material_plain = ""

    if req.generatedKeypairId:
        if req.authAlgorithm != "ED25519":
            raise HTTPException(status_code=400, detail="generatedKeypairId is only valid with ED25519 authAlgorithm.")
        with db_session() as conn:
            kp = conn.execute(
                "SELECT * FROM binance_generated_keypairs WHERE keypair_id = ?",
                (req.generatedKeypairId.strip(),),
            ).fetchone()
            if kp is None:
                raise HTTPException(status_code=404, detail="Generated Ed25519 keypairId not found in server vault.")
            aad_kp = f"binance-ed25519-keypair:{kp['purpose']}:{kp['keypair_id']}"
            secret_material_plain = decrypt_vault_secret(str(kp["private_key_ciphertext"]), aad_context=aad_kp)
            public_key_pem = str(kp["public_key_pem"])
            conn.execute(
                "UPDATE binance_generated_keypairs SET consumed = 1 WHERE keypair_id = ?",
                (req.generatedKeypairId.strip(),),
            )
    elif req.authAlgorithm in {"ED25519", "RSA_SHA256"}:
        if not req.privateKeyPem or "PRIVATE KEY" not in req.privateKeyPem:
            raise HTTPException(
                status_code=400,
                detail=f"{req.authAlgorithm} requires either generatedKeypairId (recommended) or a valid PKCS#8 PRIVATE KEY PEM.",
            )
        secret_material_plain = req.privateKeyPem.strip()
        # التحقق من صحة مفتاح PEM واستخراج المفتاح العام للعرض الآمن فقط
        try:
            loaded_pk = serialization.load_pem_private_key(secret_material_plain.encode("utf-8"), password=None)
            public_key_pem = (
                loaded_pk.public_key()
                .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
                .decode("ascii")
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid asymmetric PRIVATE KEY PEM format.") from exc
    else:
        if not req.apiSecret or len(req.apiSecret.strip()) < 10:
            raise HTTPException(status_code=400, detail="HMAC_SHA256 requires a valid apiSecret (min 10 chars).")
        secret_material_plain = req.apiSecret.strip()

    cred_id = f"bcred_{uuid.uuid4().hex[:16]}"
    aad_api = f"binance-api-key:{req.purpose}:{cred_id}"
    aad_sec = f"binance-secret:{req.purpose}:{cred_id}"
    enc_api = encrypt_vault_secret(api_key_clean, aad_context=aad_api)
    enc_sec = encrypt_vault_secret(secret_material_plain, aad_context=aad_sec)

    clean_ips = [ip.strip()[:45] for ip in req.trustedIps if ip.strip()][:10]
    clean_syms = [
        s.strip().upper()
        for s in (req.trackedSymbols or list(DEFAULT_TRACKED_SPOT_SYMBOLS[:4]))
        if s.strip().isalnum()
    ][:12] or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    now = utc_now_iso()
    with db_session() as conn:
        prev = conn.execute(
            "SELECT rotated_count FROM binance_owner_credentials WHERE purpose = ?",
            (req.purpose,),
        ).fetchone()
        rot_count = (int(prev["rotated_count"]) + 1) if (prev is not None and (is_rotation or prev is not None)) else 0
        if prev is None:
            conn.execute(
                """
                INSERT INTO binance_owner_credentials (
                    purpose, credential_id, key_label, auth_algorithm, environment, base_url,
                    api_key_masked, api_key_sha256, api_key_ciphertext, secret_ciphertext,
                    public_key_pem, trusted_ips_json, tracked_symbols_json, permission_snapshot_json,
                    verification_status, verification_reason, rotated_count, created_at, updated_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', 'CONFIGURED_PENDING_VERIFICATION', 'Pending live scope audit', 0, ?, ?, '')
                """,
                (
                    req.purpose,
                    cred_id,
                    req.keyLabel.strip(),
                    req.authAlgorithm,
                    req.environment,
                    base_url,
                    masked_key,
                    api_key_hash,
                    enc_api,
                    enc_sec,
                    public_key_pem,
                    json.dumps(clean_ips),
                    json.dumps(clean_syms),
                    now,
                    now,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE binance_owner_credentials
                SET credential_id = ?, key_label = ?, auth_algorithm = ?, environment = ?, base_url = ?,
                    api_key_masked = ?, api_key_sha256 = ?, api_key_ciphertext = ?, secret_ciphertext = ?,
                    public_key_pem = ?, trusted_ips_json = ?, tracked_symbols_json = ?,
                    permission_snapshot_json = '{}', verification_status = 'CONFIGURED_PENDING_VERIFICATION',
                    verification_reason = 'Rotated — pending live scope audit', rotated_count = ?,
                    consecutive_failures = 0, rate_limit_cooldown_until = 0, updated_at = ?, revoked_at = ''
                WHERE purpose = ?
                """,
                (
                    cred_id,
                    req.keyLabel.strip(),
                    req.authAlgorithm,
                    req.environment,
                    base_url,
                    masked_key,
                    api_key_hash,
                    enc_api,
                    enc_sec,
                    public_key_pem,
                    json.dumps(clean_ips),
                    json.dumps(clean_syms),
                    rot_count,
                    now,
                    req.purpose,
                ),
            )

        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="BINANCE_VAULT",
            action="BINANCE_CREDENTIAL_ROTATED" if is_rotation else "BINANCE_CREDENTIAL_STORED",
            severity="INFO",
            details_ar=(
                f"حفظ بيانات اعتماد Binance مشفرة بـ AES-256-GCM للغرض ({req.purpose}) بالخوارزمية ({req.authAlgorithm}) "
                f"للمفتاح المخفي ({masked_key}) — يظل التنفيذ مقفلاً على PAPER."
            ),
            details_en=(
                f"{'Rotated' if is_rotation else 'Stored'} AES-256-GCM encrypted Binance credential ({req.purpose}, "
                f"alg={req.authAlgorithm}, key={masked_key}); execution remains locked to PAPER."
            ),
            conn=conn,
        )

    verification_result = None
    if req.verifyImmediately:
        verification_result = verify_and_update_credential_permissions(purpose=req.purpose)

    return {
        "saved": True,
        "rotated": is_rotation,
        "purpose": req.purpose,
        "credentialId": cred_id,
        "apiKeyMasked": masked_key,
        "authAlgorithm": req.authAlgorithm,
        "environment": req.environment,
        "secretExposed": False,
        "tradingMode": "PAPER",
        "liveAuthorized": False,
        "verification": verification_result,
    }


@binance_personal_router.get("/overview")
def api_get_personal_binance_overview() -> dict[str, Any]:
    """استرجاع حالة اتصال حساب Binance الشخصي والمحفظة الفورية الفعلية وسجل الصفقات دون كشف أي سر."""
    return get_personal_binance_overview()


@binance_personal_router.post("/ed25519/generate")
async def api_generate_ed25519_keypair(
    request: Request,
    raw_body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """توليد زوج مفاتيح Ed25519 بالخادم الخلفي وإرجاع المفتاح العام (PUBLIC KEY PEM) فقط للمالك."""
    reject_prohibited_credential_fields(raw_body)
    req = GenerateEd25519Request.model_validate(raw_body)
    auth_info = require_owner_biometric_for_binance(
        request,
        req.adminSecret,
        action_label="BINANCE_ED25519_GENERATE",
    )
    result = generate_server_ed25519_keypair(purpose=req.purpose)
    result["authorizedVia"] = auth_info["authMethod"]
    return result


@binance_personal_router.post("/credentials")
async def api_save_binance_credential(
    request: Request,
    raw_body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """حفظ مفتاح API الشخصي مشفراً بـ AES-256-GCM بعد مصادقة المالك والتصعيد البيومتري."""
    reject_prohibited_credential_fields(raw_body)
    req = SaveBinanceCredentialRequest.model_validate(raw_body)
    auth_info = require_owner_biometric_for_binance(
        request,
        req.adminSecret,
        action_label=f"BINANCE_CREDENTIAL_SAVE:{req.purpose}",
    )
    res = _store_or_rotate_credential(req, raw_body, is_rotation=False)
    res["authorizedVia"] = auth_info["authMethod"]
    return res


@binance_personal_router.post("/credentials/{purpose}/rotate")
async def api_rotate_binance_credential(
    purpose: CredentialPurpose,
    request: Request,
    raw_body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """تدوير مفتاح API الشخصي ذرياً واستبدال النص المشفر القديم فوراً."""
    reject_prohibited_credential_fields(raw_body)
    raw_body = {**raw_body, "purpose": purpose}
    req = SaveBinanceCredentialRequest.model_validate(raw_body)
    auth_info = require_owner_biometric_for_binance(
        request,
        req.adminSecret,
        action_label=f"BINANCE_CREDENTIAL_ROTATE:{purpose}",
    )
    res = _store_or_rotate_credential(req, raw_body, is_rotation=True)
    res["authorizedVia"] = auth_info["authMethod"]
    return res


@binance_personal_router.delete("/credentials/{purpose}")
async def api_revoke_binance_credential(
    purpose: CredentialPurpose,
    request: Request,
    admin_secret: str | None = Query(default=None, alias="adminSecret"),
) -> dict[str, Any]:
    """الإبطال الفوري ومسح النصوص المشفرة لبيانات اعتماد Binance عند الطلب أو الطوارئ."""
    auth_info = require_owner_biometric_for_binance(
        request,
        admin_secret,
        action_label=f"BINANCE_CREDENTIAL_REVOKE:{purpose}",
    )
    ensure_binance_personal_tables()
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE binance_owner_credentials
            SET api_key_ciphertext = 'WIPED', secret_ciphertext = 'WIPED',
                verification_status = 'REVOKED', verification_reason = 'Revoked by owner',
                revoked_at = ?, updated_at = ?
            WHERE purpose = ?
            """,
            (now, now, purpose),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="BINANCE_VAULT",
            action="BINANCE_CREDENTIAL_REVOKED",
            severity="WARNING",
            details_ar=f"تم إبطال ومسح بيانات اعتماد Binance المشفرة فوراً للغرض ({purpose}).",
            details_en=f"Immediately revoked and wiped encrypted Binance credential for slot {purpose}.",
            conn=conn,
        )
    return {
        "revoked": True,
        "purpose": purpose,
        "revokedAt": now,
        "authorizedVia": auth_info["authMethod"],
    }


@binance_personal_router.post("/verify-permissions")
async def api_verify_binance_permissions(
    request: Request,
    purpose: CredentialPurpose = Body(default="READ_ONLY_MONITORING", embed=True),
    admin_secret: str | None = Body(default=None, embed=True, alias="adminSecret"),
) -> dict[str, Any]:
    """تشغيل فحص الصلاحيات المغلق بأمان (Fail-Closed) مقابل Binance API."""
    require_authenticated_session_or_secret(
        request,
        admin_secret,
        action_label=f"BINANCE_VERIFY_PERMISSIONS:{purpose}",
    )
    return verify_and_update_credential_permissions(purpose=purpose)


@binance_personal_router.post("/sync")
async def api_sync_personal_binance(
    request: Request,
    purpose: CredentialPurpose = Body(default="READ_ONLY_MONITORING", embed=True),
    admin_secret: str | None = Body(default=None, embed=True, alias="adminSecret"),
) -> dict[str, Any]:
    """تشغيل مزامنة القراءة فقط للأرصدة والأوامر والصفقات والتدفقات النقدية من حساب Binance الشخصي."""
    require_authenticated_session_or_secret(
        request,
        admin_secret,
        action_label=f"BINANCE_READ_ONLY_SYNC:{purpose}",
    )
    return sync_personal_binance_account(purpose=purpose)
