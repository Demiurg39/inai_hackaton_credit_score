"""
services/explainer.py — Caring parent text formatter.

Takes a DecisionReason and produces human-readable Russian text.
Tone: protective, warm, honest but supportive. Not corporate.
"""
from services.reason_engine import DecisionReason


def explain(reason: DecisionReason, amount: float, description: str) -> str:
    """
    Format a DecisionReason as caring parent text.
    """
    severity = reason["severity"]

    if severity == "block":
        return _explain_block(reason, amount, description)
    elif severity == "warn":
        return _explain_warn(reason, amount, description)
    else:
        return _explain_ok(reason, amount, description)


def _explain_block(reason: DecisionReason, amount: float, description: str) -> str:
    amt = f"{amount:,.0f}"
    days_left = reason["days_left"]
    survival_pct = int(reason["survival"] * 100)
    overshoot_pct = reason["overshoot"]
    details = reason["details"]
    days = reason.get("days", 1)
    primary = reason["primary"]

    detail_lines = "\n".join(f"• {d}" for d in details[:3]) if details else ""

    return (
        f"🤔 Подожди-ка, «{description}» за {amt} — тут всё непросто.\n\n"
        f"Основная причина: {primary}\n\n"
        f"Что это значит:\n"
        f"• Хватит примерно на {days_left:.1f} дн. — а до зарплаты {days} дн.\n"
        f"• Шанс дотянуть до зарплаты — около {survival_pct}%\n"
        f"• Превышение лимита на {overshoot_pct:.0f}%\n\n"
        f"{detail_lines}\n\n"
        f"Я понимаю, что хочется. Но давай посмотрим на картину целиком — "
        f"ты сказал мне следить за тем, чтобы деньги не кончились раньше зарплаты. "
        f"Это именно тот случай, когда стоит подождать. 💜"
    )


def _explain_warn(reason: DecisionReason, amount: float, description: str) -> str:
    amt = f"{amount:,.0f}"
    days_left = reason["days_left"]
    survival_pct = int(reason["survival"] * 100)
    overshoot_pct = reason["overshoot"]
    details = reason["details"]
    days = reason.get("days", 1)

    detail_lines = "\n".join(f"• {d}" for d in details[:3]) if details else ""

    return (
        f"💭 «{description}» за {amt} — можно, но давай я объясню что происходит.\n\n"
        f"• Превышение лимита на {overshoot_pct:.0f}%\n"
        f"• Хватит на {days_left:.1f} дн. из {days} дн.\n"
        f"• Твой прогноз выживаемости: {survival_pct}%\n\n"
        f"{detail_lines}\n\n"
        f"Ты вправе решать сам — я просто предупреждаю, чтобы ты знал(а) что почём. "
        f"Если хочешь подождать до завтра — шансы будут лучше. 💜"
    )


def _explain_ok(reason: DecisionReason, amount: float, description: str) -> str:
    amt = f"{amount:,.0f}"
    limit = reason.get("limit", 0.0)
    days_left = reason["days_left"]
    days = reason.get("days", 1)
    limit_pct = int(amount / limit * 100) if limit > 0 else 0

    return (
        f"✅ Давай! «{description}» за {amt} — в рамках того, что мы запланировали.\n\n"
        f"• Лимит на сегодня: {limit:,.0f} — ты используешь {limit_pct}%\n"
        f"• Хватит ещё на {days_left:.1f} дн.\n"
        f"• До зарплаты: {days} дн.\n\n"
        f"Всё в порядке, держись в этом темпе. 💪"
    )