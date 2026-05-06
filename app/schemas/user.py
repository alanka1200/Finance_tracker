"""Pydantic-схемы пользователя для API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserPublic(BaseModel):
    """Безопасное публичное представление пользователя для фронтенда."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
    is_premium: bool
    base_currency: str
    timezone: str
    referral_code: str | None
    notifications_enabled: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Что пользователь может менять в своём профиле."""

    base_currency: str | None = Field(None, pattern=r"^[A-Z]{3,8}$")
    timezone: str | None = None
    notifications_enabled: bool | None = None


class AuthResponse(BaseModel):
    """Ответ на /auth/telegram — выдаём токены и юзера."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
