"""
services/reason_engine.py — Rule-based decision reason builder.

Analyzes evaluation result and produces structured DecisionReason.
No LLM — pure rules with caring-parent semantics.
"""
from typing import TypedDict


class DecisionReason(TypedDict):
    severity: str          # 'block', 'warn', 'ok'
    primary: str            # main message line
    details: list[str]      # supporting reasons
    days_left: float       # days_left_after
    survival: float         # survival_probability fraction
    overshoot: float        # overshoot_pct
    category: str           # category name
    rule_tags: list[str]   # which rules fired, for debugging
    days: int              # days until payday


# Default per-category thresholds (fraction)
_DEFAULT_THRESHOLDS = {
    # Necessities — looser
    "food": (0.35, 0.50),
    "food & drink": (0.35, 0.50),
    "продукты": (0.35, 0.50),
    "транспорт": (0.40, 0.55),
    "transport": (0.40, 0.55),
    "коммуналка": (0.30, 0.45),
    "utilities": (0.30, 0.45),
    "здоровье": (0.35, 0.50),
    "healthcare": (0.35, 0.50),
    "health": (0.35, 0.50),
    # Discretionary — stricter
    "entertainment": (0.60, 0.75),
    "развлечения": (0.60, 0.75),
    "shopping": (0.55, 0.70),
    "покупки": (0.55, 0.70),
    # Default
    "other": (0.52, 0.65),
    "прочее": (0.52, 0.65),
}


def _get_category_thresholds(category: str) -> tuple[float, float]:
    """Return (fuzzy_threshold, survival_threshold) for a category."""
    cat_lower = category.lower().strip()
    for key, vals in _DEFAULT_THRESHOLDS.items():
        if key in cat_lower:
            return vals
    return (0.52, 0.65)  # Default


def build_reason(amount: float, result: dict, category: str) -> DecisionReason:
    """
    Analyze evaluation result and produce structured reason.
    Returns severity 'block', 'warn', or 'ok'.
    """
    fuzzy = result.get("fuzzy_score", 0.0)
    survival = result.get("survival_probability", 0.0)
    overshoot = result.get("overshoot_pct", 0.0)
    days_left = result.get("days_left_after", 0.0)
    days = result.get("days", 1)
    approved = result.get("approved", False)
    limit = result.get("limit", 0.0)
    available = result.get("available", 0.0)
    new_balance = result.get("new_balance", available)
    reserve = result.get("reserve", 0.0)

    rule_tags: list[str] = []
    details: list[str] = []

    fuzzy_thresh, survival_thresh = _get_category_thresholds(category)

    # === SURVIVAL CHECK ===
    if survival < survival_thresh:
        rule_tags.append("low_survival")
        details.append(f"шанс дотянуть до зарплаты — только {survival * 100:.0f}%")
    elif survival < 0.65:
        rule_tags.append("moderate_survival")

    # === OVERSPEND CHECK ===
    if overshoot > 100:
        rule_tags.append("massive_overspend")
        details.append(f"превышение лимита на {overshoot:.0f}% — это очень много")
    elif overshoot > 50:
        rule_tags.append("big_overspend")
        details.append(f"превышение на {overshoot:.0f}% сверх дневного лимита")
    elif overshoot > 20:
        rule_tags.append("moderate_overspend")
        details.append(f"немного сверх лимита — на {overshoot:.0f}%")

    # === DAYS LEFT CHECK ===
    if days_left < 1:
        rule_tags.append("no_buffer")
        details.append("деньги закончатся буквально завтра")
    elif days_left < days * 0.3:
        rule_tags.append("low_buffer")
        details.append(f"хватит всего на {days_left:.1f} дн. из {days}")

    # === CATEGORY-SPECIFIC ===
    cat_lower = category.lower()
    discretionary = any(
        c in cat_lower
        for c in ["entertainment", "развлечения", "shopping", "покупки"]
    )

    if discretionary and overshoot > 30:
        rule_tags.append("discretionary_high_overspend")
        details.append(f"{category} — не критично, можно и подождать")

    # === RESERVE CHECK ===
    if new_balance < reserve * 0.5:
        rule_tags.append("reserve_danger")
        details.append(f"баланс упадёт ниже половины резерва ({reserve * 0.5:,.0f})")
    elif new_balance < reserve:
        rule_tags.append("reserve_touched")
        details.append("баланс упадёт ниже резерва")

    # === SEVERITY DETERMINATION ===
    if new_balance < reserve * 0.5:
        severity = "block"
        primary = _block_primary(amount, category, days_left, days)
    elif survival < survival_thresh and days_left < 2:
        severity = "block"
        primary = _block_primary(amount, category, days_left, days)
    elif survival < survival_thresh:
        severity = "warn"
        primary = _warn_primary(amount, category, days_left, survival, overshoot)
    elif survival < 0.65 or overshoot > 50:
        severity = "warn"
        primary = _warn_primary(amount, category, days_left, survival, overshoot)
    else:
        severity = "ok"
        primary = _ok_primary(amount, category, limit, days_left, days)

    return DecisionReason(
        severity=severity,
        primary=primary,
        details=details,
        days_left=days_left,
        survival=survival,
        overshoot=overshoot,
        category=category or "другое",
        rule_tags=rule_tags,
        days=days,
    )


def _block_primary(amount: float, category: str, days_left: float, days: int) -> str:
    if days_left < 1:
        return f"«{category}» за {amount:,.0f} — денег хватит меньше чем на день"
    if days_left < 2:
        return f"«{category}» за {amount:,.0f} — риск не дотянуть до зарплаты слишком высок"
    return f"«{category}» за {amount:,.0f} — я не могу это одобрить прямо сейчас"


def _warn_primary(
    amount: float, category: str, days_left: float, survival: float, overshoot: float
) -> str:
    return f"«{category}» за {amount:,.0f} — можно, но есть риски о которых стоит знать"


def _ok_primary(amount: float, category: str, limit: float, days_left: float, days: int) -> str:
    pct = int(amount / limit * 100) if limit > 0 else 0
    return f"«{category}» за {amount:,.0f} — в рамках плана ({pct}% лимита)"