import pytest
import sys
sys.path.insert(0, "/home/demi/dev/projects/python/inai_hackaton")

from services.reason_engine import build_reason, DecisionReason


def test_build_reason_blocks_low_survival():
    result = {
        "fuzzy_score": 0.4,
        "survival_probability": 0.35,
        "overshoot_pct": 120.0,
        "days_left_after": 1.5,
        "days": 5,
        "risk_level": "critical",
        "approved": False,
        "limit": 1000.0,
        "available": 3000.0,
    }
    reason = build_reason(3000, result, "Entertainment")
    assert reason["severity"] == "block"
    assert "low_survival" in reason["rule_tags"]


def test_build_reason_warns_moderate_overspend():
    result = {
        "fuzzy_score": 0.5,
        "survival_probability": 0.6,
        "overshoot_pct": 60.0,
        "days_left_after": 5.0,
        "days": 10,
        "risk_level": "high",
        "approved": True,
        "limit": 1000.0,
        "available": 3000.0,
    }
    reason = build_reason(1500, result, "Shopping")
    assert reason["severity"] == "warn"


def test_build_reason_ok_small_spend():
    result = {
        "fuzzy_score": 0.8,
        "survival_probability": 0.9,
        "overshoot_pct": 10.0,
        "days_left_after": 8.0,
        "days": 10,
        "risk_level": "low",
        "approved": True,
        "limit": 1000.0,
        "available": 3000.0,
    }
    reason = build_reason(300, result, "Food & Drink")
    assert reason["severity"] == "ok"


def test_build_reason_blocks_reserve_drop():
    result = {
        "fuzzy_score": 0.5,
        "survival_probability": 0.55,
        "overshoot_pct": 80.0,
        "days_left_after": 2.0,
        "days": 5,
        "risk_level": "critical",
        "approved": False,
        "limit": 1000.0,
        "available": 2000.0,
        "new_balance": 500.0,
        "reserve": 1500.0,
    }
    reason = build_reason(2000, result, "Entertainment")
    assert reason["severity"] == "block"