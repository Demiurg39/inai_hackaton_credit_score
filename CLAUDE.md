# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FinGuard** — Telegram bot that acts as a strict-but-caring financial guardian. Approves or blocks purchases based on daily spending limits derived from balance, reserve, and days until next income.

Entry point: `bot.py`

## Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Configure bot token
cp .env.example .env
# Edit .env and set BOT_TOKEN=<your Telegram bot token>

# Run the bot
python bot.py

# Run tests
pytest tests/ -v
# Single test file
pytest tests/test_calculator.py -v
```

## Architecture

### Handler Flow
Router order in `bot.py` matters — most specific handlers registered first:
1. `start.router` — /start and onboarding FSM
2. `settings.router` — inline keyboard callbacks (registered before purchase)
3. `status.router` — /status and health bar
4. `purchase.router` — catch-all for free-text purchase parsing

### Middleware
`OnboardingCheckMiddleware` intercepts every message. Unboarded users are redirected to /start unless already in an FSM state group (OnboardingStates or SettingsStates). Onboarded users are cached in-memory to skip DB lookups.

### FSM States
- `OnboardingStates` — 3-step setup (balance → reserve → income_date)
- `PurchaseStates` — waits for purchase input after button press
- `SettingsStates` — inline settings update flow

### Database
SQLite via aiosqlite. `database/db.py` manages connection and runs non-destructive migrations on startup to add missing columns.

Key tables:
- `users` — balance, reserve, next_income_date, period_available, period_start_date, per-user spending stats (avg_daily_spend, std_daily_spend, spend_velocity, risk_tolerance)
- `transactions` — amount, description, verdict, created_at
- `user_category_stats` — per-category spending patterns (moving average)
- `user_recurring_spends` — detected recurring transactions with confidence scores

## Financial Logic

### Basic Evaluation (`services/calculator.py`)
```
available = balance - reserve
daily_limit = available / days_until_income
overshoot% = (amount - daily_limit) / daily_limit × 100
approved = overshoot% <= 50
```

### Advanced Evaluation (`services/calculator_advanced.py`)
Uses personalized stats (std_daily_spend, risk_tolerance) with:
- **Fuzzy Logic** — soft scoring (0.0–1.0) based on overshoot%
- **Monte Carlo Simulation** — 2000 simulations of future spending to compute survival probability
- **Risk-adaptive thresholds** — fuzzy_score and survival_probability thresholds shift based on user's risk_tolerance (0.0–1.0)

### Health Bar
```
ideal_available = period_available × (1.0 - days_passed / total_days)
health = actual_available / ideal_available
```

### Forecast
```
average_spend = (period_available - current_available) / days_passed
days_budget_covers = current_available / average_spend
deficit = days_until_income - days_budget_covers
```

## Services

- `calculator.py` — basic purchase evaluation
- `calculator_advanced.py` — personalized evaluation with Monte Carlo
- `llm.py` — verdict message generation (stub, LLM-ready via LLM_URL env var)
- `triton.py` — category prediction via Triton Inference Server (graceful fallback if unavailable)

## Config

`.env` variables:
- `BOT_TOKEN` — required, Telegram bot token
- `LLM_URL` — optional, LLM endpoint for verdict messages
- `TRITON_URL` — optional, Triton inference server URL
- `DB_PATH` — optional, SQLite database path (default: finguard.db)
