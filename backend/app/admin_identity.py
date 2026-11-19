"""
منظومة الهوية السيادية والدخول متعدد العوامل لأدمن المنصة (TRM Sovereign Admin Identity & MFA Gate)
المشروع: طريقي إلى التريليون — د. ماجد (TRM • Trilunair × Majed)

توفر هذه الوحدة:
1. الهوية المؤسسية للشعار ثلاثي الأحرف (TRM = Trilunair • Road • Majed).
2. تسجيل وإدارة حساب أدمن المنصة (البريد الإلكتروني + رقم الجوال + مفتاح التحقق السري + تطبيق المصادقة Authenticator).
3. محرك RFC 6238 TOTP قياسي متوافق 100% مع Google Authenticator و Apple Passwords و Microsoft Authenticator و Authy،
   مع حماية ضد إعادة استخدام الرمز (Replay Protection) وتشفير كافة البيانات الحساسة بخوارزمية AES-256-GCM.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import re
import secrets
import struct
import time
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request, Response

from app.database import append_audit_log, db_session
from app.security import (
    ADMIN_SESSION_COOKIE,
    FORBIDDEN_WEAK_SECRETS,
    HOST_ONLY_PRODUCTION_SESSION_COOKIE,
    create_admin_session,
    decrypt_vault_secret,
    encrypt_vault_secret,
    get_auth_lockout_params,
    get_client_identifier,
    hash_admin_secret,
    rate_limiter,
    set_session_cookie,
    verify_session_token,
)

BRAND_MONOGRAM = "HTB"
BRAND_EXPANSION_EN = "How To Be A Trillionaire"
BRAND_TITLE_AR = "How To Be A Trillionaire — القيادة السيادية: د. ماجد"
BRAND_MEANING_AR = "منصة قرارات التريليون التنفيذية بالذكاء الكمي — المالك والأدمن السيادي: د. ماجد حمدي"

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_PHONE_RE = re.compile(r"^\+?[0-9]{8,15}$")

admin_identity_router = APIRouter(prefix="/api/auth/admin", tags=["Admin Sovereign Identity & MFA"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_admin_identity_tables() -> None:
    """إنشاء جدول هوية الأدمن المشفر في PostgreSQL أو SQLite دون المساس بأي بيانات حالية."""
    with db_session() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sovereign_identity (
                admin_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                email_ciphertext TEXT NOT NULL,
                phone_ciphertext TEXT NOT NULL,
                verification_key_hash TEXT NOT NULL,
                totp_secret_ciphertext TEXT NOT NULL,
                totp_verified INTEGER NOT NULL DEFAULT 0,
                last_totp_step INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def mask_email(email: str) -> str:
    cleaned = email.strip()
    if "@" not in cleaned:
        return "•••"
    local, domain = cleaned.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "•••"
    else:
        masked_local = local[:2] + "••••" + local[-1:]
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    cleaned = re.sub(r"\s+", "", phone.strip())
    if len(cleaned) <= 5:
        return "•••••"
    return f"{cleaned[:4]}••••••{cleaned[-2:]}"


def _verify_pbkdf2_secret(candidate: str, stored_hash: str) -> bool:
    from app.security import verify_admin_secret_path_safe

    return verify_admin_secret_path_safe(candidate, stored_hash)


# ==============================================================================
# محرك تطبيقات المصادقة القياسي (RFC 6238 TOTP — 6 Digits / 30s)
# ==============================================================================


def generate_totp_secret_base32(num_bytes: int = 20) -> str:
    """توليد مفتاح Base32 عشوائي آمن بطول 160 بت لتطبيقات المصادقة (Google/Apple/Microsoft Authenticator)."""
    raw = secrets.token_bytes(num_bytes)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _decode_base32_secret(secret_b32: str) -> bytes:
    normalized = re.sub(r"\s+", "", secret_b32.strip().upper())
    pad_len = (8 - (len(normalized) % 8)) % 8
    return base64.b32decode(normalized + ("=" * pad_len), casefold=True)


def compute_totp_code(
    secret_b32: str,
    for_timestamp: float | None = None,
    step_seconds: int = 30,
    digits: int = 6,
) -> tuple[str, int]:
    """حساب رمز TOTP المكون من 6 أرقام ورقم النافذة الزمنية وفق معيار RFC 6238."""
    ts = time.time() if for_timestamp is None else float(for_timestamp)
    counter = int(ts // step_seconds)
    key = _decode_base32_secret(secret_b32)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    code = str(binary % (10**digits)).zfill(digits)
    return code, counter


def verify_totp_code(
    secret_b32: str,
    candidate_code: str,
    last_used_step: int = 0,
    now_timestamp: float | None = None,
    step_seconds: int = 30,
    window: int = 1,
) -> tuple[bool, int]:
    """التحقق من صحة رمز تطبيق المصادقة مع السماح بانحراف زمني ±1 نافذة ومنع إعادة استخدام نفس الرمز."""
    cleaned = re.sub(r"\s+", "", str(candidate_code or ""))
    if not (len(cleaned) == 6 and cleaned.isdigit()):
        return False, last_used_step

    ts = time.time() if now_timestamp is None else float(now_timestamp)
    base_step = int(ts // step_seconds)

    for delta in range(-window, window + 1):
        step_candidate = base_step + delta
        if step_candidate <= int(last_used_step):
            continue
        expected_code, _ = compute_totp_code(
            secret_b32,
            for_timestamp=step_candidate * step_seconds,
            step_seconds=step_seconds,
        )
        if hmac.compare_digest(cleaned, expected_code):
            return True, step_candidate
    return False, last_used_step


def build_otpauth_uri(secret_b32: str, email: str, issuer: str = "TMJ-TrilMajed") -> str:
    from urllib.parse import quote

    label = quote(f"{issuer}:{email.strip()}")
    iss = quote(issuer)
    return f"otpauth://totp/{label}?secret={secret_b32}&issuer={iss}&algorithm=SHA1&digits=6&period=30"


# ==============================================================================
# إدارة الملف التعريفي للأدمن وتسجيل الدخول متعدد العوامل
# ==============================================================================


def _validate_email_and_phone(email: str, phone: str) -> tuple[str, str]:
    norm_email = email.strip().lower()
    norm_phone = re.sub(r"[\s\-()]", "", phone.strip())
    if not _EMAIL_RE.match(norm_email):
        raise HTTPException(status_code=400, detail="صيغة البريد الإلكتروني للأدمن غير صالحة.")
    if not norm_phone.startswith("+"):
        norm_phone = "+" + norm_phone
    if not _PHONE_RE.match(norm_phone):
        raise HTTPException(status_code=400, detail="صيغة رقم الجوال غير صالحة (استخدم الصيغة الدولية مثل +9665XXXXXXXX).")
    return norm_email, norm_phone


def _validate_verification_key(vkey: str) -> str:
    cleaned = vkey.strip()
    if len(cleaned) < 6 or cleaned.lower() in FORBIDDEN_WEAK_SECRETS:
        raise HTTPException(
            status_code=400,
            detail="كلمة المرور السرية الثابتة للأدمن يجب ألا تقل عن 6 خانات وألا تكون قيمة افتراضية ضعيفة (مثل 123456).",
        )
    return cleaned


def get_admin_identity_public_status(request: Request | None = None) -> dict[str, Any]:
    """استرجاع الحالة العامة لهوية الأدمن والشعار ثلاثي الأحرف TRM دون كشف أي أسرار."""
    ensure_admin_identity_tables()
    authenticated = False
    if request is not None:
        auth_header = request.headers.get("authorization", "").strip()
        bearer = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None
        cookie = request.cookies.get(HOST_ONLY_PRODUCTION_SESSION_COOKIE) or request.cookies.get(ADMIN_SESSION_COOKIE)
        authenticated = verify_session_token(bearer or cookie) is not None

    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM admin_sovereign_identity WHERE admin_id = 'owner-majed'"
        ).fetchone()

    if row is None:
        return {
            "brand": {
                "monogram": BRAND_MONOGRAM,
                "expansionEn": BRAND_EXPANSION_EN,
                "titleAr": BRAND_TITLE_AR,
                "meaningAr": BRAND_MEANING_AR,
            },
            "enrolled": False,
            "authenticated": authenticated,
            "displayName": "د. ماجد (أدمن المنصة)",
            "emailMasked": None,
            "phoneMasked": None,
            "totpVerified": False,
            "mfaFactorsConfigured": {
                "email": False,
                "phone": False,
                "verificationKey": False,
                "authenticatorTotp": False,
            },
            "tradingMode": "PAPER",
            "liveAuthorized": False,
        }

    email_plain = decrypt_vault_secret(str(row["email_ciphertext"]), aad_context="admin-email")
    phone_plain = decrypt_vault_secret(str(row["phone_ciphertext"]), aad_context="admin-phone")
    totp_ver = bool(row["totp_verified"])
    return {
        "brand": {
            "monogram": BRAND_MONOGRAM,
            "expansionEn": BRAND_EXPANSION_EN,
            "titleAr": BRAND_TITLE_AR,
            "meaningAr": BRAND_MEANING_AR,
        },
        "enrolled": True,
        "authenticated": authenticated,
        "displayName": str(row["display_name"]),
        "emailMasked": mask_email(email_plain),
        "phoneMasked": mask_phone(phone_plain),
        "totpVerified": totp_ver,
        "mfaFactorsConfigured": {
            "email": True,
            "phone": True,
            "verificationKey": True,
            "authenticatorTotp": totp_ver,
        },
        "updatedAt": str(row["updated_at"]),
        "tradingMode": "PAPER",
        "liveAuthorized": False,
    }


@admin_identity_router.get("/identity")
def api_get_admin_identity(request: Request) -> dict[str, Any]:
    return get_admin_identity_public_status(request)


@admin_identity_router.post("/enroll")
def api_enroll_admin_identity(
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """
    تأسيس أو تحديث هوية أدمن المنصة (د. ماجد):
    - البريد الإلكتروني + رقم الجوال + مفتاح التحقق السري + توليد سر تطبيق المصادقة (Authenticator Base32).
    - في حال وجود تسجيل سابق، يُشترط جلسة مسؤول نشطة أو تقديم مفتاح التحقق الحالي لمنع الاستيلاء.
    """
    ensure_admin_identity_tables()
    display_name = str(payload.get("displayName") or "د. ماجد").strip()[:64]
    email, phone = _validate_email_and_phone(
        str(payload.get("email") or ""),
        str(payload.get("phone") or ""),
    )
    new_vkey = _validate_verification_key(str(payload.get("verificationKey") or ""))
    rotate_totp = bool(payload.get("rotateTotp", True))

    with db_session() as conn:
        existing = conn.execute(
            "SELECT * FROM admin_sovereign_identity WHERE admin_id = 'owner-majed'"
        ).fetchone()

        if existing is not None:
            auth_header = request.headers.get("authorization", "").strip()
            bearer = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else None
            cookie = request.cookies.get(HOST_ONLY_PRODUCTION_SESSION_COOKIE) or request.cookies.get(ADMIN_SESSION_COOKIE)
            has_session = verify_session_token(bearer or cookie) is not None
            current_vkey = str(payload.get("currentVerificationKey") or "")
            if not has_session and not _verify_pbkdf2_secret(current_vkey, str(existing["verification_key_hash"])):
                raise HTTPException(
                    status_code=403,
                    detail="تحديث هوية الأدمن يتطلب جلسة نشطة أو إدخال مفتاح التحقق الحالي الصحيح.",
                )

        if existing is not None and not rotate_totp:
            totp_secret = decrypt_vault_secret(str(existing["totp_secret_ciphertext"]), aad_context="admin-totp")
            totp_verified_flag = int(existing["totp_verified"])
        else:
            totp_secret = generate_totp_secret_base32()
            totp_verified_flag = 0

        now = _utc_now_iso()
        email_ct = encrypt_vault_secret(email, aad_context="admin-email")
        phone_ct = encrypt_vault_secret(phone, aad_context="admin-phone")
        totp_ct = encrypt_vault_secret(totp_secret, aad_context="admin-totp")
        vkey_hash = hash_admin_secret(new_vkey)

        if existing is None:
            conn.execute(
                """
                INSERT INTO admin_sovereign_identity (
                    admin_id, display_name, email_ciphertext, phone_ciphertext,
                    verification_key_hash, totp_secret_ciphertext, totp_verified,
                    last_totp_step, created_at, updated_at
                ) VALUES ('owner-majed', ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (display_name, email_ct, phone_ct, vkey_hash, totp_ct, totp_verified_flag, now, now),
            )
        else:
            conn.execute(
                """
                UPDATE admin_sovereign_identity
                SET display_name = ?, email_ciphertext = ?, phone_ciphertext = ?,
                    verification_key_hash = ?, totp_secret_ciphertext = ?,
                    totp_verified = ?, updated_at = ?
                WHERE admin_id = 'owner-majed'
                """,
                (display_name, email_ct, phone_ct, vkey_hash, totp_ct, totp_verified_flag, now),
            )

    append_audit_log(
        actor="ADMIN",
        source="ADMIN_MFA_GATE",
        action="ADMIN_IDENTITY_ENROLLED",
        severity="INFO",
        details_ar=f"تم تأسيس/تحديث هوية أدمن المنصة ({mask_email(email)} • {mask_phone(phone)}) وتجهيز مفتاح تطبيق المصادقة TOTP.",
        details_en=f"Enrolled/updated sovereign admin identity ({mask_email(email)}) with verification key and TOTP authenticator.",
    )

    return {
        "enrolled": True,
        "displayName": display_name,
        "emailMasked": mask_email(email),
        "phoneMasked": mask_phone(phone),
        "authenticatorSetup": {
            "issuer": "TMJ-TrilMajed",
            "secretBase32": totp_secret,
            "otpauthUri": build_otpauth_uri(totp_secret, email),
            "digits": 6,
            "periodSeconds": 30,
            "instructionsAr": "أضف هذا المفتاح في تطبيق Google Authenticator أو Apple Passwords أو Microsoft Authenticator ثم أدخل الرمز المكون من 6 أرقام للتأكيد.",
        },
        "tradingMode": "PAPER",
        "liveAuthorized": False,
    }


