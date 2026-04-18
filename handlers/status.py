"""
handlers/status.py — /status command and "📊 Статус" button.
"""
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from database.models import get_user, get_user_stats, get_recurring_spends
from keyboards.reply import main_menu
from services.calculator import evaluate_purchase
from services.reserve_advisor import compute_recommended_reserve

router = Router()


@router.message(Command("status"))
@router.message(F.text == "📊 Статус")
async def cmd_status(message: Message) -> None:
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user or not user["onboarded"]:
        await message.answer(
            "❌ Ты ещё не настроил FinGuard. Начни с /start",
            reply_markup=main_menu,
        )
        return

    balance = user["balance"]
    reserve = user["reserve"]
    income_date_iso = user["next_income_date"]

    period_start_date_iso = user["period_start_date"]
    period_available = user["period_available"]

    result = evaluate_purchase(0, balance, reserve, income_date_iso)
    days = result["days"]
    limit = result["limit"]
    available = result["available"]

    today = date.today()
    income_date = date.fromisoformat(income_date_iso)
    try:
        start_date = date.fromisoformat(period_start_date_iso)
    except (ValueError, TypeError):
        start_date = today

    total_days = max((income_date - start_date).days, 1)
    days_passed = max((today - start_date).days, 0)

    # Financial health: actual available vs ideal available
    ideal_available = period_available * (1.0 - (days_passed / total_days))
    ideal_available = max(ideal_available, 0.0)

    if ideal_available > 0:
        health_ratio = available / ideal_available
    else:
        health_ratio = 1.0 if available >= 0 else 0.0

    bar = _health_bar(health_ratio)

    # Forecast based on historical average spend
    spent = max(period_available - available, 0.0)
    days_spent_for_avg = max(days_passed, 1)
    average_spend = spent / days_spent_for_avg

    forecast = _forecast(available, average_spend, days)

    user_stats = await get_user_stats(user_id)
    recurring = await get_recurring_spends(user_id)

    # Show learned spend pattern
    if user_stats and user_stats["avg_daily_spend"] > 0:
        stats_lines = (
            f"  📊 Твой паттерн: `{user_stats['avg_daily_spend']:,.0f}` "
            f"± `{user_stats['std_daily_spend']:,.0f}` /день"
        )
    else:
        stats_lines = ""

    # Show recurring spends
    recurring_lines = ""
    for r in recurring:
        try:
            next_dt = date.fromisoformat(r["next_expected"])
            days_until = (next_dt - today).days
            recurring_lines += (
                f"\n  🔁 `{r['avg_amount']:,.0f}` / `{r['category']}` "
                f"— через `{days_until}` дн. (дов.{r['confidence']:.0%})"
            )
        except (ValueError, TypeError, KeyError):
            pass

    # Recommended reserve section
    reserve_lines = []
    if recurring:
        recurring_list = [{
            "amount": r["avg_amount"],
            "interval_days": r["interval_days"],
            "confidence": r["confidence"],
            "category": r["category"],
        } for r in recurring]

        rec = compute_recommended_reserve(
            balance=user["balance"],
            current=user["reserve"],
            recurring_spends=recurring_list,
            avg_daily_spend=user_stats.get("avg_daily_spend", 0.0) if user_stats else 0.0,
        )

        if rec["current"] < rec["recommended"] * 0.9:
            reserve_lines.append("")
            reserve_lines.append(f"📈 Рекомендуемый резерв: {rec['recommended']:,.0f}₽")
            for b in rec["breakdown"]:
                reserve_lines.append(f"  {b}")
            reserve_lines.append("")
            reserve_lines.append(f"🔗 [📈 Поднять до {rec['recommended']:,.0f}₽?]")

    status_text = (
        f"📊 *Твой финансовый статус*\n\n"
        f"  💰 Баланс:        `{balance:,.2f}`\n"
        f"  🛡 Резерв:        `{reserve:,.2f}`\n"
        f"  ✅ Доступно:      `{available:,.2f}`\n"
        f"  🎯 Дневной лимит: `{limit:,.2f}`\n"
        f"  📅 До зарплаты:   `{days}` дн. "
        f"(_{ income_date.strftime('%d.%m.%Y')}_)\n\n"
        f"💚 Финансовое здоровье:\n{bar}\n\n"
        f"{forecast}"
        f"{stats_lines}"
        f"{recurring_lines}"
        + "".join(reserve_lines)
    )

    await message.answer(
        f"📊 *Твой финансовый статус*\n\n"
        f"  💰 Баланс:        `{balance:,.2f}`\n"
        f"  🛡 Резерв:        `{reserve:,.2f}`\n"
        f"  ✅ Доступно:      `{available:,.2f}`\n"
        f"  🎯 Дневной лимит: `{limit:,.2f}`\n"
        f"  📅 До зарплаты:   `{days}` дн. "
        f"(_{ income_date.strftime('%d.%m.%Y')}_)\n\n"
        f"💚 Финансовое здоровье:\n{bar}\n\n"
        f"{forecast}"
        f"{stats_lines}"
        f"{recurring_lines}",
        parse_mode="Markdown",
        reply_markup=main_menu,
    )


# ─────────────────────────── Helpers ──────────────────────────────

def _health_bar(ratio: float, length: int = 12) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    pct = int(ratio * 100)
    emoji = "🟢" if ratio > 0.6 else "🟡" if ratio > 0.3 else "🔴"
    return f"{emoji} `[{bar}]` {pct}%"


def _forecast(available: float, average_spend: float, days_until_income: int) -> str:
    if average_spend <= 0:
        return "✅ *Прогноз:* Твои средние траты нулевые. Денег до зарплаты точно хватит! 🎉"

    days_budget_covers = available / average_spend
    deficit = days_until_income - days_budget_covers

    if deficit <= 0:
        return (
            f"✅ *Прогноз:* При твоём среднем расходе (`{average_spend:,.2f}`/день) "
            f"деньги дотянут до зарплаты. Запас: `{abs(deficit):.1f}` дн. 🎉"
        )
    else:
        return (
            f"⚠️ *Прогноз:* При текущих тратах (`{average_spend:,.2f}`/день) "
            f"деньги кончатся через `{days_budget_covers:.1f}` дн. — за "
            f"`{deficit:.1f}` дн. до зарплаты.\n"
            f"Сократи расходы до `{available / days_until_income:,.2f}` в день!"
        )
