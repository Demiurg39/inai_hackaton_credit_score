FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r finguard && useradd -r -g finguard finguard

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure data directory exists and has correct permissions
RUN mkdir -p /app/data && chown -R finguard:finguard /app/data

USER finguard

# Default env var for Docker
ENV DB_PATH=/app/data/finguard.db

CMD ["python", "bot.py"]
