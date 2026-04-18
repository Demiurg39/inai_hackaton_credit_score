import sys
sys.path.insert(0, "/home/demi/dev/projects/python/inai_hackaton")

from services.reserve_advisor import compute_recommended_reserve, RecommendedReserve

def test_no_recurring_fallback():
    """No recurring spends → fallback: 15% of balance"""
    result = compute_recommended_reserve(
        balance=10000.0,
        current=2000.0,
        recurring_spends=[],
        avg_daily_spend=500.0,
    )
    assert result["recommended"] == 1500.0
    assert result["confidence"] == 0.0

def test_with_recurring_covers_buffer():
    """One recurring of 2000 + buffer should give recommended = 2000 + buffer"""
    recurring = [{"amount": 2000.0, "interval_days": 30, "confidence": 0.8, "category": "Spotify"}]
    result = compute_recommended_reserve(
        balance=15000.0,
        current=1000.0,
        recurring_spends=recurring,
        avg_daily_spend=500.0,
    )
    # buffer = max(500*3, 500) = 1500
    assert result["recommended"] == 3500.0
    assert result["covered_recurring"] == 2000.0

def test_confidence_low_with_few_recurring():
    """1 recurring with 0.5 confidence → confidence = 0.5"""
    recurring = [{"amount": 1000.0, "interval_days": 30, "confidence": 0.5, "category": "Netflix"}]
    result = compute_recommended_reserve(
        balance=10000.0,
        current=1000.0,
        recurring_spends=recurring,
        avg_daily_spend=300.0,
    )
    assert result["confidence"] == 0.5

def test_min_buffer():
    """avg_daily_spend very low → min buffer 500₽"""
    recurring = [{"amount": 500.0, "interval_days": 30, "confidence": 0.9, "category": "Подписка"}]
    result = compute_recommended_reserve(
        balance=5000.0,
        current=500.0,
        recurring_spends=recurring,
        avg_daily_spend=50.0,
    )
    # buffer = max(50*3, 500) = 500
    assert result["recommended"] == 1000.0