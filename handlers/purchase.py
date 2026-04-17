"""
handlers/purchase.py — handles text messages for purchases.
"""
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.models import add_transaction, get_user
from services.calculator_advanced import evaluate_purchase_advanced
from services.llm import get_verdict_message
from services.triton import predict_category
from states.fsm import PurchaseStates

router = Router()

_NUMBER_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\b")

_STOP_WORDS = {
    "хочу", "купить", "потратить", "покупка", "взять", "на", "за", 
    "руб", "рублей", "р", "usd", "долларов", "сом", "сомов", "с"
}

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

    result = evaluate_purchase_advanced(amount, balance, reserve, income_date)
    
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


def _parse_purchase(text: str) -> tuple[float | None, str]:
    match = _NUMBER_RE.search(text)
    if not match:
        return None, text
    amount = float(match.group(1).replace(",", "."))
    description = text[:match.start()] + text[match.end():]
    words = [w for w in description.split() if w.lower() not in _STOP_WORDS]
    description = " ".join(words).strip(" .,!?-–") or "покупка"
    return amount, description


def _build_detail(result: dict, amount: float, verdict: str) -> str:
    lines = [
        "```",
        "━━━━━━━ 📊 Детали ━━━━━━━",
        f"Сумма покупки:   {amount:>10,.2f} сом",
        f"Дневной лимит:   {result['limit']:>10,.1f} сом",
        f"Доступно было:   {result['available']:>10,.2f} сом",
        f"До зарплаты:     {result['days']:>10} дн.",
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