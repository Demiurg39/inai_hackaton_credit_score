"""
services/proactive_alerts.py — Proactive alert engine.

Checks user data and recurring spends for conditions that need attention.
Formats alert messages in caring parent tone.
"""
from datetime import date, timedelta
from typing import TypedDict


class Alert(TypedDict):
    type: str
    message: str
    details: dict


def check_alerts(user: dict, recurring_spends: list[dict]) -> list[Alert]:
    """
    Check all alert conditions for a user.
    Returns list of active alerts (may be empty).
    """
    alerts: list[Alert] = []
    balance = user["balance"]
    reserve = user["reserve"]
    income_date = date.fromisoformat(user["next_income_date"])
    today = date.today()
    days_until = max((income_date - today).days, 0)
    available = max(balance - reserve, 0.0)
    avg_daily = user.get("avg_daily_spend", 0.0)

    # Alert A: predicted run-out before payday
    if avg_daily > 0 and available > 0:
        days_would_last = available / avg_daily
        if days_would_last < days_until:
            run_out_date = today + timedelta(days=int(days_would_last))
            alerts.append(Alert(
                type="run_out",
                message="",
                details={
                    "days_until": days_until,
                    "days_would_last": round(days_would_last, 1),
                    "run_out_date": run_out_date.isoformat(),
                    "daily_limit": round(available / days_until, 2) if days_until > 0 else 0,
                    "balance": balance,
                },
            ))

    # Alert B: large recurring within 7 days would breach budget
    for s in recurring_spends:
        if s.get("confidence", 0) < 0.5:
            continue
        next_exp = date.fromisoformat(s["next_expected"])
        days_to_exp = (next_exp - today).days
        if 0 <= days_to_exp <= 7 and s["amount"] > available:
            alerts.append(Alert(
                type="large_recurring",
                message="",
                details={
                    "category": s["category"],
                    "amount": s["amount"],
                    "when": next_exp.strftime("%d.%m.%Y"),
                    "days_to": days_to_exp,
                    "reserve": reserve,
                    "days_left": round(available / avg_daily, 1) if avg_daily > 0 else 0,
                },
            ))

    return alerts


def format_alert(alert: Alert, user_name: str = "друг") -> str:
    """Format an alert as caring parent message."""
    if alert["type"] == "run_out":
        d = alert["details"]
        return (
            f"💡 Заметил кое-что важное.\n\n"
            f"До зарплаты ~{d['days_until']} дн., но при текущем темпе трат "
            f"деньги могут закончиться раньше — примерно {d['run_out_date']}.\n\n"
            f"📊 Твой дневной лимит: {d['daily_limit']:,.0f}₽\n"
            f"💰 Текущий баланс: {d['balance']:,.0f}₽\n\n"
            f"Если хочешь, я могу посмотреть что можно скорректировать. 💜"
        )

    elif alert["type"] == "large_recurring":
        d = alert["details"]
        return (
            f"⚠️ Крупный платёж впереди!\n\n"
            f"«{d['category']}» — {d['amount']:,.0f}₽ ожидается {d['when']}. "
            f"Это может оставить тебя без запаса до зарплаты.\n\n"
            f"💰 Резерв: {d['reserve']:,.0f}₽\n"
            f"📅 Хватит на: {d['days_left']:,.1f} дн.\n\n"
            f"Могу предложить варианты — просто спроси. 💜"
        )

    return ""