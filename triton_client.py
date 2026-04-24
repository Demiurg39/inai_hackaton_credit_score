"""
triton_client.py — Triton Inference Server client for credit scoring model.
"""
import logging
from typing import Any

import httpx

from config import TRITON_URL

logger = logging.getLogger(__name__)

TIMEOUT = 5.0


async def predict_credit(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Call Triton /v2/models/score_model/infer with credit features.

    Args:
        inputs: dict with keys matching Triton input names:
            credit_id, age, monthly_income, employment_years,
            loan_amount, loan_term_months, interest_rate,
            past_due_30d, inquiries_6m

    Returns:
        Raw Triton response dict.

    Raises:
        httpx.HTTPStatusError: Triton returns non-2xx.
        httpx.TimeoutException: Triton does not respond within TIMEOUT.
    """
    payload = {
        "inputs": [
            {
                "name": "credit_id",
                "shape": [1],
                "datatype": "INT64",
                "data": [inputs["credit_id"]],
            },
            {
                "name": "age",
                "shape": [1],
                "datatype": "INT64",
                "data": [inputs["age"]],
            },
            {
                "name": "monthly_income",
                "shape": [1],
                "datatype": "FP64",
                "data": [inputs["monthly_income"]],
            },
            {
                "name": "employment_years",
                "shape": [1],
                "datatype": "FP64",
                "data": [inputs["employment_years"]],
            },
            {
                "name": "loan_amount",
                "shape": [1],
                "datatype": "FP64",
                "data": [inputs["loan_amount"]],
            },
            {
                "name": "loan_term_months",
                "shape": [1],
                "datatype": "INT64",
                "data": [inputs["loan_term_months"]],
            },
            {
                "name": "interest_rate",
                "shape": [1],
                "datatype": "FP64",
                "data": [inputs["interest_rate"]],
            },
            {
                "name": "past_due_30d",
                "shape": [1],
                "datatype": "INT64",
                "data": [inputs["past_due_30d"]],
            },
            {
                "name": "inquiries_6m",
                "shape": [1],
                "datatype": "INT64",
                "data": [inputs["inquiries_6m"]],
            },
        ]
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(TRITON_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


async def triton_health() -> bool:
    """
    Check if Triton is reachable.
    Returns True if Triton responds, False otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                TRITON_URL.replace("/v2/models/score_model/infer", "/v2"),
            )
            return resp.status_code == 200
    except Exception as e:
        logger.debug(f"Triton health check failed: {e}")
        return False