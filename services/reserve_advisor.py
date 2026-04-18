"""
services/reserve_advisor.py — Reserve recommendation engine.

Pure function: no I/O, no async. Takes user data → RecommendedReserve.
"""
from typing import TypedDict


class RecommendedReserve(TypedDict):
    recommended: float
    current: float
    covered_recurring: float
    buffer_days: float
    confidence: float
    breakdown: list[str]


_MIN_BUFFER = 500.0
_BUFFER_DAYS = 3


def compute_recommended_reserve(
    balance: float,
    current: float,
    recurring_spends: list[dict],
    avg_daily_spend: float,
) -> RecommendedReserve:
    """
    Compute recommended reserve amount.

    Algorithm:
      covered = sum(avg_amount for each recurring)
      buffer = max(avg_daily_spend × 3, 500)
      recommended = covered + buffer
      confidence = (count/5) × avg_confidence
    """
    if not recurring_spends:
        recommended = balance * 0.15
        return RecommendedReserve(
            recommended=round(recommended, 2),
            current=current,
            covered_recurring=0.0,
            buffer_days=0.0,
            confidence=0.0,
            breakdown=["Нет данных о регулярных тратах — рекомендую 15% баланса как резерв"],
        )

    covered = sum(s["amount"] for s in recurring_spends)
    buffer = max(avg_daily_spend * _BUFFER_DAYS, _MIN_BUFFER)
    recommended = covered + buffer

    confidences = [s["confidence"] for s in recurring_spends]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    # For a single recurring, trust its confidence directly (not enough data to penalize)
    # For multiple, scale by how many we have relative to a healthy baseline of 5
    if len(recurring_spends) == 1:
        confidence = avg_conf
    else:
        count_factor = min(len(recurring_spends) / 5.0, 1.0)
        confidence = avg_conf * count_factor

    breakdown = []
    for s in recurring_spends:
        breakdown.append(f"• {s['category']} — {s['amount']:,.0f}₽ (каждые {s['interval_days']} дн.)")
    breakdown.append(f"• Буфер на {_BUFFER_DAYS} дн.: {buffer:,.0f}₽")

    return RecommendedReserve(
        recommended=round(recommended, 2),
        current=current,
        covered_recurring=round(covered, 2),
        buffer_days=_BUFFER_DAYS,
        confidence=round(confidence, 3),
        breakdown=breakdown,
    )