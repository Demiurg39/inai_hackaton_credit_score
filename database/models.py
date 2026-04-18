"""
database/models.py — CRUD operations for users and transactions.
"""
from datetime import datetime, timezone
from typing import Optional, TypedDict

import aiosqlite

from database.db import get_db


class UserStatsSnapshot(TypedDict):
    avg_daily_spend: float
    std_daily_spend: float
    spend_velocity: float
    risk_tolerance: float
    last_computed_at: str


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


# ─────────────────────────── STATS CRUD ──────────────────────────────


async def get_user_stats(user_id: int) -> UserStatsSnapshot | None:
    """Fetch per-user spending stats from the users table."""
    async with get_db() as db:
        async with db.execute(
            "SELECT avg_daily_spend, std_daily_spend, spend_velocity, "
            "risk_tolerance, last_computed_at FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return UserStatsSnapshot(
                avg_daily_spend=row["avg_daily_spend"],
                std_daily_spend=row["std_daily_spend"],
                spend_velocity=row["spend_velocity"],
                risk_tolerance=row["risk_tolerance"],
                last_computed_at=row["last_computed_at"],
            )


async def upsert_user_stats(
    user_id: int,
    avg: float,
    std: float,
    velocity: float,
    tolerance: float,
) -> None:
    """Update the 5 stats columns in the users table, set last_computed_at."""
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute(
            """UPDATE users SET avg_daily_spend = ?, std_daily_spend = ?,
            spend_velocity = ?, risk_tolerance = ?, last_computed_at = ?
            WHERE user_id = ?""",
            (avg, std, velocity, tolerance, now, user_id),
        )
        await db.commit()


async def get_category_stats(user_id: int, category: str) -> aiosqlite.Row | None:
    """Fetch category-level stats for a user."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM user_category_stats WHERE user_id = ? AND category = ?",
            (user_id, category),
        ) as cursor:
            return await cursor.fetchone()


async def upsert_category_stats(
    user_id: int, category: str, amount: float
) -> None:
    """Insert or update avg_amount and tx_count in user_category_stats.

    Uses an incremental moving average: new_avg = (old_avg * count + amount) / (count + 1)
    """
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        async with db.execute(
            "SELECT avg_amount, tx_count FROM user_category_stats "
            "WHERE user_id = ? AND category = ?",
            (user_id, category),
        ) as cursor:
            row = await cursor.fetchone()
        if row:
            new_avg = (row["avg_amount"] * row["tx_count"] + amount) / (row["tx_count"] + 1)
            new_count = row["tx_count"] + 1
            await db.execute(
                "UPDATE user_category_stats SET avg_amount = ?, tx_count = ?, "
                "last_seen_at = ? WHERE user_id = ? AND category = ?",
                (new_avg, new_count, now, user_id, category),
            )
        else:
            await db.execute(
                "INSERT INTO user_category_stats (user_id, category, avg_amount, tx_count, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, category, amount, 1, now),
            )
        await db.commit()


async def get_category_threshold(user_id: int, category: str) -> aiosqlite.Row | None:
    """Get custom threshold for a user+category, or None if not set."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM user_category_threshold WHERE user_id = ? AND category = ?",
            (user_id, category),
        ) as cursor:
            return await cursor.fetchone()


async def upsert_category_threshold(
    user_id: int,
    category: str,
    fuzzy_threshold: float,
    survival_threshold: float,
) -> None:
    """Set or update custom threshold for a user+category."""
    async with get_db() as db:
        await db.execute(
            """INSERT OR REPLACE INTO user_category_threshold
            (user_id, category, fuzzy_threshold, survival_threshold)
            VALUES (?, ?, ?, ?)""",
            (user_id, category, fuzzy_threshold, survival_threshold),
        )
        await db.commit()


async def get_recurring_spends(user_id: int) -> list[aiosqlite.Row]:
    """Return all recurring spend rows for a user."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM user_recurring_spends WHERE user_id = ? ORDER BY id",
            (user_id,),
        ) as cursor:
            return await cursor.fetchall()


async def upsert_recurring_spend(
    user_id: int,
    category: str,
    avg_amount: float,
    interval_days: int,
    last_amount: float,
    last_date: str,
    confidence: float,
    next_expected: str,
) -> None:
    """Insert or replace a row in user_recurring_spends."""
    async with get_db() as db:
        await db.execute(
            """INSERT OR REPLACE INTO user_recurring_spends
            (user_id, category, avg_amount, interval_days, last_amount,
             last_date, confidence, next_expected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, category, avg_amount, interval_days, last_amount,
             last_date, confidence, next_expected),
        )
        await db.commit()


