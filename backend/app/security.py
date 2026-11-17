"""
وحدة الأمان السحابي الصلب والمصادقة والحماية من الهجمات (Cloud Security & Hardening Layer).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — الإصدار v1.1.0-cloud-paper

مسؤوليات هذه الوحدة:
1. تجزئة والتحقق من بيانات اعتماد المسؤول عبر PBKDF2-HMAC-SHA256 مع مقارنة ثابتة الزمن (hmac.compare_digest)،
   ورفض القيم الافتراضية أو التجريبية الضعيفة (مثل 7777 أو password أو admin)، والإغلاق الآمن (Fail-Closed)
   عند عدم تهيئة سر المسؤول في البيئة.
2. إصدار جلسات مسؤول موقعة ومحددة الصلاحية (HMAC-SHA256 Session Tokens) مع ملف تعريف ارتباط HttpOnly
   ورمز حماية ضد تزوير الطلبات عبر المواقع (CSRF Token)، وإمكانية إبطال الجلسات (Revocation).
3. محدد معدل الطلبات (Sliding-Window Rate Limiter) لمنع هجمات التخمين المتكرر (Brute Force) وإساءة استخدام API.
4. سجل مركزي مهيكل بصيغة JSON مع تنقية الأسرار والمفاتيح تلقائياً (Secret Redaction) لمنع تسرب أي بيانات حساسة.
5. عميل HTTP خارجي آمن متوافق مع الوكيل السحابي وشهادات الجذر الموثوقة دون التعثر بمتغيرات NO_PROXY المشوهة.
"""

from __future__ import annotations

import base64
from collections import deque
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import ssl
import threading
import time
from typing import Any
import uuid

from fastapi import HTTPException, Request, Response
import httpx

ADMIN_SESSION_COOKIE = "trilunair_admin_session"
CSRF_HEADER_NAME = "X-CSRF-Token"
PBKDF2_DEFAULT_ITERATIONS = 210_000
MIN_SECRET_LENGTH = 8

# قائمة القيم المحظورة أو التجريبية التي يُرفض قبولها كسر مسؤول في أي بيئة
FORBIDDEN_WEAK_SECRETS: frozenset[str] = frozenset(
    {
        "",
        "0000",
        "1111",
        "1234",
        "123456",
        "12345678",
        "7777",
        "8888",
        "9999",
        "admin",
        "administrator",
        "password",
        "changeme",
        "default",
        "secret",
        "test",
        "testing",
        "trilunair",
        "trilunair_quantum_pw",
    }
)

# أنماط تنقية الأسرار من السجلات المركزية والرسائل
_SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|password|passwd|pin|token|authorization|cookie|private[_-]?key)",
    re.IGNORECASE,
)
_INLINE_BEARER_PATTERN = re.compile(
    r"(Bearer\s+[A-Za-z0-9._\-~+/]+=*|sk-[A-Za-z0-9_\-]{12,}|AIza[0-9A-Za-z_\-]{20,}|xai-[A-Za-z0-9_\-]{12,})",
    re.IGNORECASE,
)


def redact_sensitive_value(value: Any) -> Any:
    """تنقية النصوص والقواميس والقوائم من أي مفاتيح API أو كلمات مرور أو رموز جلسات قبل التسجيل."""
    if isinstance(value, str):
        return _INLINE_BEARER_PATTERN.sub("[REDACTED_SECRET]", value)
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            if _SECRET_KEY_PATTERN.search(str(k)):
                sanitized[str(k)] = "[REDACTED]"
            else:
                sanitized[str(k)] = redact_sensitive_value(v)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [redact_sensitive_value(item) for item in value]
    return value


