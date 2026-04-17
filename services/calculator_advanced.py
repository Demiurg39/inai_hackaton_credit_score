# """
# services/calculator_advanced.py — Advanced financial logic for FinGuard
# Комбо: базовая математика + Fuzzy Logic + Monte Carlo Simulation
# """

# from datetime import date
# from typing import TypedDict
# import numpy as np

# class EvaluationResult(TypedDict):
#     limit: float                    # дневной лимит
#     days: int                       # дней до дохода
#     available: float                # доступно (balance - reserve)
#     overshoot_pct: float            # % превышения
#     approved: bool                  # финальное решение
#     new_balance: float
#     days_left_after: float
#     # === Новые крутые поля ===
#     fuzzy_score: float              # 0.0 = категорически нет → 1.0 = отлично
#     survival_probability: float     # % вероятность дотянуть до дохода (%)
#     risk_level: str                 # 'low', 'medium', 'high', 'critical'
#     days_left_mean: float           # ожидаемое количество дней после покупки

# def evaluate_purchase_advanced(
#     amount: float,
#     balance: float,
#     reserve: float,
#     next_income_date: str,
#     num_simulations: int = 1200,      # количество симуляций (можно уменьшить для скорости)
#     daily_variation_pct: float = 0.25 # 25% естественный разброс трат в день
# ) -> EvaluationResult:
#     """
#     Улучшенная оценка покупки с Fuzzy Logic + Monte Carlo.
#     """
#     today = date.today()
#     income_date = date.fromisoformat(next_income_date)
    
#     # Базовые расчёты (твой оригинальный код)
#     days = max((income_date - today).days, 1)
#     available = max(balance - reserve, 0.0)
#     daily_limit = available / days if days > 0 else 0.0

#     if daily_limit > 0:
#         overshoot_pct = (amount - daily_limit) / daily_limit * 100
#     else:
#         overshoot_pct = float("inf") if amount > 0 else 0.0

#     new_balance = balance - amount
#     remaining_available = max(new_balance - reserve, 0.0)
#     days_left_after = remaining_available / daily_limit if daily_limit > 0 else 0.0

#     # ====================== FUZZY LOGIC ======================
#     # "Родительский" мягкий вердикт
#     if overshoot_pct < 0:
#         fuzzy_score = 1.0
#     elif overshoot_pct <= 30:
#         fuzzy_score = 1.0 - (overshoot_pct / 30) * 0.3
#     elif overshoot_pct <= 70:
#         fuzzy_score = 0.7 - ((overshoot_pct - 30) / 40) * 0.4
#     else:
#         fuzzy_score = max(0.2 - ((overshoot_pct - 70) / 150) * 0.2, 0.0)

#     # ====================== MONTE CARLO ======================
#     if daily_limit > 0 and num_simulations > 0 and remaining_available > 0:
#         mean_daily = available / days
#         std_daily = mean_daily * daily_variation_pct
#         remaining_days = max(days - 1, 1)

#         # Симулируем траты на оставшиеся дни
#         daily_spends = np.random.normal(mean_daily, std_daily, size=(num_simulations, remaining_days))
#         total_future_spend = np.sum(daily_spends, axis=1)

#         survives = (remaining_available >= total_future_spend)
#         survival_probability = float(np.mean(survives))
#     else:
#         survival_probability = 1.0 if new_balance >= reserve else 0.0

#     # ====================== RISK LEVEL ======================
#     if fuzzy_score > 0.85 and survival_probability > 0.90:
#         risk_level = "low"
#     elif fuzzy_score > 0.65 and survival_probability > 0.75:
#         risk_level = "medium"
#     elif fuzzy_score > 0.40 and survival_probability > 0.50:
#         risk_level = "high"
#     else:
#         risk_level = "critical"

#     # Финальное решение — более консервативное и умное
#     approved = (fuzzy_score > 0.50) and (survival_probability > 0.60)

