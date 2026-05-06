"""Схемы аналитики и AI-советов."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CategoryBreakdown(BaseModel):
    category_id: int | None
    category_name: str
    category_icon: str
    category_color: str
    total: Decimal
    count: int
    percent: float


class PeriodSummary(BaseModel):
    """Сводка за период."""

    period_start: date
    period_end: date
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal  # income - expense
    transaction_count: int
    by_category_expense: list[CategoryBreakdown]
    by_category_income: list[CategoryBreakdown]


class DailyPoint(BaseModel):
    day: date
    income: Decimal
    expense: Decimal


class TrendData(BaseModel):
    """Тренд для графика."""

    days: list[DailyPoint]


class DashboardData(BaseModel):
    """Всё, что нужно для главного экрана Mini App."""

    balance: Decimal
    income_this_month: Decimal
    expense_this_month: Decimal
    transactions_count: int
    active_goals_count: int
    investments_total_value: Decimal
    referrals_count: int
    last_30_days_trend: list[DailyPoint]
    top_expense_categories: list[CategoryBreakdown]


class AdviceResponse(BaseModel):
    """AI/правило-ориентированный совет."""

    text: str
    source: str  # "groq" | "cerebras" | "gemini" | "rules"
    insights: list[str]  # короткие тезисы для UI
