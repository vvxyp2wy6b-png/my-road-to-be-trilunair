"""
اختبارات آلية شاملة لمنظومة الهوية السيادية ثلاثية الأحرف (TRM) ونظام دخول أدمن المنصة رباعي العوامل:
1. التحقق من الهوية المؤسسية TRM (Trilunair • Road • Majed) ومعنى اسم المنصة بالعربية.
2. تأسيس حساب الأدمن (البريد الإلكتروني + رقم الجوال الدولي + مفتاح التحقق السري + توليد سر Authenticator Base32).
3. التأكد من تشفير البريد ورقم الجوال وسر TOTP في قاعدة البيانات بخوارزمية AES-256-GCM وتجزئة مفتاح التحقق بـ PBKDF2-SHA256.
4. تأكيد إقران تطبيق المصادقة (RFC 6238 6-Digit TOTP) واختبار الدخول الرباعي وحماية منع إعادة استخدام الرمز (Replay Protection).
"""

from __future__ import annotations

import os
from pathlib import Path
import time

from fastapi.testclient import TestClient
import pytest


@pytest.fixture()
def isolated_admin_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_file = tmp_path / "trm_admin_test.db"
    monkeypatch.setenv("TRILUNAIR_DB_PATH", str(db_file))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TRILUNAIR_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("TRILUNAIR_DEFAULT_MODE", "PAPER")
    monkeypatch.setenv("TRILUNAIR_MARKET_DATA_MODE", "SIMULATED")
    monkeypatch.setenv("TRILUNAIR_SESSION_SECRET", "a1b2c3d4e5f6" * 6)
    monkeypatch.setenv("TRILUNAIR_VAULT_MASTER_KEY", "0123456789abcdef" * 4)

    from app.admin_identity import ensure_admin_identity_tables
    from app.database import init_db
    from app.main import app

    init_db()
    ensure_admin_identity_tables()
    return TestClient(app)


def test_trm_brand_and_four_factor_admin_mfa_flow(isolated_admin_client: TestClient) -> None:
    from app.admin_identity import compute_totp_code
    from app.database import db_session

    # 1. فحص حالة الهوية المبدئية والشعار الثلاثي المعتمد HTB (How To Be A Trillionaire)
    r0 = isolated_admin_client.get("/api/auth/admin/identity")
    assert r0.status_code == 200
    body0 = r0.json()
    assert body0["brand"]["monogram"] == "HTB"
    assert "Trillionaire" in body0["brand"]["expansionEn"]
    assert "ماجد" in body0["brand"]["titleAr"]
    assert body0["enrolled"] is False
    assert body0["tradingMode"] == "PAPER"
    assert body0["liveAuthorized"] is False

    # 2. تأسيس حساب أدمن المنصة بمفتاح سري من 6 خانات فأكثر (مثلاً Mj#926) + توليد مفتاح Authenticator
    enroll_payload = {
        "displayName": "د. ماجد (أدمن المنصة)",
        "email": "majed.owner@example.sa",
        "phone": "+966501234567",
        "verificationKey": "Mj#926",
    }
    r_enr = isolated_admin_client.post("/api/auth/admin/enroll", json=enroll_payload)
    assert r_enr.status_code == 200, r_enr.text
    enr = r_enr.json()
    assert enr["enrolled"] is True
    assert enr["emailMasked"] == "ma••••r@example.sa"
    assert enr["phoneMasked"].startswith("+966")
    secret_b32 = enr["authenticatorSetup"]["secretBase32"]
    assert len(secret_b32) >= 24
    assert enr["authenticatorSetup"]["otpauthUri"].startswith("otpauth://totp/")

    # 3. التحقق من أن البريد ورقم الجوال وسر TOTP ومفتاح التحقق غير مخزنة كنص صريح في قاعدة البيانات
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM admin_sovereign_identity WHERE admin_id = 'owner-majed'"
        ).fetchone()
        assert row is not None
        assert "majed.owner@example.sa" not in str(row["email_ciphertext"])
        assert "+966501234567" not in str(row["phone_ciphertext"])
        assert secret_b32 not in str(row["totp_secret_ciphertext"])
        assert str(row["verification_key_hash"]).startswith("pbkdf2_sha256$")

    # 4. تأكيد إقران تطبيق المصادقة برمز RFC 6238 مكون من 6 أرقام في النافذة السابقة (-30s)
    now_ts = int(time.time())
    confirm_code, _ = compute_totp_code(secret_b32, for_timestamp=now_ts - 30)
    r_conf = isolated_admin_client.post(
        "/api/auth/admin/totp/confirm",
        json={
            "verificationKey": "Mj#926",
            "totpCode": confirm_code,
        },
    )
    assert r_conf.status_code == 200, r_conf.text
    assert r_conf.json()["totpVerified"] is True

    # 5. اختبار منع إعادة استخدام نفس الرمز الزمني (Replay Protection)
    r_replay = isolated_admin_client.post(
        "/api/auth/admin/login",
        json={
            "email": "majed.owner@example.sa",
            "phone": "+966501234567",
            "verificationKey": "Mj#926",
            "totpCode": confirm_code,
        },
    )
    assert r_replay.status_code == 403

    # 6. رفض الدخول في حال خطأ أي عامل من العوامل الأربعة (مثلاً رقم الجوال غير مطابق)
    fresh_code, _ = compute_totp_code(secret_b32, for_timestamp=now_ts)
    r_bad_phone = isolated_admin_client.post(
        "/api/auth/admin/login",
        json={
            "email": "majed.owner@example.sa",
            "phone": "+966599999999",
            "verificationKey": "Mj#926",
            "totpCode": fresh_code,
        },
    )
    assert r_bad_phone.status_code == 403

    # 7. نجاح الدخول السيادي رباعي العوامل وإصدار جلسة موثقة مع بقاء PAPER مقفلاً
    r_login = isolated_admin_client.post(
        "/api/auth/admin/login",
        json={
            "email": "majed.owner@example.sa",
            "phone": "+966501234567",
            "verificationKey": "Mj#926",
            "totpCode": fresh_code,
        },
    )
    assert r_login.status_code == 200, r_login.text
    login_body = r_login.json()
    assert login_body["authenticated"] is True
    assert login_body["brandMonogram"] == "HTB"
    assert login_body["sessionToken"]
    assert login_body["csrfToken"]
    assert login_body["tradingMode"] == "PAPER"
    assert login_body["liveAuthorized"] is False
