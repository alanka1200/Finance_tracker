"""Тесты валидации Telegram initData. Проверяем HMAC + защиту от подделок."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.services.telegram_auth import (
    InvalidInitDataError,
    validate_init_data,
)

# Тестовый токен бота. В реальной жизни — из @BotFather
BOT_TOKEN = "1234567890:TESTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_valid_init_data(
    user_data: dict | None = None,
    auth_date: int | None = None,
    bot_token: str = BOT_TOKEN,
    extra: dict | None = None,
) -> str:
    """Генерит корректную initData строку, как это делает Telegram."""
    user = user_data or {
        "id": 12345,
        "first_name": "Тест",
        "username": "test_user",
        "language_code": "ru",
        "is_premium": False,
    }
    auth = auth_date if auth_date is not None else int(time.time())

    data = {
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
        "auth_date": str(auth),
        "query_id": "AAH123456789",
    }
    if extra:
        data.update(extra)

    # Алгоритм Telegram
    pairs = sorted(data.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in pairs)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    data["hash"] = h
    return urlencode(data)


def test_valid_init_data_passes():
    """Корректная initData с правильным хешем — должна пройти."""
    init_data = _make_valid_init_data()
    parsed = validate_init_data(init_data, bot_token=BOT_TOKEN)
    assert parsed.user.id == 12345
    assert parsed.user.first_name == "Тест"
    assert parsed.user.username == "test_user"


def test_invalid_hash_rejected():
    """initData с подделанным хешем — отклоняется."""
    init_data = _make_valid_init_data()
    # Подменяем хеш
    bad = init_data.replace("hash=", "hash=00000000")
    with pytest.raises(InvalidInitDataError):
        validate_init_data(bad, bot_token=BOT_TOKEN)


def test_modified_user_rejected():
    """Если изменить любое поле — хеш не сойдётся."""
    init_data = _make_valid_init_data()
    # После urlencode кавычки закодированы как %22, а двоеточие как %3A
    # Подменяем id пользователя в URL-encoded виде:
    # %22id%22%3A12345 → %22id%22%3A99999
    tampered = init_data.replace("%3A12345", "%3A99999")
    assert tampered != init_data, "Подмена не произошла — проверь формат"
    with pytest.raises(InvalidInitDataError):
        validate_init_data(tampered, bot_token=BOT_TOKEN)


def test_expired_init_data_rejected():
    """initData старше TTL — отклоняется."""
    old_time = int(time.time()) - 100000  # ~28 часов назад
    init_data = _make_valid_init_data(auth_date=old_time)
    with pytest.raises(InvalidInitDataError, match="устарела"):
        validate_init_data(init_data, bot_token=BOT_TOKEN, max_age_seconds=86400)


def test_future_auth_date_rejected():
    """initData с auth_date из будущего — отклоняется (защита от clock skew атак)."""
    future = int(time.time()) + 1000
    init_data = _make_valid_init_data(auth_date=future)
    with pytest.raises(InvalidInitDataError, match="будущего"):
        validate_init_data(init_data, bot_token=BOT_TOKEN)


def test_empty_init_data_rejected():
    with pytest.raises(InvalidInitDataError):
        validate_init_data("", bot_token=BOT_TOKEN)


def test_missing_hash_rejected():
    """initData без хеша — отклоняется."""
    init_data = "user=%7B%22id%22%3A1%7D&auth_date=1234567890"
    with pytest.raises(InvalidInitDataError, match="hash"):
        validate_init_data(init_data, bot_token=BOT_TOKEN)


def test_wrong_bot_token_rejected():
    """Если хеш считался с одним токеном, а валидация с другим — отклоняется."""
    init_data = _make_valid_init_data(bot_token="another:DIFFERENT_TOKEN_HERE")
    with pytest.raises(InvalidInitDataError):
        validate_init_data(init_data, bot_token=BOT_TOKEN)


def test_start_param_extracted():
    """start_param (реферальный код) извлекается корректно."""
    init_data = _make_valid_init_data(extra={"start_param": "ABCD1234"})
    parsed = validate_init_data(init_data, bot_token=BOT_TOKEN)
    assert parsed.start_param == "ABCD1234"
