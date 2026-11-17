"""
وحدة التخزين المستديم المزدوجة (PostgreSQL الأساسي + SQLite الاحتياطي + Redis للتخزين المؤقت ومنع التكرار).
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

مسؤوليات هذه الوحدة:
1. دعم PostgreSQL الحقيقي عبر متغير البيئة DATABASE_URL أو TRILUNAIR_POSTGRES_DSN (الإنتاج و Docker Compose)،
   مع التراجع التلقائي السلس إلى SQLite (وضع WAL) عند استخدام TRILUNAIR_DB_PATH في البيئات المحلية والاختبارات.
2. دعم الاتصال بخادم Redis عبر REDIS_URL أو TRILUNAIR_REDIS_URL لتخزين أقفال منع تكرار الأوامر (Idempotency)،
   صلاحية المقترحات الزمنية (TTL)، ونبضات حداثة بيانات السوق.
3. ضمان إقلاع النظام دائماً في وضع التداول الورقي الآمن (PAPER) عند التهيئة الأولى،
   مع تعطيل التداول الحقيقي (liveAuthorized=False) وبذر المحفظة التجريبية برأسمال 1,000,000.00 دولار أمريكي.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from typing import Any, Iterator
import uuid

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]

try:
    import redis as redis_lib
except ImportError:  # pragma: no cover
    redis_lib = None  # type: ignore[assignment]

DEFAULT_DB_PATH = str(Path(__file__).resolve().parents[1] / "data" / "trilunair.db")
INITIAL_PAPER_CAPITAL_USD = 1_000_000.00
DEFAULT_MAX_DRAWDOWN_PCT = 5.0

_DB_LOCK = threading.RLock()
_INITIALIZED_TARGETS: set[str] = set()
_REDIS_CLIENT_CACHE: dict[str, Any] = {}


def utc_now_iso() -> str:
    """إرجاع الطابع الزمني الحالي بصيغة ISO-8601 القياسية بالتوقيت العالمي UTC."""
    return datetime.now(timezone.utc).isoformat()


def get_postgres_dsn() -> str | None:
    """استرجاع عنوان اتصال PostgreSQL في حال تهيئته عبر البيئة."""
    dsn = (
        os.getenv("TRILUNAIR_POSTGRES_DSN", "").strip()
        or os.getenv("DATABASE_URL", "").strip()
    )
    if dsn.startswith(("postgresql://", "postgres://")):
        return dsn
    return None


def is_postgres_active() -> bool:
    """التحقق مما إذا كان المحرك النشط حالياً هو PostgreSQL."""
    return get_postgres_dsn() is not None


def get_db_path() -> Path:
    """استرجاع مسار قاعدة بيانات SQLite المحلية."""
    raw_path = os.getenv("TRILUNAIR_DB_PATH", "").strip() or DEFAULT_DB_PATH
    resolved = Path(raw_path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _translate_qmarks_to_psycopg(sql: str) -> str:
    """تحويل علامات الاستفهام القياسية (?) خارج النصوص المفردة إلى (%s) المتوافقة مع psycopg."""
    out: list[str] = []
    in_single_quote = False
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":
            out.append(ch)
            if in_single_quote and i + 1 < n and sql[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            in_single_quote = not in_single_quote
        elif ch == "?" and not in_single_quote:
            out.append("%s")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _adapt_ddl_for_postgres(script: str) -> list[str]:
    """تكييف عبارات إنشاء الجداول (DDL) من صيغة SQLite إلى صيغة PostgreSQL القياسية."""
    adapted = re.sub(
        r"seq\s+INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "seq BIGSERIAL PRIMARY KEY",
        script,
        flags=re.IGNORECASE,
    )
    adapted = re.sub(r"\bREAL\b", "DOUBLE PRECISION", adapted)
    statements = [stmt.strip() for stmt in adapted.split(";") if stmt.strip()]
    return statements


class UnifiedCursorWrapper:
    """واجهة مؤشر موحدة بين psycopg و sqlite3."""

    def __init__(self, raw_cursor: Any) -> None:
        self._cur = raw_cursor

    @property
    def rowcount(self) -> int:
        return int(getattr(self._cur, "rowcount", 0) or 0)

    def fetchone(self) -> Any:
        return self._cur.fetchone()

    def fetchall(self) -> list[Any]:
        return list(self._cur.fetchall())


class PostgresConnectionWrapper:
    """غلاف اتصال PostgreSQL يحاكي واجهة sqlite3.Connection لتكامل شفاف عبر جميع الوحدات."""

    is_postgres = True

    def __init__(self, dsn: str) -> None:
        if psycopg is None:
            raise RuntimeError("حزمة psycopg غير مثبتة للاتصال بـ PostgreSQL.")
        self._conn = psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5)

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> UnifiedCursorWrapper:
        pg_sql = _translate_qmarks_to_psycopg(sql)
        cur = self._conn.cursor()
        if params:
            cur.execute(pg_sql, params)
        else:
            cur.execute(pg_sql)
        return UnifiedCursorWrapper(cur)

    def executemany(self, sql: str, seq_of_params: list[tuple[Any, ...]]) -> None:
        pg_sql = _translate_qmarks_to_psycopg(sql)
        with self._conn.cursor() as cur:
            cur.executemany(pg_sql, seq_of_params)

    def executescript(self, script: str) -> None:
        for stmt in _adapt_ddl_for_postgres(script):
            with self._conn.cursor() as cur:
                cur.execute(stmt)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "PostgresConnectionWrapper":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()


def _connect_sqlite(db_path: Path) -> sqlite3.Connection:
    """إنشاء اتصال SQLite مهيأ بوضع WAL لسلامة التزامن والأداء العالي."""
    conn = sqlite3.connect(str(db_path), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _open_configured_connection() -> tuple[Any, str]:
    """فتح اتصال بقاعدة البيانات النشطة (PostgreSQL إن وجد، وإلا SQLite)."""
    pg_dsn = get_postgres_dsn()
    if pg_dsn:
        return PostgresConnectionWrapper(pg_dsn), f"pg:{pg_dsn}"
    db_path = get_db_path()
    return _connect_sqlite(db_path), f"sqlite:{db_path}"


def _ensure_column_migrations(conn: Any, target_key: str) -> None:
    """ترقية الجداول القائمة بأعمدة انتهاء الصلاحية ومنع تكرار الأوامر دون فقدان البيانات."""
    is_pg = target_key.startswith("pg:")
    migrations = [
        ("trade_proposals", "expires_at", "TEXT"),
        ("trade_proposals", "client_order_id", "TEXT"),
        ("orders", "client_order_id", "TEXT"),
    ]
    for table, col, col_type in migrations:
        if is_pg:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )
        else:
            cols = [
                r["name"]
                for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            if col not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")

    # إنشاء الفهارس الفريدة الحتمية لمنع تنفيذ المقترح أو معرّف العميل مرتين
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_unique_proposal ON orders(proposal_id)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_unique_client_oid ON orders(client_order_id) WHERE client_order_id IS NOT NULL"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_proposals_unique_client_oid ON trade_proposals(client_order_id) WHERE client_order_id IS NOT NULL"
    )


CORE_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS system_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    trading_mode TEXT NOT NULL DEFAULT 'PAPER',
    kill_switch_active INTEGER NOT NULL DEFAULT 0,
    live_authorized INTEGER NOT NULL DEFAULT 0,
    cash_balance REAL NOT NULL,
    initial_equity REAL NOT NULL,
    peak_equity REAL NOT NULL,
    max_allowed_drawdown_pct REAL NOT NULL DEFAULT 5.0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    name_ar TEXT NOT NULL,
    name_en TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_entry_price REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    client_order_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity REAL NOT NULL,
    executed_price REAL NOT NULL,
    notional_usd REAL NOT NULL,
    total_fee_usd REAL NOT NULL,
    trading_mode TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trade_proposals (
    proposal_id TEXT PRIMARY KEY,
    client_order_id TEXT,
    status TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity REAL NOT NULL,
    limit_price REAL,
    stop_loss REAL,
    take_profit REAL,
    source TEXT NOT NULL,
    rationale TEXT,
    reference_price REAL NOT NULL,
    estimated_costs_json TEXT NOT NULL,
    risk_assessment_json TEXT NOT NULL,
    trading_mode TEXT NOT NULL,
    requires_live_pin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS active_theme_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    active_theme_id TEXT NOT NULL,
    custom_overrides_json TEXT NOT NULL,
    modifiers_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_themes (
    id TEXT PRIMARY KEY,
    theme_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT UNIQUE NOT NULL,
    message_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_meetings (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    meeting_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL,
    source TEXT NOT NULL,
    action TEXT NOT NULL,
    severity TEXT NOT NULL,
    details_ar TEXT NOT NULL,
    details_en TEXT NOT NULL
);
"""