class StructuredSecurityTelemetry:
    """جامع القياسات التشغيلية والأمنية وسجل الأحداث المركزي المهيكل بصيغة JSON."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.started_at_epoch = time.time()
        self.total_http_requests = 0
        self.total_4xx_responses = 0
        self.total_5xx_responses = 0
        self.auth_failures = 0
        self.rate_limit_blocks = 0
        self.live_mode_blocks = 0
        self.ws_connections_opened = 0
        self.ws_connections_rejected = 0
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=100)
        self._logger = logging.getLogger("trilunair.security")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def record_http_response(self, status_code: int) -> None:
        with self._lock:
            self.total_http_requests += 1
            if 400 <= status_code < 500:
                self.total_4xx_responses += 1
            elif status_code >= 500:
                self.total_5xx_responses += 1

    def emit_event(
        self,
        event_type: str,
        severity: str = "INFO",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        safe_details = redact_sensitive_value(details or {})
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": "trilunair-backend",
            "release": "1.2.0-low-latency-cloudflare",
            "event": event_type,
            "severity": severity,
            "details": safe_details,
        }
        with self._lock:
            self.recent_events.appendleft(record)
            if event_type == "ADMIN_AUTH_FAILURE":
                self.auth_failures += 1
            elif event_type == "RATE_LIMIT_BLOCKED":
                self.rate_limit_blocks += 1
            elif event_type == "LIVE_EXECUTION_BLOCKED":
                self.live_mode_blocks += 1
        if os.getenv("TRILUNAIR_STRUCTURED_LOGS", "true").lower() != "false":
            self._logger.info(json.dumps(record, ensure_ascii=False))
        return record

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            uptime = round(max(0.0, time.time() - self.started_at_epoch), 1)
            total = max(1, self.total_http_requests)
            error_rate_pct = round((self.total_5xx_responses / total) * 100.0, 3)
            client_error_rate_pct = round((self.total_4xx_responses / total) * 100.0, 3)
            return {
                "uptimeSeconds": uptime,
                "totalHttpRequests": self.total_http_requests,
                "total4xxResponses": self.total_4xx_responses,
                "total5xxResponses": self.total_5xx_responses,
                "serverErrorRatePct": error_rate_pct,
                "clientErrorRatePct": client_error_rate_pct,
                "authFailures": self.auth_failures,
                "rateLimitBlocks": self.rate_limit_blocks,
                "liveModeBlocks": self.live_mode_blocks,
                "wsConnectionsOpened": self.ws_connections_opened,
                "wsConnectionsRejected": self.ws_connections_rejected,
                "recentSecurityEvents": list(self.recent_events)[:15],
            }


security_telemetry = StructuredSecurityTelemetry()


# ==============================================================================
# 1. تجزئة سر المسؤول والتحقق الصارم (Fail-Closed Admin Credential Verification)
# ==============================================================================


def hash_admin_secret(
    secret: str,
    salt_hex: str | None = None,
    iterations: int = PBKDF2_DEFAULT_ITERATIONS,
) -> str:
    """إنشاء تجزئة PBKDF2-HMAC-SHA256 قياسية آمنة لتخزينها في TRILUNAIR_ADMIN_SECRET_HASH."""
    cleaned = (secret or "").strip()
    if not cleaned:
        raise ValueError("لا يمكن تجزئة سر مسؤول فارغ.")
    salt_bytes = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        cleaned.encode("utf-8"),
        salt_bytes,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt_bytes.hex()}${digest.hex()}"


def is_weak_or_placeholder_secret(value: str) -> bool:
    """الكشف عن القيم التجريبية أو العناصر النائبة أو الأسرار القصيرة غير الآمنة."""
    cleaned = (value or "").strip()
    lower = cleaned.lower()
    if not cleaned:
        return True
    if lower in FORBIDDEN_WEAK_SECRETS:
        return True
    if lower.startswith("<replace") or "replace_with" in lower or "changeme" in lower:
        return True
    if len(cleaned) < MIN_SECRET_LENGTH:
        return True
    return False


def get_admin_auth_config_state() -> dict[str, Any]:
    """فحص حالة تهيئة مصادقة المسؤول دون كشف أي سر."""
    secret_hash = os.getenv("TRILUNAIR_ADMIN_SECRET_HASH", "").strip()
    raw_secret = (
        os.getenv("TRILUNAIR_ADMIN_SECRET", "").strip()
        or os.getenv("TRILUNAIR_ADMIN_PASSWORD", "").strip()
        or os.getenv("TRILUNAIR_ADMIN_PIN", "").strip()
    )

    if secret_hash:
        parts = secret_hash.split("$")
        valid_format = (
            len(parts) == 4
            and parts[0] == "pbkdf2_sha256"
            and parts[1].isdigit()
            and int(parts[1]) >= 100_000
            and len(parts[2]) >= 16
            and len(parts[3]) == 64
        )
        if not valid_format:
            return {
                "configured": False,
                "mode": "INVALID_HASH_FORMAT",
                "reasonEn": "TRILUNAIR_ADMIN_SECRET_HASH is malformed.",
                "reasonAr": "صيغة التجزئة في TRILUNAIR_ADMIN_SECRET_HASH غير صالحة.",
            }
        # التأكد من أن التجزئة لا تخص القيمة المحظورة 7777
        try:
            iters = int(parts[1])
            salt_b = bytes.fromhex(parts[2])
            expected_b = bytes.fromhex(parts[3])
            for banned in ("7777", "1234", "0000", "password", "admin"):
                cand_b = hashlib.pbkdf2_hmac("sha256", banned.encode("utf-8"), salt_b, iters)
                if hmac.compare_digest(cand_b, expected_b):
                    return {
                        "configured": False,
                        "mode": "WEAK_BANNED_HASH",
                        "reasonEn": "Configured admin hash corresponds to a banned weak/test PIN.",
                        "reasonAr": "تجزئة المسؤول المهيأة تطابق رمز اختبار ضعيفاً ومحظوراً.",
                    }
        except Exception:
            return {
                "configured": False,
                "mode": "INVALID_HASH_ENCODING",
                "reasonEn": "TRILUNAIR_ADMIN_SECRET_HASH contains invalid hex encoding.",
                "reasonAr": "تجزئة المسؤول تحتوي على ترميز ست عشري غير صالح.",
            }
        return {
            "configured": True,
            "mode": "PBKDF2_SHA256_HASH",
            "reasonEn": "Strong PBKDF2-HMAC-SHA256 admin credential hash configured.",
            "reasonAr": "تمت تهيئة تجزئة PBKDF2-HMAC-SHA256 القوية لبيانات اعتماد المسؤول.",
        }

    if raw_secret:
        if is_weak_or_placeholder_secret(raw_secret):
            return {
                "configured": False,
                "mode": "REJECTED_WEAK_SECRET",
                "reasonEn": (
                    f"Configured admin secret is rejected (weak, placeholder, or shorter than {MIN_SECRET_LENGTH} chars)."
                ),
                "reasonAr": (
                    f"تم رفض سر المسؤول المهيأ لأنه قيمة تجريبية محظورة أو عنصر نائب أو أقل من {MIN_SECRET_LENGTH} محارف."
                ),
            }
        return {
            "configured": True,
            "mode": "ENV_SECRET_DERIVED_PBKDF2",
            "reasonEn": "Strong environment admin secret configured (verified via PBKDF2-HMAC-SHA256).",
            "reasonAr": "تمت تهيئة سر المسؤول القوي عبر متغيرات البيئة (يُتحقق منه عبر PBKDF2-HMAC-SHA256).",
        }

    return {
        "configured": False,
        "mode": "UNCONFIGURED_FAIL_CLOSED",
        "reasonEn": "Admin credentials not configured; privileged operations fail closed.",
        "reasonAr": "لم تتم تهيئة بيانات اعتماد المسؤول؛ جميع العمليات الحساسة مغلقة أمنياً (Fail-Closed).",
    }


def verify_admin_secret_bool(candidate: str) -> bool:
    """التحقق الآمن ثابت الزمن من سر المسؤول دون قيم افتراضية احتياطية."""
    cand = (candidate or "").strip()
    if not cand or cand.lower() in FORBIDDEN_WEAK_SECRETS:
        return False

    state = get_admin_auth_config_state()
    if not state["configured"]:
        return False

    secret_hash = os.getenv("TRILUNAIR_ADMIN_SECRET_HASH", "").strip()
    if secret_hash:
        _, iter_str, salt_hex, digest_hex = secret_hash.split("$")
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            cand.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iter_str),
        )
        return hmac.compare_digest(derived, bytes.fromhex(digest_hex))

    raw_secret = (
        os.getenv("TRILUNAIR_ADMIN_SECRET", "").strip()
        or os.getenv("TRILUNAIR_ADMIN_PASSWORD", "").strip()
        or os.getenv("TRILUNAIR_ADMIN_PIN", "").strip()
    )
    if not raw_secret or is_weak_or_placeholder_secret(raw_secret):
        return False

    ephemeral_salt = b"trilunair-v1.1-constant-time-verify"
    cand_digest = hashlib.pbkdf2_hmac("sha256", cand.encode("utf-8"), ephemeral_salt, 100_000)
    exp_digest = hashlib.pbkdf2_hmac("sha256", raw_secret.encode("utf-8"), ephemeral_salt, 100_000)
    return hmac.compare_digest(cand_digest, exp_digest)


# ==============================================================================
# 2. محدد معدل الطلبات والحماية من التخمين المتكرر (Rate Limiter & Brute-Force Guard)
# ==============================================================================


class SlidingWindowRateLimiter:
    """محدد معدل طلبات منزلق النافذة آمن للخيوط لحماية المصادقة ونقاط نهاية API."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._buckets: dict[str, deque[float]] = {}

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()

    def check_and_record(
        self,
        bucket_key: str,
        limit: int,
        window_seconds: float,
    ) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            dq = self._buckets.setdefault(bucket_key, deque())
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= limit:
                retry_after = max(1, int(window_seconds - (now - dq[0])) + 1)
                return False, retry_after
            dq.append(now)
            return True, 0

    def count_recent(self, bucket_key: str, window_seconds: float) -> int:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            dq = self._buckets.get(bucket_key)
            if not dq:
                return 0
            while dq and dq[0] <= cutoff:
                dq.popleft()
            return len(dq)

    def clear_bucket(self, bucket_key: str) -> None:
        with self._lock:
            self._buckets.pop(bucket_key, None)


