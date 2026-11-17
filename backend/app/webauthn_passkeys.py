"""
وحدة المصادقة البيومترية للمالك عبر مفاتيح المرور القياسية (WebAuthn Level 2 / FIDO2 Passkeys).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.2.0-low-latency-cloudflare

المتطلبات الأمنية المطبقة:
1. دعم Face ID (آيفون/آيباد)، Touch ID (ماك بوك)، Apple Passkeys، ومفاتيح الأمان المادية FIDO2/YubiKey.
2. عدم تخزين أي بصمات أو صور وجه أو قوالب بيومترية نهائياً؛ يُخزن المفتاح العام (Public Key) ومعرّف الاعتماد فقط.
3. تحقق تشفيري حقيقي كامل (ES256 P-256 / EdDSA Ed25519 / RS256) من توقيع الموثّق وبيانات العميل وهاش النطاق (rpIdHash).
4. حماية صارمة ضد إعادة الإرسال والاستنساخ عبر تحديات أحادية الاستخدام قصيرة العمر وفحص عداد التوقيع التصاعدي (signCount).
5. إجراءات استرداد طوارئ مشفرة بتجزئة PBKDF2-HMAC-SHA256 لرموز الاسترداد أحادية الاستخدام (One-Time Recovery Codes).
6. إصدار والتحقق من رموز التصعيد الأمني قصيرة الصلاحية (Step-Up Verification Tokens) للعمليات الحساسة مع تدقيق كامل.
7. عزل كامل عن النطاق الأب (medinsup.com): يُحظر قبول أي أصل يطابق medinsup.com الطبي، ويُقبل حصراً trilunair.medinsup.com أو بيئة التطوير المحلية.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from typing import Any
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from fastapi import HTTPException, Request

from app.database import append_audit_log, db_session, utc_now_iso
from app.security import (
    _get_session_signing_key,
    create_admin_session,
    get_allowed_cors_origins,
    hash_admin_secret,
    security_telemetry,
)


STEP_UP_HEADER_NAME = "X-Step-Up-Token"
CHALLENGE_TTL_SECONDS = 180
STEP_UP_TTL_SECONDS = 300

# رموز خوارزميات COSE القياسية في WebAuthn
COSE_ALG_ES256 = -7     # ECDSA w/ SHA-256 over NIST P-256 (Face ID, Touch ID, Apple Passkeys, YubiKey)
COSE_ALG_EDDSA = -8     # Ed25519
COSE_ALG_RS256 = -257   # RSASSA-PKCS1-v1_5 w/ SHA-256 (Windows Hello TPM / Legacy FIDO2)


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def b64url_decode(encoded: str) -> bytes:
    cleaned = (encoded or "").strip()
    pad = "=" * (-len(cleaned) % 4)
    return base64.urlsafe_b64decode((cleaned + pad).encode("ascii"))


# ==============================================================================
# 1. محلل CBOR خفيف وآمن مطابق لمعيار RFC 8949 لفك attestationObject ومفاتيح COSE
# ==============================================================================


class _CborCursor:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def read(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ValueError("Unexpected end of CBOR payload")
        out = self.data[self.pos : self.pos + n]
        self.pos += n
        return out

    def _read_uint(self, add_info: int) -> int:
        if add_info < 24:
            return add_info
        if add_info == 24:
            return self.read(1)[0]
        if add_info == 25:
            return struct.unpack("!H", self.read(2))[0]
        if add_info == 26:
            return struct.unpack("!I", self.read(4))[0]
        if add_info == 27:
            return struct.unpack("!Q", self.read(8))[0]
        raise ValueError(f"Unsupported CBOR additional info: {add_info}")

    def decode_item(self) -> Any:
        initial = self.read(1)[0]
        major = initial >> 5
        add_info = initial & 0x1F

        if major == 0:  # Unsigned integer
            return self._read_uint(add_info)
        if major == 1:  # Negative integer
            return -1 - self._read_uint(add_info)
        if major == 2:  # Byte string
            length = self._read_uint(add_info)
            return self.read(length)
        if major == 3:  # UTF-8 string
            length = self._read_uint(add_info)
            return self.read(length).decode("utf-8")
        if major == 4:  # Array
            length = self._read_uint(add_info)
            return [self.decode_item() for _ in range(length)]
        if major == 5:  # Map
            length = self._read_uint(add_info)
            out_map: dict[Any, Any] = {}
            for _ in range(length):
                k = self.decode_item()
                v = self.decode_item()
                out_map[k] = v
            return out_map
        if major == 6:  # Semantic tag
            _ = self._read_uint(add_info)
            return self.decode_item()
        if major == 7:  # Simple / Bool / Null
            if add_info == 20:
                return False
            if add_info == 21:
                return True
            if add_info in (22, 23):
                return None
            raise ValueError(f"Unsupported CBOR simple value: {add_info}")
        raise ValueError(f"Unsupported CBOR major type: {major}")


def cbor_decode(data: bytes) -> Any:
    """فك ترميز كائن CBOR الأول مع إرجاع القيمة المهيكلة."""
    cursor = _CborCursor(data)
    return cursor.decode_item()


def cbor_decode_with_offset(data: bytes) -> tuple[Any, int]:
    """فك ترميز كائن CBOR مع إرجاع موضع نهاية البايتات المقروءة (مهم لـ credentialPublicKey متبوعاً بـ extensions)."""
    cursor = _CborCursor(data)
    val = cursor.decode_item()
    return val, cursor.pos


# ==============================================================================
# 2. تهيئة جداول مفاتيح المرور والتحديات ورموز الاسترداد في PostgreSQL / SQLite
# ==============================================================================


def ensure_passkey_tables() -> None:
    """إنشاء جداول WebAuthn Passkeys المتوافقة مع PostgreSQL و SQLite."""
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS owner_passkeys (
                credential_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'owner-dr-majood',
                device_label TEXT NOT NULL,
                public_key_pem TEXT NOT NULL,
                cose_alg INTEGER NOT NULL DEFAULT -7,
                sign_count INTEGER NOT NULL DEFAULT 0,
                aaguid TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
                transports_json TEXT NOT NULL DEFAULT '["internal","hybrid"]',
                rp_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                revoked INTEGER NOT NULL DEFAULT 0,
                revoked_at TEXT
            );

            CREATE TABLE IF NOT EXISTS webauthn_challenges (
                challenge_id TEXT PRIMARY KEY,
                challenge_b64 TEXT NOT NULL,
                ceremony TEXT NOT NULL,
                rp_id TEXT NOT NULL,
                expected_origin TEXT NOT NULL,
                expires_at_epoch INTEGER NOT NULL,
                consumed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS owner_recovery_codes (
                code_id TEXT PRIMARY KEY,
                code_hash TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                used_at TEXT
            );
            """
        )


