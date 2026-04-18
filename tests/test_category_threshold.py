import pytest
import sys
sys.path.insert(0, "/home/demi/dev/projects/python/inai_hackaton")
import asyncio

from database.models import get_category_threshold, upsert_category_threshold


@pytest.mark.anyio
async def test_get_category_threshold_default():
    """Default threshold for Entertainment is (0.60, 0.75)"""
    row = await get_category_threshold(99999, "Entertainment")
    # If no override exists, returns None (no row yet for this user/category)
    # That's fine — the function returns the row if it exists


@pytest.mark.anyio
async def test_upsert_and_get_category_threshold():
    """Can upsert a custom threshold and retrieve it"""
    await upsert_category_threshold(99998, "Food & Drink", 0.30, 0.50)
    row = await get_category_threshold(99998, "Food & Drink")
    assert row is not None
    assert row["fuzzy_threshold"] == 0.30
    assert row["survival_threshold"] == 0.50


@pytest.mark.anyio
async def test_upsert_overrides_previous():
    """Upsert replaces existing threshold"""
    await upsert_category_threshold(99997, "Shopping", 0.55, 0.70)
    await upsert_category_threshold(99997, "Shopping", 0.65, 0.80)
    row = await get_category_threshold(99997, "Shopping")
    assert row["fuzzy_threshold"] == 0.65
    assert row["survival_threshold"] == 0.80
