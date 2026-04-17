"""
handlers/purchase.py — handles text messages for purchases.
"""
import re
from datetime import date
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.models import add_transaction, get_user
from services.calculator_advanced import evaluate_purchase_advanced
from services.llm import get_verdict_message
from services.triton import predict_category
from states.fsm import PurchaseStates

router = Router()

# Words to strip when extracting description
_STOP_WORDS = {
    "хочу", "купить", "потратить", "покупка", "взять", "на", "за",
    "руб", "рублей", "р", "usd", "долларов", "сом", "сомов", "с"
}

# Regex: grab numeric tokens (integer or decimal) more strictly
_NUMBER_RE = re.compile(r"(?<!\d)(\d+(?:[.,]\d+)?)(?!\d)")

# ─────────────── "💳 Проверить покупку" button ────────────────────

@router.message(F.text == "💳 Проверить покупку")
async def ask_for_purchase(message: Message, state: FSMContext) -> None:
    await state.set_state(PurchaseStates.waiting_purchase_input)
    await message.answer(
        "💳 Напиши, что хочешь купить и за сколько.\n\n"
        "Примеры:\n"
        "  • `300 обед`\n"
        "  • `стрижка 800`\n"
        "  • `хочу купить кофе за 250`\n"
        "  • `1200` _(только сумма — тоже работает)_",
        parse_mode="Markdown",
        reply_markup=remove_kb,
    )

# ─────────────── FSM: waiting for purchase input ──────────────────

@router.message(PurchaseStates.waiting_purchase_input)
async def handle_purchase_fsm(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _process_purchase(message)

# ─────────────── Direct text → try to parse as purchase ───────────
# This catches messages that DON'T match any command or button text.

@router.message(
    F.text.regexp(r"\d"),           # must contain at least one digit
    ~F.text.startswith("/"),        # not a command
)
async def handle_purchase_direct(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is not None:
        return
    await _process_purchase(message)

async def _process_purchase(message: Message) -> None:
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.answer("Сначала пройди настройку: /start")
        return

    # Enrich description with Triton category prediction
    category = await predict_category(description)
    if category:
        description = f"[{category}] {description}"

    if amount <= 0:
        await message.answer(
            "❌ Сумма должна быть больше нуля.",
            reply_markup=main_menu,
        )
        return

    if amount is None or amount <= 0:
        await message.answer("Не вижу в твоём сообщении нормальной суммы. 🧐")
        return

    balance = user["balance"]
    reserve = user["reserve"]
    income_date = user["next_income_date"]
    # NOTE: period_available not accessing
    period_available = user["period_available"] or max(balance - reserve, 1.0)
    today = date.today()

    result = evaluate_purchase(amount, balance, reserve, income_date, today)

    result = await evaluate_purchase_advanced(amount, balance, reserve, income_date)

    verdict = "approved" if result["approved"] else "blocked"

    await add_transaction(user_id, amount, description, verdict)

    context = {
        "limit": result["limit"],
        "overshoot_pct": result["overshoot_pct"],
        "days": result["days"],
        "days_left_after": result["days_left_after"],
        "survival_probability": result["survival_probability"],
        "risk_level": result["risk_level"],
        "fuzzy_score": result["fuzzy_score"],
    }

    verdict_text = await get_verdict_message(description, amount, verdict, context)
    detail = _build_detail(result, amount, verdict)

    warn = "\n\n⚠️ *Внимание:* Баланс приближается к резерву!" if result["approved"] and result["new_balance"] < reserve + 100 else ""

    await message.answer(
        f"{verdict_text}\n\n{detail}{warn}",
        parse_mode="Markdown",
    )

# ─────────────────────────── Helpers ──────────────────────────────

def _parse_purchase(text: str) -> tuple[float | None, str]:
    """
    Extract (amount, description) from a free-form string.

    Supports:
        "300 coffee", "coffee 300", "300",
        "want to buy coffee for 300", "хочу купить кофе за 250"
    """
    matches = _NUMBER_RE.findall(text)
    if not matches:
        return None, text

    # Use the first number found as the amount
    amount_str = matches[0].replace(",", ".")
    try:
        amount = float(amount_str)
    except ValueError:
        return None, text

    # Remove the matched number from the description
    description = _NUMBER_RE.sub("", text, count=1)
    # Strip stop-words and clean up
    words = [
        w for w in description.split()
        if w.lower() not in _STOP_WORDS
    ]
    description = " ".join(words).strip(" .,!?-–")
    if not description:
        description = "покупка"

    return amount, description

def _health_bar(ratio: float, length: int = 12) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    pct = int(ratio * 100)
    emoji = "🟢" if ratio > 0.6 else "🟡" if ratio > 0.3 else "🔴"
    return f"{emoji} `[{bar}]` {pct}%"

def _build_detail(result: dict, period_available: float, amount: float, verdict: str) -> str:
    limit = result["limit"]
    days = result["days"]
    available = result["available"]
    # NOTE: not accessing
    new_balance = result["new_balance"]
    days_left_after = result["days_left_after"]
    overshoot = result["overshoot_pct"]

    # Financial health ratio: current available (if approved that is after purchase, else just current) / period_available
    # If blocked, available doesn't change, meaning new_balance = balance -> wait, the result dictionary has the hypothetical new available
    if verdict == "approved":
        current_available = max(available - amount, 0.0)
    else:
        current_available = available

    ratio = current_available / max(period_available, 1.0)
    # NOTE: not accessed also
    bar = _health_bar(ratio)

    lines = [
        "```",
        "━━━━━━━ 📊 Детали ━━━━━━━",
        f"Сумма покупки:  {amount:>10,.2f}",
        f"Дневной лимит:  {limit:>10,.2f}",
        f"Доступно:       {available:>10,.2f}",
        f"До зарплаты:    {days:>10} дн.",
    ]

    if verdict == "approved":
        lines.extend([
            f"Остаток лимита:  {max(result['limit'] - amount, 0):>10,.1f}",
            f"Новый баланс:    {result['new_balance']:>10,.2f}",
            f"Хватит на:       {result['days_left_after']:>9.1f} дн."
        ])
    else:
        lines.extend([
            f"Превышение:      {result['overshoot_pct']:>9.1f}%",
            f"Хватит на:       {max(result['days_left_after'], 0):>9.1f} дн.",
            f"Вероятность:     {result['survival_probability']:>8.1f}%"
        ])

    lines.append("```")
    return "\n".join(lines)
