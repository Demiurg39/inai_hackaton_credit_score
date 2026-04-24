"""
main.py — FastAPI application for Credit Scoring API.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import httpx

from config import HOST, PORT
from triton_client import predict_credit, triton_health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreditScoringRequest(BaseModel):
    credit_id: int = Field(..., description="Unique credit application ID")
    age: int = Field(..., description="Borrower's age")
    monthly_income: float = Field(..., description="Monthly income")
    employment_years: float = Field(..., description="Employment years")
    loan_amount: float = Field(..., description="Loan amount")
    loan_term_months: int = Field(..., description="Loan term in months")
    interest_rate: float = Field(..., description="Interest rate")
    past_due_30d: int = Field(..., description="Number of 30+ day delinquencies")
    inquiries_6m: int = Field(..., description="Credit inquiries in last 6 months")

    model_config = {
        "json_schema_extra": {
            "example": {
                "credit_id": 12345,
                "age": 35,
                "monthly_income": 80000.0,
                "employment_years": 5.5,
                "loan_amount": 500000.0,
                "loan_term_months": 24,
                "interest_rate": 15.5,
                "past_due_30d": 0,
                "inquiries_6m": 2,
            }
        }
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Credit Scoring API starting up")
    yield
    logger.info("Credit Scoring API shutting down")


app = FastAPI(
    title="FinGuard Credit Scoring API",
    description="FastAPI wrapper for Triton credit scoring model",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/predict", response_model=dict)
async def predict(request: CreditScoringRequest):
    """
    Run credit scoring inference via Triton.
    Returns raw Triton output — no transformation applied.
    """
    try:
        result = await predict_credit(request.model_dump())
        return result
    except httpx.TimeoutException:
        logger.error("Triton timeout on /predict")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Triton unavailable",
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Triton HTTP error: {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Triton unavailable",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in /predict: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.get("/health")
async def health():
    """
    Health check. Returns status and Triton connectivity.
    """
    triton_ok = await triton_health()
    return {
        "status": "ok",
        "triton": "connected" if triton_ok else "unavailable",
    }


@app.get("/ready")
async def ready():
    """
    Readiness probe. Returns true only if Triton is reachable.
    """
    triton_ok = await triton_health()
    return {"ready": triton_ok}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