def get_passkey_rp_config(request: Request | None = None) -> dict[str, Any]:
    """
    تحديد معرّف الطرف المعتمد (RP ID) والأصول المسموح بها مع فرض العزل القاطع عن medinsup.com الأب.
    """
    configured_rp_id = os.getenv("TRILUNAIR_WEBAUTHN_RP_ID", "").strip().lower()
    primary_domain = os.getenv("TRILUNAIR_PRIMARY_DOMAIN", "trilunair.medinsup.com").strip().lower()

    if configured_rp_id == "medinsup.com":
        raise HTTPException(
            status_code=500,
            detail="حظر عزل المنصة: يمنع ضبط TRILUNAIR_WEBAUTHN_RP_ID على النطاق الطبي الأب medinsup.com؛ استخدم trilunair.medinsup.com حصراً.",
        )

    req_origin = ""
    req_host = ""
    if request is not None:
        req_origin = (request.headers.get("origin") or "").strip().rstrip("/")
        req_host = (request.headers.get("host") or "").split(":", 1)[0].strip().lower()

    if configured_rp_id:
        rp_id = configured_rp_id
    elif req_host in {"localhost", "127.0.0.1", "testserver"}:
        rp_id = "localhost" if req_host in {"localhost", "testserver"} else "127.0.0.1"
    elif req_host == primary_domain:
        rp_id = primary_domain
    else:
        env_mode = os.getenv("TRILUNAIR_ENV", "development").strip().lower()
        rp_id = primary_domain if env_mode == "production" else "localhost"

    allowed_origins = {
        f"https://{primary_domain}",
        *[o.rstrip("/") for o in get_allowed_cors_origins()],
    }
    # ضمان عدم السماح أبداً بالنطاق الطبي الأب medinsup.com أو www.medinsup.com
    allowed_origins.discard("https://medinsup.com")
    allowed_origins.discard("http://medinsup.com")
    allowed_origins.discard("https://www.medinsup.com")

    if req_origin and req_origin in allowed_origins:
        effective_origin = req_origin
    elif rp_id == primary_domain:
        effective_origin = f"https://{primary_domain}"
    else:
        effective_origin = "http://localhost:5173"

    return {
        "rpId": rp_id,
        "rpName": "QUANTUM TRILUNAIR — Dr.MaJoOoOoOoD",
        "primaryDomain": primary_domain,
        "isolatedParentDomain": "medinsup.com",
        "effectiveOrigin": effective_origin,
        "allowedOrigins": sorted(allowed_origins),
    }


# ==============================================================================
# 3. تحويل مفاتيح COSE والتحقق التشفيري من بيانات الموثق والتوقيعات
# ==============================================================================


def _cose_key_to_pem_and_alg(cose_map: dict[Any, Any]) -> tuple[str, int]:
    """تحويل مفتاح COSE_Key المستخرج من authData إلى صيغة PEM قياسية للتحقق التشفيري."""
    kty = int(cose_map.get(1, 0))
    alg = int(cose_map.get(3, COSE_ALG_ES256))

    if kty == 2 and alg == COSE_ALG_ES256:  # EC2 P-256
        crv = int(cose_map.get(-1, 0))
        x_bytes = cose_map.get(-2)
        y_bytes = cose_map.get(-3)
        if crv != 1 or not isinstance(x_bytes, bytes) or not isinstance(y_bytes, bytes):
            raise ValueError("Invalid COSE EC2 P-256 public key parameters")
        if len(x_bytes) != 32 or len(y_bytes) != 32:
            raise ValueError("Invalid P-256 coordinate length")
        pub_numbers = ec.EllipticCurvePublicNumbers(
            int.from_bytes(x_bytes, "big"),
            int.from_bytes(y_bytes, "big"),
            ec.SECP256R1(),
        )
        pub_key = pub_numbers.public_key()
        pem = pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        return pem, COSE_ALG_ES256

    if kty == 1 and alg == COSE_ALG_EDDSA:  # OKP Ed25519
        x_bytes = cose_map.get(-2)
        if not isinstance(x_bytes, bytes) or len(x_bytes) != 32:
            raise ValueError("Invalid Ed25519 COSE key")
        pub_key_ed = ed25519.Ed25519PublicKey.from_public_bytes(x_bytes)
        pem = pub_key_ed.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        return pem, COSE_ALG_EDDSA

    if kty == 3 and alg == COSE_ALG_RS256:  # RSA
        n_bytes = cose_map.get(-1)
        e_bytes = cose_map.get(-2)
        if not isinstance(n_bytes, bytes) or not isinstance(e_bytes, bytes):
            raise ValueError("Invalid RSA COSE key")
        pub_numbers_rsa = rsa.RSAPublicNumbers(
            int.from_bytes(e_bytes, "big"),
            int.from_bytes(n_bytes, "big"),
        )
        pub_key_rsa = pub_numbers_rsa.public_key()
        pem = pub_key_rsa.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        return pem, COSE_ALG_RS256

    raise ValueError(f"Unsupported COSE key type/alg combination: kty={kty}, alg={alg}")


