"""
handlers/settings.py — /settings command, inline option handling,
                        and "📜 История" (transaction history) button.
"""
from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database.models import (
    get_recent_transactions,
    get_user,
    get_user_stats,
    upsert_user_stats,
    update_user_balance,
    update_user_income_date,
    update_user_reserve,
    reset_period_available,
)
from database.db import get_db
from keyboards.reply import main_menu, remove_kb
from states.fsm import SettingsStates

router = Router()

# ─────────────────────── Inline keyboard ──────────────────────────

_settings_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Обновить баланс",   callback_data="set_balance"),
            InlineKeyboardButton(text="🛡 Обновить резерв",   callback_data="set_reserve"),
        ],
        [
            InlineKeyboardButton(text="📅 Дата зарплаты",     callback_data="set_income"),
            InlineKeyboardButton(text="⚖️ Риск-толерантность", callback_data="set_risk"),
        ],
        [
            InlineKeyboardButton(text="🔔 Уведомления",      callback_data="set_notify"),
        ],
    ]
)


# ─────────────────────── /settings entry ──────────────────────────

@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message) -> None:
    user = await get_user(message.from_user.id)
    if not user or not user["onboarded"]:
        await message.answer("Сначала пройди настройку: /start")
        return

    balance = user["balance"]
    reserve = user["reserve"]
    income_date = user["next_income_date"]

    await message.answer(
        f"⚙️ *Настройки FinGuard*\n\n"
        f"  💰 Баланс:   `{balance:,.2f}`\n"
        f"  🛡 Резерв:   `{reserve:,.2f}`\n"
        f"  📅 Зарплата: `{income_date}`\n\n"
        "Что хочешь изменить?",
        parse_mode="Markdown",
        reply_markup=_settings_kb,
    )


# ─────────────────────── Callback handlers ────────────────────────

