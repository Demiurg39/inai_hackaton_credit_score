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
    # Non-destructive migration for existing DBs
    try:
        await _db_connection.execute(
            "ALTER TABLE users ADD COLUMN period_available REAL NOT NULL DEFAULT 0"
        )
    except Exception:
        pass  # Column already exists
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
    await _db_connection.commit()


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