# ─────────────────────────── COMPUTE USER STATS ─────────────────────


async def compute_user_stats(user_id: int) -> UserStatsSnapshot:
    """
    Compute personalized spending signals from transaction history.

    Falls back to global defaults if user has < 5 approved transactions.
    """
    from datetime import timedelta

    async with get_db() as db:
        async with db.execute(
            """SELECT created_at, amount FROM transactions
            WHERE user_id = ? AND verdict = 'approved'
            ORDER BY created_at DESC LIMIT 90""",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()

    if len(rows) < 5:
        return UserStatsSnapshot(
            avg_daily_spend=0.0,
            std_daily_spend=0.0,
            spend_velocity=1.0,
            risk_tolerance=0.5,
            last_computed_at=datetime.now(timezone.utc).isoformat(),
        )

    # Group by day
    daily_totals: dict[str, float] = {}
    for row in rows:
        day = row["created_at"][:10]
        daily_totals[day] = daily_totals.get(day, 0.0) + row["amount"]

    amounts = sorted(daily_totals.values())
    n = len(amounts)
    avg = sum(amounts) / n
    std = (
        (sum((x - avg) ** 2 for x in amounts) / n) ** 0.5
        if n > 1 else 0.0
    )

    # Detect recurring patterns
    recurring = _detect_recurring(rows)
    for r in recurring:
        await upsert_recurring_spend(
            user_id,
            r["category"],
            r["avg_amount"],
            r["interval_days"],
            r["last_amount"],
            r["last_date"],
            r["confidence"],
            r["next_expected"],
        )

    snapshot = UserStatsSnapshot(
        avg_daily_spend=round(avg, 2),
        std_daily_spend=round(std, 2),
        spend_velocity=1.0,
        risk_tolerance=0.5,
        last_computed_at=datetime.now(timezone.utc).isoformat(),
    )

    await upsert_user_stats(
        user_id,
        avg=snapshot["avg_daily_spend"],
        std=snapshot["std_daily_spend"],
        velocity=snapshot["spend_velocity"],
        tolerance=snapshot["risk_tolerance"],
    )

    return snapshot


def _detect_recurring(transactions: list[aiosqlite.Row]) -> list[dict]:
    """Group transactions by approximate amount and interval to find recurring patterns."""
    from datetime import timedelta

    # Sort by date
    tx_list = sorted(transactions, key=lambda r: r["created_at"])
    recurring = []
    # Group by category (description)
    by_category: dict[str, list[aiosqlite.Row]] = {}
    for tx in tx_list:
        cat = tx.get("description", "other")[:20]
        by_category.setdefault(cat, []).append(tx)

    for cat, txs in by_category.items():
        if len(txs) < 3:
            continue
        # Check intervals between consecutive transactions
        amounts = [t["amount"] for t in txs]
        for ref_amt in set(amounts):
            matching = [t for t in txs if abs(t["amount"] - ref_amt) / ref_amt < 0.1]
            if len(matching) < 3:
                continue
            # Compute intervals
            intervals = []
            for i in range(1, len(matching)):
                d1 = datetime.fromisoformat(matching[i]["created_at"])
                d0 = datetime.fromisoformat(matching[i - 1]["created_at"])
                intervals.append((d0 - d1).days)
            if not intervals:
                continue
            avg_interval = sum(intervals) / len(intervals)
            if 25 <= avg_interval <= 35:  # monthly
                interval_days = 30
            elif 6 <= avg_interval <= 8:  # weekly
                interval_days = 7
            else:
                continue
            recurring.append({
                "category": cat,
                "avg_amount": ref_amt,
                "interval_days": interval_days,
                "last_amount": matching[-1]["amount"],
                "last_date": matching[-1]["created_at"],
                "confidence": min(len(matching) / 10, 1.0),
                "next_expected": (datetime.fromisoformat(matching[-1]["created_at"])
                                   + timedelta(days=interval_days)).isoformat(),
            })
    return recurring
