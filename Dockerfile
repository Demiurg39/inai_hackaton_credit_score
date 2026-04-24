FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx python-dotenv pydantic joblib

COPY . .

CMD ["python", "main.py"]
