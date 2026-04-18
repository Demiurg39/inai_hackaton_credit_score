"""
middlewares/notification.py — Fires daily notification if due.
"""
from aiogram.types import Message
from handlers.notifications import _check_and_send_notification
from services.proactive_alerts import check_alerts, format_alert
from database.models import get_recurring_spends, get_user, get_user_stats


async def _check_and_fire_alerts(event: Message) -> None:
    user_id = event.from_user.id
    user = await get_user(user_id)
    if not user:
        return

    stats = await get_user_stats(user_id)
    recurring_rows = await get_recurring_spends(user_id)

    recurring_list = []
    for r in recurring_rows:
        recurring_list.append({
            "amount": r["avg_amount"],
            "interval_days": r["interval_days"],
            "confidence": r["confidence"],
            "category": r["category"],
            "next_expected": r["next_expected"],
        })

    user_data = {
        "balance": user["balance"],
        "reserve": user["reserve"],
        "next_income_date": user["next_income_date"],
        "avg_daily_spend": stats.get("avg_daily_spend", 0.0) if stats else 0.0,
    }

    alerts = check_alerts(user_data, recurring_list)
    for alert in alerts:
        text = format_alert(alert, event.from_user.first_name or "друг")
        await event.answer(text, parse_mode="Markdown")


class NotificationMiddleware:
    def __init__(self, period_available_getter):
        # period_available_getter: callable(user_id) → float
        self._get_period = period_available_getter

    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            user_id = event.from_user.id
            period = self._get_period(user_id)
            await _check_and_send_notification(
                user_id,
                event.from_user.first_name,
                period,
                event,
            )
            await _check_and_fire_alerts(event)
        return await handler(event, data)