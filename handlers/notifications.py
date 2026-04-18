"""
handlers/notifications.py — /notify command and notification scheduler.
"""
from datetime import date, datetime
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.models import get_user
from database.db import get_db
from keyboards.reply import main_menu
from services.proactive_alerts import check_alerts, format_alert

router = Router()


async def _should_send_notification(user_id: int) -> bool:
    """Check if daily notification should be sent for this user."""
    async with get_db() as db:
        async with db.execute(
            "SELECT notify_enabled, notify_time, last_notification_date FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()

    if not row or not row["notify_enabled"]:
        return False

    today_str = date.today().isoformat()
    if row["last_notification_date"] == today_str:
        return False

    notify_time = row["notify_time"] or "10:00"
    now = datetime.now()
    hour, minute = map(int, notify_time.split(":"))
    current_minutes = now.hour * 60 + now.minute
    notify_minutes = hour * 60 + minute
    return current_minutes >= notify_minutes


async def _send_notification(user_id: int, first_name: str, period_available: float) -> str:
    """Build and return the daily morning notification text."""
    user = await get_user(user_id)
    if not user:
        return ""

    balance = user["balance"]
    reserve = user["reserve"]
    income_date = user["next_income_date"]
    days = max((date.fromisoformat(income_date) - date.today()).days, 0)
    available = max(balance - reserve, 0.0)
    daily_limit = round(available / days, 2) if days > 0 else 0.0

    health = min(available / max(period_available, available), 1.0)
    health_pct = int(health * 100)

    if health > 0.7:
        encouragement = "Всё идёт по плану — держишься молодцом!"
    elif health > 0.4:
        encouragement = "Немного экономим — но всё под контролем."
    else:
        encouragement = "Сегодня лучше быть аккуратнее. Ты справишься!"

    bar = _health_bar(health)
    name = first_name or "друг"

    return (
        f"☀️ Доброе утро, {name}!\n\n"
        f"💰 Баланс: {balance:,.0f}₽\n"
        f"📅 До зарплаты: {days} дн.\n"
        f"🎯 Сегодня можешь потратить: {daily_limit:,.0f}₽\n\n"
        f"{bar} — {health_pct}% финансового здоровья\n\n"
        f"{encouragement}\n\n"
        f"Хорошего дня! 💪"
    )


def _health_bar(ratio: float, length: int = 12) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    pct = int(ratio * 100)
    emoji = "🟢" if ratio > 0.6 else "🟡" if ratio > 0.3 else "🔴"
    return f"{emoji} `[{bar}]` {pct}%"


async def _check_and_send_notification(user_id: int, first_name: str, period_available: float, message: Message) -> None:
    """Called on each bot poll. Fires notification if due."""
    if await _should_send_notification(user_id):
        text = await _send_notification(user_id, first_name, period_available)
        if text:
            await message.answer(text, parse_mode="Markdown")

        async with get_db() as db:
            await db.execute(
                "UPDATE users SET last_notification_date = ? WHERE user_id = ?",
                (date.today().isoformat(), user_id),
            )
            await db.commit()


@router.message(Command("notify"))
@router.message(F.text == "🔔 Уведомления")
async def cmd_notify(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала /start")
        return

    new_state = not bool(user.get("notify_enabled", False))
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET notify_enabled = ? WHERE user_id = ?",
            (int(new_state), user_id),
        )
        await db.commit()

    if new_state:
        await message.answer(
            "🔔 *Уведомления включены!*\n\n"
            "Каждое утро в 10:00 буду присылать тебе краткий статус.\n"
            "Напиши `/notify` снова чтобы выключить.",
            parse_mode="Markdown",
            reply_markup=main_menu,
        )
    else:
        await message.answer(
            "🔕 *Уведомления выключены.*\n\n"
            "Буду присылать только важные алерты.",
            parse_mode="Markdown",
            reply_markup=main_menu,
        )