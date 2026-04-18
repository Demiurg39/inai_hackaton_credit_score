import pytest
import sys
sys.path.insert(0, "/home/demi/dev/projects/python/inai_hackaton")

from services.explainer import explain
from services.reason_engine import DecisionReason


def test_explain_block():
    reason: DecisionReason = {
        "severity": "block",
        "primary": "«Entertainment» за 3000 — шанс дотянуть только 30%",
        "details": ["шанс дотянуть до зарплаты — только 30%", "превышение на 200%"],
        "days_left": 1.5,
        "survival": 0.3,
        "overshoot": 200.0,
        "category": "Entertainment",
        "rule_tags": ["low_survival", "massive_overspend"],
        "days": 5,
    }
    text = explain(reason, 3000, "игра в Steam")
    assert "подожди" in text.lower()
    assert "30%" in text or "30" in text
    assert "1.5" in text


def test_explain_warn():
    reason: DecisionReason = {
        "severity": "warn",
        "primary": "«Shopping» за 1500 — можно, но есть риски",
        "details": ["превышение на 60% сверх дневного лимита"],
        "days_left": 5.0,
        "survival": 0.55,
        "overshoot": 60.0,
        "category": "Shopping",
        "rule_tags": ["moderate_survival", "big_overspend"],
        "days": 10,
    }
    text = explain(reason, 1500, "кроссовки")
    assert "риск" in text.lower() or "предупрежда" in text.lower()


def test_explain_ok():
    reason: DecisionReason = {
        "severity": "ok",
        "primary": "«Food & Drink» за 300 — в рамках плана (30% лимита)",
        "details": [],
        "days_left": 8.0,
        "survival": 0.9,
        "overshoot": 10.0,
        "category": "Food & Drink",
        "rule_tags": [],
        "days": 10,
        "limit": 1000.0,
    }
    text = explain(reason, 300, "обед")
    assert "✅" in text or "давай" in text.lower()