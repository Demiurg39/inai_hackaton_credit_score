import sys
sys.path.insert(0, "/home/demi/dev/projects/python/inai_hackaton")

from services.proactive_alerts import check_alerts, format_alert

def test_no_alert_when_healthy():
    """No alerts if money lasts well beyond payday"""
    user = {
        "balance": 15000.0,
        "reserve": 3000.0,
        "next_income_date": "2026-05-01",
        "avg_daily_spend": 300.0,
    }
    recurring = []
    alerts = check_alerts(user, recurring)
    assert len(alerts) == 0

def test_alert_when_run_out_before_payday():
    """Alert when predicted run-out date is before payday"""
    from datetime import date, timedelta
    user = {
        "balance": 3000.0,
        "reserve": 1000.0,
        "next_income_date": (date.today() + timedelta(days=10)).isoformat(),
        "avg_daily_spend": 500.0,
    }
    recurring = []
    alerts = check_alerts(user, recurring)
    assert len(alerts) > 0
    assert alerts[0]["type"] == "run_out"

def test_alert_when_large_recurring_breaches():
    """Alert when upcoming recurring spend > available-reserve"""
    from datetime import date, timedelta
    user = {
        "balance": 5000.0,
        "reserve": 1000.0,
        "next_income_date": (date.today() + timedelta(days=30)).isoformat(),
        "avg_daily_spend": 200.0,
    }
    recurring = [{
        "amount": 4500.0,
        "next_expected": (date.today() + timedelta(days=5)).isoformat(),
        "category": "Аренда",
        "interval_days": 30,
        "confidence": 0.9,
    }]
    alerts = check_alerts(user, recurring)
    assert any(a["type"] == "large_recurring" for a in alerts)