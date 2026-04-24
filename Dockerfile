FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx python-dotenv pydantic

COPY . .

CMD ["python", "main.py"]