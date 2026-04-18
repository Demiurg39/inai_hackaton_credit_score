"""
Tests for stats CRUD in database/models.py
TDD: Write tests first (they fail), implement in models.py, tests pass.
"""
import pytest
import os
import tempfile
import asyncio
import sys

sys.path.insert(0, "/home/demi/dev/projects/python/inai_hackaton")


def get_temp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def test_get_user_stats_default():
    """
    Step 1: Verify get_user_stats returns defaults for non-existent user.
    TDD: This FAILS until get_user_stats is implemented.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()
            from database.models import get_user_stats
            stats = await get_user_stats(99999)
            assert stats is None or stats["risk_tolerance"] == 0.5

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_get_user_stats_existing_user():
    """
    Verify get_user_stats returns correct data for existing user.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()
            from database.models import create_user, get_user_stats
            await create_user(12345)
            stats = await get_user_stats(12345)
            assert stats is not None
            assert "avg_daily_spend" in stats
            assert "risk_tolerance" in stats

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_upsert_user_stats():
    """
    Step 3: Verify upsert_user_stats updates all 5 stats columns.
    TDD: This FAILS until upsert_user_stats is implemented.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()
            from database.models import create_user, upsert_user_stats, get_user_stats
            await create_user(123)
            await upsert_user_stats(123, avg=500.0, std=150.0, velocity=1.1, tolerance=0.3)
            stats = await get_user_stats(123)
            assert stats["avg_daily_spend"] == 500.0
            assert stats["std_daily_spend"] == 150.0
            assert stats["spend_velocity"] == 1.1
            assert stats["risk_tolerance"] == 0.3

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_upsert_category_stats():
    """
    Step 5: Verify upsert_category_stats handles insert and update with moving average.
    TDD: This FAILS until upsert_category_stats and get_category_stats are implemented.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()
            from database.models import create_user, upsert_category_stats, get_category_stats
            await create_user(123)
            await upsert_category_stats(123, "Food & Drink", 250.0)
            await upsert_category_stats(123, "Food & Drink", 270.0)  # update
            stat = await get_category_stats(123, "Food & Drink")
            assert stat["tx_count"] == 2
            assert 260.0 < stat["avg_amount"] < 270.0

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_get_category_stats_not_found():
    """
    Verify get_category_stats returns None for non-existent user/category.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()
            from database.models import get_category_stats
            stat = await get_category_stats(99999, "Nonexistent")
            assert stat is None

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_get_recurring_spends_empty():
    """
    Verify get_recurring_spends returns empty list for user with no recurring spends.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()
            from database.models import get_recurring_spends
            rows = await get_recurring_spends(99999)
            assert rows == []

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_upsert_recurring_spend():
    """
    Step 7: Verify upsert_recurring_spend inserts a recurring spend row.
    TDD: This FAILS until upsert_recurring_spend is implemented.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()
            from database.models import create_user, upsert_recurring_spend, get_recurring_spends
            await create_user(123)
            await upsert_recurring_spend(
                user_id=123,
                category="Spotify",
                avg_amount=9.99,
                interval_days=30,
                last_amount=9.99,
                last_date="2026-04-01T00:00:00",
                confidence=0.8,
                next_expected="2026-05-01T00:00:00",
            )
            rows = await get_recurring_spends(123)
            assert len(rows) == 1
            assert rows[0]["category"] == "Spotify"
            assert rows[0]["avg_amount"] == 9.99
            assert rows[0]["confidence"] == 0.8

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_upsert_recurring_spend_replace():
    """
    Verify upsert_recurring_spend replaces existing row for same user+category.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()
            from database.models import create_user, upsert_recurring_spend, get_recurring_spends
            await create_user(123)
            await upsert_recurring_spend(
                user_id=123,
                category="Netflix",
                avg_amount=15.0,
                interval_days=30,
                last_amount=15.0,
                last_date="2026-04-01T00:00:00",
                confidence=0.5,
                next_expected="2026-05-01T00:00:00",
            )
            await upsert_recurring_spend(
                user_id=123,
                category="Netflix",
                avg_amount=17.0,
                interval_days=30,
                last_amount=17.0,
                last_date="2026-04-15T00:00:00",
                confidence=0.9,
                next_expected="2026-05-15T00:00:00",
            )
            rows = await get_recurring_spends(123)
            assert len(rows) == 1
            assert rows[0]["avg_amount"] == 17.0
            assert rows[0]["confidence"] == 0.9

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]