def _parse_authenticator_data(auth_data: bytes, expect_attested_cred: bool = False) -> dict[str, Any]:
    """تفكيك بنية authenticatorData الثنائية وفق معيار W3C WebAuthn Level 2."""
    if len(auth_data) < 37:
        raise ValueError("authenticatorData shorter than mandatory 37 bytes")
    rp_id_hash = auth_data[:32]
    flags = auth_data[32]
    sign_count = struct.unpack("!I", auth_data[33:37])[0]

    user_present = bool(flags & 0x01)
    user_verified = bool(flags & 0x04)
    backup_eligible = bool(flags & 0x08)
    backup_state = bool(flags & 0x10)
    attested_cred_present = bool(flags & 0x40)

    result: dict[str, Any] = {
        "rpIdHash": rp_id_hash,
        "flags": flags,
        "userPresent": user_present,
        "userVerified": user_verified,
        "backupEligible": backup_eligible,
        "backupState": backup_state,
        "signCount": sign_count,
    }

    if expect_attested_cred:
        if not attested_cred_present or len(auth_data) < 55:
            raise ValueError("Missing attestedCredentialData in registration authenticatorData")
        aaguid_bytes = auth_data[37:53]
        aaguid_str = str(uuid.UUID(bytes=aaguid_bytes))
        cred_id_len = struct.unpack("!H", auth_data[53:55])[0]
        if len(auth_data) < 55 + cred_id_len + 1:
            raise ValueError("Truncated credentialId in authenticatorData")
        cred_id_bytes = auth_data[55 : 55 + cred_id_len]
        cose_bytes = auth_data[55 + cred_id_len :]
        cose_map, _ = cbor_decode_with_offset(cose_bytes)
        if not isinstance(cose_map, dict):
            raise ValueError("Decoded credentialPublicKey is not a COSE map")
        pem, alg = _cose_key_to_pem_and_alg(cose_map)
        result["aaguid"] = aaguid_str
        result["credentialIdB64"] = b64url_encode(cred_id_bytes)
        result["publicKeyPem"] = pem
        result["coseAlg"] = alg

    return result


def _verify_cose_signature(
    public_key_pem: str,
    cose_alg: int,
    signed_payload: bytes,
    signature_bytes: bytes,
) -> bool:
    """التحقق التشفيري من توقيع WebAuthn (يدعم DER و Raw R||S لـ ES256، بالإضافة إلى EdDSA و RS256)."""
    pub_key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
    try:
        if cose_alg == COSE_ALG_ES256 and isinstance(pub_key, ec.EllipticCurvePublicKey):
            sig_to_verify = signature_bytes
            # في حال أرسل الموثق توقيع P-256 بصيغة 64 بايت خام (r || s) نحوله إلى ASN.1 DER
            if len(signature_bytes) == 64 and signature_bytes[0] != 0x30:
                r_int = int.from_bytes(signature_bytes[:32], "big")
                s_int = int.from_bytes(signature_bytes[32:], "big")
                sig_to_verify = encode_dss_signature(r_int, s_int)
            pub_key.verify(sig_to_verify, signed_payload, ec.ECDSA(hashes.SHA256()))
            return True
        if cose_alg == COSE_ALG_EDDSA and isinstance(pub_key, ed25519.Ed25519PublicKey):
            pub_key.verify(signature_bytes, signed_payload)
            return True
        if cose_alg == COSE_ALG_RS256 and isinstance(pub_key, rsa.RSAPublicKey):
            pub_key.verify(signature_bytes, signed_payload, padding.PKCS1v15(), hashes.SHA256())
            return True
    except InvalidSignature:
        return False
    except Exception:
        return False
    return False


# ==============================================================================
# 4. رموز التصعيد الأمني قصيرة الصلاحية (Step-Up Verification Tokens)
# ==============================================================================


