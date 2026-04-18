"""
middlewares/notification.py — Fires daily notification if due.
"""
from aiogram.types import Message
from handlers.notifications import _check_and_send_notification

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
        return await handler(event, data)
