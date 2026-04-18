import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.whisper import transcribe, WhisperError


def test_transcribe_returns_text():
    """Valid audio bytes → Triton → transcript string."""
    audio = b"fake ogg audio bytes"
    transcript_text = "купил кофе за 300"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "outputs": [{
            "name": "transcript",
            "data": [base64.b64encode(transcript_text.encode()).decode()]
        }]
    })

    with patch("services.whisper.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_instance

        result = asyncio.run(transcribe(audio))

        assert result == transcript_text


def test_transcribe_whisper_error():
    """Triton unavailable → raises WhisperError."""
    with patch("services.whisper.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value.post.side_effect = Exception("connection refused")
        mock_cls.return_value = mock_instance

        with pytest.raises(WhisperError):
            asyncio.run(transcribe(b"audio"))