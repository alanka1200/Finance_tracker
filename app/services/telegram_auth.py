"""Валидация Telegram WebApp initData по официальному алгоритму.

Док: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

Алгоритм:
1. Парсим initData как querystring → dict.
2. Достаём 'hash' (это контрольная сумма, отдельно).
3. Сортируем оставшиеся пары по ключу, склеиваем "key=value\\n".
   Это data_check_string.
4. secret_key = HMAC-SHA256(key="WebAppData", message=bot_token)
   ⚠️ Внимание: bot_token — это сообщение, "WebAppData" — это ключ.
5. computed_hash = HMAC-SHA256(key=secret_key, message=data_check_string).hex()
6. Сравниваем computed_hash и hash через hmac.compare_digest (constant-time).
7. Проверяем, что auth_date не старее, чем TTL.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, unquote

from loguru import logger
from pydantic import BaseModel

from app.config import settings


class TelegramUser(BaseModel):
    """Структура user из Telegram WebApp initData."""

    id: int
    is_bot: bool = False
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool = False
    allows_write_to_pm: bool = False
    photo_url: str | None = None


class TelegramInitData(BaseModel):
    """Распарсенный initData."""

    user: TelegramUser
    auth_date: int
    query_id: str | None = None
    hash: str
    start_param: str | None = None  # реферальный код, если был

    @property
    def auth_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.auth_date, tz=timezone.utc)


class InvalidInitDataError(Exception):
    """initData не прошла HMAC-проверку или истёк срок."""


def parse_init_data(raw: str) -> dict[str, str]:
    """Парсит querystring-формат, не декодируя значения дважды."""
    # parse_qsl разкодирует значения; для пересчёта хеша нам нужны
    # значения В ТОМ ВИДЕ, в каком они пришли (decode raw URL-encoded только один раз).
    return dict(parse_qsl(raw, keep_blank_values=True, strict_parsing=False))


def _compute_hash(data: dict[str, str], bot_token: str) -> str:
    """Считает ожидаемый хеш по алгоритму Telegram."""
    # Все поля КРОМЕ 'hash', отсортированные по ключу, в формате key=value\n
    pairs = sorted((k, v) for k, v in data.items() if k != "hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in pairs)

    # Шаг 4: secret_key = HMAC-SHA256("WebAppData", bot_token)
    # КЛЮЧ — это "WebAppData", СООБЩЕНИЕ — это bot_token
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    # Шаг 5: computed = HMAC-SHA256(secret_key, data_check_string)
    computed = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return computed


def validate_init_data(
    raw_init_data: str,
    bot_token: str | None = None,
    max_age_seconds: int | None = None,
) -> TelegramInitData:
    """Полностью валидирует initData. Бросает InvalidInitDataError при ошибке.

    Параметры:
        raw_init_data: содержимое window.Telegram.WebApp.initData
        bot_token: переопределение токена (для тестов); по умолчанию из settings
        max_age_seconds: переопределение TTL; по умолчанию из settings
    """
    if not raw_init_data:
        raise InvalidInitDataError("initData пустая")

    bot_token = bot_token or settings.bot_token
    max_age = max_age_seconds if max_age_seconds is not None else settings.telegram_initdata_ttl_seconds

    parsed = parse_init_data(raw_init_data)

    received_hash = parsed.get("hash")
    if not received_hash:
        raise InvalidInitDataError("отсутствует поле hash")

    expected_hash = _compute_hash(parsed, bot_token)

    # Constant-time сравнение
    if not hmac.compare_digest(expected_hash, received_hash):
        logger.warning("HMAC-проверка initData провалилась")
        raise InvalidInitDataError("неверная подпись initData")

    # Проверка срока годности
    auth_date_str = parsed.get("auth_date")
    if not auth_date_str:
        raise InvalidInitDataError("отсутствует auth_date")
    try:
        auth_date = int(auth_date_str)
    except ValueError as e:
        raise InvalidInitDataError("некорректный формат auth_date") from e

    now = int(datetime.now(timezone.utc).timestamp())
    age = now - auth_date
    if age < 0:
        # auth_date из будущего — clock skew или подделка
        raise InvalidInitDataError("auth_date из будущего")
    if age > max_age:
        raise InvalidInitDataError(
            f"initData устарела ({age}s > {max_age}s); пользователю нужно перезапустить Mini App"
        )

    # Парсим вложенный JSON 'user'
    user_raw = parsed.get("user")
    if not user_raw:
        raise InvalidInitDataError("отсутствует поле user")
    try:
        # parse_qsl уже разкодировал URL, поэтому это валидный JSON-строка
        user_data = json.loads(unquote(user_raw)) if "%" in user_raw else json.loads(user_raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise InvalidInitDataError(f"невалидный JSON в user: {e}") from e

    try:
        user = TelegramUser(**user_data)
    except (ValueError, TypeError) as e:
        raise InvalidInitDataError(f"некорректная структура user: {e}") from e

    init_data_kwargs: dict[str, Any] = {
        "user": user,
        "auth_date": auth_date,
        "hash": received_hash,
        "query_id": parsed.get("query_id"),
        "start_param": parsed.get("start_param"),
    }
    return TelegramInitData(**init_data_kwargs)
