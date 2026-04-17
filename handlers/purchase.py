"""
handlers/purchase.py — Purchase evaluation flow.

Handles:
  • The "💳 Проверить покупку" keyboard button → enters FSM waiting state
  • Any free-text message (after onboarding) parsed as a purchase
  • Inline-trigger: just typing an amount/description directly
"""
import re
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.models import add_transaction, get_user, update_user_balance
from keyboards.reply import main_menu, remove_kb
from services.calculator import evaluate_purchase
from services.llm import get_verdict_message
from states.fsm import PurchaseStates
from services.calculator_advanced import evaluate_purchase_advanced

router = Router()

# Words to strip when extracting description
_STOP_WORDS = {"want", "buy", "for", "som", "rub", "хочу", "купить", "за", "сом", "руб"}

# Regex: grab the first numeric token (integer or decimal)
_NUMBER_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\b")


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
        # Some other FSM is active — don't interfere
        return
    await _process_purchase(message)


# ─────────────────────────── Core logic ───────────────────────────

# async def _process_purchase(message: Message) -> None:
#     user_id = message.from_user.id
#     text = (message.text or "").strip()

#     # Parse amount and description
#     amount, description = _parse_purchase(text)
#     if amount is None:
#         await message.answer(
#             "❌ Не смог найти сумму в твоём сообщении.\n"
#             "Попробуй: `300 кофе` или `стрижка 500`",
#             parse_mode="Markdown",
#             reply_markup=main_menu,
#         )
#         return

#     if amount <= 0:
#         await message.answer(
#             "❌ Сумма должна быть больше нуля.",
#             reply_markup=main_menu,
#         )
#         return

#     user = await get_user(user_id)
#     if not user:
#         await message.answer("Сначала пройди настройку: /start")
#         return

#     balance = user["balance"]
#     reserve = user["reserve"]
#     income_date = user["next_income_date"]
#     period_available = user["period_available"] or max(balance - reserve, 1.0)

#     # result = evaluate_purchase(amount, balance, reserve, income_date)
#     result = evaluate_purchase_advanced(amount, balance, reserve, income_date)


#     verdict = "approved" if result["approved"] else "blocked"

#     # Persist the transaction
#     await add_transaction(user_id, amount, description, verdict)

#     # Update balance only if approved
#     if result["approved"]:
#         await update_user_balance(user_id, result["new_balance"])

#     # Build verdict message via LLM stub
#     context = {
#         "overshoot_pct": result["overshoot_pct"],
#         "days": result["days"],
#         "days_left_after": result["days_left_after"],
#         "limit": result["limit"],
#     }
#     verdict_text = await get_verdict_message(description, amount, verdict, context)

#     # Build the detail block
#     detail = _build_detail(result, period_available, amount, verdict)

#     warn = ""
#     if result["approved"] and result["new_balance"] < reserve:
#         warn = "\n\n⚠️ *Внимание:* После этой покупки баланс упадёт ниже резерва!"

#     await message.answer(
#         f"{verdict_text}\n\n{detail}{warn}",
#         parse_mode="Markdown",
#         reply_markup=main_menu,
#     )
async def _process_purchase(message: Message) -> None:
    user_id = message.from_user.id
    text = (message.text or "").strip()

    # Parse amount and description
    amount, description = _parse_purchase(text)
    if amount is None:
        await message.answer(
            "❌ Не смог найти сумму в твоём сообщении.\n"
            "Попробуй: `300 кофе` или `стрижка 500`",
            parse_mode="Markdown",
            reply_markup=main_menu,
        )
        return

    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше нуля.", reply_markup=main_menu)
        return

    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала пройди настройку: /start")
        return

    balance = user["balance"]
    reserve = user["reserve"]
    income_date = user["next_income_date"]
    period_start_date = user["period_start_date"]
    period_available = user["period_available"]

    # ← Главный вызов
    result = evaluate_purchase_advanced(
        amount=amount,
        balance=balance,
        reserve=reserve,
        next_income_date=income_date
    )

    verdict = "approved" if result["approved"] else "blocked"

    # Persist transaction
    await add_transaction(user_id, amount, description, verdict)

    # Update balance ONLY if approved
    if result["approved"]:
        await update_user_balance(user_id, result["new_balance"])

    # Context для сообщений
    context = {
        "overshoot_pct": result["overshoot_pct"],
        "days": result["days"],
        "days_left_after": result["days_left_after"],
        "limit": result["limit"],
        "survival_probability": result.get("survival_probability", 50),
        "risk_level": result.get("risk_level", "medium"),
        "fuzzy_score": result.get("fuzzy_score", 0.5),
    }

    verdict_text = await get_verdict_message(description, amount, verdict, context)

    # Детали
    detail = _build_detail(
        result, amount, verdict,
        period_available=period_available,
        period_start_date_iso=period_start_date,
        income_date_iso=income_date
    )

    warn = ""
    if result["approved"] and result["new_balance"] < reserve + 100:  # небольшой запас
        warn = "\n\n⚠️ *Внимание:* Баланс приближается к резерву!"

    await message.answer(
        f"{verdict_text}\n\n{detail}{warn}",
        parse_mode="Markdown",
        reply_markup=main_menu,
    )


