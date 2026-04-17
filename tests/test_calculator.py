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
    assert result["available"] == 800.0
    assert result["approved"] is True
