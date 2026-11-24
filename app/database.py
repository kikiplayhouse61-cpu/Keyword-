import asyncio
import logging
import os
import aiosqlite
from typing import Optional, List, Dict, Any

from app.config import Config

logger = logging.getLogger(__name__)

# Global single write lock — prevents "database is locked" errors
_write_lock = asyncio.Lock()

# Schema version — bump when schema changes
SCHEMA_VERSION = 3


async def get_connection() -> aiosqlite.Connection:
    """Return an open connection with WAL mode and busy timeout."""
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = await aiosqlite.connect(Config.DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA busy_timeout=10000")
    await conn.execute("PRAGMA synchronous=NORMAL")
    return conn


async def init_database():
    """Create all tables if they don't exist and run migrations."""
    async with _write_lock:
        async with await get_connection() as db:
            # schema_version table first
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                )
            """)
            await db.commit()

            row = await (await db.execute("SELECT version FROM schema_version LIMIT 1")).fetchone()
            current_version = row["version"] if row else 0

            if current_version < SCHEMA_VERSION:
                await _run_migrations(db, current_version)

            # Ensure base tables exist regardless
            await _create_tables(db)
            await db.commit()
            logger.info(f"Database ready at {Config.DATABASE_PATH}")


async def _create_tables(db: aiosqlite.Connection):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword     TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            enabled     INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id        INTEGER NOT NULL UNIQUE,
            group_name      TEXT    NOT NULL,
            group_username  TEXT,
            member_count    INTEGER,
            last_seen       TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword         TEXT    NOT NULL,
            sender_name     TEXT,
            sender_username TEXT,
            sender_id       INTEGER,
            group_name      TEXT,
            group_id        INTEGER,
            message_text    TEXT,
            message_id      INTEGER,
            alerted_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS processed_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            message_key TEXT    NOT NULL UNIQUE,
            processed_at TEXT   NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key     TEXT NOT NULL PRIMARY KEY,
            value   TEXT NOT NULL
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_state (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            message_id  INTEGER,
            chat_id     INTEGER,
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Indexes
    await db.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_alerted_at ON alert_history(alerted_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_processed_messages_key ON processed_messages(message_key)")


async def _run_migrations(db: aiosqlite.Connection, from_version: int):
    logger.info(f"Running migrations from version {from_version} to {SCHEMA_VERSION}")

    if from_version < 1:
        # Initial schema — handled by _create_tables
        pass

    if from_version < 2:
        # Add enabled column to keywords if missing
        try:
            await db.execute("ALTER TABLE keywords ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass  # Column already exists

    if from_version < 3:
        # Add group_username to groups if missing
        try:
            await db.execute("ALTER TABLE groups ADD COLUMN group_username TEXT")
        except Exception:
            pass

    # Update schema version
    await db.execute("DELETE FROM schema_version")
    await db.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    await db.commit()
    logger.info(f"Migration complete — now at version {SCHEMA_VERSION}")


# ─────────────────────────── KEYWORD OPERATIONS ──────────────────────────────

async def add_keyword(keyword: str) -> bool:
    """Returns True if added, False if duplicate."""
    keyword = keyword.strip()
    async with _write_lock:
        try:
            async with await get_connection() as db:
                await db.execute(
                    "INSERT INTO keywords (keyword) VALUES (?)",
                    (keyword,)
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False


async def remove_keyword(keyword_id: int) -> bool:
    async with _write_lock:
        async with await get_connection() as db:
            cur = await db.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
            await db.commit()
            return cur.rowcount > 0


async def toggle_keyword(keyword_id: int) -> Optional[bool]:
    """Toggle enabled state. Returns new state or None if not found."""
    async with _write_lock:
        async with await get_connection() as db:
            row = await (await db.execute(
                "SELECT enabled FROM keywords WHERE id = ?", (keyword_id,)
            )).fetchone()
            if not row:
                return None
            new_state = 0 if row["enabled"] else 1
            await db.execute(
                "UPDATE keywords SET enabled = ? WHERE id = ?", (new_state, keyword_id)
            )
            await db.commit()
            return bool(new_state)


async def get_all_keywords() -> List[Dict[str, Any]]:
    async with await get_connection() as db:
        rows = await (await db.execute(
            "SELECT id, keyword, enabled, created_at FROM keywords ORDER BY id"
        )).fetchall()
        return [dict(r) for r in rows]


async def get_active_keywords() -> List[str]:
    async with await get_connection() as db:
        rows = await (await db.execute(
            "SELECT keyword FROM keywords WHERE enabled = 1"
        )).fetchall()
        return [r["keyword"] for r in rows]


async def search_keywords(query: str) -> List[Dict[str, Any]]:
    async with await get_connection() as db:
        rows = await (await db.execute(
            "SELECT id, keyword, enabled, created_at FROM keywords WHERE keyword LIKE ? ORDER BY id",
            (f"%{query}%",)
        )).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────── GROUP OPERATIONS ────────────────────────────────

async def upsert_group(group_id: int, group_name: str, group_username: Optional[str] = None, member_count: Optional[int] = None):
    async with _write_lock:
        async with await get_connection() as db:
            await db.execute("""
                INSERT INTO groups (group_id, group_name, group_username, member_count, last_seen)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(group_id) DO UPDATE SET
                    group_name = excluded.group_name,
                    group_username = excluded.group_username,
                    member_count = excluded.member_count,
                    last_seen = datetime('now')
            """, (group_id, group_name, group_username, member_count))
            await db.commit()


async def get_all_groups() -> List[Dict[str, Any]]:
    async with await get_connection() as db:
        rows = await (await db.execute(
            "SELECT * FROM groups ORDER BY group_name"
        )).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────── ALERT HISTORY ───────────────────────────────────

async def save_alert(
    keyword: str,
    sender_name: Optional[str],
    sender_username: Optional[str],
    sender_id: Optional[int],
    group_name: Optional[str],
    group_id: Optional[int],
    message_text: Optional[str],
    message_id: Optional[int],
):
    async with _write_lock:
        async with await get_connection() as db:
            await db.execute("""
                INSERT INTO alert_history
                (keyword, sender_name, sender_username, sender_id, group_name, group_id, message_text, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (keyword, sender_name, sender_username, sender_id, group_name, group_id, message_text, message_id))
            await db.commit()