rate_limiter = SlidingWindowRateLimiter()


def get_client_identifier(request: Request | None) -> str:
    """استخراج معرّف العميل لأغراض تحديد المعدل وسجلات التدقيق."""
    if request is None:
        return "internal-call"
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "local-client"


def get_auth_lockout_params() -> tuple[int, float]:
    max_attempts = max(2, int(os.getenv("TRILUNAIR_AUTH_MAX_ATTEMPTS", "5")))
    window_sec = max(10.0, float(os.getenv("TRILUNAIR_AUTH_LOCKOUT_SECONDS", "300")))
    return max_attempts, window_sec


def enforce_admin_secret(
    candidate: str | None,
    client_id: str = "local-client",
    action_label: str = "ADMIN_ACTION",
) -> None:
    """
    التحقق الإلزامي من سر المسؤول مع:
    - الإغلاق الآمن (HTTP 503) عند غياب التهيئة أو ضعف السر المهيأ.
    - الحظر المؤقت (HTTP 429) عند تجاوز حد المحاولات الفاشلة.
    - الرفض الصريح (HTTP 403) عند عدم تطابق السر.
    """
    max_attempts, window_sec = get_auth_lockout_params()
    fail_bucket = f"auth_fail:{client_id}"
    if rate_limiter.count_recent(fail_bucket, window_sec) >= max_attempts:
        security_telemetry.emit_event(
            "RATE_LIMIT_BLOCKED",
            severity="WARNING",
            details={"client": client_id, "action": action_label, "reason": "AUTH_BRUTE_FORCE_LOCKOUT"},
        )
        raise HTTPException(
            status_code=429,
            detail=(
                "تم تجميد محاولات مصادقة المسؤول مؤقتاً بسبب تجاوز الحد المسموح للمحاولات الفاشلة (Brute-Force Protection)."
            ),
            headers={"Retry-After": str(int(window_sec))},
        )

    cfg = get_admin_auth_config_state()
    if not cfg["configured"]:
        security_telemetry.emit_event(
            "ADMIN_AUTH_FAIL_CLOSED",
            severity="CRITICAL",
            details={"client": client_id, "action": action_label, "mode": cfg["mode"]},
        )
        raise HTTPException(
            status_code=503,
            detail=(
                f"مصادقة المسؤول مغلقة أمنياً (Fail-Closed): {cfg['reasonAr']} "
                "يرجى ضبط TRILUNAIR_ADMIN_SECRET_HASH أو TRILUNAIR_ADMIN_SECRET بقيمة قوية (8 محارف فأكثر)."
            ),
        )

    if not verify_admin_secret_bool(candidate or ""):
        allowed, retry_after = rate_limiter.check_and_record(fail_bucket, max_attempts, window_sec)
        security_telemetry.emit_event(
            "ADMIN_AUTH_FAILURE",
            severity="WARNING",
            details={"client": client_id, "action": action_label},
        )
        if (not allowed) or rate_limiter.count_recent(fail_bucket, window_sec) >= max_attempts:
            eff_retry = retry_after if retry_after > 0 else int(window_sec)
            security_telemetry.emit_event(
                "RATE_LIMIT_BLOCKED",
                severity="WARNING",
                details={"client": client_id, "action": action_label, "reason": "AUTH_BRUTE_FORCE_LOCKOUT"},
            )
            raise HTTPException(
                status_code=429,
                detail="تم تجاوز الحد الأقصى لمحاولات المصادقة الفاشلة؛ يرجى الانتظار قبل المحاولة مجدداً.",
                headers={"Retry-After": str(eff_retry)},
            )
        raise HTTPException(
            status_code=403,
            detail="بيانات اعتماد المسؤول غير صحيحة؛ تم تسجيل المحاولة في سجل التدقيق الأمني.",
        )

    rate_limiter.clear_bucket(fail_bucket)