# ─────────────────────────── Helpers ──────────────────────────────

def _parse_purchase(text: str) -> tuple[float | None, str]:
    """
    Extract (amount, description) from a free-form string.

    Supports:
        "300 coffee", "coffee 300", "300",
        "want to buy coffee for 300", "хочу купить кофе за 250"
    """
    match = _NUMBER_RE.search(text)
    if not match:
        return None, text

    amount_str = match.group(1).replace(",", ".")
    try:
        amount = float(amount_str)
    except ValueError:
        return None, text

    # Remove the matched number from the description
    description = text[: match.start()] + text[match.end() :]
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


# def _build_detail(result: dict, period_available: float, amount: float, verdict: str) -> str:
#     limit = result["limit"]
#     days = result["days"]
#     available = result["available"]
#     new_balance = result["new_balance"]
#     days_left_after = result["days_left_after"]
#     overshoot = result["overshoot_pct"]

#     # Financial health ratio: current available (if approved that is after purchase, else just current) / period_available
#     # If blocked, available doesn't change, meaning new_balance = balance -> wait, the result dictionary has the hypothetical new available
#     if verdict == "approved":
#         current_available = max(available - amount, 0.0)
#     else:
#         current_available = available

#     ratio = current_available / max(period_available, 1.0)
#     bar = _health_bar(ratio)

#     lines = [
#         "```",
#         f"━━━━━━━ 📊 Детали ━━━━━━━",
#         f"Сумма покупки:  {amount:>10,.2f}",
#         f"Дневной лимит:  {limit:>10,.2f}",
#         f"Доступно:       {available:>10,.2f}",
#         f"До зарплаты:    {days:>10} дн.",
#     ]

#     if verdict == "approved":
#         remaining_daily = result["limit"] - amount
#         lines.append(f"Остаток лимита: {remaining_daily:>10,.2f}")
#         lines.append(f"Новый баланс:   {new_balance:>10,.2f}")
#     else:
#         lines.append(f"Превышение:     {overshoot:>9.1f}%")
#         lines.append(f"Хватит на:      {max(days_left_after,0):>9.1f} дн.")

#     lines.append("```")
#     lines.append(f"💚 Здоровье: {bar}")
#     return "\n".join(lines)

def _build_detail(
    result: dict, amount: float, verdict: str,
    period_available: float = 0.0,
    period_start_date_iso: str = "",
    income_date_iso: str = ""
) -> str:
    """
    Красивый и стабильный блок деталей
    """
    limit = result.get("limit", 0.0)
    days = result.get("days", 1)
    available_before = result.get("available", 0.0)      # доступно ДО покупки
    new_balance = result.get("new_balance", 0.0)
    days_left_after = result.get("days_left_after", 0.0)
    overshoot = result.get("overshoot_pct", 0.0)
    survival = result.get("survival_probability", 0.0)

    # Health bar — считаем от идеального графика
    from datetime import date
    today = date.today()
    try:
        start_date = date.fromisoformat(period_start_date_iso)
    except (ValueError, TypeError):
        start_date = today
    try:
        inc_date = date.fromisoformat(income_date_iso)
    except (ValueError, TypeError):
        inc_date = today
        
    total_days = max((inc_date - start_date).days, 1)
    days_passed = max((today - start_date).days, 0)
    
    ideal_available = period_available * (1.0 - (days_passed / total_days))
    ideal_available = max(ideal_available, 0.0)

    # Если одобрена покупка, считаем здоровье после списания
    current_available = max(new_balance - result.get("reserve", 0.0), 0) if verdict == "approved" else max(available_before, 0)
    
    if ideal_available > 0:
        health_ratio = current_available / ideal_available
    else:
        health_ratio = 1.0 if current_available >= 0 else 0.0

    bar = _health_bar(health_ratio)

    lines = [
        "```",
        "━━━━━━━ 📊 Детали ━━━━━━━",
        f"Сумма покупки:   {amount:>10,.2f}",
        f"Дневной лимит:   {limit:>10,.2f}",
        f"Доступно было:   {available_before:>10,.2f}",
        f"До зарплаты:     {days:>10} дн.",
    ]

    if verdict == "approved":
        remaining_daily = max(limit - amount, 0.0)
        lines.extend([
            f"Остаток лимита:  {remaining_daily:>10,.2f}",
            f"Новый баланс:    {new_balance:>10,.2f}",
            f"Хватит на:       {days_left_after:>9.1f} дн."
        ])
    else:
        lines.extend([
            f"Превышение:      {overshoot:>9.1f}%",
            f"Хватит на:       {max(days_left_after, 0):>9.1f} дн.",
            f"Вероятность:     {survival:>8.1f}%"
        ])

    lines.append("```")
    lines.append(f"💚 Здоровье: {bar}")

    return "\n".join(lines)