"""
handlers/purchase.py — Purchase evaluation flow.

Handles:
  • The "💳 Проверить покупку" keyboard button → enters FSM waiting state
  • Any free-text message (after onboarding) parsed as a purchase
  • Inline-trigger: just typing an amount/description directly
"""
import re
from aiogram import F, Router
from aiogram.filters import Command, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database.models import add_transaction, compute_user_stats, get_user, get_user_stats, update_user_balance, upsert_category_stats
from keyboards.reply import main_menu, remove_kb
from services.calculator_advanced import evaluate_purchase_advanced
from services.llm import parse_purchase_with_llm, LLMError
from services.triton import predict_category
from services.reason_engine import build_reason
from services.explainer import explain
from states.fsm import PlaygroundStates, PurchaseStates

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


# ─────────────── 🎮 Playground mode ────────────────────────────────

@router.message(Command("playground"))
@router.message(F.text == "🎮 Что если?")
async def cmd_playground(message: Message, state: FSMContext) -> None:
    await state.set_state(PlaygroundStates.waiting_playground_input)
    await message.answer(
        "🎮 *Режим «А что если?»*\n\n"
        "Напиши мне покупку — например `3000 playstation` — и я покажу тебе "
        "мой вердикт БЕЗ сохранения транзакции и БЕЗ изменения баланса.\n\n"
        "Это просто симуляция, чтобы понять как решение повлияет на твой прогноз.\n\n"
        "Напиши `стоп` чтобы выйти.",
        parse_mode="Markdown",
        reply_markup=remove_kb,
    )


@router.message(PlaygroundStates.waiting_playground_input)
async def handle_playground(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text.lower() == "стоп":
        await state.clear()
        await message.answer("Выхожу из режима «Что если». Возвращаемся в меню.", reply_markup=main_menu)
        return

    amount, description = _parse_purchase(text)
    if amount is None or amount <= 0:
        await message.answer(
            "❌ Не вижу сумму. Напиши например `3000 playstation`",
            parse_mode="Markdown",
            reply_markup=main_menu,
        )
        await state.clear()
        return

    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала /start")
        await state.clear()
        return

    balance = user["balance"]
    reserve = user["reserve"]
    income_date = user["next_income_date"]

    result = await evaluate_purchase_advanced(amount, balance, reserve, income_date)

    category = await predict_category(description)
    reason = build_reason(amount, result, category or "другое")
    verdict_text = explain(reason, amount, description)

    await message.answer(
        f"🎮 *Результат симуляции:*\n\n{verdict_text}\n\n_Это только симуляция. Баланс не изменился._",
        parse_mode="Markdown",
        reply_markup=main_menu,
    )
    await state.clear()

# ─────────────── Core logic ───────────────────────────

@router.callback_query(F.data.startswith("llm_parse:"))
async def handle_llm_reparse(callback: CallbackQuery, state: FSMContext) -> None:
    original_text = callback.data.split(":", 1)[1]
    await callback.message.edit_reply_markup(reply_markup=None)

    try:
        amount, description = await parse_purchase_with_llm(original_text)
    except LLMError:
        await callback.message.answer(
            "❌ LLM недоступен. Попробуй позже.",
            reply_markup=main_menu,
        )
        return

    original_message = callback.message
    original_message.text = f"{amount} {description}"
    await _process_purchase(original_message)


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
        await message.answer(
            "❌ Сумма должна быть больше нуля.",
            reply_markup=main_menu,
        )
        return

    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала пройди настройку: /start")
        return

    balance = user["balance"]
    reserve = user["reserve"]
    income_date = user["next_income_date"]
    period_available = user["period_available"] or max(balance - reserve, 1.0)

    # Enrich description with Triton category prediction
    category = await predict_category(description)
    if category:
        description = f"[{category}] {description}"

    result = await evaluate_purchase_advanced(amount, balance, reserve, income_date)

    verdict = "approved" if result["approved"] else "blocked"

    # Persist the transaction
    await add_transaction(user_id, amount, description, verdict)

    # Update balance only if approved
    if result["approved"]:
        await update_user_balance(user_id, result["new_balance"])

    # Update per-user spending stats
    await compute_user_stats(user_id)

    # Upsert category stats if Triton provided a category
    if category:
        await upsert_category_stats(user_id, category, amount)

    # Build verdict message via rule-based reason engine + explainer
    reason = build_reason(amount, result, category or "другое")
    verdict_text = explain(reason, amount, description)

    # Build the detail block
    detail = _build_detail(result, period_available, amount, verdict)

    warn = ""
    if result["approved"] and result["new_balance"] < reserve:
        warn = "\n\n⚠️ *Внимание:* После этой покупки баланс упадёт ниже резерва!"

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Сумма неверна", callback_data=f"llm_parse:{text}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])
    await message.answer(
        f"{verdict_text}\n\n{detail}{warn}",
        parse_mode="Markdown",
        reply_markup=inline_kb,
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


def _build_detail(result: dict, period_available: float, amount: float, verdict: str) -> str:
    limit = result["limit"]
    days = result["days"]
    available = result["available"]
    new_balance = result["new_balance"]
    days_left_after = result["days_left_after"]
    overshoot = result["overshoot_pct"]
    survival = result.get("survival_probability", 0.0)

    # Financial health ratio
    if verdict == "approved":
        current_available = max(available - amount, 0.0)
    else:
        current_available = available

    ratio = current_available / max(period_available, 1.0)
    bar = _health_bar(ratio)

    lines = [
        "```",
        f"━━━━━━━ 📊 Детали ━━━━━━━",
        f"Сумма покупки:  {amount:>10,.2f}",
        f"Дневной лимит:  {limit:>10,.2f}",
        f"Доступно:       {available:>10,.2f}",
        f"До зарплаты:    {days:>10} дн.",
    ]

    if verdict == "approved":
        remaining_daily = result["limit"] - amount
        lines.append(f"Остаток лимита: {remaining_daily:>10,.2f}")
        lines.append(f"Новый баланс:   {new_balance:>10,.2f}")
    else:
        lines.append(f"Превышение:     {overshoot:>9.1f}%")
        lines.append(f"Хватит на:      {max(days_left_after,0):>9.1f} дн.")
        lines.append(f"Вероятность:    {survival * 100:>8.1f}%")

    lines.append("```")
    lines.append(f"💚 Здоровье: {bar}")
    return "\n".join(lines)
