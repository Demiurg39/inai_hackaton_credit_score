"""
handlers/voice.py — Voice message transcription via Whisper.
"""
import logging

from aiogram import F, Router
from aiogram.types import Message

from handlers.purchase import _process_purchase
from services.whisper import transcribe, WhisperError
from keyboards.reply import main_menu

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """
    Download voice message, transcribe via Whisper Triton, process as purchase.
    """
    try:
        file = await message.bot.get_file(message.voice.file_id)
        audio_bytes = await message.bot.download(file)
    except Exception as e:
        logger.error(f"Voice download failed: {e}")
        await message.answer(
            "❌ Ошибка загрузки голосового. Попробуй ещё раз.",
            reply_markup=main_menu,
        )
        return

    try:
        transcript = await transcribe(audio_bytes)
    except WhisperError:
        await message.answer(
            "❌ Не удалось распознать голос. Попробуй текстом.",
            reply_markup=main_menu,
        )
        return

    if not transcript:
        await message.answer(
            "❌ Не удалось распознать голос. Попробуй текстом.",
            reply_markup=main_menu,
        )
        return

    await _process_purchase(message.with_text(transcript))