"""
services/calculator.py — Core financial logic for FinGuard.
"""
from datetime import date, datetime
from typing import TypedDict


class EvaluationResult(TypedDict):
    limit: float          # daily spending limit
    days: int             # days until next income
    available: float      # balance - reserve
    overshoot_pct: float  # how much over daily limit (negative = under)
    approved: bool        # True if within acceptable range
    new_balance: float    # hypothetical balance after purchase
    days_left_after: float  # days budget would cover after purchase


def evaluate_purchase(
    amount: float,
    balance: float,
    reserve: float,
    next_income_date: str,
    today: date | None = None,
) -> EvaluationResult:
    """
    Evaluate whether a purchase should be approved.

    Args:
        amount:           Requested purchase amount.
        balance:          Current user balance.
        reserve:          Untouchable emergency reserve.
        next_income_date: ISO date string "YYYY-MM-DD".
        today:            Current date (optional, defaults to date.today()).

    Returns:
        EvaluationResult dict with all computed fields.
    """
    if today is None:
        today = date.today()
    income_date = date.fromisoformat(next_income_date)

    # Step 1: days until next income (minimum 1 to avoid division by zero)
    days = max((income_date - today).days, 1)

    # Step 2: money actually available to spend
    available = max(balance - reserve, 0.0)

    # Step 3: daily spending limit
    daily_limit = available / days

    # Step 4: overshoot percentage (negative means under limit → comfortable)
    if daily_limit > 0:
        overshoot_pct = (amount - daily_limit) / daily_limit * 100
    else:
        # If available is 0, any spend is 100 %+ overshoot
        overshoot_pct = float("inf") if amount > 0 else 0.0

    # Step 5: approval gate — blocked only if exceeds limit by MORE than 50 %
    approved = overshoot_pct <= 50

    # Step 6: hypothetical new balance
    new_balance = balance - amount

    # Step 7: how many days the remaining budget covers
    remaining_available = new_balance - reserve
    if daily_limit > 0:
        days_left_after = remaining_available / daily_limit
    else:
        days_left_after = 0.0

    return EvaluationResult(
        limit=round(daily_limit, 2),
        days=days,
        available=round(available, 2),
        overshoot_pct=round(overshoot_pct, 1),
        approved=approved,
        new_balance=round(new_balance, 2),
        days_left_after=round(days_left_after, 1),
    )