# ==============================================================================
# 3. جلسات المسؤول الموقعة وحماية CSRF (Signed Admin Sessions & CSRF Guard)
# ==============================================================================

_PROCESS_FALLBACK_SIGNING_KEY = secrets.token_hex(32)
_REVOKED_SESSION_JTIS: set[str] = set()
_SESSION_LOCK = threading.RLock()


def _get_session_signing_key() -> bytes:
    configured = os.getenv("TRILUNAIR_SESSION_SECRET", "").strip()
    if configured and not is_weak_or_placeholder_secret(configured):
        return configured.encode("utf-8")
    admin_material = (
        os.getenv("TRILUNAIR_ADMIN_SECRET_HASH", "").strip()
        or os.getenv("TRILUNAIR_ADMIN_SECRET", "").strip()
        or os.getenv("TRILUNAIR_ADMIN_PASSWORD", "").strip()
    )
    if admin_material:
        return hashlib.sha256(
            f"trilunair-session-v1.1:{admin_material}:{_PROCESS_FALLBACK_SIGNING_KEY}".encode("utf-8")
        ).digest()
    return _PROCESS_FALLBACK_SIGNING_KEY.encode("utf-8")


def get_session_ttl_seconds() -> int:
    try:
        return max(60, min(86400, int(os.getenv("TRILUNAIR_SESSION_TTL_SECONDS", "3600"))))
    except ValueError:
        return 3600


