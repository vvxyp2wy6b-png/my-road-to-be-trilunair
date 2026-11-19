"""
مشغل المنظومة الأصلي بدون دوكر (100% Docker-Free Native Local Server Supervisor)
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD — v1.3.0-binance-personal-guard

يشغّل الخلفية (FastAPI + Uvicorn + WebSockets) والواجهة الأمامية المبنية (React 19 + Vite dist)
بشكل أصلي تماماً بدون Docker عبر:
1. الاتصال بمحرك PostgreSQL المحلي إن كان متاحاً على المنفذ 5432، أو التحول التلقائي السلس إلى محرك SQLite WAL المحلي الأصلي دون الحاجة لأي حاويات.
2. الاتصال بخادم Redis المحلي إن وُجد، أو تشغيل خادم TCP RESP مضمّن داخل عملية Python.
3. توليد وحفظ مفاتيح التشفير المحلية في ملف .env.local بصلاحيات مقيدة (0600) خارج Git.
4. فرض القفل الدائم على وضع التداول الورقي (PAPER) مع liveAuthorized=false.
"""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import socket
import sys
import threading

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.security import hash_admin_secret  # noqa: E402
import uvicorn  # noqa: E402


def _tcp_reachable(host: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _load_or_create_local_env() -> Path:
    """تحميل أو إنشاء ملف .env.local بصلاحيات 0600 لضمان ثبات خزنة AES-256-GCM عبر عمليات إعادة التشغيل بدون Docker."""
    env_file = REPO_ROOT / ".env.local"
    if env_file.is_file():
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    else:
        bootstrap_secret = f"TrilunairOwner#{secrets.token_urlsafe(14)}"
        admin_hash = hash_admin_secret(bootstrap_secret)
        session_secret = secrets.token_hex(32)
        vault_key = secrets.token_hex(32)
        lines = [
            "# Auto-generated Native Local Server Environment (0600 — Git-Ignored, Zero Docker)",
            "TRILUNAIR_DEFAULT_MODE=PAPER",
            "TRILUNAIR_MARKET_DATA_MODE=LIVE_PUBLIC",
            f"TRILUNAIR_SESSION_SECRET={session_secret}",
            f"TRILUNAIR_VAULT_MASTER_KEY={vault_key}",
            f"TRILUNAIR_ADMIN_SECRET_HASH={admin_hash}",
            "",
        ]
        env_file.write_text("\n".join(lines), encoding="utf-8")
        try:
            os.chmod(env_file, 0o600)
        except OSError:
            pass
    os.environ.setdefault("TRILUNAIR_REQUIRE_CFO_LOGIN", "1")
    return env_file


def _configure_native_database() -> str:
    """استخدام PostgreSQL الأصلي إن كان يعمل محلياً، وإلا استخدام SQLite WAL المحلي تلقائياً بدون Docker."""
    explicit_dsn = os.getenv("DATABASE_URL") or os.getenv("TRILUNAIR_POSTGRES_DSN")
    if explicit_dsn:
        return f"PostgreSQL (explicit DSN)"

    if _tcp_reachable("127.0.0.1", 5432):
        pg_user = os.getenv("PGUSER", "trilunair")
        pg_db = os.getenv("PGDATABASE", "trilunair")
        candidate_dsn = f"postgresql://{pg_user}@127.0.0.1:5432/{pg_db}"
        try:
            import psycopg

            with psycopg.connect(candidate_dsn, connect_timeout=2) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            os.environ["DATABASE_URL"] = candidate_dsn
            return f"Native PostgreSQL ({candidate_dsn})"
        except Exception:
            pass

    data_dir = BACKEND_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = Path(os.getenv("TRILUNAIR_DB_PATH", str(data_dir / "trilunair_native.db")))
    os.environ["TRILUNAIR_DB_PATH"] = str(sqlite_path)
    return f"Native SQLite WAL ({sqlite_path})"


def _configure_native_redis() -> str:
    """استخدام خادم Redis الأصلي إن كان نشطاً، أو تشغيل خادم TCP RESP مضمّن بدون Docker."""
    if os.getenv("REDIS_URL") and _tcp_reachable("127.0.0.1", 6379):
        os.environ.setdefault("TRILUNAIR_REDIS_IS_MOCK", "false")
        return f"Native Redis ({os.environ['REDIS_URL']})"

    if _tcp_reachable("127.0.0.1", 6379):
        os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/0"
        os.environ.setdefault("TRILUNAIR_REDIS_IS_MOCK", "false")
        return "Native Redis (redis://127.0.0.1:6379/0)"

    from fakeredis import TcpFakeServer

    TcpFakeServer.allow_reuse_address = True
    try:
        redis_srv = TcpFakeServer(("127.0.0.1", 6379), server_type="redis")
    except OSError:
        redis_srv = TcpFakeServer(("127.0.0.1", 0), server_type="redis")
    actual_port = redis_srv.server_address[1]
    os.environ["REDIS_URL"] = f"redis://127.0.0.1:{actual_port}/0"
    os.environ["TRILUNAIR_REDIS_IS_MOCK"] = "true"
    t = threading.Thread(target=redis_srv.serve_forever, daemon=True)
    t.start()
    return f"Embedded Python TCP RESP Server (127.0.0.1:{actual_port})"


def main() -> None:
    env_path = _load_or_create_local_env()
    os.environ["TRILUNAIR_DEFAULT_MODE"] = "PAPER"
    os.environ.setdefault("TRILUNAIR_MARKET_DATA_MODE", "LIVE_PUBLIC")
    os.environ.setdefault("TRILUNAIR_SESSION_SECRET", secrets.token_hex(32))
    os.environ.setdefault("TRILUNAIR_VAULT_MASTER_KEY", secrets.token_hex(32))
    if not os.getenv("TRILUNAIR_ADMIN_SECRET_HASH") and not os.getenv("TRILUNAIR_ADMIN_SECRET"):
        os.environ["TRILUNAIR_ADMIN_SECRET_HASH"] = hash_admin_secret(f"TrilunairRuntime#{secrets.token_urlsafe(12)}")

    db_desc = _configure_native_database()
    redis_desc = _configure_native_redis()

    from app.admin_identity import ensure_admin_identity_tables
    from app.binance_personal_account import ensure_binance_personal_tables
    from app.binance_spot_execution_adapter import ensure_spot_execution_tables
    from app.database import init_db
    from app.quantum_hub import ensure_quantum_tables
    from app.webauthn_passkeys import ensure_passkey_tables
    from app.wealth_architect import ensure_wealth_architect_tables

    init_db()
    ensure_passkey_tables()
    ensure_admin_identity_tables()
    ensure_quantum_tables()
    ensure_wealth_architect_tables()
    ensure_binance_personal_tables()
    ensure_spot_execution_tables()

    dist_index = REPO_ROOT / "frontend" / "dist" / "index.html"
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print("======================================================================", flush=True)
    print(" QUANTUM TRILUNAIR v1.3.0 — NATIVE LOCAL SERVER (ZERO DOCKER)", flush=True)
    print("======================================================================", flush=True)
    print(f"[Native] Env Vault File : {env_path}", flush=True)
    print(f"[Native] Database       : {db_desc}", flush=True)
    print(f"[Native] Cache / PubSub : {redis_desc}", flush=True)
    print(f"[Native] Frontend SPA   : {'READY (' + str(dist_index) + ')' if dist_index.is_file() else 'MISSING dist/index.html'}", flush=True)
    print(f"[Native] Market Feed    : {os.environ['TRILUNAIR_MARKET_DATA_MODE']}", flush=True)
    print("[Native] Safety Lock    : PAPER PERMANENT LOCK (liveAuthorized=false)", flush=True)
    print(f"[Native] Unified Server : http://127.0.0.1:{port}", flush=True)
    print("======================================================================", flush=True)

    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