def create_step_up_token(
    auth_method: str,
    credential_id: str | None = None,
    scope: str = "ALL_SENSITIVE_ADMIN",
    ttl_seconds: int = STEP_UP_TTL_SECONDS,
) -> dict[str, Any]:
    """إنشاء رمز تصعيد أمني قصير العمر (5 دقائق) موقع بـ HMAC-SHA256 للعمليات الحساسة."""
    now = int(time.time())
    exp = now + max(60, min(900, ttl_seconds))
    jti = f"stepup_{uuid.uuid4().hex}"
    claims = {
        "typ": "TRILUNAIR_STEP_UP",
        "sub": "OWNER_DR_MAJOOD",
        "amr": auth_method,
        "cred": credential_id or "",
        "scope": scope,
        "jti": jti,
        "iat": now,
        "exp": exp,
    }
    body_b64 = b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(_get_session_signing_key(), body_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return {
        "stepUpToken": f"{body_b64}.{sig}",
        "authMethod": auth_method,
        "expiresAtEpoch": exp,
        "ttlSeconds": exp - now,
    }


def verify_step_up_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    parts = token.strip().split(".")
    if len(parts) != 2:
        return None
    body_b64, sig_hex = parts
    expected = hmac.new(_get_session_signing_key(), body_b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig_hex, expected):
        return None
    try:
        claims = json.loads(b64url_decode(body_b64).decode("utf-8"))
    except Exception:
        return None
    if not isinstance(claims, dict) or claims.get("typ") != "TRILUNAIR_STEP_UP":
        return None
    if int(claims.get("exp", 0)) <= int(time.time()):
        return None
    return claims


# ==============================================================================
# 5. عمليات تسجيل مفاتيح المرور والمصادقة البيومترية وإدارة الأجهزة والاسترداد
# ==============================================================================


def list_registered_passkeys(include_revoked: bool = False) -> list[dict[str, Any]]:
    ensure_passkey_tables()
    with db_session() as conn:
        query = (
            "SELECT credential_id, owner_id, device_label, cose_alg, sign_count, aaguid, "
            "transports_json, rp_id, created_at, last_used_at, revoked, revoked_at "
            "FROM owner_passkeys "
        )
        if not include_revoked:
            query += "WHERE revoked = 0 "
        query += "ORDER BY created_at DESC"
        rows = conn.execute(query).fetchall()

    devices: list[dict[str, Any]] = []
    for r in rows:
        try:
            transports = json.loads(r["transports_json"] or "[]")
        except Exception:
            transports = ["internal"]
        cid = str(r["credential_id"])
        devices.append(
            {
                "credentialId": cid,
                "credentialIdPreview": f"{cid[:10]}...{cid[-6:]}" if len(cid) > 18 else cid,
                "ownerId": str(r["owner_id"]),
                "deviceLabel": str(r["device_label"]),
                "algorithm": (
                    "ES256 (P-256)"
                    if int(r["cose_alg"]) == COSE_ALG_ES256
                    else ("EdDSA (Ed25519)" if int(r["cose_alg"]) == COSE_ALG_EDDSA else "RS256")
                ),
                "signCount": int(r["sign_count"]),
                "aaguid": str(r["aaguid"]),
                "transports": transports,
                "rpId": str(r["rp_id"]),
                "createdAt": str(r["created_at"]),
                "lastUsedAt": r["last_used_at"],
                "revoked": bool(r["revoked"]),
                "revokedAt": r["revoked_at"],
                "biometricTemplateStored": False,
            }
        )
    return devices


def get_passkey_security_posture(request: Request | None = None) -> dict[str, Any]:
    ensure_passkey_tables()
    rp_cfg = get_passkey_rp_config(request)
    active_devices = list_registered_passkeys(include_revoked=False)
    with db_session() as conn:
        rem_row = conn.execute(
            "SELECT COUNT(*) AS c FROM owner_recovery_codes WHERE used = 0"
        ).fetchone()
        remaining_codes = int(rem_row["c"]) if rem_row else 0

    return {
        "webauthnSupported": True,
        "biometricImagesOrTemplatesStored": False,
        "rpId": rp_cfg["rpId"],
        "rpName": rp_cfg["rpName"],
        "primaryDomain": rp_cfg["primaryDomain"],
        "isolatedMedicalDomain": rp_cfg["isolatedParentDomain"],
        "allowedOrigins": rp_cfg["allowedOrigins"],
        "registeredDeviceCount": len(active_devices),
        "remainingRecoveryCodes": remaining_codes,
        "supportedAuthenticators": [
            "Apple iPhone / iPad Face ID (Passkeys)",
            "Apple MacBook Touch ID (Platform Authenticator)",
            "iCloud Keychain Synced Passkeys",
            "FIDO2 / WebAuthn Hardware Security Keys (YubiKey / Titan)",
        ],
        "stepUpRequiredActions": [
            "MODIFY_API_CREDENTIALS",
            "CHANGE_TRADING_AUTHORIZATION_POLICY",
            "EDIT_RISK_PARAMETERS",
            "CHANGE_AGENT_PERMISSIONS",
            "CHANGE_INFRASTRUCTURE_SETTINGS",
            "REVOKE_DEVICE_OR_RECOVERY_ACCESS",
        ],
        "devices": active_devices,
    }


def generate_registration_options(
    device_label: str = "MacBook Pro Touch ID / iPhone Face ID",
    request: Request | None = None,
) -> dict[str, Any]:
    """توليد خيارات تسجيل مفتاح مرور WebAuthn جديدة للمالك الوحيد."""
    ensure_passkey_tables()
    rp_cfg = get_passkey_rp_config(request)
    challenge_bytes = secrets.token_bytes(32)
    challenge_b64 = b64url_encode(challenge_bytes)
    challenge_id = f"chal_{uuid.uuid4().hex}"
    now_epoch = int(time.time())
    now_iso = utc_now_iso()

    existing = list_registered_passkeys(include_revoked=False)
    exclude_credentials = [
        {"type": "public-key", "id": d["credentialId"], "transports": d["transports"]}
        for d in existing
    ]

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO webauthn_challenges (
                challenge_id, challenge_b64, ceremony, rp_id, expected_origin,
                expires_at_epoch, consumed, created_at
            ) VALUES (?, ?, 'registration', ?, ?, ?, 0, ?)
            """,
            (
                challenge_id,
                challenge_b64,
                rp_cfg["rpId"],
                rp_cfg["effectiveOrigin"],
                now_epoch + CHALLENGE_TTL_SECONDS,
                now_iso,
            ),
        )

    owner_handle = b64url_encode(b"owner-dr-majood-trilunair-v1")
    return {
        "challengeId": challenge_id,
        "deviceLabel": device_label,
        "publicKey": {
            "rp": {
                "name": rp_cfg["rpName"],
                "id": rp_cfg["rpId"],
            },
            "user": {
                "id": owner_handle,
                "name": "owner@trilunair.medinsup.com",
                "displayName": "Dr.MaJoOoOoOoD (Owner)",
            },
            "challenge": challenge_b64,
            "pubKeyCredParams": [
                {"type": "public-key", "alg": COSE_ALG_ES256},
                {"type": "public-key", "alg": COSE_ALG_EDDSA},
                {"type": "public-key", "alg": COSE_ALG_RS256},
            ],
            "timeout": CHALLENGE_TTL_SECONDS * 1000,
            "attestation": "none",
            "authenticatorSelection": {
                "residentKey": "preferred",
                "userVerification": "required",
            },
            "excludeCredentials": exclude_credentials,
        },
    }


def _consume_and_validate_challenge(
    challenge_id: str,
    expected_ceremony: str,
    client_data_b64: str,
    allowed_origins: list[str],
) -> tuple[dict[str, Any], bytes]:
    ensure_passkey_tables()
    now_epoch = int(time.time())
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM webauthn_challenges WHERE challenge_id = ?",
            (challenge_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=400, detail="تحدي WebAuthn غير موجود أو غير صالح.")
        if int(row["consumed"]) == 1:
            security_telemetry.emit_event(
                "WEBAUTHN_REPLAY_BLOCKED",
                severity="CRITICAL",
                details={"challengeId": challenge_id, "reason": "CHALLENGE_ALREADY_CONSUMED"},
            )
            raise HTTPException(status_code=403, detail="حظر أمني (Replay): تم استخدام تحدي WebAuthn مسبقاً.")
        if int(row["expires_at_epoch"]) <= now_epoch:
            conn.execute("UPDATE webauthn_challenges SET consumed = 1 WHERE challenge_id = ?", (challenge_id,))
            raise HTTPException(status_code=400, detail="انتهت صلاحية تحدي WebAuthn؛ يرجى طلب تحدٍ جديد.")
        if str(row["ceremony"]) != expected_ceremony:
            raise HTTPException(status_code=400, detail="نوع عملية WebAuthn لا يطابق التحدي المصدر.")

        # إبطال التحدي فوراً لضمان الاستخدام لمرة واحدة فقط (Single-Use Replay Protection)
        conn.execute("UPDATE webauthn_challenges SET consumed = 1 WHERE challenge_id = ?", (challenge_id,))

    raw_client_data = b64url_decode(client_data_b64)
    try:
        client_data = json.loads(raw_client_data.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="تعذر قراءة clientDataJSON.") from exc

    expected_type = "webauthn.create" if expected_ceremony == "registration" else "webauthn.get"
    if client_data.get("type") != expected_type:
        raise HTTPException(status_code=400, detail=f"قيمة clientData.type غير صالحة ({client_data.get('type')}).")

    received_chal = str(client_data.get("challenge") or "").rstrip("=")
    stored_chal = str(row["challenge_b64"]).rstrip("=")
    if not hmac.compare_digest(received_chal, stored_chal):
        security_telemetry.emit_event(
            "WEBAUTHN_CHALLENGE_MISMATCH",
            severity="WARNING",
            details={"challengeId": challenge_id},
        )
        raise HTTPException(status_code=403, detail="فشل التحقق التشفيري: قيمة التحدي (challenge) غير مطابقة.")

    origin = str(client_data.get("origin") or "").strip().rstrip("/")
    if origin in {"https://medinsup.com", "http://medinsup.com", "https://www.medinsup.com"}:
        security_telemetry.emit_event(
            "PLATFORM_ISOLATION_VIOLATION_BLOCKED",
            severity="CRITICAL",
            details={"origin": origin, "reason": "PARENT_MEDICAL_DOMAIN_REJECTED"},
        )
        raise HTTPException(
            status_code=403,
            detail="رفض عزل المنصة: لا يُسمح بمشاركة مصادقة WebAuthn مع النطاق الطبي الأب medinsup.com.",
        )

    valid_origins = set(allowed_origins) | {str(row["expected_origin"]).rstrip("/")}
    if origin not in valid_origins:
        raise HTTPException(
            status_code=403,
            detail=f"رفض أمني: أصل WebAuthn ({origin}) غير مدرج ضمن قائمة النطاقات المسموحة.",
        )

    return dict(row), raw_client_data


def verify_registration_response(
    payload: dict[str, Any],
    request: Request | None = None,
) -> dict[str, Any]:
    """التحقق التشفيري من استجابة تسجيل مفتاح المرور وحفظ المفتاح العام للمالك فقط."""
    rp_cfg = get_passkey_rp_config(request)
    challenge_id = str(payload.get("challengeId") or "").strip()
    device_label = str(payload.get("deviceLabel") or "Owner Passkey Device").strip()[:80]
    cred = payload.get("credential") or {}
    resp = cred.get("response") or {}

    client_data_b64 = str(resp.get("clientDataJSON") or "")
    attestation_b64 = str(resp.get("attestationObject") or "")
    if not challenge_id or not client_data_b64 or not attestation_b64:
        raise HTTPException(status_code=400, detail="بيانات تسجيل مفتاح المرور ناقصة.")

    chal_row, raw_client_data = _consume_and_validate_challenge(
        challenge_id=challenge_id,
        expected_ceremony="registration",
        client_data_b64=client_data_b64,
        allowed_origins=rp_cfg["allowedOrigins"],
    )

    try:
        att_obj = cbor_decode(b64url_decode(attestation_b64))
        if not isinstance(att_obj, dict) or not isinstance(att_obj.get("authData"), bytes):
            raise ValueError("Malformed attestationObject")
        auth_data_bytes: bytes = att_obj["authData"]
        parsed_auth = _parse_authenticator_data(auth_data_bytes, expect_attested_cred=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"فشل تحليل attestationObject: {exc}") from exc

    expected_rp_hash = hashlib.sha256(str(chal_row["rp_id"]).encode("utf-8")).digest()
    if not hmac.compare_digest(parsed_auth["rpIdHash"], expected_rp_hash):
        raise HTTPException(status_code=403, detail="رفض أمني: rpIdHash في بيانات الموثق لا يطابق النطاق المعتمد.")

    if not parsed_auth["userPresent"] or not parsed_auth["userVerified"]:
        raise HTTPException(
            status_code=403,
            detail="يتطلب تسجيل مفتاح المرور التحقق البيومتري الفعلي للمالك (User Verification Required).",
        )

    # إذا تضمنت شهادة الإثبات (attStmt) توقيعاً ذاتياً أو مباشراً بدون x5c نتحقق منه ضد المفتاح المسجل
    att_stmt = att_obj.get("attStmt")
    if isinstance(att_stmt, dict) and isinstance(att_stmt.get("sig"), bytes) and not att_stmt.get("x5c"):
        client_hash = hashlib.sha256(raw_client_data).digest()
        if not _verify_cose_signature(
            parsed_auth["publicKeyPem"],
            parsed_auth["coseAlg"],
            auth_data_bytes + client_hash,
            att_stmt["sig"],
        ):
            raise HTTPException(status_code=403, detail="فشل التحقق التشفيري من توقيع الإثبات الذاتي (Self Attestation).")

    cred_id_b64 = parsed_auth["credentialIdB64"]
    outer_id = str(cred.get("id") or "").strip()
    if outer_id and outer_id != cred_id_b64:
        raise HTTPException(status_code=400, detail="عدم تطابق معرّف الاعتماد (credential.id) مع authData.")

    transports = resp.get("transports")
    if not isinstance(transports, list) or not transports:
        transports = ["internal", "hybrid"]

    now_iso = utc_now_iso()
    with db_session() as conn:
        existing = conn.execute(
            "SELECT credential_id FROM owner_passkeys WHERE credential_id = ?",
            (cred_id_b64,),
        ).fetchone()
        if existing is not None:
            raise HTTPException(status_code=409, detail="معرّف مفتاح المرور هذا مسجل مسبقاً.")

        conn.execute(
            """
            INSERT INTO owner_passkeys (
                credential_id, owner_id, device_label, public_key_pem, cose_alg,
                sign_count, aaguid, transports_json, rp_id, created_at, revoked
            ) VALUES (?, 'owner-dr-majood', ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                cred_id_b64,
                device_label,
                parsed_auth["publicKeyPem"],
                int(parsed_auth["coseAlg"]),
                int(parsed_auth["signCount"]),
                str(parsed_auth["aaguid"]),
                json.dumps([str(t) for t in transports[:6]]),
                str(chal_row["rp_id"]),
                now_iso,
            ),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="WEBAUTHN_PASSKEY",
            action="PASSKEY_DEVICE_REGISTERED",
            severity="INFO",
            details_ar=f"تم تسجيل مفتاح مرور بيومتري جديد للمالك ({device_label}) دون تخزين أي بيانات حيوية.",
            details_en=f"Registered owner FIDO2/WebAuthn passkey ({device_label}); zero biometric templates stored.",
            conn=conn,
        )

    step_up = create_step_up_token(auth_method="WEBAUTHN_PASSKEY_REGISTRATION", credential_id=cred_id_b64)
    return {
        "registered": True,
        "credentialId": cred_id_b64,
        "deviceLabel": device_label,
        "rpId": chal_row["rp_id"],
        "biometricTemplateStored": False,
        "stepUpToken": step_up["stepUpToken"],
        "stepUpExpiresAtEpoch": step_up["expiresAtEpoch"],
    }


