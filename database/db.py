"""
database/db.py — SQLite connection pool and table initialization.
"""
import os
from contextlib import asynccontextmanager

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "finguard.db")
_db_connection: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Create tables if they don't exist. Called once on bot startup."""
    global _db_connection
    _db_connection = await aiosqlite.connect(DB_PATH)
    _db_connection.row_factory = aiosqlite.Row

    # --- Base users table ---
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id          INTEGER PRIMARY KEY,
            balance          REAL    NOT NULL DEFAULT 0,
            reserve          REAL    NOT NULL DEFAULT 0,
            next_income_date TEXT    NOT NULL DEFAULT '',
            period_available REAL    NOT NULL DEFAULT 0,
            onboarded        INTEGER NOT NULL DEFAULT 0,
            created_at       TEXT    NOT NULL DEFAULT ''
        )
    """)
    # --- Non-destructive migrations for existing DBs ---
    await _migrate_users(_db_connection)

    # --- Transactions table ---
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL    NOT NULL,
            description TEXT,
            verdict     TEXT,
            created_at  TEXT    NOT NULL DEFAULT ''
        )
    """)

    # --- Personalized stats: user_category_stats ---
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS user_category_stats (
            user_id         INTEGER NOT NULL,
            category        TEXT    NOT NULL,
            avg_amount      REAL    NOT NULL DEFAULT 0,
            tx_count        INTEGER NOT NULL DEFAULT 0,
            last_seen_at    TEXT    NOT NULL DEFAULT '',
            PRIMARY KEY (user_id, category)
        )
    """)

    # --- Personalized stats: user_recurring_spends ---
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS user_recurring_spends (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            category        TEXT    NOT NULL,
            avg_amount      REAL    NOT NULL DEFAULT 0,
            interval_days   INTEGER NOT NULL DEFAULT 30,
            last_amount     REAL    NOT NULL DEFAULT 0,
            last_date       TEXT    NOT NULL DEFAULT '',
            confidence      REAL    NOT NULL DEFAULT 0,
            next_expected   TEXT    NOT NULL DEFAULT '',
            UNIQUE (user_id, category)
        )
    """)

    # --- Per-category risk thresholds ---
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS user_category_threshold (
            user_id             INTEGER NOT NULL,
            category            TEXT    NOT NULL,
            fuzzy_threshold     REAL    NOT NULL DEFAULT 0.52,
            survival_threshold  REAL    NOT NULL DEFAULT 0.65,
            PRIMARY KEY (user_id, category)
        )
    """)

    await _db_connection.commit()


async def _migrate_users(conn: aiosqlite.Connection) -> None:
    """Add missing columns to users table (non-destructive migrations)."""
    await _add_column(conn, "period_available", "REAL NOT NULL DEFAULT 0")
    await _add_column(conn, "period_start_date", "TEXT NOT NULL DEFAULT ''")
    # --- Personalized stats columns ---
    await _add_column(conn, "avg_daily_spend", "REAL NOT NULL DEFAULT 0")
    await _add_column(conn, "std_daily_spend", "REAL NOT NULL DEFAULT 0")
    await _add_column(conn, "spend_velocity", "REAL NOT NULL DEFAULT 1.0")
    await _add_column(conn, "risk_tolerance", "REAL NOT NULL DEFAULT 0.5")
    await _add_column(conn, "last_computed_at", "TEXT NOT NULL DEFAULT ''")
    # --- Notification columns ---
    await _add_column(conn, "notify_enabled", "INTEGER NOT NULL DEFAULT 0")
    await _add_column(conn, "notify_time", "TEXT NOT NULL DEFAULT '10:00'")
    await _add_column(conn, "last_notification_date", "TEXT NOT NULL DEFAULT ''")


async def _add_column(conn: aiosqlite.Connection, column: str, typedecl: str) -> None:
    """Add a column to users table if it doesn't exist."""
    try:
        await conn.execute(f"ALTER TABLE users ADD COLUMN {column} {typedecl}")
    except Exception:
        pass  # Column already exists


async def close_db() -> None:
    """Close the global database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None


@asynccontextmanager
async def get_db():
    """
    Async context manager that yields the global aiosqlite connection.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db