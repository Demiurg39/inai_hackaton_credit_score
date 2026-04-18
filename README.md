# FinGuard — Telegram Financial Guard Bot

> A strict-but-caring parent that **approves ✅ or blocks ⛔** every purchase based on your daily spending limit.

---

## How It Works

### The Core Idea

You set up the bot with your current balance, a safety reserve (money you never touch), and your next payday. The bot calculates a **daily spending limit** — the amount you can safely spend each day without running out before payday.

When you ask about a purchase, the bot:
1. Compares it against your daily limit
2. Runs a **Monte Carlo simulation** (2000 scenarios) to estimate the probability of making it to payday
3. Applies **fuzzy scoring** to weigh how much you're overspending
4. Gives a verdict: **approved** (✅) or **blocked** (⛔) with a caring explanation

---

## Algorithms

### 1. Daily Limit Calculation

```
available = balance - reserve
daily_limit = available / days_until_payday
```

If `available = 15,000₽` and `days_until_payday = 10`, your daily limit is `1,500₽`.

### 2. Overshoot Percentage

```
overshoot_pct = (purchase_amount - daily_limit) / daily_limit × 100
```

A `3000₽` purchase against a `1500₽` limit = `100% overshoot`.

### 3. Fuzzy Score (0.0 → 1.0)

Soft scoring that penalizes overspending progressively:

| Overshoot | Fuzzy Score |
|-----------|-------------|
| 0% | 1.0 (perfect) |
| 40% | 0.65 |
| 80% | 0.20 |
| >80% | 0.0–0.15 |

Formula:
```
overshoot ≤ 0%    → score = 1.0
overshoot ≤ 40%   → score = 1.0 - (overshoot/40) × 0.35
overshoot ≤ 80%   → score = 0.65 - ((overshoot-40)/40) × 0.45
overshoot > 80%   → score = max(0.15 - ((overshoot-80)/200) × 0.15, 0.0)
```

### 4. Monte Carlo Simulation

Estimates **survival probability** — the chance you won't run out of money before payday.

1. Take the `remaining_available` amount after the purchase
2. Divide it by remaining days → `mean_daily_after`
3. Use per-user `std_daily_spend` (learned from transaction history) as variation
4. Run 2000 simulations: each day draw a random spend from `N(mean, std)`
5. Count how many simulations survive the full period without going to zero
6. `survival_probability = surviving_sims / 2000`

The simulation is offloaded to a thread pool via `asyncio.to_thread()` so it never blocks the event loop.

### 5. Risk Tolerance Scaling

Each user has a `risk_tolerance` (0.0 = strict, 1.0 = lenient). Thresholds shift based on this:

```
fuzzy_threshold    = 0.52 - (risk_tol - 0.5) × 0.4    → 0.32 (strict) to 0.72 (lenient)
survival_threshold = 0.65 - (risk_tol - 0.5) × 0.5    → 0.40 (strict) to 0.90 (lenient)
```

Final approval: `fuzzy > fuzzy_threshold AND survival > survival_threshold`

### 6. Health Bar (Financial Health)

Answers: "Are we on track with our planned spending pace?"

```
ideal_remaining = period_available × (1 - days_passed / total_days)
health = available / ideal_remaining
```

Example: budgeted 30,000₽ for 30 days. Day 15 → ideal remaining is 15,000₽. If you actually have 10,000₽ left, health = 67%.

### 7. Reserve Recommendation (Phase 3)

When the bot detects recurring expenses (monthly subscriptions, rent, etc.):

```
covered_recurring = sum of all recurring expense amounts
buffer = max(avg_daily_spend × 3, 500₽)   # minimum 500₽ buffer
recommended_reserve = covered_recurring + buffer
```

If no recurring expenses detected: `recommended = balance × 0.15` (15% fallback).

---

## Features

### Purchase Evaluation
- Free-text input: `300 dinner`, `хочу купить кофе за 250`, `1200` (amount only)
- Triton category prediction (e.g., categorizes "стрижка 800" as "Красота")
- Verdict: approved with balance update OR blocked with explanation

### Decision Engine (Phase 2)
Rule-based caring-parent reasoning — **no LLM required**:
- `block` severity when survival probability < 40% or balance would drop below 50% of reserve
- `warn` severity when survival < 65% or overshoot > 50%
- `ok` otherwise

### Playground Mode
Type `🎮 Что если?` to preview any purchase decision **without committing** the transaction or changing your balance.

### Daily Notifications (Phase 3)
Opt-in morning notifications at your preferred time (default 10:00am) with:
- Current balance + daily limit
- Financial health bar
- Encouraging message based on your health level

### Proactive Alerts (Phase 3)
Automatically warns you when:
- Predicted money-run-out date is before your next payday
- A large recurring expense (e.g., rent) is due within 7 days and would breach your budget

### Personalized Stats (Phase 1)
Learns from your transaction history:
- `avg_daily_spend` / `std_daily_spend` — your actual spending pattern
- `spend_velocity` — how your spending rate changes over time
- `risk_tolerance` — configurable in `/settings`
- Recurring expense detection (amount + interval fingerprinting)

---

## Project Structure

```
finguard/
├── bot.py                        # Entry point, router registration
├── config.py                     # BOT_TOKEN from .env
├── database/
│   ├── db.py                    # SQLite init, non-destructive migrations
│   └── models.py                # CRUD: users, transactions, stats
├── handlers/
│   ├── start.py                 # /start — 3-step onboarding FSM
│   ├── purchase.py              # Purchase evaluator + playground mode
│   ├── status.py                # /status — health bar + forecast + reserve rec
│   ├── settings.py              # /settings — inline updates + history
│   └── notifications.py         # /notify — daily notification scheduler
├── services/
│   ├── calculator_advanced.py   # Core logic: fuzzy + Monte Carlo
│   ├── reason_engine.py         # Rule-based verdict reasoning
│   ├── explainer.py            # Caring-parent message formatter
│   ├── reserve_advisor.py       # Reserve recommendation engine
│   ├── proactive_alerts.py      # Alert detection + formatting
│   └── triton.py                # Triton category prediction
├── middlewares/
│   ├── onboarding_check.py      # Redirect unboarded users to /start
│   └── notification.py         # Fires daily notifications on each poll
└── states/
    └── fsm.py                   # FSM state groups
```

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure bot token
cp .env.example .env
# Edit .env and set BOT_TOKEN=<your Telegram bot token>

# Run
python bot.py
```

The SQLite database (`finguard.db`) is created automatically on first run.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Telegram BotFather token |
| `DB_PATH` | ❌ | SQLite path (default: `finguard.db`) |
| `TRITON_URL` | ❌ | Triton Inference Server URL |
| `LLM_URL` | ❌ | LLM endpoint (unused — Phase 2 is rule-based) |
