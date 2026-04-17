"""
middlewares/onboarding_check.py

BaseMiddleware that intercepts every Message update:
• If the user row doesn't exist yet → creates it silently.
• If the user is not onboarded AND the update is NOT already handled
  by the onboarding FSM → sends a nudge to /start and cancels the update.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.models import create_user, get_user
from states.fsm import OnboardingStates, SettingsStates


# States that are part of FSM flows — we never interrupt these.
_FSM_STATE_GROUPS = (OnboardingStates, SettingsStates)


class OnboardingCheckMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()
        # Cache for users who have already finished onboarding
        self._onboarded_cache: set[int] = set()

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        user_id: int = event.from_user.id

        # If user is in cache, skip DB check entirely
        if user_id in self._onboarded_cache:
            return await handler(event, data)

        # Ensure a user row always exists
        await create_user(user_id)

        user = await get_user(user_id)
        if user and user["onboarded"]:
            # User is set up — update cache and pass through
            self._onboarded_cache.add(user_id)
            return await handler(event, data)

        # User is NOT onboarded yet.
        # Check if they are already inside an FSM state.
        state: FSMContext = data.get("state")
        current_state = await state.get_state() if state else None

        # Allow through if they typed /start or are mid-onboarding FSM
        text = (event.text or "").strip()
        if text == "/start" or (
            current_state
            and any(
                current_state.startswith(g.__name__)
                for g in _FSM_STATE_GROUPS
            )
        ):
            return await handler(event, data)

        # Otherwise, redirect to /start
        await event.answer(
            "👋 Привет! Сначала нужно пройти быструю настройку.\n"
            "Нажми /start, чтобы начать.",
        )
        return  # drop the update
