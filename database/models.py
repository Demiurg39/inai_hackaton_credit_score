"""
database/models.py — CRUD operations for users and transactions.
"""
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from database.db import get_db


# ─────────────────────────── USER CRUD ────────────────────────────


async def get_user(user_id: int) -> Optional[aiosqlite.Row]:
    """Fetch a user row by Telegram user_id. Returns None if not found."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()


async def create_user(user_id: int) -> None:
    """Insert a new user skeleton (onboarded=0) if not already present."""
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users
                (user_id, balance, reserve, next_income_date, onboarded, created_at)
            VALUES (?, 0, 0, '', 0, ?)
            """,
            (user_id, now),
        )
        await db.commit()


async def update_user_balance(user_id: int, balance: float) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?", (balance, user_id)
        )
        await db.commit()


async def update_user_reserve(user_id: int, reserve: float) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET reserve = ? WHERE user_id = ?", (reserve, user_id)
        )
        await db.commit()


async def update_user_income_date(user_id: int, date_str: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET next_income_date = ? WHERE user_id = ?",
            (date_str, user_id),
        )
        await db.commit()


async def set_onboarded(
    user_id: int,
    balance: float,
    reserve: float,
    income_date: str,
) -> None:
    """Finalize onboarding: save all three fields and mark onboarded=1."""
    period_available = max(balance - reserve, 0.0)
    async with get_db() as db:
        await db.execute(
            """
            UPDATE users
            SET balance = ?, reserve = ?, next_income_date = ?, 
                period_available = ?, onboarded = 1
            WHERE user_id = ?
            """,
            (balance, reserve, income_date, period_available, user_id),
        )
        await db.commit()


async def reset_period_available(user_id: int, new_period_available: float) -> None:
    """Reset the period baseline (used when user updates settings manually)."""
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET period_available = ? WHERE user_id = ?",
            (max(new_period_available, 0.0), user_id),
        )
        await db.commit()


# ─────────────────────────── TRANSACTION CRUD ─────────────────────


async def add_transaction(
    user_id: int,
    amount: float,
    description: str,
    verdict: str,
) -> None:
    """Persist a purchase evaluation result."""
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO transactions (user_id, amount, description, verdict, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, amount, description, verdict, now),
        )
        await db.commit()


async def get_recent_transactions(
    user_id: int, limit: int = 5
) -> list[aiosqlite.Row]:
    """Return the most recent `limit` transactions for a user."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cursor:
            return await cursor.fetchall()