async def get_alert_history(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    async with await get_connection() as db:
        rows = await (await db.execute(
            "SELECT * FROM alert_history ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )).fetchall()
        return [dict(r) for r in rows]


async def get_alert_count_today() -> int:
    async with await get_connection() as db:
        row = await (await db.execute(
            "SELECT COUNT(*) as cnt FROM alert_history WHERE date(alerted_at) = date('now')"
        )).fetchone()
        return row["cnt"] if row else 0


async def get_total_alert_count() -> int:
    async with await get_connection() as db:
        row = await (await db.execute("SELECT COUNT(*) as cnt FROM alert_history")).fetchone()
        return row["cnt"] if row else 0


async def get_top_keywords(limit: int = 5) -> List[Dict[str, Any]]:
    async with await get_connection() as db:
        rows = await (await db.execute("""
            SELECT keyword, COUNT(*) as hits
            FROM alert_history
            GROUP BY keyword
            ORDER BY hits DESC
            LIMIT ?
        """, (limit,))).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────── DEDUP ───────────────────────────────────────────

async def is_message_processed(message_key: str) -> bool:
    async with await get_connection() as db:
        row = await (await db.execute(
            "SELECT id FROM processed_messages WHERE message_key = ?", (message_key,)
        )).fetchone()
        return row is not None


async def mark_message_processed(message_key: str):
    async with _write_lock:
        async with await get_connection() as db:
            try:
                await db.execute(
                    "INSERT INTO processed_messages (message_key) VALUES (?)", (message_key,)
                )
                await db.commit()
            except aiosqlite.IntegrityError:
                pass  # Already processed


async def cleanup_old_processed(days: int = 7):
    """Prune old dedup records to keep table small."""
    async with _write_lock:
        async with await get_connection() as db:
            await db.execute(
                "DELETE FROM processed_messages WHERE processed_at < datetime('now', ?)",
                (f"-{days} days",)
            )
            await db.commit()


# ─────────────────────────── SETTINGS ────────────────────────────────────────

async def get_setting(key: str, default: str = "") -> str:
    async with await get_connection() as db:
        row = await (await db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )).fetchone()
        return row["value"] if row else default


async def set_setting(key: str, value: str):
    async with _write_lock:
        async with await get_connection() as db:
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value)
            )
            await db.commit()


# ─────────────────────────── DASHBOARD STATE ─────────────────────────────────

async def get_dashboard_state() -> Optional[Dict[str, Any]]:
    async with await get_connection() as db:
        row = await (await db.execute("SELECT * FROM dashboard_state WHERE id = 1")).fetchone()
        return dict(row) if row else None


async def save_dashboard_state(message_id: int, chat_id: int):
    async with _write_lock:
        async with await get_connection() as db:
            await db.execute("""
                INSERT INTO dashboard_state (id, message_id, chat_id)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    message_id = excluded.message_id,
                    chat_id = excluded.chat_id,
                    updated_at = datetime('now')
            """, (message_id, chat_id))
            await db.commit()


async def clear_dashboard_state():
    async with _write_lock:
        async with await get_connection() as db:
            await db.execute("DELETE FROM dashboard_state WHERE id = 1")
            await db.commit()