#     return EvaluationResult(
#         limit=round(daily_limit, 2),
#         days=days,
#         available=round(available, 2),
#         overshoot_pct=round(overshoot_pct, 1) if overshoot_pct != float("inf") else float("inf"),
#         approved=approved,
#         new_balance=round(new_balance, 2),
#         days_left_after=round(days_left_after, 1),
#         fuzzy_score=round(fuzzy_score, 3),
#         survival_probability=round(survival_probability * 100, 1),  # в процентах
#         risk_level=risk_level,
#         days_left_mean=round(remaining_available / (available / days), 1) if daily_limit > 0 else days_left_after
#     )



"""
services/calculator_advanced.py — Advanced financial logic for FinGuard
Комбо: базовая математика + Fuzzy Logic + Monte Carlo Simulation
"""

from datetime import date
from typing import TypedDict
import numpy as np


class EvaluationResult(TypedDict):
    limit: float
    days: int
    available: float
    overshoot_pct: float
    approved: bool
    new_balance: float
    days_left_after: float
    fuzzy_score: float          # 0.0 = плохо → 1.0 = отлично
    survival_probability: float # вероятность дотянуть до дохода в %
    risk_level: str             # 'low', 'medium', 'high', 'critical'
    days_left_mean: float


# def evaluate_purchase_advanced(
#     amount: float,
#     balance: float,
#     reserve: float,
#     next_income_date: str,      # "YYYY-MM-DD"
#     num_simulations: int = 1000,   # уменьшил до 1000 для скорости
#     daily_variation_pct: float = 0.25
# ) -> EvaluationResult:
    
#     today = date.today()
#     income_date = date.fromisoformat(next_income_date)
    
#     # === Базовые расчёты (как в твоём старом файле) ===
#     days = max((income_date - today).days, 1)
#     available = max(balance - reserve, 0.0)
#     daily_limit = available / days if days > 0 else 0.0

#     if daily_limit > 0:
#         overshoot_pct = (amount - daily_limit) / daily_limit * 100
#     else:
#         overshoot_pct = float("inf") if amount > 0 else 0.0

#     new_balance = balance - amount
#     remaining_available = max(new_balance - reserve, 0.0)
#     days_left_after = remaining_available / daily_limit if daily_limit > 0 else 0.0

#     # === FUZZY LOGIC (мягкое "родительское" решение) ===
#     if overshoot_pct < 0:
#         fuzzy_score = 1.0
#     elif overshoot_pct <= 30:
#         fuzzy_score = 1.0 - (overshoot_pct / 30) * 0.3
#     elif overshoot_pct <= 70:
#         fuzzy_score = 0.7 - ((overshoot_pct - 30) / 40) * 0.4
#     else:
#         fuzzy_score = max(0.2 - ((overshoot_pct - 70) / 150) * 0.2, 0.0)

#     # # === MONTE CARLO (реалистичный прогноз выживаемости) ===
#     # if daily_limit > 0 and remaining_available > 0:
#     #     mean_daily = available / days
#     #     std_daily = mean_daily * daily_variation_pct
#     #     remaining_days = max(days - 1, 1)

#     #     daily_spends = np.random.normal(mean_daily, std_daily, size=(num_simulations, remaining_days))
#     #     total_future_spend = np.sum(daily_spends, axis=1)

#     #     survives = remaining_available >= total_future_spend
#     #     survival_probability = float(np.mean(survives))
#     # else:
#     #     survival_probability = 1.0 if new_balance >= reserve else 0.0
    
#     # === MONTE CARLO SIMULATION (исправленная версия) ===
#     if daily_limit > 0 and remaining_available > 0:
#         # ← КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ:
#         # Считаем среднюю ежедневную трату на ОСНОВЕ ОСТАТКА после покупки
#         mean_daily_after = remaining_available / days   # или / remaining_days, но days проще и стабильнее
        
#         # Разброс оставляем относительно старого среднего (реалистичнее)
#         std_daily = (available / days) * daily_variation_pct
        
#         remaining_days = max(days - 1, 1)   # дни после сегодняшней покупки

#         # Генерируем симуляции
#         daily_spends = np.random.normal(mean_daily_after, std_daily, size=(num_simulations, remaining_days))
#         total_future_spend = np.sum(daily_spends, axis=1)

