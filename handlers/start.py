"""
handlers/start.py — /start command + FSM onboarding flow.
"""
from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.models import create_user, get_user, set_onboarded
from keyboards.reply import main_menu, remove_kb
from services.calculator import evaluate_purchase
from states.fsm import OnboardingStates

router = Router()


# ─────────────────────────── /start ───────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    await create_user(user_id)

    user = await get_user(user_id)
    if user and user["onboarded"]:
        await message.answer(
            "👋 С возвращением! Ты уже настроен.\n"
            "Используй меню внизу или просто напиши покупку — "
            "я скажу, можно ли её позволить. 💳",
            reply_markup=main_menu,
        )
        return

    # Start onboarding
    await state.clear()
    await state.set_state(OnboardingStates.waiting_balance)
    await message.answer(
        "👋 Привет! Я *FinGuard* — твой финансовый страж.\n\n"
        "Я буду следить за тем, чтобы твои деньги не кончились раньше зарплаты. "
        "Давай настроимся!\n\n"
        "💰 *Шаг 1/3* — Сколько денег у тебя сейчас? "
        "_(введи сумму цифрами, например: 15000)_",
        parse_mode="Markdown",
        reply_markup=remove_kb,
    )


# ─────────────────── Step 1: balance ──────────────────────────────

@router.message(OnboardingStates.waiting_balance)
async def step_balance(message: Message, state: FSMContext) -> None:
    balance = _parse_positive_number(message.text)
    if balance is None:
        await message.answer(
            "❌ Пожалуйста, введи *положительное число*.\n"
            "Например: `15000` или `3500.50`",
            parse_mode="Markdown",
        )
        return

    await state.update_data(balance=balance)
    await state.set_state(OnboardingStates.waiting_reserve)
    await message.answer(
        f"✅ Записал: *{balance:,.2f}*\n\n"
        "🛡 *Шаг 2/3* — Какую сумму отложить в «неприкосновенный запас»?\n"
        "_(Эти деньги не учитываются в расчётах — НЗ на крайний случай)_",
        parse_mode="Markdown",
    )


# ─────────────────── Step 2: reserve ──────────────────────────────

@router.message(OnboardingStates.waiting_reserve)
async def step_reserve(message: Message, state: FSMContext) -> None:
    reserve = _parse_non_negative_number(message.text)
    if reserve is None:
        await message.answer(
            "❌ Введи *неотрицательное число*.\n"
            "Если НЗ нет — просто напиши `0`",
            parse_mode="Markdown",
        )
        return

    data = await state.get_data()
    balance = data["balance"]
    if reserve >= balance:
        await message.answer(
            "⚠️ Резерв не может быть больше или равен балансу!\n"
            f"Твой баланс: *{balance:,.2f}*. Введи меньшую сумму.",
            parse_mode="Markdown",
        )
        return

    await state.update_data(reserve=reserve)
    await state.set_state(OnboardingStates.waiting_income_date)
    await message.answer(
        f"✅ Резерв: *{reserve:,.2f}*\n\n"
        "📅 *Шаг 3/3* — Когда следующая зарплата / пополнение?\n"
        "_(Введи дату в формате ДД.ММ.ГГГГ, например: `25.04.2025`)_",
        parse_mode="Markdown",
    )


# ─────────────────── Step 3: income date ──────────────────────────

@router.message(OnboardingStates.waiting_income_date)
async def step_income_date(message: Message, state: FSMContext) -> None:
    income_date = _parse_future_date(message.text)
    if income_date is None:
        await message.answer(
            "❌ Не могу распознать дату или она уже прошла.\n"
            "Формат: `ДД.ММ.ГГГГ`, например `25.04.2025`\n"
            "Дата должна быть в будущем.",
            parse_mode="Markdown",
        )
        return

    data = await state.get_data()
    balance: float = data["balance"]
    reserve: float = data["reserve"]
    income_date_iso = income_date.isoformat()

    await set_onboarded(
        message.from_user.id,
        balance=balance,
        reserve=reserve,
        income_date=income_date_iso,
    )
    await state.clear()

    # Show the first daily limit calculation
    result = evaluate_purchase(0, balance, reserve, income_date_iso)
    days = result["days"]
    limit = result["limit"]

    # At the exact moment of onboarding, health is 100% because no time has passed 
    # to deviate from the ideal spending curve.
    health_bar = _health_bar(1.0)
    await message.answer(
        f"🎉 *Настройка завершена!* Добро пожаловать в FinGuard.\n\n"
        f"📊 *Твой финансовый дашборд:*\n"
        f"  💰 Баланс:       `{balance:,.2f}`\n"
        f"  🛡 Резерв:       `{reserve:,.2f}`\n"
        f"  📅 До зарплаты:  `{days}` дн.\n"
        f"  🎯 Дневной лимит: `{limit:,.2f}`\n\n"
        f"{health_bar}\n\n"
        "Теперь просто напиши мне что хочешь купить — "
        "например `300 обед` или `стрижка 800` — и я скажу, можно ли! 💳",
        parse_mode="Markdown",
        reply_markup=main_menu,
    )


# ─────────────────────────── Helpers ──────────────────────────────

def _parse_positive_number(text: str) -> float | None:
    try:
        val = float(text.replace(",", ".").replace(" ", ""))
        return val if val > 0 else None
    except (ValueError, AttributeError):
        return None


def _parse_non_negative_number(text: str) -> float | None:
    try:
        val = float(text.replace(",", ".").replace(" ", ""))
        return val if val >= 0 else None
    except (ValueError, AttributeError):
        return None


def _parse_future_date(text: str) -> date | None:
    """Parse DD.MM.YYYY and ensure it is in the future."""
    try:
        d = datetime.strptime(text.strip(), "%d.%m.%Y").date()
        return d if d > date.today() else None
    except ValueError:
        return None


def _health_bar(ratio: float, length: int = 10) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    pct = int(ratio * 100)
    return f"💚 Финансовое здоровье: [{bar}] {pct}%"
