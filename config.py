"""
config.py — Environment variables for Credit Scoring API.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TRITON_URL: str = os.getenv(
    "TRITON_URL",
    "http://triton:8000/v2/models/score_model/infer"
)
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8080"))
