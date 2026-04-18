from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.whisper import WhisperError


def test_voice_handler_transcribes_and_processes():
    """Voice message → transcribe → _process_purchase called."""
    from handlers.voice import handle_voice

    mock_message = MagicMock()
    mock_message.from_user.id = 123
    mock_message.voice.file_id = "file123"

    mock_file = MagicMock()
    mock_audio = b"audio_bytes"

    mock_bot = AsyncMock()
    mock_bot.get_file = AsyncMock(return_value=mock_file)
    mock_bot.download = AsyncMock(return_value=mock_audio)
    mock_message.bot = mock_bot

    transcript_text = "купил кофе за 300"
    mock_message.with_text = MagicMock(return_value=mock_message)

    with patch("handlers.voice.transcribe", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = transcript_text

        with patch("handlers.voice._process_purchase", new_callable=AsyncMock) as mock_process:
            import asyncio
            asyncio.run(handle_voice(mock_message))

            mock_transcribe.assert_called_once_with(mock_audio)
            mock_message.with_text.assert_called_once_with(transcript_text)
            mock_process.assert_called_once()


def test_voice_handler_download_error():
    """Download fail → error message."""
    from handlers.voice import handle_voice

    mock_message = MagicMock()
    mock_message.voice.file_id = "file123"
    mock_message.answer = AsyncMock()

    mock_bot = AsyncMock()
    mock_bot.get_file = AsyncMock(side_effect=Exception("network error"))
    mock_message.bot = mock_bot

    with patch("handlers.voice.main_menu", "reply_markup"):
        import asyncio
        asyncio.run(handle_voice(mock_message))

        mock_message.answer.assert_called()


def test_voice_handler_whisper_error():
    """Whisper fail → error message."""
    from handlers.voice import handle_voice

    mock_message = MagicMock()
    mock_message.voice.file_id = "file123"
    mock_message.answer = AsyncMock()

    mock_bot = AsyncMock()
    mock_bot.get_file = AsyncMock()
    mock_bot.download = AsyncMock(return_value=b"audio_bytes")
    mock_message.bot = mock_bot

    with patch("handlers.voice.transcribe", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.side_effect = WhisperError("fail")

        with patch("handlers.voice.main_menu", "reply_markup"):
            import asyncio
            asyncio.run(handle_voice(mock_message))

            mock_message.answer.assert_called()