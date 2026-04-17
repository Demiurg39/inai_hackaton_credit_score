from datetime import date
from services.calculator import evaluate_purchase

def test_evaluate_purchase_basic():
    result = evaluate_purchase(
        amount=30.0,
        balance=1000.0,
        reserve=200.0,
        next_income_date="2026-05-10", # Future date
        today=date(2026, 4, 17)
    )
    # days = 23
    # available = 800.0
    # daily_limit = 800 / 23 = 34.78
    assert result["available"] == 800.0
    assert result["approved"] is True

def test_evaluate_purchase_at_limit():
    # available = 1000 - 200 = 800
    # days = 10 (2026-04-27 - 2026-04-17)
    # daily_limit = 80
    # limit + 50% = 80 + 40 = 120
    result = evaluate_purchase(
        amount=120.0,
        balance=1000.0,
        reserve=200.0,
        next_income_date="2026-04-27",
        today=date(2026, 4, 17)
    )
    assert result["limit"] == 80.0
    assert result["overshoot_pct"] == 50.0
    assert result["approved"] is True

def test_evaluate_purchase_above_limit():
    # daily_limit = 80
    # 120.1 > 120
    result = evaluate_purchase(
        amount=120.1,
        balance=1000.0,
        reserve=200.0,
        next_income_date="2026-04-27",
        today=date(2026, 4, 17)
    )
    assert result["approved"] is False

def test_evaluate_purchase_zero_available():
    result = evaluate_purchase(
        amount=10.0,
        balance=200.0,
        reserve=200.0,
        next_income_date="2026-04-27",
        today=date(2026, 4, 17)
    )
    assert result["available"] == 0.0
    assert result["limit"] == 0.0
    assert result["approved"] is False
    assert result["overshoot_pct"] == float('inf')

def test_evaluate_purchase_min_days():
    # today == next_income_date -> days = 1
    result = evaluate_purchase(
        amount=50.0,
        balance=100.0,
        reserve=0.0,
        next_income_date="2026-04-17",
        today=date(2026, 4, 17)
    )
    assert result["days"] == 1
    assert result["limit"] == 100.0
    assert result["approved"] is True
