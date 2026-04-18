"""
services/whisper.py — Triton Whisper transcription client.
"""
import base64
import logging

import httpx

from config import WHISPER_TRITON_URL

logger = logging.getLogger(__name__)


class WhisperError(Exception):
    """Raised when Whisper transcription fails."""


async def transcribe(audio_bytes: bytes) -> str:
    """
    Send audio bytes to Triton Whisper endpoint, return transcript text.

    Args:
        audio_bytes: Raw audio file bytes (ogg/mp3/etc from Telegram).

    Returns:
        Transcript string.

    Raises:
        WhisperError: On Triton unavailable, timeout, or transcription failure.
    """
    payload = {
        "inputs": [
            {
                "name": "audio_bytes",
                "shape": [1],
                "datatype": "BYTES",
                "data": [base64.b64encode(audio_bytes).decode()],
            }
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(WHISPER_TRITON_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            transcript_b64 = data["outputs"][0]["data"][0]
            return base64.b64decode(transcript_b64).decode("utf-8").strip()
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise WhisperError(f"Transcription failed: {e}") from e