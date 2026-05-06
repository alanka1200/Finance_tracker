"""Pydantic-схемы транзакций."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionKind


class TransactionCreate(BaseModel):
    """Запрос на создание транзакции."""

    kind: TransactionKind
    amount: Decimal = Field(..., gt=0, le=Decimal("999999999999.9999"))
    currency: str = Field(default="RUB", pattern=r"^[A-Z]{3,8}$")
    category_id: int | None = None
    description: str | None = Field(None, max_length=512)
    tags: str | None = Field(None, max_length=256)
    occurred_at: datetime | None = None  # если None — берём now()


class TransactionUpdate(BaseModel):
    """Частичное обновление транзакции."""

    kind: TransactionKind | None = None
    amount: Decimal | None = Field(None, gt=0)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3,8}$")
    category_id: int | None = None
    description: str | None = Field(None, max_length=512)
    tags: str | None = Field(None, max_length=256)
    occurred_at: datetime | None = None


class TransactionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    kind: TransactionKind
    amount: Decimal
    currency: str
    category_id: int | None
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None
    description: str | None
    tags: str | None
    occurred_at: datetime
    created_at: datetime


class TransactionList(BaseModel):
    """Пагинированный список транзакций."""

    items: list[TransactionPublic]
    total: int
    page: int
    page_size: int
    has_more: bool