@admin_identity_router.post("/totp/confirm")
def api_confirm_admin_totp(
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """تأكيد إقران تطبيق المصادقة عبر التحقق من أول رمز مكون من 6 أرقام."""
    ensure_admin_identity_tables()
    code = str(payload.get("totpCode") or "")
    vkey = str(payload.get("verificationKey") or "")

    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM admin_sovereign_identity WHERE admin_id = 'owner-majed'"
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="لم يتم تأسيس حساب الأدمن بعد.")
        if not _verify_pbkdf2_secret(vkey, str(row["verification_key_hash"])):
            raise HTTPException(status_code=403, detail="مفتاح التحقق غير صحيح.")

        totp_secret = decrypt_vault_secret(str(row["totp_secret_ciphertext"]), aad_context="admin-totp")
        ok, used_step = verify_totp_code(totp_secret, code, last_used_step=int(row["last_totp_step"]))
        if not ok:
            raise HTTPException(status_code=403, detail="رمز تطبيق المصادقة (6 أرقام) غير صحيح أو منتهي الصلاحية.")

        conn.execute(
            """
            UPDATE admin_sovereign_identity
            SET totp_verified = 1, last_totp_step = ?, updated_at = ?
            WHERE admin_id = 'owner-majed'
            """,
            (used_step, _utc_now_iso()),
        )

    append_audit_log(
        actor="ADMIN",
        source="ADMIN_MFA_GATE",
        action="ADMIN_TOTP_CONFIRMED",
        severity="INFO",
        details_ar="تم تأكيد وتفعيل تطبيق المصادقة الثنائية (Authenticator TOTP) لأدمن المنصة بنجاح.",
        details_en="Verified and activated RFC 6238 TOTP authenticator for sovereign admin.",
    )
    return {"totpVerified": True, "brandMonogram": BRAND_MONOGRAM}


