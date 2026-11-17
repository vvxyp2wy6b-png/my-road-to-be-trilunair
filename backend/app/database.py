"""
وحدة التخزين المستديم بقاعدة بيانات SQLite لنظام مركز القيادة الهولوغرامي.
المشروع: My Road to be Trilunair Dr.MaJoOoOoOoD

مسؤوليات هذه الوحدة:
1. تهيئة جداول SQLite تلقائياً في المسار المحدد عبر متغير البيئة TRILUNAIR_DB_PATH.
2. ضمان إقلاع النظام دائماً في وضع التداول الورقي الآمن (PAPER) عند التهيئة الأولى،
   مع تعطيل التداول الحقيقي (liveAuthorized=False) وجهوزية مفتاح الإيقاف الطارئ.
3. بذر المحفظة التجريبية برأسمال ابتدائي قدره 1,000,000.00 دولار أمريكي ومراكز واقعية صغيرة
   (0.5 BTC-USD و 150 NVDA) لعرض مؤشرات الربح والخسارة والقيمة المعرضة للمخاطر فوراً.
4. حفظ السمات المخصصة، حالة السمة النشطة، مقترحات الصفقات، الصفقات المنفذة،
   سجل المحادثات، اجتماعات الوكلاء، وسجل التدقيق الأمني الشامل.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterator
import uuid

DEFAULT_DB_PATH = str(Path(__file__).resolve().parents[1] / "data" / "trilunair.db")
INITIAL_PAPER_CAPITAL_USD = 1_000_000.00
DEFAULT_MAX_DRAWDOWN_PCT = 5.0

_DB_LOCK = threading.RLock()
_INITIALIZED_DB_FILES: set[str] = set()


def utc_now_iso() -> str:
    """إرجاع الطابع الزمني الحالي بصيغة ISO-8601 القياسية بالتوقيت العالمي UTC."""
    return datetime.now(timezone.utc).isoformat()


def get_db_path() -> Path:
    """استرجاع مسار قاعدة البيانات الفعلي من متغير البيئة TRILUNAIR_DB_PATH أو المسار الافتراضي."""
    raw_path = os.getenv("TRILUNAIR_DB_PATH", "").strip() or DEFAULT_DB_PATH
    resolved = Path(raw_path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _connect_raw(db_path: Path) -> sqlite3.Connection:
    """إنشاء اتصال SQLite مهيأ بوضع WAL لسلامة التزامن والأداء العالي."""
    conn = sqlite3.connect(str(db_path), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(force_recheck: bool = False) -> Path:
    """
    تهيئة مخطط قاعدة البيانات وبذر البيانات الابتدائية الآمنة عند أول تشغيل.
    يضمن دائماً أن وضع التداول الابتدائي هو PAPER وأن التداول الحقيقي غير مفعل.
    """
    db_path = get_db_path()
    db_key = str(db_path)

    with _DB_LOCK:
        if not force_recheck and db_key in _INITIALIZED_DB_FILES and db_path.exists():
            return db_path

        conn = _connect_raw(db_path)
        try:
            with conn:
                conn.executescript(
                    """
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
                        created_at TEXT NOT NULL
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
                )

                # التحقق مما إذا كانت حالة النظام موجودة مسبقاً أم أنها الإقلاع الأول
                existing_state = conn.execute(
                    "SELECT id FROM system_state WHERE id = 1"
                ).fetchone()

                if existing_state is None:
                    now = utc_now_iso()
                    # حساب التكلفة الابتدائية للمركزين التجريبيين:
                    # 0.5 BTC-USD بسعر دخول 94,200.00 = 47,100.00$
                    # 150 NVDA بسعر دخول 134.50 = 20,175.00$
                    # إجمالي التكلفة = 67,275.00$ -> الرصيد النقدي المتبقي = 932,725.00$
                    btc_seed_qty = 0.5
                    btc_seed_entry = 94_200.00
                    nvda_seed_qty = 150.0
                    nvda_seed_entry = 134.50
                    seeded_cost = (btc_seed_qty * btc_seed_entry) + (
                        nvda_seed_qty * nvda_seed_entry
                    )
                    initial_cash = round(INITIAL_PAPER_CAPITAL_USD - seeded_cost, 2)

                    # فرض وضع التداول الورقي PAPER دائماً عند التهيئة الأولى دون استثناء
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

                    # بذر المراكز الابتدائية الصغيرة لثراء لوحة المحفظة ومؤشرات المخاطر
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

                    # تسجيل أوامر التأسيس الورقية في سجل الصفقات
                    conn.executemany(
                        """
                        INSERT INTO orders (
                            order_id, proposal_id, symbol, side, order_type,
                            quantity, executed_price, notional_usd, total_fee_usd,
                            trading_mode, source, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                "ord_seed_btc01",
                                "prop_seed_btc01",
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

                    # تهيئة السمة الافتراضية الملكية الذهبية (Royal Gold)
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

                    # إضافة رسالة ترحيبية استراتيجية في سجل المحادثة
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

                    # تسجيل حدث الإقلاع الآمن في سجل التدقيق الأمني
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
                            "تم إقلاع مركز القيادة في وضع التداول الورقي الآمن (PAPER) وتفعيل جميع الضوابط الخمسة لمحرك المخاطر الحتمي.",
                            "Command Center booted in safe PAPER trading mode with all 5 deterministic risk engine controls active.",
                        ),
                    )

            _INITIALIZED_DB_FILES.add(db_key)
        finally:
            conn.close()

    return db_path


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """مدير سياق آمن للخيوط يوفر اتصال قاعدة بيانات مهيأ مع حفظ المعاملات تلقائياً."""
    db_path = init_db()
    with _DB_LOCK:
        conn = _connect_raw(db_path)
        try:
            with conn:
                yield conn
        finally:
            conn.close()


def append_audit_log(
    actor: str,
    source: str,
    action: str,
    severity: str,
    details_ar: str,
    details_en: str,
    conn: sqlite3.Connection | None = None,
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
                   details_ar AS detailsAr, details_en AS detailsEn
            FROM audit_logs
            ORDER BY seq DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def check_audit_trail_health() -> bool:
    """التحقق الفعلي من سلامة وجاهزية جدول سجل التدقيق الأمني في SQLite."""
    try:
        with db_session() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM audit_logs").fetchone()
            return row is not None and int(row["cnt"]) >= 1
    except Exception:
        return False