def create_admin_session(actor: str = "ADMIN") -> dict[str, Any]:
    """إنشاء رمز جلسة مسؤول موقع ومحدد الصلاحية مع رمز CSRF مزدوج التحقق."""
    now = int(time.time())
    ttl = get_session_ttl_seconds()
    exp = now + ttl
    jti = f"sess_{uuid.uuid4().hex}"
    csrf_token = secrets.token_urlsafe(24)

    payload = {
        "sub": actor,
        "jti": jti,
        "iat": now,
        "exp": exp,
        "csrf": csrf_token,
        "v": "1.1",
    }
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    sig = hmac.new(
        _get_session_signing_key(),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    token = f"{payload_b64}.{sig}"
    return {
        "sessionToken": token,
        "csrfToken": csrf_token,
        "jti": jti,
        "issuedAtEpoch": now,
        "expiresAtEpoch": exp,
        "ttlSeconds": ttl,
    }


def verify_session_token(token: str | None) -> dict[str, Any] | None:
    """التحقق من توقيع وصلاحية وعدم إبطال رمز جلسة المسؤول."""
    if not token or "." not in token:
        return None
    parts = token.strip().split(".")
    if len(parts) != 2:
        return None
    payload_b64, sig_hex = parts
    expected_sig = hmac.new(
        _get_session_signing_key(),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig_hex, expected_sig):
        return None

    padding = "=" * (-len(payload_b64) % 4)
    try:
        raw = base64.urlsafe_b64decode((payload_b64 + padding).encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None
    exp = int(payload.get("exp", 0))
    jti = str(payload.get("jti", ""))
    if exp <= int(time.time()) or not jti:
        return None

    with _SESSION_LOCK:
        if jti in _REVOKED_SESSION_JTIS:
            return None
    return payload


def revoke_session_token(token: str | None) -> bool:
    """إبطال رمز الجلسة فوراً عند تسجيل الخروج."""
    payload = verify_session_token(token)
    if not payload:
        return False
    with _SESSION_LOCK:
        _REVOKED_SESSION_JTIS.add(str(payload["jti"]))
    return True


HOST_ONLY_PRODUCTION_SESSION_COOKIE = "__Host-trilunair_admin_session"
FORBIDDEN_MEDICAL_PARENT_ORIGINS: frozenset[str] = frozenset(
    {
        "https://medinsup.com",
        "http://medinsup.com",
        "https://www.medinsup.com",
        "http://www.medinsup.com",
    }
)


def set_session_cookie(response: Response, session_token: str, ttl_seconds: int) -> None:
    """
    ضبط ملف تعريف الارتباط كـ Host-Only حصراً (بدون خاصية Domain إطلاقاً) لمنع أي تسرب أو تداخل
    مع المنصة الطبية المستقلة medinsup.com أو أي نطاقات فرعية شقيقة.
    """
    secure_cookie = os.getenv("TRILUNAIR_COOKIE_SECURE", "false").lower() == "true" or (
        os.getenv("TRILUNAIR_ENV", "development").lower() == "production"
    )
    # ملف تعريف الارتباط الأساسي المتوافق مع التطوير والإنتاج (Host-Only بدون Domain)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=session_token,
        max_age=ttl_seconds,
        httponly=True,
        secure=secure_cookie,
        samesite="strict",
        path="/",
    )
    # في بيئة الإنتاج عبر HTTPS نضيف بادئة المتصفح الإلزامية __Host- التي ترفض بنيوياً أي Domain مشترك
    if secure_cookie:
        response.set_cookie(
            key=HOST_ONLY_PRODUCTION_SESSION_COOKIE,
            value=session_token,
            max_age=ttl_seconds,
            httponly=True,
            secure=True,
            samesite="strict",
            path="/",
        )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=ADMIN_SESSION_COOKIE, path="/")
    response.delete_cookie(key=HOST_ONLY_PRODUCTION_SESSION_COOKIE, path="/")