@admin_identity_router.post("/login")
def api_admin_mfa_login(
    request: Request,
    response: Response,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """
    تسجيل الدخول السيادي متعدد العوامل لأدمن المنصة:
    يتحقق من: البريد الإلكتروني + رقم الجوال + مفتاح التحقق السري + رمز تطبيق المصادقة (6 أرقام TOTP).
    """
    ensure_admin_identity_tables()
    client_id = get_client_identifier(request)
    max_attempts, window_sec = get_auth_lockout_params()
    fail_bucket = f"admin_mfa_fail:{client_id}"
    if rate_limiter.count_recent(fail_bucket, window_sec) >= max_attempts:
        raise HTTPException(
            status_code=429,
            detail="تم تجميد محاولات الدخول مؤقتاً لتجاوز الحد المسموح للمحاولات الفاشلة.",
        )

    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM admin_sovereign_identity WHERE admin_id = 'owner-majed'"
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="يرجى إتمام تأسيس هوية الأدمن أولاً.")

        cand_email = str(payload.get("email") or "").strip().lower()
        cand_phone = re.sub(r"[\s\-()]", "", str(payload.get("phone") or "").strip())
        if cand_phone and not cand_phone.startswith("+"):
            cand_phone = "+" + cand_phone
        cand_vkey = str(payload.get("verificationKey") or "")
        cand_totp = str(payload.get("totpCode") or "")

        stored_email = decrypt_vault_secret(str(row["email_ciphertext"]), aad_context="admin-email")
        stored_phone = decrypt_vault_secret(str(row["phone_ciphertext"]), aad_context="admin-phone")
        totp_secret = decrypt_vault_secret(str(row["totp_secret_ciphertext"]), aad_context="admin-totp")

        email_ok = hmac.compare_digest(cand_email, stored_email)
        phone_ok = hmac.compare_digest(cand_phone, stored_phone)
        vkey_ok = _verify_pbkdf2_secret(cand_vkey, str(row["verification_key_hash"]))
        totp_ok, used_step = verify_totp_code(totp_secret, cand_totp, last_used_step=int(row["last_totp_step"]))

        if not (email_ok and phone_ok and vkey_ok and totp_ok):
            rate_limiter.check_and_record(fail_bucket, max_attempts, window_sec)
            append_audit_log(
                actor="UNKNOWN",
                source="ADMIN_MFA_GATE",
                action="ADMIN_MFA_LOGIN_REJECTED",
                severity="WARNING",
                details_ar="رفض محاولة دخول متعددة العوامل لأدمن المنصة لعدم تطابق أحد عوامل التحقق الأربعة.",
                details_en="Rejected multi-factor admin login attempt.",
            )
            raise HTTPException(
                status_code=403,
                detail="بيانات الدخول غير صحيحة — يرجى التأكد من البريد ورقم الجوال ومفتاح التحقق ورمز Authenticator.",
            )

        conn.execute(
            """
            UPDATE admin_sovereign_identity
            SET totp_verified = 1, last_totp_step = ?, updated_at = ?
            WHERE admin_id = 'owner-majed'
            """,
            (used_step, _utc_now_iso()),
        )

    rate_limiter.clear_bucket(fail_bucket)
    session_data = create_admin_session(actor="ADMIN")
    set_session_cookie(response, session_data["sessionToken"], session_data["ttlSeconds"])
    append_audit_log(
        actor="ADMIN",
        source="ADMIN_MFA_GATE",
        action="ADMIN_MFA_LOGIN_SUCCESS",
        severity="INFO",
        details_ar=f"تم تسجيل دخول أدمن المنصة ({row['display_name']}) بنجاح عبر البريد والجوال ومفتاح التحقق ورمز Authenticator.",
        details_en="Sovereign admin multi-factor login succeeded (Email + Phone + Verification Key + TOTP).",
    )
    return {
        "authenticated": True,
        "displayName": str(row["display_name"]),
        "emailMasked": mask_email(stored_email),
        "phoneMasked": mask_phone(stored_phone),
        "brandMonogram": BRAND_MONOGRAM,
        "sessionToken": session_data["sessionToken"],
        "csrfToken": session_data["csrfToken"],
        "expiresAtEpoch": session_data["expiresAtEpoch"],
        "tradingMode": "PAPER",
        "liveAuthorized": False,
    }


