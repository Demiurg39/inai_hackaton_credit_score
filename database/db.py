"""
database/db.py — SQLite connection pool and table initialization.
"""
from contextlib import asynccontextmanager

import aiosqlite

DB_PATH = "finguard.db"


@asynccontextmanager
async def get_db():
    """
    Async context manager that opens an aiosqlite connection and yields it.

    Usage:
        async with get_db() as db:
            ...

    Using aiosqlite.connect() as a plain async context manager is the only
    safe pattern — awaiting it first and then entering it again would try to
    start the background thread twice, raising RuntimeError.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    """Create tables if they don't exist. Called once on bot startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
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
        # Non-destructive migration for existing DBs
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN period_available REAL NOT NULL DEFAULT 0"
            )
        except Exception:
            pass  # Column already exists
            
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN period_start_date TEXT NOT NULL DEFAULT ''"
            )
        except Exception:
            pass  # Column already exists
            
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL    NOT NULL,
                description TEXT,
                verdict     TEXT,
                created_at  TEXT    NOT NULL DEFAULT ''
            )
        """)
        await db.commit()
