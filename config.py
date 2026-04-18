"""
config.py — Load environment variables for FinGuard bot.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
LLM_URL: str = os.getenv("LLM_URL", "http://localhost:8000/v1/chat")
TRITON_URL: str = os.getenv("TRITON_URL", "http://triton:8000/v2/models/category_model/infer")
WHISPER_TRITON_URL: str = os.getenv("WHISPER_TRITON_URL", "http://triton:8000/v2/models/whisper/infer")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.minimax.io/anthropic")
LLM_MODEL: str = os.getenv("LLM_MODEL", "MiniMax-M2.7")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Copy .env.example to .env and fill it out.")