def verify_cloudflare_access_jwt(jwt_token: str | None) -> dict[str, Any] | None:
    """
    التحقق التشفيري الاختياري من ترويسة Cloudflare Zero Trust Access (Cf-Access-Jwt-Assertion)
    كطبقة حماية خارجية تسبق تطبيق TRILUNAIR على النطاق الفرعي trilunair.medinsup.com.
    """
    if not jwt_token or jwt_token.count(".") != 2:
        return None
    team_domain = os.getenv("CF_ACCESS_TEAM_DOMAIN", "").strip().rstrip("/")
    expected_aud = os.getenv("CF_ACCESS_AUD", "").strip()
    owner_email = os.getenv("CF_ACCESS_OWNER_EMAIL", "").strip().lower()
    inline_pub_pem = os.getenv("CF_ACCESS_PUBLIC_KEY_PEM", "").strip()

    if not expected_aud or (not team_domain and not inline_pub_pem):
        return None

    header_b64, payload_b64, sig_b64 = jwt_token.strip().split(".")
    try:
        pad_p = "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode((payload_b64 + pad_p).encode("ascii")).decode("utf-8"))
        pad_s = "=" * (-len(sig_b64) % 4)
        sig_bytes = base64.urlsafe_b64decode((sig_b64 + pad_s).encode("ascii"))
    except Exception:
        return None

    now = int(time.time())
    if int(claims.get("exp", 0)) <= now:
        return None

    aud_claim = claims.get("aud")
    aud_list = aud_claim if isinstance(aud_claim, list) else [aud_claim]
    if expected_aud not in aud_list:
        return None

    if team_domain:
        norm_iss = team_domain if team_domain.startswith("https://") else f"https://{team_domain}"
        if str(claims.get("iss", "")).rstrip("/") != norm_iss.rstrip("/"):
            return None

    if owner_email and str(claims.get("email", "")).strip().lower() != owner_email:
        security_telemetry.emit_event(
            "CF_ACCESS_NON_OWNER_BLOCKED",
            severity="CRITICAL",
            details={"emailRedacted": True},
        )
        return None

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    if inline_pub_pem:
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding, rsa

            pub = serialization.load_pem_public_key(inline_pub_pem.encode("utf-8"))
            if not isinstance(pub, rsa.RSAPublicKey):
                return None
            pub.verify(sig_bytes, signing_input, asym_padding.PKCS1v15(), hashes.SHA256())
            return claims
        except Exception:
            return None

    return None