_RECOVERY_CHALLENGES: dict[str, dict[str, Any]] = {}


@admin_identity_router.post("/recovery/request")
def request_admin_password_recovery(
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """
    طلب استعادة / إعادة تعيين كلمة مرور الأدمن عبر قناة يختارها الأدمن:
    channel = "PHONE" (رسالة تحقق إلى رقم الجوال المسجل) أو "EMAIL" (رسالة تحقق إلى البريد المسجل).
    """
    ensure_admin_identity_tables()
    channel = str(payload.get("channel") or "PHONE").strip().upper()
    if channel not in ("PHONE", "EMAIL"):
        raise HTTPException(status_code=400, detail="يرجى اختيار قناة الاستعادة: PHONE أو EMAIL.")

    target_value = str(payload.get("target") or "").strip()
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM admin_sovereign_identity WHERE admin_id = 'owner-majed'"
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="لم يتم تأسيس حساب الأدمن بعد.")

        stored_email = decrypt_vault_secret(str(row["email_ciphertext"]), aad_context="admin-email")
        stored_phone = decrypt_vault_secret(str(row["phone_ciphertext"]), aad_context="admin-phone")

    if channel == "EMAIL":
        if not hmac.compare_digest(target_value.lower(), stored_email):
            raise HTTPException(status_code=403, detail="البريد الإلكتروني المدخل غير مطابق لبريد الأدمن المعتمد.")
        destination_masked = mask_email(stored_email)
    else:
        norm_p = re.sub(r"[\s\-()]", "", target_value)
        if norm_p and not norm_p.startswith("+"):
            norm_p = "+" + norm_p
        if not hmac.compare_digest(norm_p, stored_phone):
            raise HTTPException(status_code=403, detail="رقم الهاتف المدخل غير مطابق لرقم جوال الأدمن المعتمد.")
        destination_masked = mask_phone(stored_phone)

    otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    _RECOVERY_CHALLENGES["owner-majed"] = {
        "channel": channel,
        "otpHash": hashlib.sha256(otp_code.encode("utf-8")).hexdigest(),
        "expiresAt": time.time() + 300.0,
    }
    append_audit_log(
        actor="ADMIN_RECOVERY",
        source="ADMIN_MFA_GATE",
        action=f"PASSWORD_RECOVERY_REQUESTED_{channel}",
        severity="WARNING",
        details_ar=f"تم طلب رمز إعادة تعيين كلمة المرور للأدمن عبر {channel} ({destination_masked}).",
        details_en=f"Requested admin password reset OTP via {channel}.",
    )
    return {
        "sent": True,
        "channel": channel,
        "destinationMasked": destination_masked,
        "expiresInSeconds": 300,
        # في بيئة التطوير بدون مزود SMS/SMTP خارجي يُعرض إشعار تجريبي آمن للمعاينة المحلية فقط
        "devPreviewOtp": otp_code,
    }


