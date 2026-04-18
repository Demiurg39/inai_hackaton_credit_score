"""
bot.py — FinGuard entry point.

Run with:  python bot.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db, close_db
from handlers import start, purchase, status, settings, notifications
from middlewares.onboarding_check import OnboardingCheckMiddleware
from middlewares.notification import NotificationMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

async def main() -> None:
    # ── Database ──────────────────────────────────────────────────
    logger.info("Initialising database…")
    await init_db()

    # ── Bot & Dispatcher ──────────────────────────────────────────
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ── Middleware ────────────────────────────────────────────────
    dp.message.middleware(OnboardingCheckMiddleware())
    dp.message.middleware(NotificationMiddleware(lambda uid: 0.0))  # placeholder; real value set at runtime

    # ── Routers (order matters: more specific first) ──────────────
    dp.include_router(start.router)
    dp.include_router(settings.router)   # settings before purchase (has buttons)
    dp.include_router(status.router)
    dp.include_router(notifications.router)
    dp.include_router(purchase.router)   # catch-all purchase parser last

    # ── Start polling ─────────────────────────────────────────────
    logger.info("FinGuard is running… Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await close_db()
        await bot.session.close()
        logger.info("FinGuard stopped.")

if __name__ == "__main__":
    asyncio.run(main())
