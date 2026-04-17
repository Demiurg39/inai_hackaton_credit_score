"""
services/triton.py — Triton Inference Server client for FinGuard.
"""
import logging

import httpx

from config import TRITON_URL

logger = logging.getLogger(__name__)


async def predict_category(text: str) -> str | None:
    """
    Query Triton for a category prediction given transaction text.

    Args:
        text: Transaction description (e.g., "coffee", "обед").

    Returns:
        Category string if successful, None if Triton is unavailable.
    """
    payload = {
        "inputs": [
            {
                "name": "TEXT",
                "shape": [1],
                "datatype": "BYTES",
                "data": [text],
            }
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(TRITON_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["outputs"][0]["data"][0]
    except Exception as e:
        logger.error(f"Triton inference failed: {e}")
        return None