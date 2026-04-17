"""
services/llm.py — LLM integration stub for FinGuard verdict messages.

When you're ready to plug in a real LLM, uncomment the httpx block
and remove or wrap the stub section.
"""
from __future__ import annotations

# TODO: Uncomment when integrating a real LLM endpoint.
# import httpx
# from config import LLM_URL


# async def get_verdict_message(
#     purchase: str,
#     amount: float,
#     verdict: str,       # "approved" or "blocked"
#     context: dict,      # keys: overshoot_pct, days, days_left_after, limit
# ) -> str:
#     """
#     Return a personality-rich verdict message for the user.

#     Stub implementation returns hardcoded templates based on verdict severity.
#     Signature is kept identical to what a real LLM call would require.

#     Real LLM call (commented out):
#     ---
#     # async with httpx.AsyncClient(timeout=10) as client:
#     #     payload = {
#     #         "model": "finguard-guardian-v1",
#     #         "messages": [
#     #             {"role": "system", "content": SYSTEM_PROMPT},
#     #             {"role": "user", "content": user_prompt},
#     #         ]
#     #     }
#     #     resp = await client.post(LLM_URL, json=payload)
#     #     resp.raise_for_status()
#     #     return resp.json()["choices"][0]["message"]["content"]
#     ---
#     """
#     overshoot: float = context.get("overshoot_pct", 0)
#     days: int = context.get("days", 1)
#     days_left: float = context.get("days_left_after", 0)
#     limit: float = context.get("limit", 0)
#     amt = f"{amount:,.0f}"

#     if verdict == "approved":
#         if overshoot <= 25:
#             # Comfortable approval
#             return (
#                 f"✅ Окей, {amt} на «{purchase}» — в рамках разумного. "
#                 f"Лимит на сегодня: {limit:,.0f}. Не расслабляйся! 😤"
#             )
#         else:
#             # Borderline approval (25–50 % over)
#             return (
#                 f"✅ Ладно... разрешаю. Но это последняя крупная трата сегодня. "
#                 f"Ты превысил дневной лимит на {overshoot:.0f}%. Я слежу. 👀"
#             )
#     else:
#         # blocked
#         if overshoot <= 100:
#             # 50–100 % over limit
#             return (
#                 f"⛔ {amt} на «{purchase}»?! Это на {overshoot:.0f}% выше твоего "
#                 f"дневного лимита ({limit:,.0f}). До получки {days} дн. "
#                 f"Серьёзно подумай о своих жизненных выборах. 🤦"
#             )
#         else:
#             # 100 %+ over limit — critical
#             return (
#                 f"🚨 КАТЕГОРИЧЕСКИ НЕТ. Если купишь это, денег хватит ещё на "
#                 f"{max(days_left, 0):.1f} дн. — а до зарплаты {days} дн. "
#                 f"Положи телефон и открой холодильник. 💸"
#             )


# async def get_verdict_message(
#     purchase: str,
#     amount: float,
#     verdict: str,           # "approved" или "blocked"
#     context: dict           # теперь сюда будем класть весь result
# ) -> str:
    
#     overshoot = context.get("overshoot_pct", 0)
#     days = context.get("days", 1)
#     survival = context.get("survival_probability", 50)
#     risk = context.get("risk_level", "medium")
#     fuzzy = context.get("fuzzy_score", 0.5)
#     limit = context.get("limit", 0)
#     days_left = context.get("days_left_after", 0)

#     amt = f"{amount:,.0f}"

#     if verdict == "approved":
#         if fuzzy > 0.85:
#             return (f"✅ Отлично, {amt} на «{purchase}» — полностью в рамках! "
#                     f"Дневной лимит: {limit:,.0f} сом. Молодец, продолжай в том же духе 😤")
#         elif fuzzy > 0.65:
#             return (f"✅ Ладно, разрешаю {amt} на «{purchase}». "
#                     f"Но это уже близко к лимиту. Я слежу за тобой 👀")
#         else:
#             return (f"✅ Хорошо, бери. Но вероятность дотянуть до зарплаты всего {survival}%. "
#                     f"Не расслабляйся.")
    
#     else:  # blocked
#         if risk == "critical":
#             return (f"🚨 КАТЕГОРИЧЕСКИ НЕТ! {amt} на «{purchase}» — это критический риск. "
#                     f"Шанс дотянуть до получки всего {survival}%. "
#                     f"Положи телефон и иди к холодильнику 💸")
#         elif risk == "high":
#             return (f"⛔ Нет, брат. {amt} на «{purchase}» — это слишком. "
#                     f"Мы превысили лимит на {overshoot:.0f}%. "
#                     f"Давай подумаем о чём-то подешевле?")
#         else:
#             return (f"⛔ Не стоит. Если купишь это, вероятность выжить до зарплаты — всего {survival}%. "
#                     f"Давай найдём альтернативу.")
async def get_verdict_message(
    purchase: str,
    amount: float,
    verdict: str,
    context: dict
) -> str:
    
    overshoot = context.get("overshoot_pct", 0)
    survival = context.get("survival_probability", 50)
    risk = context.get("risk_level", "medium")
    fuzzy = context.get("fuzzy_score", 0.5)
    limit = context.get("limit", 0)
    days_left = context.get("days_left_after", 0)
    amt = f"{amount:,.0f}"

    if verdict == "approved":
        if fuzzy > 0.85:
            return (f"✅ Отлично! {amt} сом на «{purchase}» — полностью в рамках. "
                    f"Молодец, держишься 👍")
        elif fuzzy > 0.65:
            return (f"✅ Ладно, разрешаю {amt} на «{purchase}». "
                    f"Но уже близко к лимиту. Я за тобой слежу 👀")
        else:
            return (f"✅ Хорошо, бери. Но вероятность дотянуть до зарплаты — {survival}%. "
                    f"Не расслабляйся слишком сильно.")

    else:  # blocked
        if risk == "critical" or survival < 40:
            return (f"🚨 КАТЕГОРИЧЕСКИ НЕТ! {amt} на «{purchase}» — это очень рискованно. "
                    f"Шанс дотянуть до получки всего {survival}%. "
                    f"Положи телефон и иди лучше к холодильнику 💸")
        elif risk == "high" or overshoot > 80:
            return (f"⛔ Нет, братан. {amt} на «{purchase}» — сильно превышаем лимит ({overshoot:.0f}%). "
                    f"Давай найдём вариант подешевле?")
        else:
            return (f"⛔ Не стоит пока. Если купишь это, вероятность выжить до зарплаты — всего {survival}%. "
                    f"Давай подумаем об альтернативе.")