def init_db(force_recheck: bool = False) -> Path:
    """
    تهيئة مخطط قاعدة البيانات (PostgreSQL أو SQLite) وبذر البيانات الابتدائية الآمنة عند أول تشغيل.
    يضمن دائماً أن وضع التداول الابتدائي هو PAPER وأن التداول الحقيقي غير مفعل.
    """
    pg_dsn = get_postgres_dsn()
    db_path = get_db_path()
    target_key = f"pg:{pg_dsn}" if pg_dsn else f"sqlite:{db_path}"

    with _DB_LOCK:
        if (
            not force_recheck
            and target_key in _INITIALIZED_TARGETS
            and (pg_dsn is not None or db_path.exists())
        ):
            return db_path

        conn, _ = _open_configured_connection()
        try:
            with conn:
                conn.executescript(CORE_SCHEMA_DDL)
                _ensure_column_migrations(conn, target_key)

                existing_state = conn.execute(
                    "SELECT id FROM system_state WHERE id = 1"
                ).fetchone()

                if existing_state is None:
                    now = utc_now_iso()
                    btc_seed_qty = 0.5
                    btc_seed_entry = 94_200.00
                    nvda_seed_qty = 150.0
                    nvda_seed_entry = 134.50
                    seeded_cost = (btc_seed_qty * btc_seed_entry) + (
                        nvda_seed_qty * nvda_seed_entry
                    )
                    initial_cash = round(INITIAL_PAPER_CAPITAL_USD - seeded_cost, 2)

                    conn.execute(
                        """
                        INSERT INTO system_state (
                            id, trading_mode, kill_switch_active, live_authorized,
                            cash_balance, initial_equity, peak_equity,
                            max_allowed_drawdown_pct, updated_at
                        ) VALUES (1, 'PAPER', 0, 0, ?, ?, ?, ?, ?)
                        """,
                        (
                            initial_cash,
                            INITIAL_PAPER_CAPITAL_USD,
                            INITIAL_PAPER_CAPITAL_USD,
                            DEFAULT_MAX_DRAWDOWN_PCT,
                            now,
                        ),
                    )

                    conn.executemany(
                        """
                        INSERT INTO positions (
                            symbol, name_ar, name_en, quantity, avg_entry_price, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                "BTC-USD",
                                "بيتكوين مقابل الدولار",
                                "Bitcoin / USD",
                                btc_seed_qty,
                                btc_seed_entry,
                                now,
                            ),
                            (
                                "NVDA",
                                "إنفيديا للذكاء الاصطناعي",
                                "NVIDIA Corp",
                                nvda_seed_qty,
                                nvda_seed_entry,
                                now,
                            ),
                        ],
                    )

                    conn.executemany(
                        """
                        INSERT INTO orders (
                            order_id, proposal_id, client_order_id, symbol, side, order_type,
                            quantity, executed_price, notional_usd, total_fee_usd,
                            trading_mode, source, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                "ord_seed_btc01",
                                "prop_seed_btc01",
                                "seed-btc-01",
                                "BTC-USD",
                                "BUY",
                                "LIMIT",
                                btc_seed_qty,
                                btc_seed_entry,
                                round(btc_seed_qty * btc_seed_entry, 2),
                                0.0,
                                "PAPER",
                                "TERMINAL",
                                "FILLED",
                                now,
                            ),
                            (
                                "ord_seed_nvda01",
                                "prop_seed_nvda01",
                                "seed-nvda-01",
                                "NVDA",
                                "BUY",
                                "LIMIT",
                                nvda_seed_qty,
                                nvda_seed_entry,
                                round(nvda_seed_qty * nvda_seed_entry, 2),
                                0.0,
                                "PAPER",
                                "TERMINAL",
                                "FILLED",
                                now,
                            ),
                        ],
                    )

                    default_modifiers = {
                        "glowIntensity": 58,
                        "blurRadius": 16,
                        "panelOpacity": 78,
                        "animationIntensity": 85,
                        "motionDisabled": False,
                        "highContrast": False,
                        "lowPowerMode": False,
                    }
                    conn.execute(
                        """
                        INSERT INTO active_theme_state (
                            id, active_theme_id, custom_overrides_json, modifiers_json, updated_at
                        ) VALUES (1, 'royal-gold', '{}', ?, ?)
                        """,
                        (json.dumps(default_modifiers, ensure_ascii=False), now),
                    )

                    welcome_msg = {
                        "id": "msg_welcome_01",
                        "role": "assistant",
                        "senderNameAr": "المجلس التنفيذي — كبير المستشارين",
                        "senderNameEn": "Chief Strategist — Executive Council",
                        "agentId": "chief-strategist",
                        "source": "TEXT",
                        "language": "ar",
                        "contentAr": (
                            "مرحباً بك د. ماجد في مركز القيادة الهولوغرامي «رحلتي نحو التريليون». "
                            "النظام يعمل في وضع التداول الورقي الآمن (PAPER) برأسمال ابتدائي $1,000,000.00. "
                            "جميع الوكلاء الخمسة جاهزون لتحليل الأسواق ومقارنة الأصول وتجهيز مقترحات الصفقات المحكومة بفحص المخاطر الحتمي."
                        ),
                        "contentEn": (
                            "Welcome Dr. MaJoOoOoOoD to the Holographic Command Center — My Road to be Trilunair. "
                            "System booted safely in PAPER trading mode with $1,000,000.00 initial capital. "
                            "All 5 specialist agents are online for market analysis, asset comparisons, and risk-checked trade proposals."
                        ),
                        "createdAt": now,
                        "uiAction": None,
                        "tradeProposalEvaluation": None,
                        "meetingId": None,
                    }
                    conn.execute(
                        "INSERT INTO chat_messages (id, message_json, created_at) VALUES (?, ?, ?)",
                        (
                            welcome_msg["id"],
                            json.dumps(welcome_msg, ensure_ascii=False),
                            now,
                        ),
                    )

                    conn.execute(
                        """
                        INSERT INTO audit_logs (
                            id, timestamp, actor, source, action, severity, details_ar, details_en
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"aud_{uuid.uuid4().hex[:12]}",
                            now,
                            "SYSTEM_KERNEL",
                            "SYSTEM",
                            "BOOT_PAPER_SAFETY_LOCK",
                            "INFO",
                            "تم إقلاع مركز القيادة في وضع التداول الورقي الآمن (PAPER) وتفعيل جميع الضوابط لمحرك المخاطر الحتمي.",
                            "Command Center booted in safe PAPER trading mode with deterministic risk engine controls active.",
                        ),
                    )

            _INITIALIZED_TARGETS.add(target_key)
        finally:
            conn.close()

    return db_path


@contextmanager
def db_session() -> Iterator[Any]:
    """مدير سياق آمن للخيوط يوفر اتصال قاعدة بيانات (PostgreSQL أو SQLite) مع حفظ المعاملات تلقائياً."""
    init_db()
    with _DB_LOCK:
        conn, _ = _open_configured_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()


# ==============================================================================
# طبقة اتصال Redis للتخزين المؤقت، صلاحية المقترحات (TTL)، وأقفال منع التكرار
# ==============================================================================


def get_redis_url() -> str | None:
    """استرجاع عنوان خادم Redis من متغيرات البيئة."""
    url = (
        os.getenv("TRILUNAIR_REDIS_URL", "").strip()
        or os.getenv("REDIS_URL", "").strip()
    )
    return url or None


def get_redis_client() -> Any | None:
    """الحصول على عميل Redis نشط متصل عبر TCP عند ضبط REDIS_URL."""
    url = get_redis_url()
    if not url or redis_lib is None:
        return None
    cached = _REDIS_CLIENT_CACHE.get(url)
    if cached is not None:
        return cached
    client = redis_lib.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=1.5,
        socket_timeout=1.5,
    )
    _REDIS_CLIENT_CACHE[url] = client
    return client


def acquire_redis_idempotency_lock(
    namespace: str, key: str, ttl_seconds: int = 86400
) -> bool:
    """
    محاولة حجز قفل عدم تكرار ذري عبر Redis (SET NX EX).
    تعيد True إذا كان الطلب جديداً (أو إذا كان Redis غير مهيأ حيث تتولى قاعدة البيانات القفل الفريد)،
    وتعيد False إذا كان المفتاح مكرراً بالفعل في Redis.
    """
    client = get_redis_client()
    if client is None or not key:
        return True
    try:
        redis_key = f"trilunair:idem:{namespace}:{key}"
        acquired = client.set(redis_key, utc_now_iso(), nx=True, ex=ttl_seconds)
        return bool(acquired)
    except Exception:
        # في حال تعذر الوصول لـ Redis مؤقتاً تظل القيود الفريدة في PostgreSQL/SQLite حارساً إلزامياً
        return True


def cache_proposal_in_redis(
    proposal_id: str, payload: dict[str, Any], ttl_seconds: int
) -> None:
    """تخزين مقترح الصفقة في Redis مع مدة انتهاء الصلاحية التلقائية (TTL)."""
    client = get_redis_client()
    if client is None:
        return
    try:
        client.set(
            f"trilunair:proposal:{proposal_id}",
            json.dumps(payload, ensure_ascii=False),
            ex=max(1, int(ttl_seconds)),
        )
    except Exception:
        pass


def check_infrastructure_status() -> dict[str, Any]:
    """فحص الاتصال الحقيقي والاستدامة لكل من PostgreSQL / SQLite و Redis بشفافية كاملة."""
    pg_dsn = get_postgres_dsn()
    db_info: dict[str, Any] = {
        "engine": "postgresql" if pg_dsn else "sqlite",
        "connected": False,
        "persistenceVerified": False,
        "version": "",
        "latencyMs": 0.0,
    }

    t0 = time.perf_counter()
    try:
        with db_session() as conn:
            if pg_dsn:
                ver_row = conn.execute("SELECT version() AS v").fetchone()
                db_info["version"] = str(ver_row["v"]) if ver_row else "PostgreSQL"
            else:
                ver_row = conn.execute("SELECT sqlite_version() AS v").fetchone()
                db_info["version"] = (
                    f"SQLite {ver_row['v']}" if ver_row else "SQLite"
                )
            cnt_row = conn.execute("SELECT COUNT(*) AS cnt FROM system_state").fetchone()
            db_info["connected"] = True
            db_info["persistenceVerified"] = bool(cnt_row and int(cnt_row["cnt"]) == 1)
    except Exception as exc:
        db_info["error"] = str(exc)
    db_info["latencyMs"] = round((time.perf_counter() - t0) * 1000.0, 2)

    redis_url = get_redis_url()
    redis_info: dict[str, Any] = {
        "configured": bool(redis_url),
        "connected": False,
        "persistenceVerified": False,
        "mode": "unconfigured",
        "latencyMs": 0.0,
    }
    if redis_url:
        t1 = time.perf_counter()
        client = get_redis_client()
        if client is not None:
            try:
                probe_key = "trilunair:health:probe"
                probe_val = utc_now_iso()
                client.set(probe_key, probe_val, ex=60)
                read_back = client.get(probe_key)
                try:
                    srv_info = client.info() or {}
                except Exception:
                    srv_info = {}
                is_fake = (
                    not srv_info.get("redis_version")
                    or "fakeredis" in str(srv_info).lower()
                    or os.getenv("TRILUNAIR_REDIS_IS_MOCK", "").lower() in ("1", "true")
                )
                redis_info["connected"] = True
                redis_info["persistenceVerified"] = read_back == probe_val
                redis_info["mode"] = (
                    "mock-tcp-resp-server" if is_fake else "redis-native-tcp"
                )
                redis_info["redisVersion"] = srv_info.get("redis_version", "resp-compatible")
            except Exception as exc:
                redis_info["mode"] = "connection-error"
                redis_info["error"] = str(exc)
        redis_info["latencyMs"] = round((time.perf_counter() - t1) * 1000.0, 2)

    return {
        "database": db_info,
        "redis": redis_info,
        "timestamp": utc_now_iso(),
    }


def append_audit_log(
    actor: str,
    source: str,
    action: str,
    severity: str,
    details_ar: str,
    details_en: str,
    conn: Any | None = None,
) -> dict[str, Any]:
    """إضافة سجل تدقيق أمني جديد في جدول audit_logs وإرجاعه كقاموس."""
    entry = {
        "id": f"aud_{uuid.uuid4().hex[:12]}",
        "timestamp": utc_now_iso(),
        "actor": actor,
        "source": source,
        "action": action,
        "severity": severity,
        "detailsAr": details_ar,
        "detailsEn": details_en,
    }

    sql = """
        INSERT INTO audit_logs (
            id, timestamp, actor, source, action, severity, details_ar, details_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        entry["id"],
        entry["timestamp"],
        entry["actor"],
        entry["source"],
        entry["action"],
        entry["severity"],
        entry["detailsAr"],
        entry["detailsEn"],
    )

    if conn is not None:
        conn.execute(sql, params)
    else:
        with db_session() as local_conn:
            local_conn.execute(sql, params)

    return entry


def fetch_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    """استرجاع أحدث سجلات التدقيق الأمني مرتبة تنازلياً من الأحدث إلى الأقدم."""
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT id, timestamp, actor, source, action, severity,
                   details_ar AS "detailsAr", details_en AS "detailsEn"
            FROM audit_logs
            ORDER BY seq DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def check_audit_trail_health() -> bool:
    """التحقق الفعلي من سلامة وجاهزية جدول سجل التدقيق الأمني في قاعدة البيانات النشطة."""
    try:
        with db_session() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM audit_logs").fetchone()
            return row is not None and int(row["cnt"]) >= 1
    except Exception:
        return False


def reset_db_init_cache() -> None:
    """إعادة ضبط ذاكرة التهيئة المؤقتة عند تبديل محرك قاعدة البيانات أو عنوان Redis أثناء الاختبارات."""
    with _DB_LOCK:
        _INITIALIZED_TARGETS.clear()
        _REDIS_CLIENT_CACHE.clear()