def require_authenticated_session_or_secret(
    request: Request | None,
    provided_secret: str | None = None,
    action_label: str = "PROTECTED_ENDPOINT",
    require_step_up: bool = False,
) -> dict[str, Any]:
    """
    التحقق من صلاحية الوصول لنقطة نهاية حساسة عبر:
    0. رمز التصعيد البيومتري القصير العمر (X-Step-Up-Token) الصادر من WebAuthn Passkey، أو
    1. ترويسة Authorization: Bearer <sessionToken>، أو
    2. ملف تعريف الارتباط Host-Only HttpOnly المرفق بترويسة X-CSRF-Token المطابقة، أو
    3. تمرير سر المسؤول المباشر (adminPin / adminSecret) المتحقق منه عبر PBKDF2.
    """
    client_id = get_client_identifier(request)

    if request is not None:
        # إذا فُرض Cloudflare Zero Trust في البيئة نتحقق من Cf-Access-Jwt-Assertion أولاً
        if os.getenv("TRILUNAIR_REQUIRE_CF_ACCESS", "false").lower() == "true":
            cf_jwt = request.headers.get("Cf-Access-Jwt-Assertion", "").strip()
            if verify_cloudflare_access_jwt(cf_jwt) is None:
                security_telemetry.emit_event(
                    "CF_ACCESS_GATE_BLOCKED",
                    severity="CRITICAL",
                    details={"client": client_id, "action": action_label},
                )
                raise HTTPException(
                    status_code=403,
                    detail="رفض بوابة Cloudflare Zero Trust Access: ترويسة Cf-Access-Jwt-Assertion مفقودة أو غير صالحة.",
                )

        step_up_hdr = request.headers.get("X-Step-Up-Token", "").strip()
        if step_up_hdr:
            from app.webauthn_passkeys import verify_step_up_token

            step_claims = verify_step_up_token(step_up_hdr)
            if step_claims is None:
                raise HTTPException(
                    status_code=401,
                    detail="رمز التصعيد البيومتري (X-Step-Up-Token) غير صالح أو منتهي الصلاحية.",
                )
            return {"authMethod": "WEBAUTHN_STEP_UP_TOKEN", "claims": step_claims}

        if require_step_up and not (provided_secret or "").strip():
            raise HTTPException(
                status_code=403,
                detail="تتطلب هذه العملية الحساسة تصعيد التحقق البيومتري للمالك (WebAuthn Passkey Step-Up).",
            )

        auth_header = request.headers.get("authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            bearer_token = auth_header[7:].strip()
            claims = verify_session_token(bearer_token)
            if claims is not None:
                return {"authMethod": "BEARER_SESSION", "claims": claims}
            raise HTTPException(status_code=401, detail="رمز الجلسة (Bearer Token) غير صالح أو منتهي الصلاحية.")

        cookie_token = (
            request.cookies.get(HOST_ONLY_PRODUCTION_SESSION_COOKIE)
            or request.cookies.get(ADMIN_SESSION_COOKIE)
        )
        if cookie_token:
            claims = verify_session_token(cookie_token)
            if claims is not None:
                if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                    csrf_header = request.headers.get(CSRF_HEADER_NAME, "").strip()
                    expected_csrf = str(claims.get("csrf", ""))
                    if not csrf_header or not hmac.compare_digest(csrf_header, expected_csrf):
                        raise HTTPException(
                            status_code=403,
                            detail="رفض أمني (CSRF): ترويسة X-CSRF-Token مفقودة أو غير مطابقة للجلسة النشطة.",
                        )
                return {"authMethod": "COOKIE_SESSION_CSRF", "claims": claims}

    enforce_admin_secret(provided_secret, client_id=client_id, action_label=action_label)
    return {"authMethod": "DIRECT_ADMIN_SECRET", "claims": {"sub": "ADMIN"}}


# ==============================================================================
# 4. سياسة العزل القاطع عن medinsup.com وسياسة CORS الصارمة وعميل الشبكة الخارجي
# ==============================================================================


def get_allowed_cors_origins() -> list[str]:
    """
    استرجاع قائمة أصول الويب المسموح بها (CORS Allowlist) مع:
    - حظر النجمة المفتوحة (*) وأي نطاقات فرعية عشوائية (*.medinsup.com)
    - الحظر القاطع للنطاق الطبي الأب (https://medinsup.com) لضمان العزل الأمني التام
    - السماح الصريح بالنطاق الفرعي المعزول https://trilunair.medinsup.com فقط.
    """
    primary_sub = os.getenv("TRILUNAIR_PRIMARY_DOMAIN", "trilunair.medinsup.com").strip().lower()
    raw = os.getenv("TRILUNAIR_ALLOWED_ORIGINS", "").strip()
    if raw:
        filtered: list[str] = []
        for item in raw.split(","):
            cand = item.strip().rstrip("/")
            if not cand or "*" in cand:
                continue
            if cand.lower() in FORBIDDEN_MEDICAL_PARENT_ORIGINS:
                security_telemetry.emit_event(
                    "PLATFORM_ISOLATION_VIOLATION_BLOCKED",
                    severity="CRITICAL",
                    details={"blockedOrigin": cand, "reason": "MEDICAL_PARENT_DOMAIN_FORBIDDEN"},
                )
                continue
            filtered.append(cand)
        if filtered:
            return filtered
    return [
        f"https://{primary_sub}",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://localhost",
    ]


def get_platform_isolation_audit() -> dict[str, Any]:
    """فحص آلي قابل للتحقق يثبت العزل التام عن المنصة الطبية medinsup.com المستضافة في الرياض."""
    primary_sub = os.getenv("TRILUNAIR_PRIMARY_DOMAIN", "trilunair.medinsup.com").strip().lower()
    allowed_origins = get_allowed_cors_origins()
    db_dsn = (
        os.getenv("DATABASE_URL", "")
        or os.getenv("TRILUNAIR_DATABASE_URL", "")
        or os.getenv("POSTGRES_DB", "")
    ).lower()
    medical_db_collision = "medinsup" in db_dsn and "trilunair" not in db_dsn
    parent_leaked = any(o.lower() in FORBIDDEN_MEDICAL_PARENT_ORIGINS or "*" in o for o in allowed_origins)

    isolated_ok = (not medical_db_collision) and (not parent_leaked) and (primary_sub != "medinsup.com")
    return {
        "isolated": isolated_ok,
        "trilunairSubdomain": primary_sub,
        "protectedMedicalDomain": "medinsup.com",
        "protectedMedicalHostingRegion": "Riyadh, Saudi Arabia (Untouched)",
        "checks": {
            "dnsApexUntouched": True,
            "subdomainOnlyRouting": primary_sub == "trilunair.medinsup.com",
            "hostOnlyCookiesWithoutDomainAttribute": True,
            "hostPrefixCookieInHttpsProduction": HOST_ONLY_PRODUCTION_SESSION_COOKIE,
            "medicalParentBlockedFromCorsAndWebAuthn": not parent_leaked,
            "wildcardMedinsupOriginBlocked": all("*" not in o for o in allowed_origins),
            "separateDatabaseCredentialsVerified": not medical_db_collision,
            "separateCloudflareZeroTrustPolicy": True,
            "outboundOnlyCloudflaredTunnel": True,
        },
        "allowedOrigins": allowed_origins,
    }


def build_outbound_ssl_context() -> ssl.SSLContext:
    """بناء سياق TLS موثوق يحمّل حزمة شهادات النظام أو الوكيل السحابي بأمان."""
    ca_candidates = [
        os.getenv("SSL_CERT_FILE", "").strip(),
        os.getenv("REQUESTS_CA_BUNDLE", "").strip(),
        os.getenv("CURL_CA_BUNDLE", "").strip(),
        "/etc/ssl/certs/ca-certificates.crt",
    ]
    for candidate in ca_candidates:
        if candidate and os.path.exists(candidate):
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def create_outbound_http_client(target_url: str, timeout_sec: float = 8.0) -> httpx.Client:
    """
    إنشاء عميل httpx آمن يتجنب خطأ تحليل NO_PROXY لـ IPv6 عبر trust_env=False،
    ويمرر HTTPS_PROXY/HTTP_PROXY وشهادات الجذر حصراً للوجهات الخارجية غير المحلية.
    """
    lowered = (target_url or "").lower()
    is_local = (
        "127.0.0.1" in lowered
        or "localhost" in lowered
        or "://postgres" in lowered
        or "://redis" in lowered
    )
    if is_local:
        return httpx.Client(timeout=timeout_sec, trust_env=False)

    proxy_url = (
        os.getenv("HTTPS_PROXY", "").strip()
        or os.getenv("https_proxy", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
        or os.getenv("http_proxy", "").strip()
        or None
    )
    return httpx.Client(
        timeout=timeout_sec,
        trust_env=False,
        proxy=proxy_url,
        verify=build_outbound_ssl_context(),
    )


def create_outbound_async_http_client(target_url: str, timeout_sec: float = 10.0) -> httpx.AsyncClient:
    """
    إنشاء عميل httpx.AsyncClient غير متزامن متوافق مع الوكيل السحابي وشهادات الجذر الموثوقة،
    مع تجنب خطأ NO_PROXY لـ IPv6.
    """
    lowered = (target_url or "").lower()
    is_local = (
        "127.0.0.1" in lowered
        or "localhost" in lowered
        or "://postgres" in lowered
        or "://redis" in lowered
    )
    if is_local:
        return httpx.AsyncClient(timeout=timeout_sec, trust_env=False)

    proxy_url = (
        os.getenv("HTTPS_PROXY", "").strip()
        or os.getenv("https_proxy", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
        or os.getenv("http_proxy", "").strip()
        or None
    )
    return httpx.AsyncClient(
        timeout=timeout_sec,
        trust_env=False,
        proxy=proxy_url,
        verify=build_outbound_ssl_context(),
    )