#         survives = remaining_available >= total_future_spend
#         survival_probability = float(np.mean(survives))
#     else:
#         survival_probability = 1.0 if new_balance >= reserve else 0.0
#     # === RISK LEVEL ===
#     if fuzzy_score > 0.85 and survival_probability > 0.90:
#         risk_level = "low"
#     elif fuzzy_score > 0.65 and survival_probability > 0.75:
#         risk_level = "medium"
#     elif fuzzy_score > 0.40 and survival_probability > 0.50:
#         risk_level = "high"
#     else:
#         risk_level = "critical"

#     # Финальное решение (умнее, чем просто 50%)
#     approved = (fuzzy_score > 0.50) and (survival_probability > 0.60)

#     return EvaluationResult(
#         limit=round(daily_limit, 2),
#         days=days,
#         available=round(available, 2),
#         overshoot_pct=round(overshoot_pct, 1) if overshoot_pct != float("inf") else float("inf"),
#         approved=approved,
#         new_balance=round(new_balance, 2),
#         days_left_after=round(days_left_after, 1),
#         fuzzy_score=round(fuzzy_score, 3),
#         survival_probability=round(survival_probability * 100, 1),
#         risk_level=risk_level,
#         days_left_mean=round(days_left_after, 1)
#     )
def evaluate_purchase_advanced(
    amount: float,
    balance: float,
    reserve: float,
    next_income_date: str,
    num_simulations: int = 2000,
    daily_variation_pct: float = 0.18
) -> EvaluationResult:
    
    today = date.today()
    income_date = date.fromisoformat(next_income_date)
    
    days = max((income_date - today).days, 1)
    available = max(balance - reserve, 0.0)
    daily_limit = round(available / days, 2) if days > 0 else 0.0

    overshoot_pct = (amount - daily_limit) / daily_limit * 100 if daily_limit > 0 else (float("inf") if amount > 0 else 0.0)

    new_balance = round(balance - amount, 2)
    remaining_available = max(new_balance - reserve, 0.0)
    days_left_after = round(remaining_available / daily_limit, 1) if daily_limit > 0 else 0.0

    # Fuzzy Logic (мягче)
    if overshoot_pct <= 0:
        fuzzy_score = 1.0
    elif overshoot_pct <= 40:
        fuzzy_score = 1.0 - (overshoot_pct / 40) * 0.35
    elif overshoot_pct <= 80:
        fuzzy_score = 0.65 - ((overshoot_pct - 40) / 40) * 0.45
    else:
        fuzzy_score = max(0.15 - ((overshoot_pct - 80) / 200) * 0.15, 0.0)

    # Monte Carlo (исправленный)
    if daily_limit > 0 and remaining_available > 0:
        mean_daily_after = remaining_available / days
        std_daily = (available / days) * daily_variation_pct
        remaining_days = max(days - 1, 1)

        daily_spends = np.random.normal(mean_daily_after, std_daily, size=(num_simulations, remaining_days))
        total_future_spend = np.sum(daily_spends, axis=1)

        survives = remaining_available >= total_future_spend
        survival_probability = float(np.mean(survives))
    else:
        survival_probability = 1.0 if new_balance >= reserve else 0.0

    # Risk level
    if fuzzy_score > 0.85 and survival_probability > 0.85:
        risk_level = "low"
    elif fuzzy_score > 0.65 and survival_probability > 0.70:
        risk_level = "medium"
    elif fuzzy_score > 0.40 and survival_probability > 0.50:
        risk_level = "high"
    else:
        risk_level = "critical"

    approved = (fuzzy_score > 0.52) and (survival_probability > 0.65)

    return EvaluationResult(
        limit=daily_limit,
        days=days,
        available=round(available, 2),
        overshoot_pct=round(overshoot_pct, 1) if overshoot_pct != float("inf") else float("inf"),
        approved=approved,
        new_balance=new_balance,
        days_left_after=days_left_after,
        fuzzy_score=round(fuzzy_score, 3),
        survival_probability=round(survival_probability * 100, 1),
        risk_level=risk_level,
        days_left_mean=days_left_after
    )