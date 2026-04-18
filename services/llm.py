"""
services/llm.py — LLM integration for FinGuard.
Uses MiniMax via Anthropic SDK.
"""
import os
import logging

import anthropic

from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            base_url=ANTHROPIC_BASE_URL,
            api_key=ANTHROPIC_API_KEY,
        )
    return _client


class LLMError(Exception):
    """Raised when LLM parsing fails."""


PARSING_PROMPT = """Пользователь хочет купить: "{text}"
Извлеки сумму и описание покупки.
Верни в формате: сумма|описание
Если сумма не найдена, верни: 0|{text}
Примеры:
"300 кофе" → 300|кофе
"билет на концерт 1500" → 1500|билет на концерт
"хочу купить айфон за 1200" → 1200|айфон
"билет на концерт 26 апреля за 1500" → 1500|билет на концерт"""


async def parse_purchase_with_llm(text: str) -> tuple[float, str]:
    """
    Send text to MiniMax LLM, extract (amount, description).

    Args:
        text: Original user message describing a purchase.

    Returns:
        (amount, description) tuple.

    Raises:
        LLMError: On LLM unavailable, timeout, or invalid response.
    """
    prompt = PARSING_PROMPT.format(text=text)
    try:
        client = _get_client()
        message = client.messages.create(
            model=LLM_MODEL,
            max_tokens=50,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        content = message.content[0].text.strip()
        parts = content.split("|")
        if len(parts) != 2:
            raise LLMError(f"Invalid response format: {content}")
        amount = float(parts[0].strip())
        description = parts[1].strip()
        if amount == 0:
            raise LLMError(f"No amount found in: {content}")
        return amount, description
    except LLMError:
        raise
    except Exception as e:
        logger.error(f"LLM parsing failed: {e}")
        raise LLMError(f"LLM parsing failed: {e}") from e


async def get_verdict_message(purchase: str, amount: float, verdict: str, context: dict) -> str:
    """Stub verdict message — returns hardcoded Russian strings."""
    survival_raw = context.get("survival_probability", 0.5)
    survival = int(survival_raw * 100)
    overshoot = context.get("overshoot_pct", 0)
    amt = f"{amount:,.0f}"

    if verdict == "approved":
        if survival > 85:
            return f"✅ Отлично! {amt} сом на «{purchase}» — можно брать.\nМолодец!"
        else:
            return f"✅ Ладно, разрешаю {amt} на «{purchase}».\nНо будь осторожен, до зарплаты ещё {context.get('days', 5)} дней."
    else:
        if survival < 30:
            return f"🚨 КАТЕГОРИЧЕСКИ НЕТ!\n\n{amt} сом на «{purchase}» — слишком рискованно.\nШанс дотянуть — всего {survival}%. Иди к холодильнику 💸"
        else:
            return f"⛔ Нет, не стоит.\n\n{amt} сом на «{purchase}» — мы превысили лимит на {overshoot:.0f}%.\nДавай найдём что-то дешевле?"