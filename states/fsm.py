"""
states/fsm.py — FSM state groups for FinGuard.
"""
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    waiting_balance = State()       # Step 1: current balance
    waiting_reserve = State()       # Step 2: emergency reserve
    waiting_income_date = State()   # Step 3: next income date


class PurchaseStates(StatesGroup):
    waiting_purchase_input = State()


class SettingsStates(StatesGroup):
    waiting_new_balance = State()
    waiting_new_reserve = State()
    waiting_new_income_date = State()
    waiting_new_risk_tolerance = State()