@router.callback_query(F.data == "set_balance")
async def cb_set_balance(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(SettingsStates.waiting_new_balance)
    await call.message.answer(
        "💰 Введи новый *текущий баланс* (например `12000`):",
        parse_mode="Markdown",
        reply_markup=remove_kb,
    )


@router.callback_query(F.data == "set_reserve")
async def cb_set_reserve(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(SettingsStates.waiting_new_reserve)
    await call.message.answer(
        "🛡 Введи новый *резерв* (или `0` если не нужен):",
        parse_mode="Markdown",
        reply_markup=remove_kb,
    )


@router.callback_query(F.data == "set_income")
async def cb_set_income(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(SettingsStates.waiting_new_income_date)
    await call.message.answer(
        "📅 Введи новую дату зарплаты в формате `ДД.ММ.ГГГГ`:",
        parse_mode="Markdown",
        reply_markup=remove_kb,
    )


@router.callback_query(F.data == "set_risk")
async def cb_set_risk(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(SettingsStates.waiting_new_risk_tolerance)
    await call.message.answer(
        "⚖️ Установи свой риск-профиль (0.0 = строгий, 1.0 = лояльный):\n"
        "Примеры:\n  `0.0` — максимально осторожный\n  `0.5` — сбалансированный\n  `1.0` — разрешаю многое",
        parse_mode="Markdown",
        reply_markup=remove_kb,
    )


@router.callback_query(F.data == "set_notify")
async def cb_set_notify(call: CallbackQuery) -> None:
    await call.answer()
    user_id = call.from_user.id
    user = await get_user(user_id)
    if not user:
        await call.message.answer("Сначала /start")
        return

    new_state = not bool(user.get("notify_enabled", False))
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET notify_enabled = ? WHERE user_id = ?",
            (int(new_state), user_id),
        )
        await db.commit()

    if new_state:
        await call.message.answer(
            "🔔 *Уведомления включены!*\n\n"
            "Каждое утро в 10:00 буду присылать тебе краткий статус.",
            parse_mode="Markdown",
            reply_markup=_settings_kb,
        )
    else:
        await call.message.answer(
            "🔕 *Уведомления выключены.*",
            parse_mode="Markdown",
            reply_markup=_settings_kb,
        )


# ─────────────────────── FSM update handlers ──────────────────────

@router.message(SettingsStates.waiting_new_balance)
async def update_balance(message: Message, state: FSMContext) -> None:
    val = _parse_positive(message.text)
    if val is None:
        await message.answer("❌ Введи положительное число.")
        return
    user_id = message.from_user.id
    user = await get_user(user_id)
    await update_user_balance(user_id, val)
    if user:
        await reset_period_available(user_id, val - user["reserve"])
    await state.clear()
    await message.answer(
        f"✅ Баланс обновлён: *{val:,.2f}*",
        parse_mode="Markdown",
        reply_markup=main_menu,
    )


@router.message(SettingsStates.waiting_new_reserve)
async def update_reserve(message: Message, state: FSMContext) -> None:
    val = _parse_non_negative(message.text)
    if val is None:
        await message.answer("❌ Введи неотрицательное число (или 0).")
        return
    user_id = message.from_user.id
    user = await get_user(user_id)
    await update_user_reserve(user_id, val)
    if user:
        await reset_period_available(user_id, user["balance"] - val)
    await state.clear()
    await message.answer(
        f"✅ Резерв обновлён: *{val:,.2f}*",
        parse_mode="Markdown",
        reply_markup=main_menu,
    )


@router.message(SettingsStates.waiting_new_income_date)
async def update_income_date(message: Message, state: FSMContext) -> None:
    d = _parse_future_date(message.text)
    if d is None:
        await message.answer(
            "❌ Неверный формат или дата уже прошла.\n"
            "Пример: `25.04.2025`",
            parse_mode="Markdown",
        )
        return
    user_id = message.from_user.id
    user = await get_user(user_id)
    await update_user_income_date(user_id, d.isoformat())
    if user:
        await reset_period_available(user_id, user["balance"] - user["reserve"])
    await state.clear()
    await message.answer(
        f"✅ Дата зарплаты обновлена: *{d.strftime('%d.%m.%Y')}*",
        parse_mode="Markdown",
        reply_markup=main_menu,
    )


@router.message(SettingsStates.waiting_new_risk_tolerance)
async def update_risk_tolerance(message: Message, state: FSMContext) -> None:
    try:
        val = float(message.text.replace(",", ".").strip())
        if not (0.0 <= val <= 1.0):
            raise ValueError()
    except (ValueError, AttributeError):
        await message.answer("❌ Введи число от 0.0 до 1.0.")
        return
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user:
        stats = await get_user_stats(user_id) or {}
        await upsert_user_stats(
            user_id,
            avg=stats.get("avg_daily_spend", 0.0),
            std=stats.get("std_daily_spend", 0.0),
            velocity=stats.get("spend_velocity", 1.0),
            tolerance=val,
        )
    await state.clear()
    await message.answer(
        f"✅ Риск-профиль: *{val:.1f}*",
        parse_mode="Markdown",
        reply_markup=main_menu,
    )


# ─────────────────────── History handler ──────────────────────────

@router.message(F.text == "📜 История")
async def cmd_history(message: Message) -> None:
    rows = await get_recent_transactions(message.from_user.id, limit=5)
    if not rows:
        await message.answer(
            "📜 История пуста — ещё не было ни одной проверки покупки.",
            reply_markup=main_menu,
        )
        return

    lines = ["📜 *Последние 5 покупок:*\n"]
    for row in rows:
        icon = "✅" if row["verdict"] == "approved" else "⛔"
        desc = row["description"] or "—"
        amt = row["amount"]
        # Created_at is UTC ISO — show just the date part
        created = (row["created_at"] or "")[:10]
        lines.append(f"{icon} `{amt:,.0f}` — {desc} _{created}_")

    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=main_menu,
    )


# ─────────────────────────── Helpers ──────────────────────────────

def _parse_positive(text: str) -> float | None:
    try:
        v = float(text.replace(",", ".").replace(" ", ""))
        return v if v > 0 else None
    except (ValueError, AttributeError):
        return None


def _parse_non_negative(text: str) -> float | None:
    try:
        v = float(text.replace(",", ".").replace(" ", ""))
        return v if v >= 0 else None
    except (ValueError, AttributeError):
        return None


def _parse_future_date(text: str) -> date | None:
    try:
        d = datetime.strptime(text.strip(), "%d.%m.%Y").date()
        return d if d > date.today() else None
    except ValueError:
        return None
