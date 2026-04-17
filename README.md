# FinGuard 🛡 — Telegram Financial Guard Bot

> A strict-but-caring parent that **approves ✅ or blocks ⛔** every purchase based on your daily spending limit.

---

## Quick Start

```bash
# 1. Clone / enter the project
cd finguard

# 2. Create & activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your token
cp .env.example .env
# edit .env and set BOT_TOKEN=<your Telegram bot token>

# 5. Run
python bot.py
```

The SQLite database (`finguard.db`) is created automatically on first run.

---

## Project Structure

```
finguard/
├── bot.py                     # Entry point — starts long-polling
├── config.py                  # Loads BOT_TOKEN / LLM_URL from .env
├── .env.example               # Copy to .env and fill in
├── requirements.txt
├── database/
│   ├── db.py                  # SQLite init + get_db()
│   └── models.py              # CRUD for users & transactions
├── handlers/
│   ├── start.py               # /start + FSM onboarding (3 steps)
│   ├── purchase.py            # Free-text purchase evaluator
│   ├── status.py              # /status — health bar + forecast
│   └── settings.py            # /settings — inline update + history
├── services/
│   ├── calculator.py          # Core math: evaluate_purchase()
│   └── llm.py                 # Verdict messages (stub, LLM-ready)
├── states/
│   └── fsm.py                 # OnboardingStates, PurchaseStates, SettingsStates
├── keyboards/
│   └── reply.py               # Main menu ReplyKeyboardMarkup
└── middlewares/
    └── onboarding_check.py    # Redirect unboarded users to /start
```

---

## Core Algorithm & Financial Logic

В боте работают три основные метрики, позволяющие честно отслеживать финансовые успехи. Вся логика базируется на метриках `period_available` (изначальный бюджет на месяц) и `period_start_date`.

### 1. Purchase Evaluation (Оценка конкретной покупки)
Каждая транзакция проходит через `calculator_advanced.py`.
```python
available = balance - reserve
daily_limit = available / days_until_income
overshoot% = (amount - daily_limit) / daily_limit × 100
```
**Суть:** Бот оценивает, выдержит ли текущий баланс покупку, если оставшиеся деньги "размазать" поровну на оставшиеся дни. Расчет обогащен *Fuzzy Logic* (мягким скорингом) и *Monte Carlo Simulation* (прогнозом вероятности дожить до зарплаты) для вынесения итоговых вердиктов Approved/Blocked.

### 2. Financial Health (Здоровье / Healthbar)
Отвечает на вопрос: **Идем ли мы по графику расходов?**
```python
total_days = next_income_date - period_start_date
days_passed = today - period_start_date
# Сколько реально должно было остаться на счету к этому дню:
ideal_available = period_available * (1.0 - (days_passed / total_days))
health = current_available / ideal_available
```
**Кейс для понимания:**
Вы настроили бота: 30 000 руб. на 30 дней.
Прошло 15 дней. В идеальном мире равномерных расходов у вас должно было остаться ровно `15 000 руб.` (`ideal_available`).
* Если у вас по факту осталось 15 000 руб. ➔ Здоровье 100%
* Если осталось 7 500 руб. (сорили деньгами) ➔ Здоровье 50% (полоска покраснеет)
* Если осталось 25 000 руб. (экономили) ➔ Здоровье 100% (у вас запас прочности)

### 3. Forecast (Прогноз до зарплаты)
Рассчитывается на основе вашей **реальной исторической скорости трат**, а не абстрактного лимита.
```python
spent = period_available - current_available
average_spend = spent / days_passed
days_budget_covers = current_available / average_spend
deficit = days_until_income - days_budget_covers
```
**Кейс для понимания:**
Тот же бюджет 30 000 руб. на 30 дней.
Прошло 10 дней. У вас осталось всего 10 000 руб. (потратили 20 000 руб.).
Ваш средний расход `average_spend = 2000 руб./день`.
Осталось 10 000 руб. Если продолжить так же, денег хватит на `10000 / 2000 = 5 дней`.
Но до зарплаты ещё 20 дней! Бот честно скажет: *"Денег хватит всего на 5 дней — за 15 дней до зарплаты!"*

---

## Demo Scenarios

Set up with **balance = 2000, reserve = 500, income in 5 days → limit = 300/day**

| Input | Expected |
|---|---|
| `250 обед` | ✅ Approved — within limit |
| `1200 steam` | ⛔ Blocked — 300% over limit |
| `/status` | 📊 Health bar + days-left forecast |

---

## Input Formats Supported

```
300 кофе        →  amount=300  description="кофе"
кофе 300        →  amount=300  description="кофе"
300             →  amount=300  description="покупка"
хочу купить кофе за 300  →  same result
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Your BotFather token |
| `LLM_URL` | ❌ | Real LLM endpoint (future use) |

---

## LLM Integration (Future)

`services/llm.py` has the full async signature ready.  
Uncomment the `httpx` block and point `LLM_URL` at your model endpoint.
