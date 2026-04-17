FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir aiogram aiosqlite httpx python-dotenv

COPY . .

CMD ["python", "bot.py"]