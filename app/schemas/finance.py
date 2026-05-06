"""Схемы категорий, целей, инвестиций."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.category import CategoryKind
from app.models.goal import GoalPriority, GoalStatus
from app.models.investment import InvestmentType


# ===== Категории =====
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    kind: CategoryKind
    icon: str = Field(default="💰", max_length=8)
    color: str = Field(default="#40a7e3", pattern=r"^#[0-9a-fA-F]{6}$")
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    icon: str | None = Field(None, max_length=8)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    sort_order: int | None = None


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: CategoryKind
    icon: str
    color: str
    is_system: bool
    sort_order: int


# ===== Цели =====
class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(None, max_length=512)
    target_amount: Decimal = Field(..., gt=0)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="RUB", pattern=r"^[A-Z]{3,8}$")
    deadline: date | None = None
    category_label: str | None = Field(None, max_length=64)
    icon: str = Field(default="🎯", max_length=8)
    priority: GoalPriority = GoalPriority.MEDIUM


class GoalUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=512)
    target_amount: Decimal | None = Field(None, gt=0)
    current_amount: Decimal | None = Field(None, ge=0)
    deadline: date | None = None
    category_label: str | None = None
    icon: str | None = None
    priority: GoalPriority | None = None
    status: GoalStatus | None = None


class GoalContribution(BaseModel):
    """Пополнение цели."""

    amount: Decimal = Field(..., gt=0)
    comment: str | None = Field(None, max_length=256)


class GoalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    deadline: date | None
    completed_at: datetime | None
    category_label: str | None
    icon: str
    priority: GoalPriority
    status: GoalStatus
    progress_percent: float
    remaining: Decimal
    created_at: datetime


# ===== Инвестиции =====
class InvestmentCreate(BaseModel):
    type: InvestmentType
    name: str = Field(..., min_length=1, max_length=128)
    ticker: str | None = Field(None, max_length=32)
    purchase_amount: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    purchase_price: Decimal | None = Field(None, gt=0)
    purchase_date: date
    currency: str = Field(default="RUB", pattern=r"^[A-Z]{3,8}$")
    notes: str | None = Field(None, max_length=512)


class InvestmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    ticker: str | None = None
    quantity: Decimal | None = Field(None, gt=0)
    current_price: Decimal | None = Field(None, gt=0)
    notes: str | None = None


class InvestmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: InvestmentType
    name: str
    ticker: str | None
    purchase_amount: Decimal
    quantity: Decimal
    purchase_price: Decimal | None
    purchase_date: date
    current_price: Decimal | None
    current_value: Decimal | None
    currency: str
    notes: str | None
    profit_loss: Decimal
    profit_loss_percent: float
    created_at: datetime
