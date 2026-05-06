"""Безопасность: выпуск и валидация JWT токенов.

После проверки Telegram initData пользователю выдаётся access JWT (короткий)
и refresh JWT (длинный). Дальнейшие запросы — только с access JWT в заголовке
Authorization.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

TokenType = Literal["access", "refresh"]


class TokenPayload(BaseModel):
    """Содержимое JWT — что положили, то и достанем."""

    sub: str  # user_id (наш внутренний UUID/int как строка)
    telegram_id: int
    type: TokenType
    exp: int  # Unix timestamp


def create_access_token(user_id: int, telegram_id: int) -> str:
    """Короткоживущий токен (по умолчанию 60 минут)."""
    return _create_token(
        user_id, telegram_id, "access", timedelta(minutes=settings.jwt_access_token_ttl_minutes)
    )


def create_refresh_token(user_id: int, telegram_id: int) -> str:
    """Долгоживущий токен (по умолчанию 30 дней). Используется для обновления access."""
    return _create_token(
        user_id, telegram_id, "refresh", timedelta(days=settings.jwt_refresh_token_ttl_days)
    )


def _create_token(
    user_id: int,
    telegram_id: int,
    token_type: TokenType,
    ttl: timedelta,
) -> str:
    expire = datetime.now(timezone.utc) + ttl
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "type": token_type,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType = "access") -> TokenPayload | None:
    """Валидирует подпись + срок жизни + тип. Возвращает None при ошибке."""
    try:
        raw = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None

    try:
        payload = TokenPayload(**raw)
    except (ValueError, TypeError):
        return None

    if payload.type != expected_type:
        return None
    return payload
