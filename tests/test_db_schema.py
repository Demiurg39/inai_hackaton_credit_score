"""
Tests for personalized stats schema in database/db.py
TDD: Write tests first (they fail), implement schema in db.py, tests pass.
"""
import pytest
import os
import tempfile
import asyncio
import sys

# Add project root to path
sys.path.insert(0, "/home/demi/dev/projects/python/inai_hackaton")


def get_temp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def test_users_table_has_5_new_columns():
    """
    Step 1: Verify the 5 new columns exist on users table after init_db().
    TDD: This FAILS until db.py is updated with the new columns.
    """
    path = get_temp_db_path()
    try:
        # Set temp DB path so init_db uses it
        os.environ["DB_PATH"] = path

        async def run():
            # Import and call init_db - this should create the new columns
            from database.db import init_db
            await init_db()

            # Verify columns exist
            import aiosqlite
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("PRAGMA table_info(users)") as cursor:
                    cols = {row["name"] for row in await cursor.fetchall()}

            expected = {
                "avg_daily_spend", "std_daily_spend", "spend_velocity",
                "risk_tolerance", "last_computed_at"
            }
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_user_category_stats_table_schema():
    """
    Step 2: Verify user_category_stats table exists with correct schema.
    TDD: This FAILS until db.py creates this table in init_db().
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()

            import aiosqlite
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("PRAGMA table_info(user_category_stats)") as cursor:
                    cols = {row["name"] for row in await cursor.fetchall()}

            expected = {"user_id", "category", "avg_amount", "tx_count", "last_seen_at"}
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_user_recurring_spends_table_schema():
    """
    Step 3: Verify user_recurring_spends table exists with correct schema.
    TDD: This FAILS until db.py creates this table in init_db().
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()

            import aiosqlite
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("PRAGMA table_info(user_recurring_spends)") as cursor:
                    cols = {row["name"] for row in await cursor.fetchall()}

            expected = {
                "id", "user_id", "category", "avg_amount", "interval_days",
                "last_amount", "last_date", "confidence", "next_expected"
            }
            assert expected.issubset(cols), f"Missing columns: {expected - cols}"

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_user_category_stats_primary_key():
    """
    Step 2b: Verify (user_id, category) is the primary key on user_category_stats.
    TDD: This FAILS until db.py creates the composite primary key.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()

            import aiosqlite
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='user_category_stats'"
                ) as cursor:
                    indexes = await cursor.fetchall()
            pk_indexes = [i for i in indexes if "primary" in i["name"].lower()]
            assert len(pk_indexes) >= 1, "user_category_stats should have a primary key index"

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]


def test_all_tables_exist_after_migration():
    """
    Step 4: Integration test - all tables present after full migration.
    TDD: This FAILS until db.py creates all new tables.
    """
    path = get_temp_db_path()
    try:
        os.environ["DB_PATH"] = path

        async def run():
            from database.db import init_db
            await init_db()

            import aiosqlite
            async with aiosqlite.connect(path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ) as cursor:
                    tables = {row["name"] for row in await cursor.fetchall()}

            expected_tables = {"users", "transactions", "user_category_stats", "user_recurring_spends"}
            assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        asyncio.run(run())
    finally:
        os.unlink(path)
        if "DB_PATH" in os.environ:
            del os.environ["DB_PATH"]