def generate_authentication_options(request: Request | None = None) -> dict[str, Any]:
    """توليد تحدي مصادقة أو تصعيد أمني (Biometric Login / Step-Up) لمفاتيح مرور المالك النشطة."""
    ensure_passkey_tables()
    rp_cfg = get_passkey_rp_config(request)
    active_devices = list_registered_passkeys(include_revoked=False)
    if not active_devices:
        raise HTTPException(
            status_code=404,
            detail="لا توجد مفاتيح مرور بيومترية نشطة مسجلة حالياً؛ يرجى تسجيل جهاز المالك أولاً.",
        )

    challenge_b64 = b64url_encode(secrets.token_bytes(32))
    challenge_id = f"chal_{uuid.uuid4().hex}"
    now_epoch = int(time.time())
    now_iso = utc_now_iso()

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO webauthn_challenges (
                challenge_id, challenge_b64, ceremony, rp_id, expected_origin,
                expires_at_epoch, consumed, created_at
            ) VALUES (?, ?, 'authentication', ?, ?, ?, 0, ?)
            """,
            (
                challenge_id,
                challenge_b64,
                rp_cfg["rpId"],
                rp_cfg["effectiveOrigin"],
                now_epoch + CHALLENGE_TTL_SECONDS,
                now_iso,
            ),
        )

    return {
        "challengeId": challenge_id,
        "publicKey": {
            "challenge": challenge_b64,
            "rpId": rp_cfg["rpId"],
            "timeout": CHALLENGE_TTL_SECONDS * 1000,
            "userVerification": "required",
            "allowCredentials": [
                {
                    "type": "public-key",
                    "id": d["credentialId"],
                    "transports": d["transports"],
                }
                for d in active_devices
            ],
        },
    }


def verify_authentication_response(
    payload: dict[str, Any],
    request: Request | None = None,
) -> dict[str, Any]:
    """
    التحقق التشفيري من توقيع مفتاح المرور (Face ID / Touch ID / Security Key)،
    وفحص عداد التوقيع التصاعدي ضد الاستنساخ، ثم إصدار جلسة المالك ورمز Step-Up.
    """
    rp_cfg = get_passkey_rp_config(request)
    challenge_id = str(payload.get("challengeId") or "").strip()
    cred = payload.get("credential") or {}
    cred_id = str(cred.get("id") or "").strip()
    resp = cred.get("response") or {}

    client_data_b64 = str(resp.get("clientDataJSON") or "")
    auth_data_b64 = str(resp.get("authenticatorData") or "")
    sig_b64 = str(resp.get("signature") or "")

    if not challenge_id or not cred_id or not client_data_b64 or not auth_data_b64 or not sig_b64:
        raise HTTPException(status_code=400, detail="حمولة توقيع مفتاح المرور غير مكتملة.")

    chal_row, raw_client_data = _consume_and_validate_challenge(
        challenge_id=challenge_id,
        expected_ceremony="authentication",
        client_data_b64=client_data_b64,
        allowed_origins=rp_cfg["allowedOrigins"],
    )

    with db_session() as conn:
        pk_row = conn.execute(
            "SELECT * FROM owner_passkeys WHERE credential_id = ?",
            (cred_id,),
        ).fetchone()

    if pk_row is None:
        raise HTTPException(status_code=403, detail="مفتاح المرور غير معروف.")
    if int(pk_row["revoked"]) == 1:
        security_telemetry.emit_event(
            "REVOKED_PASSKEY_REJECTED",
            severity="WARNING",
            details={"credentialId": cred_id[:16]},
        )
        raise HTTPException(status_code=403, detail="تم إلغاء صلاحية هذا الجهاز مسبقاً ولا يمكن استخدامه.")

    auth_data_bytes = b64url_decode(auth_data_b64)
    sig_bytes = b64url_decode(sig_b64)

    try:
        parsed_auth = _parse_authenticator_data(auth_data_bytes, expect_attested_cred=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"بيانات authenticatorData غير صالحة: {exc}") from exc

    expected_rp_hash = hashlib.sha256(str(pk_row["rp_id"]).encode("utf-8")).digest()
    if not hmac.compare_digest(parsed_auth["rpIdHash"], expected_rp_hash):
        raise HTTPException(status_code=403, detail="رفض أمني: rpIdHash لا يطابق النطاق المسجل لمفتاح المرور.")

    if not parsed_auth["userPresent"] or not parsed_auth["userVerified"]:
        raise HTTPException(status_code=403, detail="فشل التحقق البيومتري: يشترط تحقق المالك (UV=1, UP=1).")

    client_data_hash = hashlib.sha256(raw_client_data).digest()
    signed_bytes = auth_data_bytes + client_data_hash
    if not _verify_cose_signature(
        str(pk_row["public_key_pem"]),
        int(pk_row["cose_alg"]),
        signed_bytes,
        sig_bytes,
    ):
        security_telemetry.emit_event(
            "ADMIN_AUTH_FAILURE",
            severity="WARNING",
            details={"method": "WEBAUTHN_PASSKEY", "reason": "INVALID_CRYPTOGRAPHIC_SIGNATURE"},
        )
        raise HTTPException(status_code=403, detail="فشل التحقق التشفيري من توقيع مفتاح المرور.")

    prev_count = int(pk_row["sign_count"])
    new_count = int(parsed_auth["signCount"])
    # معيار WebAuthn: إذا كان الموثق يدعم عداد التوقيع (> 0) يجب أن يزداد بشكل رتيب صارم
    if prev_count > 0 and new_count <= prev_count:
        security_telemetry.emit_event(
            "PASSKEY_CLONE_OR_REPLAY_DETECTED",
            severity="CRITICAL",
            details={"credentialId": cred_id[:16], "prevSignCount": prev_count, "newSignCount": new_count},
        )
        append_audit_log(
            actor="SECURITY_SENTINEL",
            source="WEBAUTHN_PASSKEY",
            action="PASSKEY_SIGN_COUNT_ANOMALY_BLOCKED",
            severity="CRITICAL",
            details_ar="رفض مصادقة مفتاح المرور بسبب عدم تزايد عداد التوقيع (اشتباه استنساخ أو إعادة إرسال).",
            details_en=f"Blocked WebAuthn assertion due to non-monotonic signCount ({new_count} <= {prev_count}).",
        )
        raise HTTPException(
            status_code=403,
            detail="حظر أمني حرج: عداد توقيع الموثق غير تصاعدي (حماية ضد الاستنساخ وإعادة الإرسال).",
        )

    now_iso = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            "UPDATE owner_passkeys SET sign_count = ?, last_used_at = ? WHERE credential_id = ?",
            (max(prev_count, new_count), now_iso, cred_id),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="WEBAUTHN_PASSKEY",
            action="PASSKEY_BIOMETRIC_AUTH_VERIFIED",
            severity="INFO",
            details_ar=f"تم التحقق البيومتري للمالك بنجاح عبر الجهاز ({pk_row['device_label']}) وإصدار رمز Step-Up.",
            details_en=f"Verified owner FIDO2 passkey assertion ({pk_row['device_label']}) and issued Step-Up token.",
            conn=conn,
        )

    session = create_admin_session(actor="OWNER_DR_MAJOOD")
    step_up = create_step_up_token(auth_method="WEBAUTHN_PASSKEY", credential_id=cred_id)
    return {
        "authenticated": True,
        "authMethod": "WEBAUTHN_PASSKEY",
        "deviceLabel": str(pk_row["device_label"]),
        "sessionToken": session["sessionToken"],
        "csrfToken": session["csrfToken"],
        "expiresAtEpoch": session["expiresAtEpoch"],
        "ttlSeconds": session["ttlSeconds"],
        "stepUpToken": step_up["stepUpToken"],
        "stepUpExpiresAtEpoch": step_up["expiresAtEpoch"],
        "tradingMode": "PAPER",
        "liveAuthorized": False,
        "executionLockedToPaper": True,
    }


def revoke_passkey_device(credential_id: str, actor: str = "OWNER_DR_MAJOOD") -> dict[str, Any]:
    """إبطال صلاحية جهاز مسجل فوراً وتسجيل العملية في سجل التدقيق غير القابل للتلاعب."""
    ensure_passkey_tables()
    now_iso = utc_now_iso()
    with db_session() as conn:
        row = conn.execute(
            "SELECT device_label, revoked FROM owner_passkeys WHERE credential_id = ?",
            (credential_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="معرّف مفتاح المرور المطلوب إلغاؤه غير موجود.")
        conn.execute(
            "UPDATE owner_passkeys SET revoked = 1, revoked_at = ? WHERE credential_id = ?",
            (now_iso, credential_id),
        )
        append_audit_log(
            actor=actor,
            source="WEBAUTHN_PASSKEY",
            action="PASSKEY_DEVICE_REVOKED",
            severity="WARNING",
            details_ar=f"تم إلغاء صلاحية جهاز مفتاح المرور ({row['device_label']}) نهائياً.",
            details_en=f"Revoked owner WebAuthn passkey device ({row['device_label']}).",
            conn=conn,
        )
    return {"revoked": True, "credentialId": credential_id, "revokedAt": now_iso}


def generate_owner_recovery_codes(count: int = 6) -> dict[str, Any]:
    """
    توليد رموز استرداد طوارئ أحادية الاستخدام عالية الإنتروبيا للمالك:
    تُعرض لمرة واحدة فقط عند التوليد وتُخزن مجزأة بـ PBKDF2-HMAC-SHA256.
    """
    ensure_passkey_tables()
    num_codes = max(4, min(10, count))
    plaintext_codes: list[str] = []
    now_iso = utc_now_iso()

    with db_session() as conn:
        # إبطال أي رموز استرداد قديمة غير مستخدمة عند تدوير حزمة الاسترداد
        conn.execute("DELETE FROM owner_recovery_codes WHERE used = 0")
        for _ in range(num_codes):
            raw_code = f"TRIL-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
            code_hash = hash_admin_secret(raw_code, iterations=120_000)
            conn.execute(
                """
                INSERT INTO owner_recovery_codes (code_id, code_hash, used, created_at)
                VALUES (?, ?, 0, ?)
                """,
                (f"rec_{uuid.uuid4().hex[:12]}", code_hash, now_iso),
            )
            plaintext_codes.append(raw_code)

        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="ACCOUNT_RECOVERY",
            action="RECOVERY_CODES_ROTATED",
            severity="WARNING",
            details_ar=f"تم توليد وتدوير {num_codes} رموز استرداد طوارئ مشفرة أحادية الاستخدام للمالك.",
            details_en=f"Generated and rotated {num_codes} PBKDF2-hashed one-time owner recovery codes.",
            conn=conn,
        )

    return {
        "generatedCount": num_codes,
        "recoveryCodesOnceOnly": plaintext_codes,
        "storedPlaintext": False,
        "hashAlgorithm": "PBKDF2-HMAC-SHA256",
        "warningAr": "احفظ رموز الاسترداد في خزنة مشفرة خارجية الآن؛ لن يتم عرضها مجدداً وتُستهلك لمرة واحدة فقط.",
        "warningEn": "Store these one-time recovery codes in an offline password vault immediately; they are never stored in plaintext.",
    }


def redeem_owner_recovery_code(candidate_code: str) -> dict[str, Any]:
    """استخدام رمز استرداد طوارئ لمرة واحدة عند فقدان الجهاز البيومتري لإصدار جلسة استرداد ورمز Step-Up."""
    ensure_passkey_tables()
    cleaned = (candidate_code or "").strip().upper()
    if len(cleaned) < 16:
        raise HTTPException(status_code=403, detail="رمز الاسترداد غير صالح.")

    now_iso = utc_now_iso()
    matched_id: str | None = None

    with db_session() as conn:
        rows = conn.execute(
            "SELECT code_id, code_hash FROM owner_recovery_codes WHERE used = 0"
        ).fetchall()
        for r in rows:
            parts = str(r["code_hash"]).split("$")
            if len(parts) != 4:
                continue
            _, iter_s, salt_hex, digest_hex = parts
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                cleaned.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iter_s),
            )
            if hmac.compare_digest(derived, bytes.fromhex(digest_hex)):
                matched_id = str(r["code_id"])
                break

        if matched_id is None:
            security_telemetry.emit_event(
                "ADMIN_AUTH_FAILURE",
                severity="WARNING",
                details={"method": "RECOVERY_CODE", "reason": "INVALID_OR_USED_RECOVERY_CODE"},
            )
            raise HTTPException(status_code=403, detail="رمز الاسترداد غير صحيح أو تم استهلاكه مسبقاً.")

        conn.execute(
            "UPDATE owner_recovery_codes SET used = 1, used_at = ? WHERE code_id = ?",
            (now_iso, matched_id),
        )
        append_audit_log(
            actor="OWNER_DR_MAJOOD",
            source="ACCOUNT_RECOVERY",
            action="RECOVERY_CODE_REDEEMED",
            severity="CRITICAL",
            details_ar="تم استرداد وصول المالك باستخدام رمز طوارئ أحادي الاستخدام وإبطاله فوراً.",
            details_en=f"Redeemed and invalidated one-time owner recovery code ({matched_id}).",
            conn=conn,
        )

    session = create_admin_session(actor="OWNER_RECOVERY")
    step_up = create_step_up_token(auth_method="ONE_TIME_RECOVERY_CODE", credential_id=matched_id)
    return {
        "authenticated": True,
        "authMethod": "ONE_TIME_RECOVERY_CODE",
        "sessionToken": session["sessionToken"],
        "csrfToken": session["csrfToken"],
        "expiresAtEpoch": session["expiresAtEpoch"],
        "ttlSeconds": session["ttlSeconds"],
        "stepUpToken": step_up["stepUpToken"],
        "stepUpExpiresAtEpoch": step_up["expiresAtEpoch"],
        "tradingMode": "PAPER",
        "liveAuthorized": False,
        "executionLockedToPaper": True,
    }
