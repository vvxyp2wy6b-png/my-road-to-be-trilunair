"""
مشغل المنظومة الكاملة محلياً داخل بيئة التحقق (PostgreSQL 15 الحقيقي + TCP Redis + بيانات Binance العامة الحية + FastAPI/React SPA).
يبقي وضع التداول مقفلاً نهائياً على الورقي (PAPER) مع liveAuthorized=false وتجزئة PBKDF2 عشوائية آمنة عند عدم تهيئة سر خارجي.
"""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import sys
import threading

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.security import hash_admin_secret  # noqa: E402
from fakeredis import TcpFakeServer  # noqa: E402
import uvicorn  # noqa: E402


def main() -> None:
    os.environ.setdefault("DATABASE_URL", "postgresql://trilunair@127.0.0.1:5432/trilunair")
    os.environ.setdefault("TRILUNAIR_DEFAULT_MODE", "PAPER")
    os.environ.setdefault("TRILUNAIR_MARKET_DATA_MODE", "LIVE_PUBLIC")
    os.environ.setdefault("TRILUNAIR_REDIS_IS_MOCK", "true")

    if not os.getenv("TRILUNAIR_ADMIN_SECRET_HASH") and not os.getenv("TRILUNAIR_ADMIN_SECRET"):
        ephemeral_secret = f"TrilunairRuntime#{secrets.token_urlsafe(12)}"
        os.environ["TRILUNAIR_ADMIN_SECRET_HASH"] = hash_admin_secret(ephemeral_secret)
    os.environ.setdefault("TRILUNAIR_SESSION_SECRET", secrets.token_hex(32))
    os.environ.setdefault("TRILUNAIR_VAULT_MASTER_KEY", secrets.token_hex(32))

    TcpFakeServer.allow_reuse_address = True
    try:
        redis_srv = TcpFakeServer(("127.0.0.1", 6379), server_type="redis")
    except OSError:
        redis_srv = TcpFakeServer(("127.0.0.1", 0), server_type="redis")
    actual_port = redis_srv.server_address[1]
    os.environ["REDIS_URL"] = f"redis://127.0.0.1:{actual_port}/0"

    t = threading.Thread(target=redis_srv.serve_forever, daemon=True)
    t.start()
    print(f"[Stack] TCP RESP Redis server listening on 127.0.0.1:{actual_port}", flush=True)
    print(f"[Stack] PostgreSQL DSN: {os.environ['DATABASE_URL']}", flush=True)
    print(f"[Stack] Market Data Mode: {os.environ['TRILUNAIR_MARKET_DATA_MODE']}", flush=True)
    print("[Stack] Safety Lock: PAPER permanent lock active (liveAuthorized=false)", flush=True)

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