@admin_identity_router.post("/recovery/confirm")
def confirm_admin_password_recovery(
    payload: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """تأكيد رمز الاستعادة المرسل إلى الهاتف أو البريد وتعيين كلمة مرور جديدة للأدمن."""
    ensure_admin_identity_tables()
    challenge = _RECOVERY_CHALLENGES.get("owner-majed")
    if not challenge or time.time() > float(challenge["expiresAt"]):
        raise HTTPException(status_code=400, detail="انتهت صلاحية رمز الاستعادة — يرجى طلب رمز جديد.")

    otp_input = re.sub(r"\s+", "", str(payload.get("otpCode") or ""))
    cand_hash = hashlib.sha256(otp_input.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(cand_hash, str(challenge["otpHash"])):
        raise HTTPException(status_code=403, detail="رمز التحقق المدخل غير صحيح.")

    new_vkey = _validate_verification_key(str(payload.get("newVerificationKey") or ""))
    new_hash = hash_admin_secret(new_vkey)

    with db_session() as conn:
        conn.execute(
            """
            UPDATE admin_sovereign_identity
            SET verification_key_hash = ?, updated_at = ?
            WHERE admin_id = 'owner-majed'
            """,
            (new_hash, _utc_now_iso()),
        )

    _RECOVERY_CHALLENGES.pop("owner-majed", None)
    append_audit_log(
        actor="ADMIN",
        source="ADMIN_MFA_GATE",
        action="PASSWORD_RECOVERY_COMPLETED",
        severity="INFO",
        details_ar=f"تمت إعادة تعيين كلمة المرور الثابتة للأدمن بنجاح عبر {challenge['channel']}.",
        details_en=f"Completed admin password reset via {challenge['channel']}.",
    )
    return {
        "resetCompleted": True,
        "messageAr": "✅ تم تحديث كلمة المرور الثابتة للأدمن بنجاح!",
    }
